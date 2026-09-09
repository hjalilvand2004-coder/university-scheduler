// frontend/src/pages/ProposalForm.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ProposalForm.css';

// ===== تنظیم آدرس پایه =====
// در صورت تنظیم پروکسی در vite، از '/api' استفاده کنید
// در غیر این صورت آدرس کامل را وارد کنید
const API_BASE = import.meta.env.VITE_API_URL || '/api';
// برای تست مستقیم، می‌توانید خط زیر را فعال کنید:
// const API_BASE = 'http://localhost:8000/api';

const ProposalForm = () => {
  // ----- state های فرم -----
  const [year, setYear] = useState('1405');
  const [semester, setSemester] = useState('mehr');
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [description, setDescription] = useState('');
  const [availableCourses, setAvailableCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // ----- گزینه‌های سال (از ۱۴۰۵ به بعد) -----
  const currentYear = 1405;
  const yearOptions = Array.from({ length: 10 }, (_, i) => (currentYear + i).toString());

  // ============================================================
  // دریافت دروس یکتا از سرور
  // ============================================================
  useEffect(() => {
    const fetchCourses = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await axios.get(`${API_BASE}/courses/unique`, {
          headers: {
            'Accept': 'application/json',
          },
          timeout: 10000, // 10 ثانیه تایم‌اوت
        });

        console.log('📚 دروس دریافتی:', response.data);

        // ===== بررسی اینکه پاسخ HTML نیست =====
        if (typeof response.data === 'string' && response.data.includes('<!doctype html>')) {
          throw new Error(
            'سرور پاسخ HTML برگرداند. لطفاً مطمئن شوید که:\n' +
            '1. بک‌اند در پورت 8000 در حال اجراست.\n' +
            '2. پروکسی Vite به درستی تنظیم شده است.\n' +
            '3. آدرس API_BASE صحیح است.'
          );
        }

        // ===== استخراج داده =====
        let courses = response.data;
        if (!Array.isArray(courses)) {
          // برخی APIها داده را در کلید data برمی‌گردانند
          if (courses && typeof courses === 'object' && Array.isArray(courses.data)) {
            courses = courses.data;
          } else if (courses && typeof courses === 'object' && Array.isArray(courses.items)) {
            courses = courses.items;
          } else if (courses && typeof courses === 'object' && Array.isArray(courses.results)) {
            courses = courses.results;
          } else {
            console.warn('داده دریافتی آرایه نیست:', courses);
            courses = [];
          }
        }

        setAvailableCourses(courses);
      } catch (err) {
        console.error('❌ خطا در دریافت دروس:', err);
        let errorMessage = 'امکان دریافت لیست دروس وجود ندارد.';
        if (err.code === 'ECONNABORTED') {
          errorMessage = 'مدت زمان درخواست به پایان رسید. لطفاً اتصال اینترنت را بررسی کنید.';
        } else if (err.response?.status === 404) {
          errorMessage = 'مسیر API یافت نشد. لطفاً آدرس را بررسی کنید.';
        } else if (err.response?.status === 500) {
          errorMessage = 'خطای داخلی سرور. لطفاً با پشتیبانی تماس بگیرید.';
        } else if (err.message) {
          errorMessage = err.message;
        }
        setError('❌ ' + errorMessage);
        setAvailableCourses([]);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  // ============================================================
  // انتخاب/لغو انتخاب یک درس
  // ============================================================
  const toggleCourseSelection = (courseId) => {
    setSelectedCourses((prev) =>
      prev.includes(courseId)
        ? prev.filter((id) => id !== courseId)
        : [...prev, courseId]
    );
  };

  // ============================================================
  // ثبت فرم
  // ============================================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (selectedCourses.length === 0) {
      setMessage('⚠️ حداقل یک درس را انتخاب کنید');
      return;
    }

    const termValue = `${year}-${semester}`;
    setSubmitting(true);
    setMessage('');
    setError('');

    try {
      const studentId = 1; // بعداً از احراز هویت دریافت شود

      // بررسی وجود دانشجو با id=1 (اختیاری)
      // می‌توانید یک درخواست جداگانه برای بررسی ارسال کنید

      await axios.post(
        `${API_BASE}/proposals`,
        {
          term: termValue,
          course_ids: selectedCourses,
          description: description.trim() || undefined,
        },
        {
          params: { student_id: studentId },
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setMessage('✅ پیشنهاد با موفقیت ثبت شد!');
      // ریست فرم
      setSelectedCourses([]);
      setDescription('');
      setYear('1405');
      setSemester('mehr');
    } catch (err) {
      console.error('❌ خطا در ثبت پیشنهاد:', err);
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'خطای ناشناخته';
      setError('❌ خطا: ' + msg);
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
  // نمایش خطا
  // ============================================================
  if (error) {
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
  const coursesList = Array.isArray(availableCourses) ? availableCourses : [];

  return (
    <div className="proposal-form-wrapper">
      <div className="proposal-header">
        <h1>📝 پیشنهاد دروس برای ترم جدید</h1>
        <p>دروس مورد نظر خود را برای ترم آینده انتخاب کنید</p>
        <p className="api-info">(اتصال به: {API_BASE})</p>
      </div>

      <form onSubmit={handleSubmit} className="proposal-form">
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
                    <span
                      className={`course-status ${
                        course.status === 'active' ? 'active' : 'inactive'
                      }`}
                    >
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
                    <span className="detail-item">
                      <span className="detail-label">متقاضی:</span>
                      <span>{course.historical_demand || '۰'}</span>
                    </span>
                  </div>
                  {isSelected && <div className="selected-badge">✓ انتخاب شده</div>}
                </div>
              );
            })
          )}
        </div>

        {/* توضیحات */}
        <div className="form-group full-width">
          <label>توضیحات (اختیاری)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="3"
            placeholder="توضیحات تکمیلی خود را وارد کنید..."
          />
        </div>

        {/* دکمه ثبت و پیام‌ها */}
        <div className="form-actions">
          <button type="submit" disabled={submitting || loading} className="submit-btn">
            {submitting ? '⏳ در حال ثبت...' : '📤 ثبت پیشنهاد'}
          </button>
          <span className="selected-count">{selectedCourses.length} درس انتخاب شده</span>
        </div>

        {message && <div className="success-message">{message}</div>}
        {error && <div className="error-message">{error}</div>}
      </form>
    </div>
  );
};

export default ProposalForm;