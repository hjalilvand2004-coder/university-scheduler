import { useState } from "react";

export default function InstructorPreferences({ instructors }) {
  const [selectedInstructor, setSelectedInstructor] = useState(null);

  const days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه"];
  const hours = ["08:00-10:00", "10:00-12:00", "13:00-15:00", "15:00-17:00"];

  return (
    <div className="preferences-container">
      <h2>👨‍🏫 مطلوبیت‌های اساتید</h2>
      <div className="preferences-filter">
        <label>انتخاب استاد:</label>
        <select
          onChange={(e) => {
            const instructor = instructors.find(
              (i) => i.id === parseInt(e.target.value)
            );
            setSelectedInstructor(instructor);
          }}
        >
          <option value="">همه اساتید</option>
          {instructors.map((inst) => (
            <option key={inst.id} value={inst.id}>
              {inst.name}
            </option>
          ))}
        </select>
      </div>

      <div className="preferences-grid">
        <div className="preference-card">
          <h3>دروس مورد علاقه</h3>
          <ul>
            {selectedInstructor?.qualified_course_ids?.map((courseId) => (
              <li key={courseId}>درس {courseId}</li>
            )) || <li>دروسی انتخاب نشده است</li>}
          </ul>
        </div>

        <div className="preference-card">
          <h3>روزهای مطلوب</h3>
          <div className="days-grid">
            {days.map((day, index) => (
              <div
                key={day}
                className={`day-cell ${
                  selectedInstructor?.preferred_days?.includes(index)
                    ? "preferred"
                    : ""
                }`}
              >
                {day}
                {selectedInstructor?.preferred_days?.includes(index) && " ✅"}
              </div>
            ))}
          </div>
        </div>

        <div className="preference-card">
          <h3>ساعات مطلوب</h3>
          <div className="hours-grid">
            {hours.map((hour, index) => (
              <div
                key={hour}
                className={`hour-cell ${
                  selectedInstructor?.preferred_slots?.includes(index + 1)
                    ? "preferred"
                    : ""
                }`}
              >
                {hour}
                {selectedInstructor?.preferred_slots?.includes(index + 1) &&
                  " ✅"}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}