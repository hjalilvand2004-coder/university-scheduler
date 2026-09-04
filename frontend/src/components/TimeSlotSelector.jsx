// frontend/src/components/TimeSlotSelector.jsx
import React, { useState, useEffect } from "react";
import { scheduleApi } from "../api/scheduleApi";
import "./TimeSlotSelector.css";

const DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];
const PERIOD_OPTIONS = [
  { value: "", label: "همه بازه‌ها" },
  { value: "morning", label: "صبح" },
  { value: "afternoon", label: "بعدازظهر" },
  { value: "evening", label: "عصر" },
];

function TimeSlotSelector({
  instructors = [],
  onChange,
  initialSelections = [],
  term = "mehr",           // ترم پیش‌فرض (می‌تواند از والد دریافت شود)
  units = 2,               // تعداد واحد پیش‌فرض
  period = "",             // فیلتر بازه (اختیاری)
}) {
  const [selectedInstructor, setSelectedInstructor] = useState("");
  const [selections, setSelections] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);

  // وضعیت مربوط به اسلات‌های دریافت‌شده از بک‌اند
  const [availableSlots, setAvailableSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // هم‌گام‌سازی انتخاب‌های اولیه
  useEffect(() => {
    if (initialSelections.length > 0) {
      setSelections(initialSelections);
    }
  }, [initialSelections]);

  // هرگاه انتخاب‌ها تغییر کنند، والد را مطلع می‌کنیم
  useEffect(() => {
    if (onChange) {
      onChange(selections);
    }
  }, [selections, onChange]);

  // دریافت اسلات‌های معتبر از بک‌اند با تغییر ترم، واحد یا فیلتر بازه
  useEffect(() => {
    const fetchSlots = async () => {
      if (!term || !units) return;
      setLoading(true);
      setError("");
      try {
        const response = await scheduleApi.searchSlots({
          term,
          units,
          period: period || undefined, // اگر خالی باشد، undefined ارسال می‌شود
        });
        setAvailableSlots(response.data.slots || []);
      } catch (err) {
        console.error("خطا در دریافت اسلات‌ها:", err);
        setError(err.response?.data?.detail || "خطا در دریافت زمان‌بندی");
        setAvailableSlots([]);
      } finally {
        setLoading(false);
      }
    };
    fetchSlots();
  }, [term, units, period]);

  // ----------------------------------------------
  // توابع مدیریت انتخاب‌ها
  // ----------------------------------------------

  const handleInstructorChange = (e) => {
    setSelectedInstructor(e.target.value);
  };

  const handleDayClick = (day) => {
    setSelectedDay(selectedDay === day ? null : day);
  };

  const handleSlotClick = (day, slotObj) => {
    if (!selectedInstructor) {
      alert("لطفاً ابتدا استاد را انتخاب کنید.");
      return;
    }

    const instructor = instructors.find(
      (inst) => (inst.code || inst.id) === selectedInstructor
    );
    if (!instructor) {
      alert("استاد انتخاب‌شده معتبر نیست.");
      return;
    }

    // بررسی تکراری نبودن برای همان روز و همان اسلات
    const exists = selections.some(
      (sel) => sel.day === day && sel.slot === slotObj.slot
    );
    if (exists) {
      alert("این بازه زمانی برای این روز قبلاً انتخاب شده است.");
      return;
    }

    // ساخت آبجکت انتخاب با استفاده از اطلاعات اسلات
    const newSelection = {
      day: day,
      slot: slotObj.slot,               // رشته مثل "07:30-09:15"
      start_time: slotObj.start,
      end_time: slotObj.end,
      period: slotObj.period,           // "morning"/"afternoon"/"evening"
      period_title: slotObj.period_title,
      instructor_code: instructor.code || instructor.id,
      instructor_name: instructor.name,
      instructor_username: instructor.username || "",
      cooperation_type: instructor.cooperation_type || "",
      expert_group: instructor.group || "",
      priority: selections.length + 1,
      status: true,
    };

    setSelections([...selections, newSelection]);
    setSelectedDay(null); // پس از انتخاب، روز را ریست می‌کنیم
  };

  const removeSelection = (index) => {
    const newSelections = selections.filter((_, i) => i !== index);
    const reordered = newSelections.map((sel, idx) => ({
      ...sel,
      priority: idx + 1,
    }));
    setSelections(reordered);
  };

  // گروه‌بندی انتخاب‌ها بر اساس روز برای نمایش
  const groupedSelections = DAYS.reduce((acc, day) => {
    acc[day] = selections.filter((sel) => sel.day === day);
    return acc;
  }, {});

  // ----------------------------------------------
  // رندر
  // ----------------------------------------------

  return (
    <div className="time-slot-selector">
      {/* انتخاب استاد */}
      <div className="instructor-selector">
        <label>استاد:</label>
        <select
          value={selectedInstructor}
          onChange={handleInstructorChange}
          className="instructor-combobox"
        >
          <option value="">انتخاب استاد...</option>
          {instructors.map((inst) => (
            <option key={inst.code || inst.id} value={inst.code || inst.id}>
              {inst.name} ({inst.code})
            </option>
          ))}
        </select>
      </div>

      {/* نمایش وضعیت بارگذاری/خطا */}
      {loading && <div className="loading-message">در حال بارگذاری اسلات‌ها...</div>}
      {error && <div className="error-message">{error}</div>}

      {/* تقویم هفتگی */}
      <div className="weekly-calendar">
        <h4>روز مورد نظر را انتخاب کنید و سپس روی یک بازه زمانی کلیک کنید</h4>
        <div className="days-row">
          {DAYS.map((day) => (
            <button
              key={day}
              className={`day-btn ${selectedDay === day ? "active" : ""}`}
              onClick={() => handleDayClick(day)}
            >
              {day}
            </button>
          ))}
        </div>

        {selectedDay && (
          <div className="time-slots">
            <p className="hint-text">روز {selectedDay} – بازه‌های معتبر برای ترم و واحد انتخاب‌شده:</p>
            {availableSlots.length === 0 ? (
              <p className="empty-slots">هیچ اسلاتی برای این ترم و تعداد واحد وجود ندارد.</p>
            ) : (
              <div className="slots-grid">
                {availableSlots.map((slotObj) => {
                  const alreadySelected = selections.some(
                    (sel) => sel.day === selectedDay && sel.slot === slotObj.slot
                  );
                  return (
                    <button
                      key={slotObj.slot}
                      className={`slot-btn ${alreadySelected ? "selected" : ""}`}
                      onClick={() => handleSlotClick(selectedDay, slotObj)}
                      disabled={alreadySelected || !selectedInstructor}
                    >
                      <span className="slot-time">{slotObj.slot}</span>
                      <span className="slot-period">{slotObj.period_title}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* لیست انتخاب‌های فعلی */}
      <div className="selections-list">
        <h4>انتخاب‌های فعلی</h4>
        {selections.length === 0 ? (
          <p className="empty-message">هیچ بازه‌ای انتخاب نشده است.</p>
        ) : (
          <div className="selections-grid">
            {DAYS.map((day) => {
              const items = groupedSelections[day] || [];
              if (items.length === 0) return null;
              return (
                <div key={day} className="day-selection-group">
                  <h5>{day}</h5>
                  {items.map((sel, idx) => {
                    const globalIndex = selections.indexOf(sel);
                    return (
                      <div key={idx} className="selection-item">
                        <span className="priority-badge">{sel.priority}</span>
                        <span className="time-label">
                          {sel.slot} ({sel.period_title})
                        </span>
                        <button
                          className="remove-btn"
                          onClick={() => removeSelection(globalIndex)}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default TimeSlotSelector;