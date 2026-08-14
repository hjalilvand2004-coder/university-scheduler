import { useState } from "react";
import CourseForm from "./CourseForm";
import ExcelUpload from "./ExcelUpload";
import TimeSlotSelector from "./TimeSlotSelector";

export default function CourseList({
  courses,
  onAdd,
  onUpdate,
  onDelete,
  onUpload,
  title,
  columns,
  type,
  instructorsList = [], // لیست اساتید
  coursesList = [],     // لیست دروس یکتا (برای مطلوبیت‌های تدریس)
  onDataChange,
}) {
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  // State برای مودال زمان‌بندی
  const [timeSlots, setTimeSlots] = useState([]);
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // State برای مودال مطلوبیت‌های تدریس
  const [teachingData, setTeachingData] = useState({
    instructor_code: "",
    instructor_name: "",
    expert_group: "",
    cooperation_type: "",
    unique_course_code: "",
    course_name: "",
    status: true,
    term_code: "",
  });
  const [showTeachingModal, setShowTeachingModal] = useState(false);
  const [isSubmittingTeaching, setIsSubmittingTeaching] = useState(false);

  // ===== توابع مدیریتی =====
  const handleEdit = (course) => {
    setEditingCourse(course);
    setEditingId(course.id);
    setShowForm(true);
  };

  const handleSubmit = (data) => {
    if (editingId) {
      onUpdate(editingId, data);
    } else {
      onAdd(data);
    }
    setShowForm(false);
    setEditingId(null);
    setEditingCourse(null);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setEditingCourse(null);
  };

  // ===== مودال زمان‌بندی =====
  const openTimeModal = () => {
    setTimeSlots([]);
    setShowTimeModal(true);
  };

  const handleTimeSlotsChange = (slots) => {
    setTimeSlots(slots);
  };

  const handleTimeSubmit = async () => {
    if (timeSlots.length === 0) {
      alert("لطفاً حداقل یک بازه زمانی انتخاب کنید.");
      return;
    }

    setIsSubmitting(true);
    try {
      for (const slot of timeSlots) {
        const record = {
          day: slot.day,
          instructor_code: slot.instructor_code,
          instructor_name: slot.instructor_name,
          instructor_username: slot.instructor_username || "",
          start_time: slot.start_time,
          end_time: slot.end_time,
          time_group: slot.time_group,
          priority: slot.priority,
          status: true,
          cooperation_type: slot.cooperation_type || "",
          expert_group: slot.expert_group || "",
        };
        await onAdd(record);
      }
      setShowTimeModal(false);
      setTimeSlots([]);
      if (typeof onDataChange === "function") onDataChange();
    } catch (error) {
      console.error("خطا در ذخیره مطلوبیت‌های زمان:", error);
      alert(`خطا در ذخیره اطلاعات: ${error.message || "خطای ناشناخته"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ===== مودال مطلوبیت‌های تدریس =====
  const openTeachingModal = () => {
    setTeachingData({
      instructor_code: "",
      instructor_name: "",
      expert_group: "",
      cooperation_type: "",
      unique_course_code: "",
      course_name: "",
      status: true,
      term_code: "",
    });
    setShowTeachingModal(true);
  };

  const handleTeachingFieldChange = (field, value) => {
    setTeachingData(prev => ({ ...prev, [field]: value }));
  };

  const handleInstructorChange = (e) => {
    const code = e.target.value;
    const instructor = instructorsList.find(inst => inst.code === code);
    if (instructor) {
      setTeachingData(prev => ({
        ...prev,
        instructor_code: code,
        instructor_name: instructor.name || "",
        expert_group: instructor.group || "",
        cooperation_type: instructor.cooperation_type || "",
      }));
    } else {
      setTeachingData(prev => ({
        ...prev,
        instructor_code: code,
        instructor_name: "",
        expert_group: "",
        cooperation_type: "",
      }));
    }
  };

  const handleCourseChange = (e) => {
    const code = e.target.value;
    const course = coursesList.find(c => c.code === code);
    if (course) {
      setTeachingData(prev => ({
        ...prev,
        unique_course_code: code,
        course_name: course.title || "",
      }));
    } else {
      setTeachingData(prev => ({
        ...prev,
        unique_course_code: code,
        course_name: "",
      }));
    }
  };

  const handleTeachingSubmit = async () => {
    // اعتبارسنجی
    if (!teachingData.instructor_code || !teachingData.unique_course_code) {
      alert("لطفاً استاد و درس را انتخاب کنید.");
      return;
    }

    setIsSubmittingTeaching(true);
    try {
      const record = {
        unique_course_code: teachingData.unique_course_code,
        course_name: teachingData.course_name,
        instructor_code: teachingData.instructor_code,
        instructor_name: teachingData.instructor_name,
        expert_group: teachingData.expert_group,
        cooperation_type: teachingData.cooperation_type,
        status: teachingData.status,
        term_code: teachingData.term_code || "",
        // row_number: courses.length + 1, // در صورت نیاز
      };
      await onAdd(record);
      setShowTeachingModal(false);
      setTeachingData({
        instructor_code: "",
        instructor_name: "",
        expert_group: "",
        cooperation_type: "",
        unique_course_code: "",
        course_name: "",
        status: true,
        term_code: "",
      });
      if (typeof onDataChange === "function") onDataChange();
    } catch (error) {
      console.error("خطا در ذخیره مطلوبیت تدریس:", error);
      alert(`خطا در ذخیره اطلاعات: ${error.message || "خطای ناشناخته"}`);
    } finally {
      setIsSubmittingTeaching(false);
    }
  };

  // ===== فیلتر جستجو =====
  const filteredCourses = courses.filter((course) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.trim().toLowerCase();
    return columns.some((col) => {
      const value = course[col.key];
      if (value && typeof value === "string") {
        return value.toLowerCase().includes(term);
      }
      if (value && typeof value === "number") {
        return value.toString().includes(term);
      }
      return false;
    });
  });

  // ============================================================
  // رندر اصلی
  // ============================================================
  return (
    <div className="course-list-container">
      <div className="course-list-header">
        <h2>{title}</h2>
        <div className="course-list-actions">
          <div className="search-box">
            <input
              type="text"
              placeholder="جستجو..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            {searchTerm && (
              <button className="clear-search" onClick={() => setSearchTerm("")}>
                ✕
              </button>
            )}
          </div>
          <button
            className="btn-primary"
            onClick={
              type === "time-preferences"
                ? openTimeModal
                : type === "teaching-preferences"
                ? openTeachingModal
                : () => setShowForm(true)
            }
          >
            ➕ افزودن
          </button>
          <ExcelUpload onUpload={onUpload} type={type} />
        </div>
      </div>

      {/* فرم معمولی برای سایر انواع */}
      {showForm && (
        <CourseForm
          course={editingCourse}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          type={type}
          instructorsList={instructorsList}
          coursesList={coursesList}
        />
      )}

      {/* مودال اختصاصی برای مطلوبیت‌های زمان‌بندی */}
      {showTimeModal && type === "time-preferences" && (
        <div className="modal-overlay" onClick={() => setShowTimeModal(false)}>
          <div className="modal-content time-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>➕ افزودن مطلوبیت‌های زمان‌بندی</h3>
              <button className="modal-close" onClick={() => setShowTimeModal(false)}>
                ×
              </button>
            </div>
            <div className="modal-body">
              <TimeSlotSelector
                instructors={instructorsList}
                onChange={handleTimeSlotsChange}
                initialSelections={[]}
              />
            </div>
            <div className="modal-footer">
              <button
                className="btn-primary"
                onClick={handleTimeSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? "در حال ذخیره..." : "💾 ذخیره همه"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowTimeModal(false)}
                disabled={isSubmitting}
              >
                ❌ انصراف
              </button>
            </div>
          </div>
        </div>
      )}

      {/* مودال اختصاصی برای مطلوبیت‌های تدریس */}
      {showTeachingModal && type === "teaching-preferences" && (
        <div className="modal-overlay" onClick={() => setShowTeachingModal(false)}>
          <div className="modal-content teaching-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>➕ افزودن مطلوبیت تدریس</h3>
              <button className="modal-close" onClick={() => setShowTeachingModal(false)}>
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="teaching-form">
                <div className="form-group">
                  <label>استاد <span className="required">*</span></label>
                  <select
                    value={teachingData.instructor_code}
                    onChange={handleInstructorChange}
                    className="form-control"
                  >
                    <option value="">انتخاب استاد...</option>
                    {instructorsList.map(inst => (
                      <option key={inst.code} value={inst.code}>
                        {inst.name} ({inst.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>درس <span className="required">*</span></label>
                  <select
                    value={teachingData.unique_course_code}
                    onChange={handleCourseChange}
                    className="form-control"
                  >
                    <option value="">انتخاب درس...</option>
                    {coursesList.map(course => (
                      <option key={course.code} value={course.code}>
                        {course.title} ({course.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>نام استاد</label>
                  <input
                    type="text"
                    value={teachingData.instructor_name}
                    readOnly
                    className="form-control"
                  />
                </div>

                <div className="form-group">
                  <label>گروه تخصصی</label>
                  <input
                    type="text"
                    value={teachingData.expert_group}
                    readOnly
                    className="form-control"
                  />
                </div>

                <div className="form-group">
                  <label>نوع همکاری</label>
                  <input
                    type="text"
                    value={teachingData.cooperation_type}
                    readOnly
                    className="form-control"
                  />
                </div>

                <div className="form-group">
                  <label>کد ترم</label>
                  <input
                    type="text"
                    value={teachingData.term_code}
                    onChange={(e) => handleTeachingFieldChange("term_code", e.target.value)}
                    placeholder="مثلاً 14031"
                    className="form-control"
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={teachingData.status}
                      onChange={(e) => handleTeachingFieldChange("status", e.target.checked)}
                    />
                    فعال
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-primary"
                onClick={handleTeachingSubmit}
                disabled={isSubmittingTeaching}
              >
                {isSubmittingTeaching ? "در حال ذخیره..." : "💾 ذخیره"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowTeachingModal(false)}
                disabled={isSubmittingTeaching}
              >
                ❌ انصراف
              </button>
            </div>
          </div>
        </div>
      )}

      {/* جدول نمایش داده‌ها */}
      <div className="table-responsive">
        <table className="course-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key}>{col.label}</th>
              ))}
              <th>عملیات</th>
            </tr>
          </thead>
          <tbody>
            {filteredCourses.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="empty-state">
                  {searchTerm ? "هیچ نتیجه‌ای با جستجوی شما یافت نشد" : "هیچ داده‌ای موجود نیست"}
                </td>
              </tr>
            ) : (
              filteredCourses.map((course) => (
                <tr key={course.id}>
                  {columns.map((col) => {
                    let value = course[col.key];

                    if (col.key === "status") {
                      let isActive = false;
                      if (typeof value === "boolean") isActive = value;
                      else if (typeof value === "number") isActive = value === 1;
                      else if (typeof value === "string") {
                        const lower = value.toLowerCase();
                        isActive = lower === "true" || lower === "active" || value === "1";
                      } else {
                        isActive = Boolean(value);
                      }
                      return (
                        <td key={col.key}>
                          <span className={`status-badge ${isActive ? "active" : "inactive"}`}>
                            {isActive ? "فعال" : "غیرفعال"}
                          </span>
                        </td>
                      );
                    }

                    return <td key={col.key}>{value || "—"}</td>;
                  })}
                  <td className="actions-cell">
                    <button
                      className="btn-edit"
                      onClick={() => handleEdit(course)}
                      title="ویرایش"
                    >
                      ✏️
                    </button>
                    <button
                      className="btn-delete"
                      onClick={() => onDelete(course.id)}
                      title="حذف"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>تعداد کل: {courses.length}</span>
        {searchTerm && <span> | تعداد نتایج: {filteredCourses.length}</span>}
      </div>
    </div>
  );
}