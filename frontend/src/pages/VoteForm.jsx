// frontend/src/pages/VoteForm.jsx
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './VoteForm.css';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const VoteForm = () => {
  const [year, setYear] = useState('1405');
  const [semester, setSemester] = useState('mehr');
  const [courses, setCourses] = useState([]);
  const [votes, setVotes] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [votedCourses, setVotedCourses] = useState(new Set());

  const currentYear = 1405;
  const yearOptions = Array.from({ length: 10 }, (_, i) => (currentYear + i).toString());

  // ============================================================
  // دریافت دروس فعال نظرسنجی
  // ============================================================
  const fetchActivePollCourses = useCallback(async () => {
    const termValue = `${year}-${semester}`;
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_BASE}/vote-polls/active`, {
        params: { term: termValue },
        headers: { Accept: 'application/json' },
        timeout: 10000,
      });

      let data = response.data;
      if (!Array.isArray(data)) {
        data = data.data || data.items || data.results || [];
      }
      setCourses(data);
      if (data.length > 0) {
        await fetchVoteStats(data);
      } else {
        setVotes({});
      }
    } catch (err) {
      console.error('❌ خطا در دریافت دروس فعال نظرسنجی:', err);
      let errorMessage = 'امکان دریافت لیست دروس فعال نظرسنجی وجود ندارد.';
      if (err.code === 'ECONNABORTED') {
        errorMessage = 'مدت زمان درخواست به پایان رسید.';
      } else if (err.response?.status === 404) {
        errorMessage = 'هیچ نظرسنجی فعالی برای این ترم یافت نشد.';
      } else if (err.response?.status === 500) {
        errorMessage = 'خطای داخلی سرور.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError('❌ ' + errorMessage);
      setCourses([]);
      setVotes({});
    } finally {
      setLoading(false);
    }
  }, [year, semester]);

  // ============================================================
  // دریافت آمار رأی‌ها (فقط تعداد درخواست‌ها)
  // ============================================================
  const fetchVoteStats = useCallback(async (courseList) => {
    const termValue = `${year}-${semester}`;
    const stats = {};
    for (const course of courseList) {
      try {
        const res = await axios.get(`${API_BASE}/votes/stats/${course.id}`, {
          params: { term: termValue },
          timeout: 5000,
        });
        // فقط تعداد درخواست‌ها را نگه می‌داریم
        stats[course.id] = {
          requests: res.data.requests || 0,
          total: res.data.total || 0,
        };
      } catch (err) {
        console.error(`خطا در دریافت آمار درس ${course.id}:`, err);
        stats[course.id] = { requests: 0, total: 0 };
      }
    }
    setVotes(stats);
  }, [year, semester]);

  // ============================================================
  // بارگذاری اولیه و به‌روزرسانی هنگام تغییر ترم
  // ============================================================
  useEffect(() => {
    fetchActivePollCourses();
  }, [fetchActivePollCourses]);

  // ============================================================
  // ثبت رأی (فقط نوع 'request')
  // ============================================================
  const handleVote = async (courseId) => {
    const termValue = `${year}-${semester}`;
    setSubmitting(true);
    setMessage('');
    setError('');

    try {
      const studentId = 1; // بعداً از احراز هویت دریافت شود

      await axios.post(
        `${API_BASE}/votes`,
        {
          course_id: courseId,
          vote_type: 'request', // فقط درخواست ارائه
          term: termValue,
        },
        {
          params: { student_id: studentId },
          headers: { 'Content-Type': 'application/json' },
        }
      );

      setMessage('✅ درخواست ارائه شما با موفقیت ثبت شد.');

      // به‌روزرسانی آمار
      await fetchVoteStats(courses);
      setVotedCourses((prev) => new Set(prev).add(courseId));
    } catch (err) {
      console.error('❌ خطا در ثبت رأی:', err);
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'خطای ناشناخته';
      setError('❌ خطا: ' + msg);
    } finally {
      setSubmitting(false);
    }
  };

  // ============================================================
  // محاسبه درصد درخواست‌ها (از کل آرا، در صورت وجود)
  // ============================================================
  const getRequestPercentage = (courseId) => {
    const stats = votes[courseId];
    if (!stats) return 0;
    const total = stats.total || 0;
    if (total === 0) return 0;
    return Math.round((stats.requests / total) * 100);
  };

  // ============================================================
  // نمایش وضعیت بارگذاری
  // ============================================================
  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>در حال بارگذاری دروس فعال نظرسنجی...</p>
      </div>
    );
  }

  // ============================================================
  // نمایش خطا
  // ============================================================
  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">🚫</span>
        <p style={{ whiteSpace: 'pre-line' }}>{error}</p>
        <button onClick={fetchActivePollCourses}>تلاش مجدد</button>
      </div>
    );
  }

  // ============================================================
  // رندر اصلی
  // ============================================================
  const coursesList = Array.isArray(courses) ? courses : [];

  return (
    <div className="vote-form-wrapper">
      <div className="vote-header">
        <h1>📝 نظرسنجی درخواست ارائه دروس</h1>
        <p>درس‌هایی که مایلید در ترم آینده ارائه شوند را انتخاب کنید</p>
        <p className="api-info">(اتصال به: {API_BASE})</p>
      </div>

      <form className="vote-form">
        {/* انتخاب ترم */}
        <div className="form-row">
          <div className="form-group">
            <label>سال تحصیلی</label>
            <select value={year} onChange={(e) => setYear(e.target.value)}>
              {yearOptions.map((y) => (
                <option key={y} value={y}>
                  {y} - {parseInt(y) + 1}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>نیمسال</label>
            <select value={semester} onChange={(e) => setSemester(e.target.value)}>
              <option value="mehr">مهر (نیمسال اول)</option>
              <option value="bahman">بهمن (نیمسال دوم)</option>
              <option value="summer">تابستان</option>
            </select>
          </div>
        </div>

        {/* پیام خالی بودن لیست */}
        {coursesList.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <p>هیچ نظرسنجی فعالی برای این ترم وجود ندارد.</p>
            <p className="empty-hint">لطفاً بعداً مراجعه کنید یا با مدیر گروه تماس بگیرید.</p>
          </div>
        ) : (
          <div className="courses-grid">
            {coursesList.map((course) => {
              const requests = votes[course.id]?.requests || 0;
              const total = votes[course.id]?.total || 0;
              const requestPercent = getRequestPercentage(course.id);
              const hasVoted = votedCourses.has(course.id);

              return (
                <div key={course.id} className="course-card">
                  <div className="card-header">
                    <span className="course-code">{course.code}</span>
                    <span className={`course-status ${course.status === 'active' ? 'active' : 'inactive'}`}>
                      {course.status === 'active' ? 'فعال' : 'غیرفعال'}
                    </span>
                  </div>
                  <h3 className="course-title">{course.title}</h3>
                  <div className="card-details">
                    <span className="detail-item">
                      <span className="detail-label">گروه:</span>
                      <span>{course.group || '—'}</span>
                    </span>
                    <span className="detail-item">
                      <span className="detail-label">ظرفیت:</span>
                      <span>{course.estimated_capacity || 'نامشخص'}</span>
                    </span>
                  </div>

                  {/* نمایش تعداد درخواست‌ها و نوار پیشرفت */}
                  <div className="vote-stats">
                    <div className="stat-bar">
                      <div
                        className="stat-bar-fill request"
                        style={{ width: `${requestPercent}%` }}
                      />
                    </div>
                    <div className="stat-labels">
                      <span className="stat-request">📝 درخواست: {requests}</span>
                      <span className="stat-total">مجموع آرا: {total}</span>
                    </div>
                  </div>

                  {/* دکمه درخواست ارائه */}
                  <div className="vote-actions">
                    <button
                      className={`vote-btn request-btn ${hasVoted ? 'voted' : ''}`}
                      onClick={() => handleVote(course.id)}
                      disabled={submitting || hasVoted}
                    >
                      📝 درخواست ارائه
                      {hasVoted && <span className="voted-badge">✓</span>}
                    </button>
                  </div>

                  {hasVoted && (
                    <div className="voted-message">
                      <span>✅ درخواست شما برای این درس ثبت شده است</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* پیام‌ها */}
        {message && <div className="success-message">{message}</div>}
        {error && <div className="error-message">{error}</div>}
      </form>
    </div>
  );
};

export default VoteForm;