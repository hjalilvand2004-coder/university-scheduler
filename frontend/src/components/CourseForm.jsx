// frontend/src/components/CourseForm.jsx
import { useState, useEffect } from "react";
import "./CourseForm.css"; // در صورت وجود فایل CSS

// ==========================================================
// ثابت‌های برگرفته از بک‌اند (برای هماهنگی)
// ==========================================================

// نگاشت روزهای هفته (همان DAY_MAP در slot_times.py)
const DAY_MAP = {
  "شنبه": 0,
  "یکشنبه": 1,
  "دوشنبه": 2,
  "سه‌شنبه": 3,
  "سهشنبه": 3,
  "چهارشنبه": 4,
  "پنجشنبه": 5,
  "جمعه": 6,
  "sat": 0,
  "sun": 1,
  "mon": 2,
  "tue": 3,
  "wed": 4,
  "thu": 5,
  "fri": 6,
};

// لیست روزهای هفته (برای سلکت)
const DAY_OPTIONS = [
  { value: "شنبه", label: "شنبه" },
  { value: "یکشنبه", label: "یکشنبه" },
  { value: "دوشنبه", label: "دوشنبه" },
  { value: "سه‌شنبه", label: "سه‌شنبه" },
  { value: "چهارشنبه", label: "چهارشنبه" },
  { value: "پنجشنبه", label: "پنجشنبه" },
];

// گزینه‌های ترم استاندارد (مطابق با TERM_ALIASES در بک‌اند)
const TERM_OPTIONS = [
  { value: "semester_1", label: "نیمسال اول (مهر)" },
  { value: "semester_2", label: "نیمسال دوم (بهمن)" },
  { value: "summer", label: "نیمسال تابستان" },
];

// گزینه‌های تعداد واحد
const UNIT_OPTIONS = [
  { value: 2, label: "۲ واحد" },
  { value: 3, label: "۳ واحد" },
  { value: 4, label: "۴ واحد" },
];

