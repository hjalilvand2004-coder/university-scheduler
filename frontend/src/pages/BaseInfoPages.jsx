// frontend/src/pages/BaseInfoPages.jsx
import React, { useState } from "react";
import CourseList from "../components/CourseList";
import "./BaseInfoPages.css";

// ============================================================
// کامپوننت wrapper برای هر صفحه با هدر و آمار
// ============================================================
function PageWrapper({ title, icon, description, children, totalCount }) {
  return (
    <div className="base-page-wrapper">
      <div className="page-header">
        <div className="page-title">
          <span className="page-icon">{icon}</span>
          <h2>{title}</h2>
        </div>
        <div className="page-stats">
          <span className="stat-badge">
            تعداد کل: <strong>{totalCount}</strong>
          </span>
        </div>
      </div>
      {description && <p className="page-description">{description}</p>}
      <div className="page-content">{children}</div>
    </div>
  );
}

// ============================================================
// صفحات اطلاعات پایه (هر کدام یک کامپوننت مجزا)
// ============================================================

// ----- صفحه دروس یکتا -----
export function UniqueCoursesPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  const [searchTerm, setSearchTerm] = useState("");
  const filteredCourses = courses.filter(
    (c) =>
      c.code?.includes(searchTerm) ||
      c.title?.includes(searchTerm)
  );

  return (
    <PageWrapper
      title="مدیریت دروس یکتا"
      icon="📚"
      description="مدیریت دروس یکتا شامل کد، عنوان، وضعیت، گروه و برآورد ظرفیت. امکان افزودن، ویرایش، حذف و بارگذاری از فایل اکسل."
      totalCount={courses.length}
    >
      <div className="page-toolbar">
        <div className="search-box">
          <input
            type="text"
            placeholder="جستجوی کد یا عنوان درس..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <span className="search-icon">🔍</span>
        </div>
        <div className="toolbar-actions">
          <button className="btn-export" onClick={() => alert("خروجی اکسل")}>
            📥 خروجی اکسل
          </button>
        </div>
      </div>
      <CourseList
        courses={filteredCourses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="unique"
        columns={[
          { key: "code", label: "کد درس یکتا" },
          { key: "title", label: "عنوان درس یکتا" },
          { key: "status", label: "وضعیت" },
          { key: "group", label: "گروه" },
          { key: "estimated_capacity", label: "برآورد ظرفیت" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه دروس ارائه -----
export function OfferedCoursesPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  return (
    <PageWrapper
      title="مدیریت دروس ارائه"
      icon="📖"
      description="مدیریت دروس ارائه شده در هر ترم با مشخصات کامل شامل ردیف، عنوان، کد یکتا، نوع درس، ساعت نظری و عملی، پیش‌نیاز و هم‌نیاز."
      totalCount={courses.length}
    >
      <CourseList
        courses={courses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="offered"
        columns={[
          { key: "row_number", label: "شماره ردیف" },
          { key: "offered_title", label: "عنوان درس ارائه" },
          { key: "unique_code", label: "کد یکتا" },
          { key: "unique_title", label: "عنوان یکتا" },
          { key: "course_type", label: "نوع درس" },
          { key: "theoretical_hours", label: "ساعت نظری" },
          { key: "practical_hours", label: "ساعت عملی" },
          { key: "prerequisite", label: "پیش‌نیاز" },
          { key: "corequisite", label: "هم‌نیاز" },
          { key: "year", label: "سال تحصیلی" },
          { key: "type_course", label: "نوع درس (جامع)" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه اساتید -----
export function InstructorsPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  return (
    <PageWrapper
      title="مدیریت اساتید"
      icon="👨‍🏫"
      description="مدیریت اطلاعات اساتید شامل کد، نام، نام کاربری، گروه، نوع همکاری و سقف تعداد واحد جهت تدریس."
      totalCount={courses.length}
    >
      <CourseList
        courses={courses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="instructors"
        columns={[
          { key: "row_number", label: "ردیف" },
          { key: "code", label: "کد" },
          { key: "name", label: "نام و نام خانوادگی" },
          { key: "username", label: "نام کاربری" },
          { key: "group", label: "گروه" },
          { key: "cooperation_type", label: "نوع همکاری" },
          { key: "max_teaching_units", label: "سقف تعداد واحد جهت تدریس" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه اتاق‌ها -----
export function RoomsPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  const totalCapacity = courses.reduce((sum, r) => sum + (r.capacity || 0), 0);
  return (
    <PageWrapper
      title="مدیریت اتاق‌ها"
      icon="🏫"
      description="مدیریت اتاق‌های آموزشی شامل کد، نام، ظرفیت، گروه و نوع مکان."
      totalCount={courses.length}
    >
      <div className="page-stats-extra">
        <span className="stat-item">مجموع ظرفیت: {totalCapacity} نفر</span>
      </div>
      <CourseList
        courses={courses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="rooms"
        columns={[
          { key: "row_number", label: "ردیف" },
          { key: "code", label: "کد کلاس" },
          { key: "name", label: "نام کلاس" },
          { key: "capacity", label: "ظرفیت" },
          { key: "group", label: "گروه" },
          { key: "place_type", label: "نوع مکان" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه سوابق برنامه‌ریزی -----
export function ScheduleHistoryPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  return (
    <PageWrapper
      title="سوابق برنامه‌ریزی ترم‌های گذشته"
      icon="📜"
      description="مشاهده و مدیریت سوابق برنامه‌ریزی ترم‌های گذشته شامل نیمسال، نام درس، استاد، روز، ساعت شروع و پایان، ظرفیت و کلاس."
      totalCount={courses.length}
    >
      <CourseList
        courses={courses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="schedule-history"
        columns={[
          { key: "semester", label: "نیمسال" },
          { key: "course_name", label: "نام درس" },
          { key: "instructor_name_clean", label: "استاد" },
          { key: "day", label: "روز" },
          { key: "start_time", label: "ساعت شروع" },
          { key: "end_time", label: "ساعت پایان" },
          { key: "max_capacity", label: "ظرفیت" },
          { key: "class_name", label: "کلاس" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه دروس ترمیک -----
export function TermCoursesPage({ courses, onAdd, onUpdate, onDelete, onUpload }) {
  const levels = [...new Set(courses.map((c) => c.level))];
  return (
    <PageWrapper
      title="مدیریت دروس ترمیک"
      icon="📅"
      description="مدیریت دروس ترمیک شامل مقطع، ترم، ردیف، نام درس، واحد، نوع درس، پیش‌نیاز، هم‌نیاز و کد یکتا."
      totalCount={courses.length}
    >
      <div className="page-stats-extra">
        <span className="stat-item">مقاطع: {levels.join("، ")}</span>
      </div>
      <CourseList
        courses={courses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="term-courses"
        columns={[
          { key: "level", label: "مقطع" },
          { key: "term", label: "ترم" },
          { key: "row_number", label: "ردیف" },
          { key: "course_name", label: "نام درس" },
          { key: "units", label: "واحد" },
          { key: "course_type", label: "نوع درس" },
          { key: "approximate_term", label: "ترم تقریبی" },
          { key: "description", label: "توضیح" },
          { key: "prerequisite_row_codes", label: "پیش‌نیاز" },
          { key: "corequisite_row_codes", label: "هم‌نیاز" },
          { key: "unique_course_code", label: "کد یکتا" },
          { key: "unique_course_name", label: "نام یکتا" },
          { key: "year_identified", label: "سال شناسایی" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه مطلوبیت‌های تدریس -----
export function TeachingPreferencesPage({
  courses,
  onAdd,
  onUpdate,
  onDelete,
  onUpload,
  coursesList = [], // ← لیست دروس یکتا از والد
  instructors = [], // ← لیست اساتید از والد
}) {
  const processedCourses = courses.map(course => ({
    ...course,
    status: Boolean(course.status)
  }));

  return (
    <PageWrapper
      title="مطلوبیت‌های تدریس اساتید"
      icon="📋"
      description="مدیریت مطلوبیت‌های تدریس اساتید شامل کد یکتا درس، نام درس، نام استاد، گروه تخصصی، وضعیت و کد ترم."
      totalCount={processedCourses.length}
    >
      <CourseList
        courses={processedCourses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="teaching-preferences"
        instructorsList={instructors} // ← ارسال لیست اساتید
        coursesList={coursesList}     // ← ارسال لیست دروس یکتا
        columns={[
          { key: "unique_course_code", label: "کد یکتا درس" },
          { key: "course_name", label: "نام درس" },
          { key: "instructor_name", label: "نام استاد" },
          { key: "expert_group", label: "گروه تخصصی" },
          { key: "status", label: "وضعیت" },
          { key: "term_code", label: "کد ترم" },
        ]}
      />
    </PageWrapper>
  );
}

// ----- صفحه مطلوبیت‌های زمان‌بندی -----
export function TimePreferencesPage({
  courses,
  onAdd,
  onUpdate,
  onDelete,
  onUpload,
  instructors = [], // لیست اساتید از والد
}) {
  const processedCourses = courses.map(course => ({
    ...course,
    status: Boolean(course.status)
  }));

  return (
    <PageWrapper
      title="مطلوبیت‌های زمان‌بندی اساتید"
      icon="⏰"
      description="مدیریت مطلوبیت‌های زمان‌بندی اساتید شامل روز، نام استاد، ساعت شروع، ساعت پایان، گروه زمانی، وضعیت و اولویت."
      totalCount={processedCourses.length}
    >
      <CourseList
        courses={processedCourses}
        onAdd={onAdd}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onUpload={onUpload}
        title=""
        type="time-preferences"
        instructorsList={instructors} // ارسال لیست اساتید به CourseList
        columns={[
          { key: "day", label: "روز" },
          { key: "instructor_name", label: "نام استاد" },
          { key: "start_time", label: "شروع" },
          { key: "end_time", label: "پایان" },
          { key: "time_group", label: "گروه زمانی" },
          { key: "status", label: "وضعیت" },
          { key: "priority", label: "اولویت" },
        ]}
      />
    </PageWrapper>
  );
}

// ============================================================
// کامپوننت اصلی که بر اساس activePage رندر می‌کند
// ============================================================
export default function BaseInfoPages({
  activePage,
  semester,
  uniqueCourses,
  offeredCourses,
  instructors,
  rooms,
  historyRecords,
  termCourses,
  teachingPreferences,
  timePreferences,
  onDataChange,
  // توابع مدیریت هر بخش
  onAddUnique,
  onUpdateUnique,
  onDeleteUnique,
  onUploadUnique,
  onAddOffered,
  onUpdateOffered,
  onDeleteOffered,
  onUploadOffered,
  onAddInstructor,
  onUpdateInstructor,
  onDeleteInstructor,
  onUploadInstructor,
  onAddRoom,
  onUpdateRoom,
  onDeleteRoom,
  onUploadRoom,
  onAddHistory,
  onUpdateHistory,
  onDeleteHistory,
  onUploadHistory,
  onAddTermCourse,
  onUpdateTermCourse,
  onDeleteTermCourse,
  onUploadTermCourse,
  onAddTeachingPref,
  onUpdateTeachingPref,
  onDeleteTeachingPref,
  onUploadTeachingPref,
  onAddTimePref,
  onUpdateTimePref,
  onDeleteTimePref,
  onUploadTimePref,
}) {
  const safeCourses = (data) => data || [];

  switch (activePage) {
    case "unique-courses":
      return (
        <UniqueCoursesPage
          courses={safeCourses(uniqueCourses)}
          onAdd={onAddUnique}
          onUpdate={onUpdateUnique}
          onDelete={onDeleteUnique}
          onUpload={onUploadUnique}
        />
      );
    case "offered-courses":
      return (
        <OfferedCoursesPage
          courses={safeCourses(offeredCourses)}
          onAdd={onAddOffered}
          onUpdate={onUpdateOffered}
          onDelete={onDeleteOffered}
          onUpload={onUploadOffered}
        />
      );
    case "instructors":
      return (
        <InstructorsPage
          courses={safeCourses(instructors)}
          onAdd={onAddInstructor}
          onUpdate={onUpdateInstructor}
          onDelete={onDeleteInstructor}
          onUpload={onUploadInstructor}
        />
      );
    case "rooms":
      return (
        <RoomsPage
          courses={safeCourses(rooms)}
          onAdd={onAddRoom}
          onUpdate={onUpdateRoom}
          onDelete={onDeleteRoom}
          onUpload={onUploadRoom}
        />
      );
    case "schedule-history":
      return (
        <ScheduleHistoryPage
          courses={safeCourses(historyRecords)}
          onAdd={onAddHistory}
          onUpdate={onUpdateHistory}
          onDelete={onDeleteHistory}
          onUpload={onUploadHistory}
        />
      );
    case "term-courses":
      return (
        <TermCoursesPage
          courses={safeCourses(termCourses)}
          onAdd={onAddTermCourse}
          onUpdate={onUpdateTermCourse}
          onDelete={onDeleteTermCourse}
          onUpload={onUploadTermCourse}
        />
      );
    case "teaching-preferences":
      return (
        <TeachingPreferencesPage
          courses={safeCourses(teachingPreferences)}
          onAdd={onAddTeachingPref}
          onUpdate={onUpdateTeachingPref}
          onDelete={onDeleteTeachingPref}
          onUpload={onUploadTeachingPref}
          coursesList={safeCourses(uniqueCourses)} // ← اضافه شد
          instructors={safeCourses(instructors)}   // ← اضافه شد
        />
      );
    case "time-preferences":
      return (
        <TimePreferencesPage
          courses={safeCourses(timePreferences)}
          onAdd={onAddTimePref}
          onUpdate={onUpdateTimePref}
          onDelete={onDeleteTimePref}
          onUpload={onUploadTimePref}
          instructors={safeCourses(instructors)} // ← ارسال لیست اساتید
        />
      );
    default:
      return (
        <div className="error-page">
          <p>صفحه‌ای با این شناسه وجود ندارد: {activePage}</p>
        </div>
      );
  }
}