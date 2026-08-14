import React from 'react';
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaChartLine,
  FaUsers,
  FaChalkboardTeacher,
  FaDoorOpen,
  FaClock,
  FaListUl,
  FaStar,
  FaDownload,
  FaPrint,
  FaTrophy,
  FaInfoCircle
} from 'react-icons/fa';

export default function ExplanationPanel({ schedule, rankedCourses: externalRanked }) {
  if (!schedule) return null;

  const {
    status,
    objective_value,
    hard_constraints_satisfied,
    explanations,
    alternative_scenarios,
    selected_courses,
    ranked_courses: scheduleRanked,
    quality_metrics,
    conflicts,
    unschedulable_courses
  } = schedule;

  // ===== اولویت با rankedCourses ارسالی از والد، سپس از schedule.ranked_courses، سپس selected_courses =====
  const rankedCourses = externalRanked || scheduleRanked || selected_courses || [];

  // محاسبه آمار
  const totalClasses = schedule?.classes?.length || 0;
  const totalCourses = selected_courses?.length || 0;
  const totalInstructors = quality_metrics?.instructors_used || 0;
  const totalRooms = quality_metrics?.rooms_used || 0;
  const totalGroups = quality_metrics?.total_groups || 0;

  // دروس با امتیاز بالا (۵ درس اول)
  const topCourses = rankedCourses?.slice(0, 5) || [];

  // مدال‌های رتبه‌بندی
  const getMedal = (index) => {
    const medals = ['🥇', '🥈', '🥉'];
    return medals[index] || `#${index + 1}`;
  };

  const getMedalColor = (index) => {
    const colors = ['#f59e0b', '#94a3b8', '#cd7f32'];
    return colors[index] || '#6366f1';
  };

  return (
    <div className="explanation-panel-wrapper">
      <div className="explanation-panel">
        {/* ===== هدر ===== */}
        <div className="panel-header">
          <h2 className="panel-title">
            <span className="title-icon">📊</span>
            گزارش تحلیلی برنامه
          </h2>
          <div className="panel-actions">
            <button className="panel-action-btn" title="خروجی PDF">
              <FaDownload /> PDF
            </button>
            <button className="panel-action-btn" title="چاپ">
              <FaPrint /> چاپ
            </button>
          </div>
        </div>

        {/* ===== کارت‌های وضعیت کلی ===== */}
        <div className="explanation-summary">
          <div className="summary-card status">
            <div className="status-icon">
              {status === 'optimal' ?
                <FaCheckCircle color="#22c55e" size={32} /> :
                <FaExclamationTriangle color="#f59e0b" size={32} />
              }
            </div>
            <div className="status-text">
              <span className="status-label">وضعیت حل</span>
              <span className="status-value">
                {status === 'optimal' ? 'بهینه 🎯' :
                 status === 'feasible' ? 'قابل قبول ⚠️' :
                 'ناموفق ❌'}
              </span>
            </div>
          </div>

          <div className="summary-card score">
            <div className="summary-icon">
              <FaChartLine color="#6366f1" size={28} />
            </div>
            <div className="summary-info">
              <span className="summary-label">امتیاز هدف</span>
              <span className="summary-value">{objective_value?.toFixed(2) || 0}</span>
            </div>
          </div>

          <div className="summary-card constraints">
            <div className="summary-icon">
              <FaCheckCircle color={hard_constraints_satisfied ? "#22c55e" : "#ef4444"} size={28} />
            </div>
            <div className="summary-info">
              <span className="summary-label">محدودیت‌های سخت</span>
              <span className="summary-value">
                {hard_constraints_satisfied ? '✅ رعایت شده' : '❌ نقض شده'}
              </span>
            </div>
          </div>

          <div className="summary-card classes-count">
            <div className="summary-icon">
              <FaListUl color="#8b5cf6" size={28} />
            </div>
            <div className="summary-info">
              <span className="summary-label">کلاس‌های برنامه</span>
              <span className="summary-value">{totalClasses}</span>
            </div>
          </div>
        </div>

        {/* ===== آمار تفصیلی ===== */}
        <div className="explanation-stats">
          <div className="stat-item">
            <FaUsers className="stat-icon" color="#3b82f6" />
            <div className="stat-info">
              <span className="stat-number">{totalCourses}</span>
              <span className="stat-label">درس انتخاب شده</span>
            </div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <FaChalkboardTeacher className="stat-icon" color="#8b5cf6" />
            <div className="stat-info">
              <span className="stat-number">{totalInstructors}</span>
              <span className="stat-label">استاد</span>
            </div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <FaDoorOpen className="stat-icon" color="#f59e0b" />
            <div className="stat-info">
              <span className="stat-number">{totalRooms}</span>
              <span className="stat-label">اتاق</span>
            </div>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <FaClock className="stat-icon" color="#ef4444" />
            <div className="stat-info">
              <span className="stat-number">{totalGroups}</span>
              <span className="stat-label">گروه</span>
            </div>
          </div>
        </div>

        {/* ===== توضیحات متنی ===== */}
        <div className="explanation-details">
          <div className="details-header">
            <span className="details-icon">📝</span>
            <span className="details-title">توضیحات برنامه</span>
          </div>
          <ul className="explanation-list">
            {explanations?.map((text, idx) => (
              <li key={idx} className="explanation-item">
                <span className="bullet">•</span>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* ===== رتبه‌بندی دروس پیشنهادی ===== */}
        {topCourses.length > 0 && (
          <div className="ranked-courses-section">
            <h3 className="section-title">
              <FaTrophy className="section-icon" color="#f59e0b" />
              رتبه‌بندی دروس پیشنهادی
              <span className="ranked-count">{topCourses.length} درس</span>
            </h3>
            <div className="ranked-courses-grid">
              {topCourses.map((course, idx) => (
                <div key={idx} className="ranked-course-card">
                  <div className="ranked-course-header">
                    <div className="rank-badge" style={{ backgroundColor: getMedalColor(idx) }}>
                      {getMedal(idx)}
                    </div>
                    <div className="ranked-course-title-wrapper">
                      <span className="ranked-course-code">{course.course_code || course.code || '-'}</span>
                      <span className="ranked-course-name">{course.course_name || course.course_title || course.title}</span>
                    </div>
                    <div className="ranked-course-score">
                      <span className="score-number">{course.score?.toFixed(1) || 0}</span>
                      <span className="score-label">امتیاز</span>
                    </div>
                  </div>
                  <div className="ranked-course-reasons">
                    {course.reasons?.map((reason, ridx) => (
                      <span key={ridx} className="reason-tag">
                        <FaInfoCircle className="reason-icon" />
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== سناریوهای جایگزین ===== */}
        {alternative_scenarios && alternative_scenarios.length > 0 && (
          <div className="scenarios-section">
            <h3 className="section-title">
              <span className="section-icon">🔄</span>
              سناریوهای جایگزین
            </h3>
            <div className="scenarios-grid">
              {alternative_scenarios.map((scenario, idx) => (
                <div key={idx} className="scenario-card">
                  <div className="scenario-header">
                    <div className="scenario-name-wrapper">
                      <span className="scenario-name">{scenario.name}</span>
                      <span className={`scenario-badge ${scenario.status === 'optimal' ? 'badge-success' : 'badge-warning'}`}>
                        {scenario.status === 'optimal' ? 'بهینه' : 'قابل قبول'}
                      </span>
                    </div>
                    <div className="scenario-score">
                      {scenario.objective_value?.toFixed(1) || 0}
                    </div>
                  </div>
                  <p className="scenario-desc">{scenario.description}</p>
                  <div className="scenario-meta">
                    <span>📚 {scenario.classes_count || 0} کلاس</span>
                    <span>⚡ {scenario.status === 'optimal' ? 'بهترین' : 'جایگزین'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== دروس غیرقابل زمان‌بندی ===== */}
        {unschedulable_courses && unschedulable_courses.length > 0 && (
          <div className="unschedulable-section">
            <h3 className="section-title warning">
              <span className="section-icon">⚠️</span>
              دروس غیرقابل زمان‌بندی ({unschedulable_courses.length})
            </h3>
            <div className="unschedulable-list">
              {unschedulable_courses.map((course, idx) => (
                <div key={idx} className="unschedulable-item">
                  <span className="course-name">{course.course_title}</span>
                  <span className="course-reason">{course.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== تداخل‌ها ===== */}
        {conflicts && conflicts.length > 0 && (
          <div className="conflicts-section">
            <h3 className="section-title danger">
              <span className="section-icon">🚨</span>
              تداخل‌های شناسایی‌شده ({conflicts.length})
            </h3>
            <div className="conflicts-list">
              {conflicts.map((conflict, idx) => (
                <div key={idx} className="conflict-item">
                  <span className="conflict-type">{conflict.type}</span>
                  <span className="conflict-message">{conflict.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== فوتر ===== */}
        <div className="panel-footer">
          <span className="footer-text">
            🧠 تولید شده توسط موتور برنامه‌ریزی هوشمند OR-Tools
          </span>
          <span className="footer-separator">|</span>
          <span className="footer-text">
            🕐 زمان اجرا: {new Date().toLocaleTimeString('fa-IR')}
          </span>
        </div>
      </div>
    </div>
  );
}