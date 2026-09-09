// frontend/src/pages/VoteManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './VoteManagement.css';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const VoteManagement = () => {
  const [year, setYear] = useState('1405');
  const [semester, setSemester] = useState('mehr');
  const [allCourses, setAllCourses] = useState([]);
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [apiAvailable, setApiAvailable] = useState(true); // وضعیت در دسترس بودن API نظرسنجی

  const currentYear = 1405;
  const yearOptions = Array.from({ length: 10 }, (_, i) => (currentYear + i).toString());

  // ============================================================
  // دریافت دروس یکتا و دروس فعال نظرسنجی
  // ============================================================
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      setApiAvailable(true);

      try {
        // 1. دریافت همه دروس یکتا
        const coursesRes = await axios.get(`${API_BASE}/courses/unique`, {
          headers: { Accept: 'application/json' },
          timeout: 10000,
        });

        let data = coursesRes.data;
        if (!Array.isArray(data)) {
          data = data.data || data.items || data.results || [];
        }
        setAllCourses(data);

        // 2. دریافت دروس فعال نظرسنجی برای ترم جاری
        const termValue = `${year}-${semester}`;
        try {
          const activeRes = await axios.get(`${API_BASE}/vote-polls/active`, {
            params: { term: termValue },
            timeout: 5000,
          });
          let activeData = activeRes.data;
          if (!Array.isArray(activeData)) {
            activeData = activeData.data || activeData.items || activeData.results || [];
          }
          // تنظیم دروس انتخاب‌شده بر اساس دروس فعال
          const activeIds = activeData.map((c) => c.id);
          setSelectedCourses(activeIds);
          setApiAvailable(true);
        } catch (activeErr) {
          // اگر API موجود نباشد، خطا را نادیده می‌گیریم
          if (activeErr.response?.status === 404) {
            console.warn('⚠️ API نظرسنجی فعال یافت نشد (404). فقط دروس یکتا بارگذاری شدند.');
            setApiAvailable(false);
            setSelectedCourses([]);
          } else {
            throw activeErr; // سایر خطاها را پرتاب می‌کنیم
          }
        }
      } catch (err) {
        console.error('❌ خطا در دریافت داده‌ها:', err);
        let errorMessage = 'امکان دریافت لیست دروس وجود ندارد.';
        if (err.code === 'ECONNABORTED') {
          errorMessage = 'مدت زمان درخواست به پایان رسید.';
        } else if (err.response?.status === 404) {
          errorMessage = 'مسیر API یافت نشد. لطفاً با پشتیبان تماس بگیرید.';
        } else if (err.response?.status === 500) {
          errorMessage = 'خطای داخلی سرور.';
        } else if (err.message) {
          errorMessage = err.message;
        }
        setError('❌ ' + errorMessage);
        setAllCourses([]);
        setSelectedCourses([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [year, semester]); // وابستگی به سال و نیمسال برای به‌روزرسانی مجدد

  // ============================================================
  // تغییر انتخاب یک درس
  // ============================================================
  const toggleCourseSelection = (courseId) => {
    setSelectedCourses((prev) =>
      prev.includes(courseId)
        ? prev.filter((id) => id !== courseId)
        : [...prev, courseId]
    );
  };

  // ============================================================
  // ذخیره تغییرات نظرسنجی
  // ============================================================
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage('');
    setError('');

    const termValue = `${year}-${semester}`;

    try {
      const response = await axios.post(
        `${API_BASE}/vote-polls/update`,
        {
          term: termValue,
          course_ids: selectedCourses,
        },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: 10000,
        }
      );

      setMessage('✅ نظرسنجی با موفقیت به‌روزرسانی شد.');
      console.log('پاسخ سرور:', response.data);
      setApiAvailable(true);
    } catch (err) {
      console.error('❌ خطا در ذخیره نظرسنجی:', err);

      if (err.response?.status === 404) {
        setError(
          '❌ مسیر API مدیریت نظرسنجی یافت نشد (404).\n' +
          'لطفاً مراحل زیر را انجام دهید:\n' +
          '1. مطمئن شوید فایل‌های بک‌اند به‌درستی ایجاد شده‌اند:\n' +
          '   - backend/app/models/vote_poll.py\n' +
          '   - backend/app/api/routes_vote_polls.py\n' +
          '2. بررسی کنید که روتر در backend/app/api/__init__.py ثبت شده باشد.\n' +
          '3. سرور بک‌اند را مجدداً راه‌اندازی کنید.\n' +
          '4. اگر از Alembic استفاده می‌کنید، مهاجرت را اجرا کنید: alembic upgrade head'
        );
      } else if (err.response?.status === 400) {
        setError('❌ داده‌های ارسالی نامعتبر است. لطفاً دوباره تلاش کنید.');
      } else if (err.code === 'ECONNABORTED') {
        setError('❌ مدت زمان درخواست به پایان رسید. لطفاً اتصال اینترنت را بررسی کنید.');
      } else {
        const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'خطای ناشناخته';
        setError('❌ خطا: ' + msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ============================================================
  // نمایش وضعیت بارگذاری
  // ============================================================
  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>در حال بارگذاری دروس...</p>
      </div>
    );
  }

  // ============================================================
  // نمایش خطا (در صورت عدم دریافت دروس)
  // ============================================================
  if (error && allCourses.length === 0) {
    return (
      <div className="error-container">
        <span className="error-icon">🚫</span>
        <p style={{ whiteSpace: 'pre-line' }}>{error}</p>
        <button onClick={() => window.location.reload()}>تلاش مجدد</button>
      </div>
    );
  }

  // ============================================================
  // رندر اصلی
  // ============================================================
  const coursesList = Array.isArray(allCourses) ? allCourses : [];

  return (
    <div className="vote-management-wrapper">
      <div className="vote-management-header">
        <h1>⚙️ مدیریت نظرسنجی دروس</h1>
        <p>درس‌هایی را که می‌خواهید برای نظرسنجی فعال شوند انتخاب کنید</p>
        {!apiAvailable && (
          <div className="api-warning">
            <span className="warning-icon">⚠️</span>
            <span>
              API نظرسنجی در دسترس نیست. فقط دروس یکتا نمایش داده می‌شوند.
              برای استفاده کامل، لطفاً APIهای مدیریت نظرسنجی را در بک‌اند پیاده‌سازی کنید.
            </span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="vote-management-form">
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

        {/* اطلاعات انتخاب‌ها */}
        <div className="selection-info">
          <span className="selected-count">✅ {selectedCourses.length} درس انتخاب شده</span>
          <span className="total-count">از {coursesList.length} درس کل</span>
        </div>

        {/* لیست دروس به صورت کارت */}
        <div className="courses-grid">
          {coursesList.length === 0 ? (
            <p className="no-courses">هیچ درسی برای نمایش وجود ندارد</p>
          ) : (
            coursesList.map((course) => {
              const isSelected = selectedCourses.includes(course.id);
              return (
                <div
                  key={course.id}
                  className={`course-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => toggleCourseSelection(course.id)}
                >
                  <div className="card-header">
                    <span className="course-code">{course.code}</span>
                    {isSelected && <span className="selected-badge">✓ انتخاب شده</span>}
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
                    <span className="detail-item">
                      <span className="detail-label">وضعیت:</span>
                      <span className={course.status === 'active' ? 'status-active' : 'status-inactive'}>
                        {course.status === 'active' ? 'فعال' : 'غیرفعال'}
                      </span>
                    </span>
                  </div>
                  <div className="card-check">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <label>انتخاب برای نظرسنجی</label>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* دکمه ذخیره */}
        <div className="form-actions">
          <button type="submit" disabled={submitting || loading} className="submit-btn">
            {submitting ? '⏳ در حال ذخیره...' : '💾 ذخیره نظرسنجی'}
          </button>
        </div>

        {/* پیام‌ها */}
        {message && <div className="success-message">{message}</div>}
        {error && <div className="error-message" style={{ whiteSpace: 'pre-line' }}>{error}</div>}
      </form>
    </div>
  );
};

export default VoteManagement;