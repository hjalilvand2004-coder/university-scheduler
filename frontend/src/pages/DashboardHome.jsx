// frontend/src/pages/DashboardHome.jsx — نسخه بازطراحی‌شده
import { useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid,
} from "recharts";
import ScheduleTable from "../components/ScheduleTable";
import ExplanationPanel from "../components/ExplanationPanel";
import "./DashboardHome.css";

const CHART_COLORS = ["#4f46e5", "#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#ef4444"];

const FA_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
const toFa = (n) => String(n).replace(/\d/g, (d) => FA_DIGITS[+d]);

export default function DashboardHome({
  uniqueCourses = [],
  offeredCourses = [],
  instructors = [],
  rooms = [],
  historyRecords = [],
  termCourses = [],
  teachingPreferences = [],
  timePreferences = [],
  baskets = [],
  schedule = null,
  rankedCourses = null,
  onNavigate,
  onSelectBasket,
  loading = false,
}) {
  // ===== آمار دروس به تفکیک ترم (نمودار میله‌ای) =====
  const termChartData = useMemo(() => {
    const byTerm = {};
    for (const tc of termCourses) {
      const t = tc?.term || "نامشخص";
      const m = String(t).match(/\d+/);
      const num = m ? parseInt(m[0], 10) : null;
      const key = num && num >= 1 && num <= 8 ? `ترم ${toFa(num)}` : "سایر";
      byTerm[key] = (byTerm[key] || 0) + 1;
    }
    const order = ["ترم ۱", "ترم ۲", "ترم ۳", "ترم ۴", "ترم ۵", "ترم ۶", "ترم ۷", "ترم ۸", "سایر"];
    return order.filter((k) => byTerm[k]).map((k) => ({ name: k, value: byTerm[k] }));
  }, [termCourses]);

  // ===== توزیع نوع کلاس‌ها (نمودار دونات) =====
  const typeChartData = useMemo(() => {
    const byType = {};
    for (const oc of offeredCourses) {
      const t = (oc?.course_type || oc?.type || "").toString().trim() || "نامشخص";
      byType[t] = (byType[t] || 0) + 1;
    }
    return Object.entries(byType)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [offeredCourses]);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>در حال بارگذاری داده‌ها...</p>
      </div>
    );
  }

  const classesCount = schedule?.classes?.length || 0;
  const unitsSum = termCourses.reduce((s, t) => s + (parseInt(t?.units, 10) || 0), 0);

  // ===== کارت‌های KPI =====
  const kpis = [
    { icon: "📚", label: "دروس یکتا", value: uniqueCourses.length, grad: "g-indigo", page: "unique-courses" },
    { icon: "👨‍🏫", label: "اساتید", value: instructors.length, grad: "g-violet", page: "instructors" },
    { icon: "🏫", label: "کلاس‌ها", value: rooms.length, grad: "g-cyan", page: "rooms" },
    { icon: "🗓️", label: "کلاس‌های برنامه", value: classesCount, grad: "g-emerald", page: "optimization" },
  ];

  const secondaryStats = [
    { label: "دروس ارائه‌شده", value: offeredCourses.length, page: "offered-courses" },
    { label: "دروس ترمیک", value: termCourses.length, page: "term-courses" },
    { label: "جمع واحدها", value: unitsSum, page: "term-courses" },
    { label: "سوابق برنامه", value: historyRecords.length, page: "schedule-history" },
    { label: "مطلوبیت تدریس", value: teachingPreferences.length, page: "teaching-preferences" },
    { label: "مطلوبیت زمانی", value: timePreferences.length, page: "time-preferences" },
    { label: "سبدهای دروس", value: baskets.length, page: "basket-list" },
  ];

  const recentBaskets = baskets.slice(-5).reverse();

  return (
    <div className="dashboard-home">
      {/* ===== بنر خوش‌آمد ===== */}
      <section className="hero-banner t-anim">
        <div className="hero-pattern" aria-hidden="true" />
        <div className="hero-content">
          <span className="hero-badge">هسته بهینه‌سازی Google OR-Tools CP-SAT</span>
          <h2>سلام مدیر گرام 👋</h2>
          <p>
            به سامانه هوشمند برنامه‌ریزی درسی خوش آمدید. از اینجا می‌توانید داده‌های پایه را مدیریت کرده و
            برنامه هفتگی کلاس‌ها را به‌صورت خودکار تولید، تخصیص کلاس و بهینه‌سازی کنید.
          </p>
          <div className="hero-actions">
            <button className="hero-btn primary" onClick={() => onNavigate("basket-list")}>
              🚀 شروع تولید برنامه
            </button>
            <button className="hero-btn ghost" onClick={() => onNavigate("term-courses")}>
              📅 مدیریت دروس ترمیک
            </button>
            <button className="hero-btn ghost" onClick={() => onNavigate("instructors")}>
              👨‍🏫 ثبت اساتید
            </button>
          </div>
        </div>
        <div className="hero-stats">
          <div className="hero-stat">
            <span className="hs-num">{toFa(uniqueCourses.length)}</span>
            <span className="hs-label">درس در پایگاه داده</span>
          </div>
          <div className="hero-stat">
            <span className="hs-num">{toFa(instructors.length)}</span>
            <span className="hs-label">عضو هیئت علمی</span>
          </div>
          <div className="hero-stat">
            <span className="hs-num">{toFa(rooms.length)}</span>
            <span className="hs-label">کلاس فعال</span>
          </div>
        </div>
      </section>

      {/* ===== کارت‌های آمار اصلی ===== */}
      <section className="kpi-grid">
        {kpis.map((k, i) => (
          <button key={k.label} className={`kpi-card t-anim t-anim-delay-${i + 1} ${k.grad}`} onClick={() => onNavigate(k.page)}>
            <span className="kpi-icon">{k.icon}</span>
            <span className="kpi-info">
              <span className="kpi-value">{toFa(k.value)}</span>
              <span className="kpi-label">{k.label}</span>
            </span>
            <span className="kpi-arrow">←</span>
          </button>
        ))}
      </section>

      {/* ===== آمارهای فرعی ===== */}
      <section className="mini-stats t-anim t-anim-delay-2">
        {secondaryStats.map((s) => (
          <button key={s.label} className="mini-stat" onClick={() => onNavigate(s.page)}>
            <span className="ms-value">{toFa(s.value)}</span>
            <span className="ms-label">{s.label}</span>
          </button>
        ))}
      </section>

      {/* ===== نمودارها ===== */}
      <section className="charts-row">
        <div className="chart-card t-anim t-anim-delay-3">
          <div className="chart-head">
            <h3>📊 توزیع دروس ترمیک بر اساس ترم</h3>
            <span className="chart-sub">مجموع {toFa(termCourses.length)} درس ترمیک ثبت‌شده</span>
          </div>
          <div className="chart-body">
            {termChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={termChartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#818cf8" />
                      <stop offset="100%" stopColor="#4f46e5" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 6" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b", fontFamily: "Vazirmatn" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontFamily: "Vazirmatn", fontSize: 12.5, direction: "rtl" }}
                    formatter={(v) => [`${toFa(v)} درس`, "تعداد"]}
                  />
                  <Bar dataKey="value" fill="url(#barGrad)" radius={[8, 8, 0, 0]} maxBarSize={44} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">هنوز درس ترمیکی ثبت نشده است</div>
            )}
          </div>
        </div>

        <div className="chart-card t-anim t-anim-delay-4">
          <div className="chart-head">
            <h3>🥧 ترکیب نوع کلاس‌های ارائه‌شده</h3>
            <span className="chart-sub">بر اساس فیلد نوع درس</span>
          </div>
          <div className="chart-body">
            {typeChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={typeChartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={62}
                    outerRadius={95}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {typeChartData.map((entry, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontFamily: "Vazirmatn", fontSize: 12.5, direction: "rtl" }}
                    formatter={(v, n) => [`${toFa(v)} درس`, n]}
                  />
                  <Legend
                    formatter={(v) => <span style={{ color: "#475569", fontSize: 12, fontFamily: "Vazirmatn" }}>{v}</span>}
                    iconType="circle"
                    iconSize={8}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">هنوز درس ارائه‌ای ثبت نشده است</div>
            )}
          </div>
        </div>
      </section>

      {/* ===== دسترسی سریع ===== */}
      <section className="quick-actions t-anim t-anim-delay-3">
        <h3>🚀 دسترسی سریع</h3>
        <div className="action-grid">
          {[
            { id: "basket-list", label: "لیست سبدها", icon: "🗂️" },
            { id: "basket", label: "سبد دروس", icon: "📦" },
            { id: "instructor-time", label: "زمان‌بندی استاد", icon: "⏳" },
            { id: "room-allocation", label: "تخصیص کلاس", icon: "🏢" },
            { id: "optimization", label: "بهینه‌سازی", icon: "⚡" },
            { id: "unique-courses", label: "دروس یکتا", icon: "📚" },
            { id: "offered-courses", label: "دروس ارائه", icon: "📖" },
            { id: "schedule-history", label: "سوابق", icon: "📜" },
          ].map((a) => (
            <button key={a.id} className="quick-action-btn" onClick={() => onNavigate(a.id)}>
              <span className="qa-icon">{a.icon}</span>
              {a.label}
            </button>
          ))}
        </div>
      </section>

      {/* ===== سبدهای اخیر ===== */}
      {recentBaskets.length > 0 && (
        <section className="recent-baskets t-anim">
          <h3>📋 سبدهای اخیر</h3>
          <div className="basket-list">
            {recentBaskets.map((basket) => (
              <div
                key={basket.id}
                className="basket-item"
                onClick={() => (onSelectBasket ? onSelectBasket(basket.id) : onNavigate("basket"))}
              >
                <span className="basket-title">{basket.title}</span>
                <span className="basket-meta">
                  {basket.semester} — {basket.year}
                  <span className="basket-count">{toFa(basket.items_count || 0)} درس</span>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ===== برنامه فعلی ===== */}
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
            <p className="empty-hint">
              برای تولید برنامه، از بخش «تولید برنامه هفتگی» و سبد دروس استفاده کنید.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
