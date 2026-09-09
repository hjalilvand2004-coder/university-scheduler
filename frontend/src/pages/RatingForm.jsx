// frontend/src/pages/RatingForm.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './RatingForm.css';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const RatingForm = () => {
  const [schedules, setSchedules] = useState([]);
  const [ratings, setRatings] = useState({}); // { scheduleId: score (1-5) }
  const [comments, setComments] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // دریافت لیست سبدهای دروس (برنامه‌های ترم)
  useEffect(() => {
    const fetchSchedules = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await axios.get(`${API_BASE}/baskets/`, {
          headers: { Accept: 'application/json' },
          timeout: 10000,
        });

        let data = response.data;
        if (!Array.isArray(data)) {
          data = data.data || data.items || data.results || [];
        }

        // تبدیل داده‌ها به فرمت مناسب برای نمایش
        const formattedData = data.map((basket) => ({
          id: basket.id,
          title: basket.title || `سبد شماره ${basket.id}`,
          description: basket.description || 'بدون توضیحات',
          schedule_id: basket.schedule_id || basket.id,
          created_at: basket.created_at,
        }));

        setSchedules(formattedData);
      } catch (err) {
        console.error('خطا در دریافت سبدهای دروس:', err);
        let errorMessage = 'امکان دریافت لیست سبدهای دروس وجود ندارد.';
        if (err.code === 'ECONNABORTED') {
          errorMessage = 'مدت زمان درخواست به پایان رسید.';
        } else if (err.response?.status === 404) {
          errorMessage = 'هیچ سبد درسی یافت نشد.';
        } else if (err.response?.status === 500) {
          errorMessage = 'خطای داخلی سرور.';
        } else if (err.message) {
          errorMessage = err.message;
        }
        setError('❌ ' + errorMessage);
        setSchedules([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSchedules();
  }, []);

  // تغییر امتیاز (۱ تا ۵)
  const handleRatingChange = (scheduleId, score) => {
    setRatings((prev) => ({ ...prev, [scheduleId]: score }));
  };

  // تغییر نظر
  const handleCommentChange = (scheduleId, value) => {
    setComments((prev) => ({ ...prev, [scheduleId]: value }));
  };

  // ثبت امتیاز
  const handleSubmit = async (scheduleId) => {
    const rating = ratings[scheduleId];
    if (!rating) {
      setError('لطفاً یک امتیاز انتخاب کنید');
      return;
    }

    setSubmitting(true);
    setMessage('');
    setError('');

    try {
      const studentId = 1; // بعداً از احراز هویت دریافت شود
      await axios.post(
        `${API_BASE}/ratings`,
        {
          schedule_id: scheduleId,
          rating: getRatingLabel(rating), // تبدیل عدد به متن
          comment: comments[scheduleId] || '',
        },
        {
          params: { student_id: studentId },
          headers: { 'Content-Type': 'application/json' },
        }
      );

      setMessage('✅ امتیاز شما با موفقیت ثبت شد!');
      // پاک کردن انتخاب
      setRatings((prev) => ({ ...prev, [scheduleId]: 0 }));
      setComments((prev) => ({ ...prev, [scheduleId]: '' }));
    } catch (err) {
      console.error('خطا در ثبت امتیاز:', err);
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'خطای ناشناخته';
      setError('❌ خطا: ' + msg);
    } finally {
      setSubmitting(false);
    }
  };

  // تبدیل عدد به متن برای ارسال به سرور
  const getRatingLabel = (score) => {
    const map = {
      1: 'very_weak',
      2: 'weak',
      3: 'average',
      4: 'good',
      5: 'excellent',
    };
    return map[score] || 'average';
  };

  // رندر ستاره‌ها
  const renderStars = (scheduleId, currentRating) => {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <span
          key={i}
          className={`star ${i <= currentRating ? 'filled' : ''}`}
          onClick={() => handleRatingChange(scheduleId, i)}
        >
          ★
        </span>
      );
    }
    return stars;
  };

  // نمایش وضعیت بارگذاری
  if (loading) {
    return (
      <div className="rating-loading">
        <div className="spinner"></div>
        <p>در حال بارگذاری سبدهای دروس...</p>
      </div>
    );
  }

  // نمایش خطا
  if (error) {
    return (
      <div className="rating-error">
        <span className="error-icon">🚫</span>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>تلاش مجدد</button>
      </div>
    );
  }

  return (
    <div className="rating-wrapper">
      <div className="rating-header">
        <h1>⭐ امتیازدهی به برنامه‌های ترم</h1>
        <p>به برنامه‌های درسی که تجربه کردید، امتیاز دهید و نظر خود را بنویسید</p>
      </div>

      <div className="rating-grid">
        {schedules.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📋</span>
            <p>هیچ سبد درسی برای امتیازدهی وجود ندارد.</p>
          </div>
        ) : (
          schedules.map((schedule) => {
            const currentRating = ratings[schedule.id] || 0;
            const comment = comments[schedule.id] || '';

            return (
              <div key={schedule.id} className="rating-card">
                <div className="card-header">
                  <h3 className="card-title">{schedule.title}</h3>
                  <span className="card-date">
                    {schedule.created_at
                      ? new Date(schedule.created_at).toLocaleDateString('fa-IR')
                      : ''}
                  </span>
                </div>

                <p className="card-description">{schedule.description}</p>

                <div className="rating-section">
                  <label className="rating-label">امتیاز شما:</label>
                  <div className="stars-container">
                    {renderStars(schedule.id, currentRating)}
                    <span className="rating-score">
                      {currentRating > 0 ? `${currentRating} / 5` : 'بدون امتیاز'}
                    </span>
                  </div>
                </div>

                <div className="comment-section">
                  <label className="comment-label">نظر شما (اختیاری):</label>
                  <textarea
                    className="comment-input"
                    value={comment}
                    onChange={(e) => handleCommentChange(schedule.id, e.target.value)}
                    placeholder="نظر خود را در مورد این برنامه بنویسید..."
                    rows="3"
                  />
                </div>

                <button
                  className="submit-btn"
                  onClick={() => handleSubmit(schedule.id)}
                  disabled={submitting || currentRating === 0}
                >
                  {submitting ? '⏳ در حال ثبت...' : '📤 ثبت امتیاز'}
                </button>
              </div>
            );
          })
        )}
      </div>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default RatingForm;