// ==========================================================
// کامپوننت اصلی
// ==========================================================
export default function CourseForm({ course, onSubmit, onCancel, type }) {
  // ===== state اولیه بر اساس نوع =====
  const getInitialState = () => {
    // فیلدهای مشترک برای همه انواع
    const base = {
      code: "",
      title: "",
      status: "active",
      group: "continuous_before_1403",
      estimated_capacity: 0,
    };

    // فیلدهای مخصوص دروس ارائه
    if (type === "offered") {
      return {
        ...base,
        row_number: "",
        offered_title: "",
        unique_code: "",
        unique_title: "",
        units: 2, // ← اضافه شد
        theoretical_hours: 0,
        practical_hours: 0,
        prerequisite: "",
        corequisite: "",
        year: "",
        course_type: "theory",
        is_active: true,
        type_course: "",
        term: "semester_1", // ← اضافه شد (برای ارتباط با اسلات‌ها)
      };
    }

    // فیلدهای مخصوص اساتید
    if (type === "instructors") {
      return {
        row_number: "",
        code: "",
        name: "",
        username: "",
        group: "",
        cooperation_type: "",
      };
    }

    // فیلدهای مخصوص اتاق‌ها
    if (type === "rooms") {
      return {
        row_number: "",
        code: "",
        name: "",
        capacity: "",
        group: "",
        place_type: "",
      };
    }

    // فیلدهای مخصوص سوابق برنامه‌ریزی
    if (type === "schedule-history") {
      return {
        semester: "",
        course_name: "",
        faculty_code: "",
        faculty_name_clean: "",
        department_code: "",
        department_name_clean: "",
        instructor_code: "",
        instructor_name_clean: "",
        max_capacity: "",
        level: "",
        course_type: "",
        day: "",
        start_time: "",
        end_time: "",
        exam_date: "",
        exam_start_time: "",
        exam_end_time: "",
        ref_course_title: "",
        ref_unique_course_code: "",
        ref_unique_course_title: "",
        class_code: "",
        class_name: "",
      };
    }

    // فیلدهای مخصوص دروس ترمیک
    if (type === "term-courses") {
      return {
        level: "",
        term: "semester_1", // ← تغییر به سلکت استاندارد
        row_number: "",
        course_name: "",
        units: 2,
        course_type: "",
        approximate_term: "",
        description: "",
        prerequisite_row_codes: "",
        corequisite_row_codes: "",
        unique_course_code: "",
        unique_course_name: "",
        year_identified: "",
      };
    }

    // فیلدهای مخصوص مطلوبیت‌های تدریس
    if (type === "teaching-preferences") {
      return {
        unique_course_code: "",
        course_name: "",
        cooperation_type: "",
        expert_group: "",
        row_number: "",
        instructor_code: "",
        instructor_name: "",
        instructor_username: "",
        status: "pending",
        term_code: "semester_1", // ← تغییر به سلکت استاندارد
      };
    }

    // فیلدهای مخصوص مطلوبیت‌های زمان‌بندی
    if (type === "time-preferences") {
      return {
        day: "شنبه",
        cooperation_type: "",
        end_time: "",
        expert_group: "",
        row_number: "",
        status: false,
        instructor_code: "",
        instructor_name: "",
        instructor_username: "",
        start_time: "",
        time_group: "",
        term: "semester_1", // ← اضافه شد
        units: 2, // ← اضافه شد (برای اعتبارسنجی اسلات)
      };
    }

    // حالت پیش‌فرض (دروس یکتا)
    return base;
  };

  const [formData, setFormData] = useState(getInitialState());

  useEffect(() => {
    if (course) {
      setFormData(course);
    } else {
      // اگر course وجود نداشت، state را به حالت اولیه بازنشانی کن
      setFormData(getInitialState());
    }
  }, [course, type]);

  const handleChange = (e) => {
    const { name, value, type: inputType, checked } = e.target;
    setFormData({
      ...formData,
      [name]: inputType === "checkbox" ? checked : value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  // ===== تعریف فیلدها بر اساس نوع =====
  const getFields = () => {
    if (type === "unique") {
      return [
        { name: "code", label: "کد درس یکتا", type: "text", required: true },
        { name: "title", label: "عنوان درس یکتا", type: "text", required: true },
        {
          name: "status",
          label: "وضعیت",
          type: "select",
          options: [
            { value: "active", label: "فعال" },
            { value: "inactive", label: "غیرفعال" },
          ],
        },
        {
          name: "group",
          label: "گروه",
          type: "select",
          options: [
            { value: "continuous_before_1403", label: "کارشناسی پیوسته قبل ۱۴۰۳" },
            { value: "continuous_after_1403", label: "کارشناسی پیوسته بعد از ۱۴۰۳" },
            { value: "non_continuous", label: "کارشناسی ناپیوسته" },
          ],
        },
        { name: "estimated_capacity", label: "برآورد ظرفیت", type: "number" },
      ];
    }

    if (type === "offered") {
      return [
        { name: "row_number", label: "شماره ردیف", type: "number" },
        { name: "offered_title", label: "عنوان درس در مقطع ارائه", type: "text", required: true },
        { name: "unique_code", label: "کد یکتا", type: "text", required: true },
        { name: "unique_title", label: "عنوان درس یکتا", type: "text", required: true },
        {
          name: "term",
          label: "ترم ارائه",
          type: "select",
          options: TERM_OPTIONS,
          required: true,
        },
        {
          name: "units",
          label: "تعداد واحد",
          type: "select",
          options: UNIT_OPTIONS,
          required: true,
        },
        { name: "theoretical_hours", label: "ساعت نظری", type: "number" },
        { name: "practical_hours", label: "ساعت عملی", type: "number" },
        { name: "prerequisite", label: "پیش‌نیاز", type: "text" },
        { name: "corequisite", label: "هم‌نیاز", type: "text" },
        { name: "year", label: "سال تحصیلی", type: "text" },
        {
          name: "course_type",
          label: "نوع درس",
          type: "select",
          options: [
            { value: "theory", label: "نظری" },
            { value: "practical", label: "عملی" },
            { value: "lab", label: "آزمایشگاهی" },
          ],
        },
        {
          name: "is_active",
          label: "فعال",
          type: "checkbox",
        },
        { name: "type_course", label: "نوع درس (جامع)", type: "text" },
      ];
    }

    if (type === "instructors") {
      return [
        { name: "row_number", label: "ردیف", type: "number" },
        { name: "code", label: "کد", type: "text", required: true },
        { name: "name", label: "نام و نام خانوادگی", type: "text", required: true },
        { name: "username", label: "نام کاربری", type: "text" },
        { name: "group", label: "گروه", type: "text" },
        { name: "cooperation_type", label: "نوع همکاری", type: "text" },
      ];
    }

    if (type === "rooms") {
      return [
        { name: "row_number", label: "ردیف", type: "number" },
        { name: "code", label: "کد کلاس", type: "text", required: true },
        { name: "name", label: "نام کلاس", type: "text", required: true },
        { name: "capacity", label: "ظرفیت", type: "number", required: true },
        { name: "group", label: "گروه", type: "text" },
        { name: "place_type", label: "نوع مکان", type: "text" },
      ];
    }

    if (type === "schedule-history") {
      return [
        { name: "semester", label: "نیمسال", type: "text", required: true },
        { name: "course_name", label: "نام درس", type: "text", required: true },
        { name: "faculty_code", label: "کد دانشکده", type: "text" },
        { name: "faculty_name_clean", label: "نام دانشکده", type: "text" },
        { name: "department_code", label: "کد گروه آموزشی", type: "text" },
        { name: "department_name_clean", label: "نام گروه آموزشی", type: "text" },
        { name: "instructor_code", label: "کد استاد", type: "text" },
        { name: "instructor_name_clean", label: "نام استاد", type: "text" },
        { name: "max_capacity", label: "حداکثر ظرفیت", type: "number" },
        { name: "level", label: "مقطع", type: "text" },
        { name: "course_type", label: "نوع درس", type: "text" },
        { name: "day", label: "روز کلاس", type: "text" },
        { name: "start_time", label: "ساعت شروع", type: "text" },
        { name: "end_time", label: "ساعت پایان", type: "text" },
        { name: "exam_date", label: "تاریخ امتحان", type: "text" },
        { name: "exam_start_time", label: "ساعت شروع امتحان", type: "text" },
        { name: "exam_end_time", label: "ساعت پایان امتحان", type: "text" },
        { name: "ref_course_title", label: "عنوان درس مرجع", type: "text" },
        { name: "ref_unique_course_code", label: "کد درس یکتا مرجع", type: "text" },
        { name: "ref_unique_course_title", label: "عنوان درس یکتا مرجع", type: "text" },
        { name: "class_code", label: "کد کلاس", type: "text" },
        { name: "class_name", label: "نام کلاس", type: "text" },
      ];
    }

    if (type === "term-courses") {
      return [
        { name: "level", label: "مقطع ارائه", type: "text", required: true },
        {
          name: "term",
          label: "ترم",
          type: "select",
          options: TERM_OPTIONS,
          required: true,
        },
        { name: "row_number", label: "ردیف", type: "number" },
        { name: "course_name", label: "نام درس", type: "text", required: true },
        {
          name: "units",
          label: "واحد",
          type: "select",
          options: UNIT_OPTIONS,
          required: true,
        },
        { name: "course_type", label: "نوع درس", type: "text" },
        { name: "approximate_term", label: "ترم تقریبی", type: "number" },
        { name: "description", label: "توضیح", type: "text" },
        { name: "prerequisite_row_codes", label: "کد ردیف پیش‌نیاز", type: "text" },
        { name: "corequisite_row_codes", label: "کد ردیف هم‌نیاز", type: "text" },
        { name: "unique_course_code", label: "کد درس یکتا", type: "text" },
        { name: "unique_course_name", label: "نام درس یکتا", type: "text" },
        { name: "year_identified", label: "سال شناسایی", type: "text" },
      ];
    }

    // ===== مطلوبیت‌های تدریس =====
    if (type === "teaching-preferences") {
      return [
        { name: "unique_course_code", label: "کد یکتا درس", type: "text" },
        { name: "course_name", label: "نام درس", type: "text", required: true },
        { name: "cooperation_type", label: "نوع همکاری", type: "text" },
        { name: "expert_group", label: "گروه تخصصی", type: "text" },
        { name: "row_number", label: "ردیف", type: "number" },
        { name: "instructor_code", label: "کد استاد", type: "text" },
        { name: "instructor_name", label: "نام استاد", type: "text", required: true },
        { name: "instructor_username", label: "یوزرنیم استاد", type: "text" },
        {
          name: "status",
          label: "وضعیت",
          type: "select",
          options: [
            { value: "pending", label: "در انتظار" },
            { value: "approved", label: "تأیید شده" },
            { value: "rejected", label: "رد شده" },
          ],
        },
        {
          name: "term_code",
          label: "کد ترم تحصیلی",
          type: "select",
          options: TERM_OPTIONS,
          required: true,
        },
      ];
    }

    // ===== مطلوبیت‌های زمان‌بندی =====
    if (type === "time-preferences") {
      return [
        {
          name: "day",
          label: "روز",
          type: "select",
          required: true,
          options: DAY_OPTIONS,
        },
        {
          name: "term",
          label: "ترم (برای اعتبارسنجی اسلات)",
          type: "select",
          options: TERM_OPTIONS,
          required: true,
        },
        {
          name: "units",
          label: "تعداد واحد (برای اعتبارسنجی اسلات)",
          type: "select",
          options: UNIT_OPTIONS,
          required: true,
        },
        { name: "cooperation_type", label: "نوع همکاری", type: "text" },
        { name: "end_time", label: "زمان پایان", type: "text", required: true },
        { name: "expert_group", label: "گروه تخصصی", type: "text" },
        { name: "row_number", label: "ردیف", type: "number" },
        { name: "status", label: "وضعیت (فعال)", type: "checkbox" },
        { name: "instructor_code", label: "کد استاد", type: "text" },
        { name: "instructor_name", label: "نام استاد", type: "text", required: true },
        { name: "instructor_username", label: "یوزرنیم استاد", type: "text" },
        { name: "start_time", label: "زمان شروع", type: "text", required: true },
        {
          name: "time_group",
          label: "گروه زمانی",
          type: "select",
          options: [
            { value: "morning", label: "صبح" },
            { value: "afternoon", label: "ظهر" },
            { value: "evening", label: "عصر" },
          ],
        },
      ];
    }

    // پیش‌فرض (برای ایمنی)
    return [];
  };

  const fields = getFields();

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            {course ? "✏️ ویرایش" : "➕ افزودن"}
            {type === "unique" && " درس یکتا"}
            {type === "offered" && " درس ارائه"}
            {type === "instructors" && " استاد"}
            {type === "rooms" && " اتاق"}
            {type === "schedule-history" && " سابقه برنامه‌ریزی"}
            {type === "term-courses" && " درس ترمیک"}
            {type === "teaching-preferences" && " مطلوبیت تدریس"}
            {type === "time-preferences" && " مطلوبیت زمان‌بندی"}
          </h3>
          <button className="modal-close" onClick={onCancel}>
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-grid">
            {fields.map((field) => (
              <div key={field.name} className="form-group">
                <label>
                  {field.label}
                  {field.required && <span className="required"> *</span>}
                </label>
                {field.type === "select" ? (
                  <select
                    name={field.name}
                    value={formData[field.name] || ""}
                    onChange={handleChange}
                    required={field.required || false}
                  >
                    <option value="">انتخاب کنید</option>
                    {field.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "checkbox" ? (
                  <input
                    type="checkbox"
                    name={field.name}
                    checked={formData[field.name] || false}
                    onChange={handleChange}
                  />
                ) : (
                  <input
                    type={field.type}
                    name={field.name}
                    value={formData[field.name] || ""}
                    onChange={handleChange}
                    required={field.required || false}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="form-actions">
            <button type="submit" className="btn-primary">
              💾 ذخیره
            </button>
            <button type="button" className="btn-secondary" onClick={onCancel}>
              ❌ انصراف
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}