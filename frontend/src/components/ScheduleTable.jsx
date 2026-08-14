import { useState, useMemo, useRef, useEffect } from "react";
import {
  FaSearch,
  FaFilter,
  FaSortUp,
  FaSortDown,
  FaUser,
  FaUsers,
  FaDoorOpen,
  FaInfoCircle,
  FaChevronDown,
  FaChevronUp,
  FaTable,
  FaThLarge,
  FaFileExport,
  FaCalendarAlt,
} from "react-icons/fa";

const DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه"];
const DAY_COLORS = {
  0: "#4f46e5",
  1: "#7c3aed",
  2: "#2563eb",
  3: "#059669",
  4: "#d97706",
};

function getDayName(day) {
  return DAYS[day] || day;
}

export default function ScheduleTable({ classes, onClassClick }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("day");
  const [sortOrder, setSortOrder] = useState("asc");
  const [filterDay, setFilterDay] = useState("all");
  const [filterInstructor, setFilterInstructor] = useState("all");
  const [expandedRow, setExpandedRow] = useState(null);
  const [viewMode, setViewMode] = useState("table");
  const [showFilters, setShowFilters] = useState(false);
  const searchInputRef = useRef(null);

  // ===== استخراج اساتید منحصر‌به‌فرد =====
  const uniqueInstructors = useMemo(() => {
    if (!classes) return [];
    const names = new Set(classes.map((c) => c.instructor_name).filter(Boolean));
    return Array.from(names).sort();
  }, [classes]);

  // ===== آمار =====
  const stats = useMemo(() => {
    if (!classes || classes.length === 0) return null;
    const totalStudents = classes.reduce((sum, c) => sum + (c.predicted_students || 0), 0);
    const uniqueInstructorsCount = new Set(classes.map((c) => c.instructor_name)).size;
    const uniqueRooms = new Set(classes.map((c) => c.room_name)).size;
    const totalGroups = classes.reduce((sum, c) => sum + (c.group_number || 1), 0);
    return { total: classes.length, totalStudents, uniqueInstructors: uniqueInstructorsCount, uniqueRooms, totalGroups };
  }, [classes]);

  // ===== فیلتر و مرتب‌سازی =====
  const filteredClasses = useMemo(() => {
    if (!classes) return [];
    let result = [...classes];

    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      result = result.filter(
        (item) =>
          (item.course_title || "").toLowerCase().includes(term) ||
          (item.course_code || "").toLowerCase().includes(term) ||
          (item.instructor_name || "").toLowerCase().includes(term) ||
          (item.room_name || "").toLowerCase().includes(term) ||
          (item.estimated_capacity || "").toString().includes(term) ||
          (item.required_classes || "").toString().includes(term)
      );
    }

    if (filterDay !== "all") {
      result = result.filter((item) => item.day === parseInt(filterDay));
    }

    if (filterInstructor !== "all") {
      result = result.filter((item) => item.instructor_name === filterInstructor);
    }

    const sortMultiplier = sortOrder === "asc" ? 1 : -1;
    switch (sortBy) {
      case "day":
        result.sort((a, b) => (a.day - b.day || (a.start || "").localeCompare(b.start || "")) * sortMultiplier);
        break;
      case "course":
        result.sort((a, b) => ((a.course_title || "").localeCompare(b.course_title || "")) * sortMultiplier);
        break;
      case "instructor":
        result.sort((a, b) => ((a.instructor_name || "").localeCompare(b.instructor_name || "")) * sortMultiplier);
        break;
      case "students":
        result.sort((a, b) => (a.predicted_students - b.predicted_students) * sortMultiplier);
        break;
      case "capacity":
        result.sort((a, b) => (a.estimated_capacity || 0) - (b.estimated_capacity || 0) * sortMultiplier);
        break;
      case "required":
        result.sort((a, b) => (a.required_classes || 0) - (b.required_classes || 0) * sortMultiplier);
        break;
      default:
        break;
    }
    return result;
  }, [classes, searchTerm, filterDay, filterInstructor, sortBy, sortOrder]);

  const handleSortChange = (newSortBy) => {
    if (sortBy === newSortBy) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(newSortBy);
      setSortOrder("asc");
    }
  };

  const handleRowClick = (index) => {
    setExpandedRow(expandedRow === index ? null : index);
    if (onClassClick && filteredClasses[index]) {
      onClassClick(filteredClasses[index]);
    }
  };

  if (!classes || classes.length === 0) {
    return (
      <div className="schedule-empty-state">
        <div className="empty-animation">
          <div className="empty-icon-wrapper">
            <span className="empty-emoji">📋</span>
            <div className="empty-pulse-ring" />
          </div>
        </div>
        <h3>برنامه‌ای تولید نشده است</h3>
        <p>
          برای تولید برنامه، روی دکمه <strong>«تولید برنامه»</strong> یا <strong>«شروع فرایند گام‌به‌گام»</strong> در
          بالای صفحه کلیک کنید.
        </p>
        <div className="empty-hint">
          <span className="hint-icon">💡</span>
          <span>پس از تولید، برنامه هفتگی در اینجا نمایش داده می‌شود.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="schedule-wrapper">
      {/* ===== هدر ===== */}
      <div className="schedule-header">
        <div className="schedule-title-section">
          <div className="title-group">
            <h2>
              <span className="title-icon">🗓️</span>
              برنامه هفتگی
              <span className="class-count-badge">{filteredClasses.length} کلاس</span>
            </h2>
            <span className="schedule-subtitle">
              {stats && `${stats.uniqueInstructors} استاد · ${stats.uniqueRooms} اتاق · ${stats.totalGroups} گروه`}
            </span>
          </div>
          <div className="schedule-actions">
            <button className="action-btn" onClick={() => setViewMode(viewMode === "table" ? "grid" : "table")}>
              {viewMode === "table" ? (
                <>
                  <FaThLarge /> کارتی
                </>
              ) : (
                <>
                  <FaTable /> جدولی
                </>
              )}
            </button>
            <button className="action-btn" onClick={() => alert("خروجی Excel در حال توسعه")}>
              <FaFileExport /> خروجی
            </button>
          </div>
        </div>

        {stats && (
          <div className="schedule-stats-grid">
            <div className="stat-card-mini">
              <div className="stat-icon purple">📚</div>
              <div className="stat-info">
                <span className="stat-number">{stats.total}</span>
                <span className="stat-label">کلاس</span>
              </div>
            </div>
            <div className="stat-card-mini">
              <div className="stat-icon blue">👨‍🏫</div>
              <div className="stat-info">
                <span className="stat-number">{stats.uniqueInstructors}</span>
                <span className="stat-label">استاد</span>
              </div>
            </div>
            <div className="stat-card-mini">
              <div className="stat-icon green">🏫</div>
              <div className="stat-info">
                <span className="stat-number">{stats.uniqueRooms}</span>
                <span className="stat-label">اتاق</span>
              </div>
            </div>
            <div className="stat-card-mini">
              <div className="stat-icon orange">👤</div>
              <div className="stat-info">
                <span className="stat-number">{stats.totalStudents}</span>
                <span className="stat-label">دانشجو</span>
              </div>
            </div>
            <div className="stat-card-mini">
              <div className="stat-icon teal">📦</div>
              <div className="stat-info">
                <span className="stat-number">{stats.totalGroups}</span>
                <span className="stat-label">گروه</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ===== نوار ابزار ===== */}
      <div className="schedule-toolbar">
        <div className="search-box">
          <FaSearch className="search-icon" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="جستجو در دروس، اساتید، کلاس‌ها..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          {searchTerm && (
            <button className="clear-search" onClick={() => setSearchTerm("")} aria-label="پاک کردن جستجو">
              ×
            </button>
          )}
        </div>
        <div className="toolbar-actions">
          <button
            className={`filter-toggle ${showFilters ? "active" : ""}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            <FaFilter /> فیلترها
          </button>
          <span className="result-count">{filteredClasses.length} کلاس</span>
        </div>
      </div>

      {/* ===== پنل فیلترها ===== */}
      <div className={`filters-panel ${showFilters ? "open" : ""}`}>
        <div className="filters-grid">
          <div className="filter-group">
            <label>
              <FaCalendarAlt className="filter-icon" /> روز هفته
            </label>
            <select value={filterDay} onChange={(e) => setFilterDay(e.target.value)}>
              <option value="all">همه روزها</option>
              {DAYS.map((day, index) => (
                <option key={index} value={index}>
                  {day}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>
              <FaUser className="filter-icon" /> استاد
            </label>
            <select value={filterInstructor} onChange={(e) => setFilterInstructor(e.target.value)}>
              <option value="all">همه اساتید</option>
              {uniqueInstructors.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group sort-group">
            <label>مرتب‌سازی بر اساس</label>
            <div className="sort-buttons">
              {["day", "course", "instructor", "capacity", "required"].map((key) => {
                const labels = { day: "روز", course: "درس", instructor: "استاد", capacity: "ظرفیت", required: "کلاس موردنیاز" };
                return (
                  <button
                    key={key}
                    className={`sort-btn ${sortBy === key ? "active" : ""}`}
                    onClick={() => handleSortChange(key)}
                  >
                    {labels[key]}
                    {sortBy === key && (sortOrder === "asc" ? <FaSortUp /> : <FaSortDown />)}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ===== نمایش جدول یا کارت ===== */}
      {viewMode === "table" ? (
        <div className="schedule-table-container">
          <div className="table-responsive-wrapper">
            <table className="schedule-table-modern">
              <thead>
                <tr>
                  <th className="col-id">#</th>
                  <th className="col-course">درس</th>
                  <th className="col-group">گروه</th>
                  <th className="col-instructor">استاد</th>
                  <th className="col-room">کلاس</th>
                  <th className="col-day">روز</th>
                  <th className="col-time">ساعت</th>
                  <th className="col-students">دانشجو</th>
                  <th className="col-capacity">ظرفیت</th>
                  <th className="col-required">کلاس موردنیاز</th>
                  <th className="col-expand">▸</th>
                </tr>
              </thead>
              <tbody>
                {filteredClasses.length === 0 ? (
                  <tr>
                    <td colSpan="11" className="no-result">
                      <span className="no-result-icon">🔍</span>
                      هیچ کلاسی با این فیلترها یافت نشد.
                    </td>
                  </tr>
                ) : (
                  filteredClasses.map((item, index) => {
                    const isExpanded = expandedRow === index;
                    return (
                      <React.Fragment key={item.id || index}>
                        <tr
                          className={`schedule-row ${isExpanded ? "expanded" : ""}`}
                          onClick={() => handleRowClick(index)}
                        >
                          <td className="row-number">{index + 1}</td>
                          <td>
                            <div className="course-info">
                              <span className="course-code">{item.course_code}</span>
                              <span className="course-title">{item.course_title}</span>
                            </div>
                          </td>
                          <td>
                            <span className="group-badge">گروه {item.group_number || 1}</span>
                          </td>
                          <td className="instructor-cell">
                            <span className="instructor-name">{item.instructor_name}</span>
                          </td>
                          <td className="room-cell">{item.room_name}</td>
                          <td>
                            <span className="day-badge" style={{ backgroundColor: DAY_COLORS[item.day] || "#6b7280" }}>
                              {getDayName(item.day)}
                            </span>
                          </td>
                          <td>
                            <span className="time-range">
                              <span className="time-start">{item.start}</span>
                              <span className="time-separator">–</span>
                              <span className="time-end">{item.end}</span>
                            </span>
                          </td>
                          <td>
                            <span className="student-badge">
                              <FaUsers /> {item.predicted_students || 0}
                            </span>
                          </td>
                          <td>
                            <span className="capacity-badge">
                              {item.estimated_capacity || "—"}
                            </span>
                          </td>
                          <td>
                            <span className="required-classes-badge">
                              {item.required_classes || "—"}
                            </span>
                          </td>
                          <td>
                            <span className="expand-icon">
                              {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                            </span>
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr className="expanded-details">
                            <td colSpan="11">
                              <div className="expanded-content">
                                <div className="detail-grid">
                                  <div className="detail-item">
                                    <span className="detail-label">کد درس</span>
                                    <span className="detail-value">{item.course_code}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">عنوان</span>
                                    <span className="detail-value">{item.course_title}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">استاد</span>
                                    <span className="detail-value">{item.instructor_name}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">کلاس</span>
                                    <span className="detail-value">{item.room_name}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">ظرفیت کلاس</span>
                                    <span className="detail-value">{item.room_capacity || "—"}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">گروه</span>
                                    <span className="detail-value">{item.group_number || 1}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">تعداد دانشجو</span>
                                    <span className="detail-value">{item.predicted_students || 0}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">ظرفیت درس</span>
                                    <span className="detail-value">{item.estimated_capacity || "—"}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">کلاس مورد نیاز</span>
                                    <span className="detail-value">{item.required_classes || "—"}</span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">نوع درس</span>
                                    <span className="detail-value">{item.course_type || "—"}</span>
                                  </div>
                                </div>
                                {item.explanation && item.explanation.length > 0 && (
                                  <div className="explanation-section">
                                    <div className="explanation-title">
                                      <FaInfoCircle /> توضیحات
                                    </div>
                                    <ul className="explanation-list">
                                      {item.explanation.map((text, i) => (
                                        <li key={i}>{text}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="schedule-grid-view">
          {filteredClasses.length === 0 ? (
            <div className="no-result-card">هیچ کلاسی با این فیلترها یافت نشد.</div>
          ) : (
            filteredClasses.map((item, index) => (
              <div
                key={item.id || index}
                className="schedule-card"
                onClick={() => handleRowClick(index)}
              >
                <div className="card-header">
                  <span className="card-day" style={{ backgroundColor: DAY_COLORS[item.day] || "#6b7280" }}>
                    {getDayName(item.day)}
                  </span>
                  <span className="card-time">
                    {item.start} – {item.end}
                  </span>
                </div>
                <div className="card-body">
                  <div className="card-course">
                    <span className="card-course-code">{item.course_code}</span>
                    <span className="card-course-title">{item.course_title}</span>
                  </div>
                  <div className="card-meta">
                    <div className="card-meta-item">
                      <FaUser /> {item.instructor_name}
                    </div>
                    <div className="card-meta-item">
                      <FaDoorOpen /> {item.room_name}
                    </div>
                    <div className="card-meta-item">
                      <FaUsers /> {item.predicted_students || 0}
                    </div>
                    <div className="card-meta-item">
                      <span>ظرفیت: {item.estimated_capacity || "—"}</span>
                    </div>
                    <div className="card-meta-item">
                      <span>کلاس موردنیاز: {item.required_classes || "—"}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <div className="schedule-footer">
        <span>نمایش {filteredClasses.length} از {classes.length} کلاس</span>
        <span className="footer-separator">|</span>
        <span>تولید شده با 🧠 موتور برنامه‌ریزی هوشمند</span>
      </div>
    </div>
  );
}