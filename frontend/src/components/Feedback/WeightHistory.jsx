// src/components/Feedback/WeightHistory.jsx
import React, { useState, useEffect } from 'react';
import { getWeightHistory } from '../../api/feedbackApi';
import './WeightHistory.css';

const WeightHistory = ({ limit = 10 }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await getWeightHistory();
      setHistory(data.slice(0, limit));
      setError(null);
    } catch (err) {
      setError('خطا در دریافت تاریخچه وزن‌ها');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">⏳ در حال بارگذاری...</div>;
  if (error) return <div className="error">❌ {error}</div>;
  if (!history || history.length === 0) {
    return <div className="no-data">ℹ️ هنوز هیچ تغییری در وزن‌ها اعمال نشده است.</div>;
  }

  return (
    <div className="weight-history-container">
      <h3>📊 تاریخچه تغییرات وزن‌ها</h3>
      <table className="weight-table">
        <thead>
          <tr>
            <th>زمان تغییر</th>
            <th>وزن جدید</th>
            <th>دلیل تغییر</th>
            <th>تأثیر</th>
          </tr>
        </thead>
        <tbody>
          {history.map((item, index) => (
            <tr key={index}>
              <td>{new Date(item.timestamp).toLocaleString('fa-IR')}</td>
              <td>
                <ul className="weight-list">
                  {Object.entries(item.new_weights || {}).map(([key, value]) => (
                    <li key={key}>{key}: {value}</li>
                  ))}
                </ul>
              </td>
              <td>{item.reason || 'تنظیم خودکار بر اساس بازخورد'}</td>
              <td>
                <span className={impact-badge }>
                  {item.impact >= 0 ? '+' : ''}{item.impact?.toFixed(2)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default WeightHistory;
