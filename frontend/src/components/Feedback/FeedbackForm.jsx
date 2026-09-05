// src/components/Feedback/FeedbackForm.jsx
import React, { useState } from 'react';
import { submitFeedback } from '../../api/feedbackApi';
import './FeedbackForm.css';

const FeedbackForm = ({ scheduleVersionId, onSuccess, onError }) => {
  const [ratings, setRatings] = useState({
    instructor: 3,
    time: 3,
    room: 3,
    overall: 3,
  });
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const ratingLabels = {
    instructor: 'رضایت از استاد',
    time: 'رضایت از زمان‌بندی',
    room: 'رضایت از اتاق',
    overall: 'رضایت کلی',
  };

  const handleRatingChange = (category, value) => {
    setRatings((prev) => ({
      ...prev,
      [category]: parseInt(value, 10),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await submitFeedback({
        schedule_version_id: scheduleVersionId,
        ratings,
        comment: comment.trim(),
        submitted_at: new Date().toISOString(),
      });
      setSubmitted(true);
      if (onSuccess) onSuccess();
    } catch (error) {
      console.error('خطا در ثبت بازخورد:', error);
      if (onError) onError(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="feedback-success">
        <h3>✅ بازخورد شما با موفقیت ثبت شد</h3>
        <p>از مشارکت شما در بهبود سیستم سپاسگزاریم.</p>
        <button onClick={() => setSubmitted(false)}>ثبت بازخورد جدید</button>
      </div>
    );
  }

  return (
    <div className="feedback-form-container">
      <h3>📝 ثبت بازخورد</h3>
      <p>لطفاً به برنامه‌ی زمان‌بندی فعلی امتیاز دهید:</p>
      <form onSubmit={handleSubmit}>
        {Object.entries(ratingLabels).map(([key, label]) => (
          <div className="rating-group" key={key}>
            <label>{label}:</label>
            <div className="stars">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  className={star }
                  onClick={() => handleRatingChange(key, star)}
                >
                  ★
                </button>
              ))}
              <span className="rating-value">{ratings[key]} / 5</span>
            </div>
          </div>
        ))}

        <div className="comment-group">
          <label>نظر شما (اختیاری):</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="لطفاً پیشنهادات یا انتقادات خود را بنویسید..."
            rows="4"
          />
        </div>

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'در حال ارسال...' : 'ارسال بازخورد'}
        </button>
      </form>
    </div>
  );
};

export default FeedbackForm;
