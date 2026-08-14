// frontend/src/components/Sidebar.jsx
import { useState } from "react";
import "./Sidebar.css";

export default function Sidebar({ onNavigate, activePage }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [openCategories, setOpenCategories] = useState({
    dashboard: true,
    "اطلاعات پایه": true,
    "برنامه‌ریزی درسی": true,
    "تولید برنامه هفتگی": true,
    تنظیمات: true,
  });

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  const toggleCategory = (title) => {
    setOpenCategories((prev) => ({
      ...prev,
      [title]: !prev[title],
    }));
  };

  const categories = [
    {
      title: "داشبورد",
      icon: "📊",
      color: "#6366f1",
      items: [{ id: "dashboard", label: "داشبورد اصلی", icon: "📊" }],
    },
    {
      title: "اطلاعات پایه",
      icon: "📋",
      color: "#3b82f6",
      items: [
        { id: "unique-courses", label: "دروس یکتا", icon: "📚" },
        { id: "offered-courses", label: "دروس ارائه", icon: "📖" },
        { id: "instructors", label: "اساتید", icon: "👨‍🏫" },
        { id: "rooms", label: "اتاق‌ها", icon: "🏫" },
      ],
    },
    {
      title: "برنامه‌ریزی درسی",
      icon: "🗓️",
      color: "#8b5cf6",
      items: [
        { id: "term-courses", label: "دروس ترمیک", icon: "📅" },
        { id: "teaching-preferences", label: "مطلوبیت‌های تدریس", icon: "📋" },
        { id: "time-preferences", label: "مطلوبیت‌های زمان‌بندی", icon: "⏰" },
        { id: "schedule-history", label: "سوابق برنامه‌ریزی", icon: "📜" },
      ],
    },
    {
      title: "تولید برنامه هفتگی",
      icon: "🚀",
      color: "#f59e0b",
      items: [
        { id: "basket", label: "مدیریت سبد دروس", icon: "📦" },  // تغییر برچسب برای وضوح
        { id: "instructor-time", label: "زمان‌بندی استاد و درس", icon: "⏳" },
        { id: "room-allocation", label: "تخصیص اتاق", icon: "🏢" },
        { id: "optimization", label: "بهینه‌سازی برنامه", icon: "⚡" },
      ],
    },
    {
      title: "تنظیمات",
      icon: "⚙️",
      color: "#6b7280",
      items: [{ id: "preferences", label: "تنظیمات", icon: "⚙️" }],
    },
  ];

  return (
    <div className={`sidebar ${isCollapsed ? "collapsed" : ""}`}>
      <div className="sidebar-toggle" onClick={toggleSidebar}>
        <span className="toggle-icon">{isCollapsed ? "▶" : "◀"}</span>
      </div>

      <div className="sidebar-header">
        <span className="logo-icon">🎓</span>
        {!isCollapsed && (
          <>
            <h2>دانشگاه</h2>
            <p>سیستم برنامه‌ریزی هوشمند</p>
          </>
        )}
      </div>

      <nav className="sidebar-nav">
        {categories.map((category) => {
          const isOpen = openCategories[category.title] !== false;
          return (
            <div key={category.title} className="sidebar-category">
              <div
                className="sidebar-category-header"
                onClick={() => toggleCategory(category.title)}
                style={{ borderColor: category.color }}
              >
                <span className="category-icon">{category.icon}</span>
                {!isCollapsed && (
                  <>
                    <span className="category-title">{category.title}</span>
                    <span className={`category-arrow ${isOpen ? "open" : ""}`}>
                      ▾
                    </span>
                  </>
                )}
              </div>
              <div className={`sidebar-items ${isOpen ? "open" : "closed"}`}>
                {category.items.map((item) => (
                  <button
                    key={item.id}
                    className={`sidebar-item ${
                      activePage === item.id ? "active" : ""
                    }`}
                    onClick={() => onNavigate(item.id)}
                  >
                    <span className="sidebar-icon">{item.icon}</span>
                    {!isCollapsed && (
                      <span className="sidebar-label">{item.label}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="user-avatar">م</div>
          {!isCollapsed && (
            <div>
              <div className="user-name">مدیر گروه</div>
              <div className="user-role">مدیریت برنامه‌ریزی</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}