// components/TimeSlotSelector.jsx
import React, { useState, useEffect } from "react";
import "./TimeSlotSelector.css";

const DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];
const TIME_GROUPS = [
  { id: "morning", label: "صبح", start: "08:00", end: "12:00" },
  { id: "afternoon", label: "ظهر", start: "12:00", end: "16:00" },
  { id: "evening", label: "عصر", start: "16:00", end: "20:00" },
];

function TimeSlotSelector({ instructors, onChange, initialSelections = [] }) {
  const [selectedInstructor, setSelectedInstructor] = useState("");
  const [selections, setSelections] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);

  useEffect(() => {
    if (initialSelections.length > 0) {
      setSelections(initialSelections);
    }
  }, [initialSelections]);

  useEffect(() => {
    if (onChange) {
      onChange(selections);
    }
  }, [selections, onChange]);

  const handleInstructorChange = (e) => {
    setSelectedInstructor(e.target.value);
  };

  const handleDayClick = (day) => {
    setSelectedDay(selectedDay === day ? null : day);
  };

  const handleTimeGroupClick = (day, timeGroup) => {
    if (!selectedInstructor) {
      alert("لطفاً ابتدا استاد را انتخاب کنید.");
      return;
    }

    // پیدا کردن استاد انتخاب‌شده
    const instructor = instructors.find(
      (inst) => (inst.code || inst.id) === selectedInstructor
    );
    if (!instructor) {
      alert("استاد انتخاب‌شده معتبر نیست.");
      return;
    }

    // بررسی تکراری نبودن
    const exists = selections.some(
      (sel) => sel.day === day && sel.timeGroup === timeGroup.id
    );
    if (exists) {
      alert("این بازه زمانی قبلاً انتخاب شده است.");
      return;
    }

    // ساخت آبجکت با تمام فیلدهای مورد نیاز بک‌اند
    const newSelection = {
      day: day,
      timeGroup: timeGroup.id,
      start_time: timeGroup.start,
      end_time: timeGroup.end,
      time_group: timeGroup.label,
      instructor_code: instructor.code,    // ← استفاده از code
      instructor_name: instructor.name,
      instructor_username: instructor.username || "",
      cooperation_type: instructor.cooperation_type || "",
      expert_group: instructor.group || "",
      priority: selections.length + 1,
      status: true, // فعال
    };

    setSelections([...selections, newSelection]);
    setSelectedDay(null);
  };

  const removeSelection = (index) => {
    const newSelections = selections.filter((_, i) => i !== index);
    const reordered = newSelections.map((sel, idx) => ({
      ...sel,
      priority: idx + 1,
    }));
    setSelections(reordered);
  };

  const groupedSelections = DAYS.reduce((acc, day) => {
    acc[day] = selections.filter((sel) => sel.day === day);
    return acc;
  }, {});

  return (
    <div className="time-slot-selector">
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

      <div className="weekly-calendar">
        <h4>روز مورد نظر را انتخاب کنید و سپس روی بازه زمانی کلیک کنید</h4>
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
          <div className="time-groups">
            <p className="hint-text">روز {selectedDay} - روی یکی از بازه‌های زیر کلیک کنید:</p>
            <div className="groups-row">
              {TIME_GROUPS.map((group) => {
                const alreadySelected = selections.some(
                  (sel) => sel.day === selectedDay && sel.timeGroup === group.id
                );
                return (
                  <button
                    key={group.id}
                    className={`time-group-btn ${alreadySelected ? "selected" : ""}`}
                    onClick={() => handleTimeGroupClick(selectedDay, group)}
                    disabled={alreadySelected}
                  >
                    <span className="group-label">{group.label}</span>
                    <span className="group-time">
                      {group.start} - {group.end}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

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
                          {sel.time_group} ({sel.start_time} - {sel.end_time})
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