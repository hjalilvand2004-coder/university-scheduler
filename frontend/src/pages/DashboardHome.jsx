// frontend/src/pages/DashboardHome.jsx
import ScheduleTable from "../components/ScheduleTable";
import ExplanationPanel from "../components/ExplanationPanel";

/**
 * صفحه اصلی داشبورد - نمایش آمار کلی و دسترسی سریع به بخش‌های مختلف
 */
export default function DashboardHome({
  uniqueCourses = [],
  offeredCourses = [],
  instructors = [],
  rooms = [],
  historyRecords = [],
  termCourses = [],
  teachingPreferences = [],
  timePreferences = [],
  baskets = [], // جدید: لیست سبدهای دروس
  schedule = null,
  rankedCourses = null,
  onNavigate,
  onSelectBasket, // جدید: تابع برای انتخاب یک سبد خاص (اختیاری)
  loading = false,
}) {
  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>در حال بارگذاری داده‌ها...</p>
      </div>
    );
  }

  // کارت‌های آماری با اطلاعات به‌روز
  const statCards = [
    { title: "📚 دروس یکتا", count: uniqueCourses.length, color: "#6366f1" },
    { title: "📖 دروس ارائه", count: offeredCourses.length, color: "#3b82f6" },
    { title: "👨‍🏫 اساتید", count: instructors.length, color: "#8b5cf6" },
    { title: "🏫 اتاق‌ها", count: rooms.length, color: "#f59e0b" },
    { title: "📜 سوابق برنامه‌ریزی", count: historyRecords.length, color: "#10b981" },
    { title: "📅 دروس ترمیک", count: termCourses.length, color: "#ef4444" },
    { title: "📋 مطلوبیت‌های تدریس", count: teachingPreferences.length, color: "#06b6d4" },
    { title: "⏰ مطلوبیت‌های زمان‌بندی", count: timePreferences.length, color: "#f472b6" },
    { title: "📦 سبدهای دروس", count: baskets.length, color: "#8b5cf6" },
    { title: "🗓️ کلاس‌های برنامه", count: schedule?.classes?.length || 0, color: "#f97316" },
  ];

  // دکمه‌های دسترسی سریع
  const quickActions = [
    { id: "unique-courses", label: "📚 دروس یکتا" },
    { id: "offered-courses", label: "📖 دروس ارائه" },
    { id: "instructors", label: "👨‍🏫 اساتید" },
    { id: "rooms", label: "🏫 اتاق‌ها" },
    { id: "schedule-history", label: "📜 سوابق" },
    { id: "term-courses", label: "📅 دروس ترمیک" },
    { id: "teaching-preferences", label: "📋 مطلوبیت تدریس" },
    { id: "time-preferences", label: "⏰ مطلوبیت زمان‌بندی" },
    { id: "schedule", label: "🗓️ تولید برنامه (قدیمی)" },
    { id: "basket", label: "📦 سبد دروس" },
    { id: "instructor-time", label: "⏳ زمان‌بندی" },
    { id: "room-allocation", label: "🏢 تخصیص اتاق" },
    { id: "optimization", label: "⚡ بهینه‌سازی" },
  ];

  // نمایش چند سبد آخر (اختیاری)
  const recentBaskets = baskets.slice(-5).reverse();

  return (
    <div className="dashboard-home">
      {/* بخش آمار */}
      <div className="dashboard-summary">
        {statCards.map((card, index) => (
          <div key={index} className="stat-card" style={{ borderTopColor: card.color }}>
            <h3>{card.title}</h3>
            <p className="stat-number">{card.count}</p>
          </div>
        ))}
      </div>

      {/* بخش دسترسی سریع */}
      <div className="quick-actions">
        <h3>🚀 دسترسی سریع</h3>
        <div className="action-grid">
          {quickActions.map((action) => (
            <button
              key={action.id}
              onClick={() => onNavigate(action.id)}
              className="quick-action-btn"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* بخش سبدهای اخیر (در صورت وجود) */}
      {recentBaskets.length > 0 && (
        <div className="recent-baskets">
          <h3>📋 سبدهای اخیر</h3>
          <div className="basket-list">
            {recentBaskets.map((basket) => (
              <div
                key={basket.id}
                className="basket-item"
                onClick={() => {
                  if (onSelectBasket) {
                    onSelectBasket(basket.id);
                  } else {
                    // در غیر این صورت به صفحه کلی سبدها برو
                    onNavigate("basket");
                  }
                }}
              >
                <span className="basket-title">{basket.title}</span>
                <span className="basket-meta">
                  {basket.semester} - {basket.year}
                  <span className="basket-count">{basket.items_count || 0} درس</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* بخش نمایش برنامه (در صورت وجود) */}
      <div className="schedule-wrapper-modern">
        {schedule?.classes && schedule.classes.length > 0 ? (
          <>
            <h3 className="schedule-title">📋 برنامه هفتگی فعلی</h3>
            <ScheduleTable classes={schedule.classes} />
            {rankedCourses && <ExplanationPanel schedule={schedule} rankedCourses={rankedCourses} />}
          </>
        ) : (
          <div className="empty-schedule">
            <span className="empty-icon">📅</span>
            <p>هیچ برنامه‌ای برای نمایش وجود ندارد.</p>
            <p className="empty-hint">برای تولید برنامه، از بخش "تولید برنامه هفتگی" استفاده کنید.</p>
          </div>
        )}
      </div>
    </div>
  );
}