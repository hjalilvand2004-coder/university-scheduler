// src/pages/FeedbackAnalyticsPage.jsx
import React, { useState, useEffect } from 'react';
import { getFeedbackAnalysis, getFeedbackStats } from '../api/feedbackApi';
import FeedbackForm from '../components/Feedback/FeedbackForm';
import WeightHistory from '../components/Feedback/WeightHistory';
import './FeedbackAnalyticsPage.css';

const FeedbackAnalyticsPage = ({ scheduleVersionId }) => {
  const [stats, setStats] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('analysis');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, analysisData] = await Promise.all([
        getFeedbackStats(),
        getFeedbackAnalysis(),
      ]);
      setStats(statsData);
      setAnalysis(analysisData);
      setError(null);
    } catch (err) {
      setError('خطا در دریافت اطلاعات تحلیل');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="analytics-container">
        <div className="loading-state">⏳ در حال بارگذاری داده‌های تحلیل...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-container">
        <div className="error-state">❌ {error}</div>
      </div>
    );
  }

  return (
    <div className="analytics-container">
      <h1>📊 تحلیل رضایت کاربران</h1>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">تعداد بازخوردها</span>
            <span className="stat-value">{stats.total_feedback || 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">میانگین رضایت کلی</span>
            <span className="stat-value">{stats.avg_overall?.toFixed(2) || '-'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">رضایت از استاد</span>
            <span className="stat-value">{stats.avg_instructor?.toFixed(2) || '-'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">رضایت از زمان</span>
            <span className="stat-value">{stats.avg_time?.toFixed(2) || '-'}</span>
          </div>
        </div>
      )}

      <div className="tabs">
        <button
          className={	ab }
          onClick={() => setActiveTab('analysis')}
        >
          📈 تحلیل و تنظیم وزن
        </button>
        <button
          className={	ab }
          onClick={() => setActiveTab('form')}
        >
          📝 ثبت بازخورد
        </button>
        <button
          className={	ab }
          onClick={() => setActiveTab('history')}
        >
          📜 تاریخچه وزن‌ها
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'analysis' && (
          <div className="analysis-panel">
            <h3>📈 تحلیل بازخوردها و تنظیم وزن‌ها</h3>
            {analysis ? (
              <div>
                <div className="correlation-info">
                  <h4>همبستگی بین امتیازات و وزن‌ها</h4>
                  <ul>
                    {Object.entries(analysis.correlations || {}).map(([key, value]) => (
                      <li key={key}>
                        <strong>{key}:</strong> {value?.toFixed(3)}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="weight-change-info">
                  <h4>وزن‌های جدید پیشنهادی</h4>
                  <ul>
                    {Object.entries(analysis.new_weights || {}).map(([key, value]) => (
                      <li key={key}>
                        <strong>{key}:</strong> {value}
                      </li>
                    ))}
                  </ul>
                  {analysis.adjustment_reason && (
                    <p className="adjustment-reason">
                      <strong>دلیل تنظیم:</strong> {analysis.adjustment_reason}
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p>هیچ داده‌ای برای تحلیل وجود ندارد. لطفاً بازخوردهای بیشتری ثبت کنید.</p>
            )}
          </div>
        )}

        {activeTab === 'form' && (
          <div className="form-panel">
            <FeedbackForm
              scheduleVersionId={scheduleVersionId}
              onSuccess={() => {
                alert('✅ بازخورد با موفقیت ثبت شد!');
                loadData();
              }}
              onError={(err) => alert('❌ خطا در ثبت بازخورد: ' + err.message)}
            />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history-panel">
            <WeightHistory limit={20} />
          </div>
        )}
      </div>
    </div>
  );
};

export default FeedbackAnalyticsPage;
