// frontend/src/components/Sidebar.jsx — نسخه بازطراحی‌شده
import { useState } from "react";
import {
  FiGrid,
  FiBookOpen,
  FiBook,
  FiUsers,
  FiHome,
  FiCalendar,
  FiClipboard,
  FiClock,
  FiFileText,
  FiEdit3,
  FiThumbsUp,
  FiStar,
  FiSettings,
  FiPackage,
  FiActivity,
  FiLayers,
  FiZap,
  FiPieChart,
  FiChevronLeft,
  FiChevronsLeft,
  FiChevronsRight,
  FiInbox,
} from "react-icons/fi";
import "./Sidebar.css";

export default function Sidebar({ onNavigate, activePage }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [openCategories, setOpenCategories] = useState({
    dashboard: true,
    "اطلاعات پایه": true,
    "برنامه‌ریزی درسی": true,
    "تعامل دانشجویی": true,
    مدیریت: true,
    "تولید برنامه هفتگی": true,
    تنظیمات: true,
  });

  const toggleSidebar = () => setIsCollapsed(!isCollapsed);

  const toggleCategory = (title) =>
    setOpenCategories((prev) => ({ ...prev, [title]: !prev[title] }));

  const categories = [
    {
      title: "داشبورد",
      icon: <FiGrid />,
      color: "#818cf8",
      items: [{ id: "dashboard", label: "داشبورد اصلی", icon: <FiPieChart /> }],
    },
    {
      title: "اطلاعات پایه",
      icon: <FiBookOpen />,
      color: "#38bdf8",
      items: [
        { id: "unique-courses", label: "دروس یکتا", icon: <FiBook /> },
        { id: "offered-courses", label: "دروس ارائه", icon: <FiLayers /> },
        { id: "instructors", label: "اساتید", icon: <FiUsers /> },
        { id: "rooms", label: "کلاس‌ها و سالن‌ها", icon: <FiHome /> },
      ],
    },
    {
      title: "برنامه‌ریزی درسی",
      icon: <FiCalendar />,
      color: "#a78bfa",
      items: [
        { id: "term-courses", label: "دروس ترمیک", icon: <FiCalendar /> },
        { id: "teaching-preferences", label: "مطلوبیت تدریس", icon: <FiClipboard /> },
        { id: "time-preferences", label: "مطلوبیت زمانی", icon: <FiClock /> },
        { id: "schedule-history", label: "سوابق برنامه‌ریزی", icon: <FiFileText /> },
      ],
    },
    {
      title: "تعامل دانشجویی",
      icon: <FiThumbsUp />,
      color: "#f472b6",
      items: [
        { id: "proposal", label: "پیشنهاد دروس", icon: <FiEdit3 /> },
        { id: "vote", label: "نظرسنجی دروس", icon: <FiThumbsUp /> },
        { id: "rating", label: "امتیاز به برنامه", icon: <FiStar /> },
      ],
    },
    {
      title: "تولید برنامه هفتگی",
      icon: <FiZap />,
      color: "#fbbf24",
      items: [
        { id: "basket-list", label: "لیست سبدها", icon: <FiInbox /> },
        { id: "basket", label: "سبد دروس", icon: <FiPackage /> },
        { id: "instructor-time", label: "زمان‌بندی استاد", icon: <FiActivity /> },
        { id: "room-allocation", label: "تخصیص کلاس", icon: <FiHome /> },
        { id: "optimization", label: "بهینه‌سازی برنامه", icon: <FiZap /> },
      ],
    },
    {
      title: "مدیریت",
      icon: <FiClipboard />,
      color: "#fb7185",
      items: [{ id: "vote-management", label: "مدیریت نظرسنجی", icon: <FiClipboard /> }],
    },
    {
      title: "تنظیمات",
      icon: <FiSettings />,
      color: "#94a3b8",
      items: [{ id: "preferences", label: "تنظیمات سامانه", icon: <FiSettings /> }],
    },
  ];

  return (
    <>
      <div className={`sidebar ${isCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-brand" onClick={() => onNavigate("dashboard")}>
          <div className="brand-logo">
            <svg viewBox="0 0 64 64" width="26" height="26" aria-hidden="true">
              <defs>
                <linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#a5b4fc" />
                  <stop offset="1" stopColor="#e0e7ff" />
                </linearGradient>
              </defs>
              <rect width="64" height="64" rx="16" fill="url(#logo-g)" opacity="0.22" />
              <path d="M32 14 L50 23 L32 32 L14 23 Z" fill="url(#logo-g)" />
              <path d="M20 27 v10 c0 4 6 7 12 7 s12 -3 12 -7 v-10 l-12 6 z" fill="url(#logo-g)" opacity=".7" />
              <rect x="47" y="23" width="3" height="14" rx="1.5" fill="url(#logo-g)" opacity=".9" />
            </svg>
          </div>
          {!isCollapsed && (
            <div className="brand-text">
              <h2>برنامه‌ریز هوشمند</h2>
              <p>سامانه چیدمان درسی دانشگاه</p>
            </div>
          )}
        </div>

        <nav className="sidebar-nav">
          {categories.map((category, ci) => {
            const isOpen = openCategories[category.title] !== false;
            const hasActive = category.items.some((i) => i.id === activePage);
            return (
              <div
                key={category.title}
                className={`sidebar-category ${isOpen ? "open" : ""} ${hasActive ? "has-active" : ""}`}
                style={{ "--cat-color": category.color, animationDelay: `${ci * 40}ms` }}
              >
                <button
                  type="button"
                  className="sidebar-category-header"
                  onClick={() => toggleCategory(category.title)}
                  title={category.title}
                >
                  <span className="category-icon">{category.icon}</span>
                  {!isCollapsed && (
                    <>
                      <span className="category-title">{category.title}</span>
                      <span className={`category-arrow ${isOpen ? "open" : ""}`}>
                        <FiChevronLeft />
                      </span>
                    </>
                  )}
                </button>
                <div className={`sidebar-items ${isOpen ? "open" : "closed"}`}>
                  {category.items.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`sidebar-item ${activePage === item.id ? "active" : ""}`}
                      onClick={() => onNavigate(item.id)}
                      title={item.label}
                    >
                      <span className="sidebar-icon">{item.icon}</span>
                      {!isCollapsed && <span className="sidebar-label">{item.label}</span>}
                      {!isCollapsed && activePage === item.id && (
                        <span className="active-dot" aria-hidden="true" />
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
              <div className="user-meta">
                <div className="user-name">مدیر گروه</div>
                <div className="user-role">مدیریت برنامه‌ریزی</div>
              </div>
            )}
            <button
              type="button"
              className="collapse-btn"
              onClick={toggleSidebar}
              title={isCollapsed ? "باز کردن منو" : "جمع کردن منو"}
            >
              {isCollapsed ? <FiChevronsRight /> : <FiChevronsLeft />}
            </button>
          </div>
          {!isCollapsed && <div className="sidebar-version">نسخه ۲.۱ — هسته بهینه‌سازی CP-SAT</div>}
        </div>
      </div>
      {isCollapsed && <div className="sidebar-rail-hint" onClick={toggleSidebar} title="باز کردن منو" />}
    </>
  );
}
