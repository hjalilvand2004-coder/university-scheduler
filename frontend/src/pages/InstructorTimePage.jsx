// frontend/src/pages/InstructorTimePage.jsx
import { useState, useEffect, useMemo, useRef } from "react";
import axios from "axios";
import EditableDataTable from "../components/EditableDataTable";
import { processSchedule } from "../api/workflowApi";
import "./InstructorTimePage.css";

// ============================================================
// بازه‌های زمانی مجاز (مطابق با بک‌اند - app/utils/constants.py)
// ============================================================
const TWO_UNIT_SLOTS = [
  "07:30-09:15",
  "09:16-11:00",
  "11:01-12:45",
  "13:00-14:45",
  "14:46-16:30",
  "15:31-17:16",
  "16:31-18:15",
  "18:16-20:00",
];

// اسلات‌های سه‌واحدی با ۸ گزینه (هم‌سان با بک‌اند)
const THREE_UNIT_SLOTS = [
  "07:30-10:10",
  "09:16-11:46",
  "10:11-12:50",
  "11:01-13:31",
  "13:00-15:30",
  "14:46-17:16",
  "15:31-18:00",
  "18:01-20:30",
];


// ============================================================
// توابع کمکی
// ============================================================
function timeToMinutes(timeStr) {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  if (parts.length !== 2) return 0;
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  return h * 60 + m;
}

/**
 * بررسی تطابق زمان با تساهل (پیش‌فرض ۶۰ دقیقه)
 * همچنین بازه‌های ۱۲:۰۰-۱۶:۰۰ به‌صورت ۱۳:۰۰-۱۷:۰۰ نرمال‌سازی می‌شوند
 */
function normalizePreferenceWindow(start, end) {
  if (start === "12:00" && end === "16:00") {
    return { start: "13:00", end: "17:00" };
  }
  return { start, end };
}

function isTimeSlotMatchWithTolerance(
  slotStart,
  slotEnd,
  prefStart,
  prefEnd,
  toleranceMinutes = 60 // ← تساهل ۶۰ دقیقه (هماهنگ با بک‌اند)
) {
  // نرمال‌سازی بازه مطلوب (۱۲-۱۶ -> ۱۳-۱۷)
  const normalized = normalizePreferenceWindow(prefStart, prefEnd);
  const actualPrefStart = normalized.start;
  const actualPrefEnd = normalized.end;

  const slotS = timeToMinutes(slotStart);
  const slotE = timeToMinutes(slotEnd);
  const prefS = timeToMinutes(actualPrefStart);
  const prefE = timeToMinutes(actualPrefEnd);
  const expandedStart = prefS - toleranceMinutes;
  const expandedEnd = prefE + toleranceMinutes;
  return slotS >= expandedStart && slotE <= expandedEnd;
}

function getDayName(dayNum) {
  const days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];
  return days[dayNum] || dayNum;
}

function getValidSlots(units) {
  if (units === 3) return THREE_UNIT_SLOTS;
  return TWO_UNIT_SLOTS;
}

function getDefaultSlot(units) {
  const slots = getValidSlots(units);
  return slots[0] || "07:30-09:15";
}

function normalizeTimeSlot(item, unitsLookup = {}) {
  if (!item) return item;
  const units = item.units || (item.unique_code && unitsLookup[item.unique_code]) || 2;
  const validSlots = getValidSlots(units);
  const currentSlot = `${item.start || ''}-${item.end || ''}`;
  if (validSlots.includes(currentSlot)) return item;
  const defaultSlot = getDefaultSlot(units);
  const [start, end] = defaultSlot.split('-');
  return { ...item, start, end, units };
}

// ============================================================
// تابع تعیین وضعیت تطابق کلی (برای نمایش وضعیت کلی)
// ============================================================
function getMatchStatus(item, teachingLookup, timeLookup) {
  const instructorCode = item.instructor_code;
  const courseCode = item.unique_code;
  const day = item.day;
  const start = item.start;
  const end = item.end;

  const hasTeachPref = courseCode && teachingLookup[courseCode] && teachingLookup[courseCode].size > 0;
  const hasTimePref = instructorCode && timeLookup[instructorCode] && timeLookup[instructorCode].length > 0;

  if (!hasTeachPref && !hasTimePref) {
    return 'no_preference';
  }

  let teachMatch = false;
  let dayMatch = false;
  let timeMatch = false;

  if (hasTeachPref && instructorCode) {
    teachMatch = teachingLookup[courseCode].has(instructorCode);
  }

  if (hasTimePref && day !== undefined) {
    const preferredSlots = timeLookup[instructorCode];
    dayMatch = preferredSlots.some(slot => slot.day === day);
    if (start && end) {
      timeMatch = preferredSlots.some(slot =>
        slot.day === day && isTimeSlotMatchWithTolerance(start, end, slot.start, slot.end, 60) // ← تساهل ۶۰
      );
    }
  }

  const matchCount = (teachMatch ? 1 : 0) + (dayMatch ? 1 : 0) + (timeMatch ? 1 : 0);
  if (matchCount === 3) return 'full';
  if (matchCount > 0) return 'partial';
  return 'none';
}

// ============================================================
// تابع تعیین وضعیت تطابق برای یک فیلد خاص (برای ستون‌های جداگانه)
// ============================================================
function getFieldMatchStatus(item, fieldKey, teachingLookup, timeLookup) {
  const instructorCode = item.instructor_code;
  const courseCode = item.unique_code;
  const day = item.day;
  const start = item.start;
  const end = item.end;

  const hasTeachPref = courseCode && teachingLookup[courseCode] && teachingLookup[courseCode].size > 0;
  const hasTimePref = instructorCode && timeLookup[instructorCode] && timeLookup[instructorCode].length > 0;

  if (!hasTeachPref && !hasTimePref) {
    return 'no_preference';
  }

  let match = false;

  if (fieldKey === 'course_name') {
    if (hasTeachPref && instructorCode) {
      match = teachingLookup[courseCode].has(instructorCode);
    }
  } else if (fieldKey === 'day') {
    if (hasTimePref && day !== undefined) {
      const preferredSlots = timeLookup[instructorCode];
      match = preferredSlots.some(slot => slot.day === day);
    }
  } else if (fieldKey === 'start' || fieldKey === 'end') {
    if (hasTimePref && day !== undefined && start && end) {
      const preferredSlots = timeLookup[instructorCode];
      match = preferredSlots.some(slot =>
        slot.day === day && isTimeSlotMatchWithTolerance(start, end, slot.start, slot.end, 60) // ← تساهل ۶۰
      );
    }
  } else {
    return null;
  }

  if (match === undefined) return 'no_preference';
  return match ? 'full' : 'none';
}

// ============================================================
// تابع جدید برای تعیین وضعیت رنگ‌بندی سلول (بر اساس وضعیت کلی)
// ============================================================
function getCellColorStatus(item, teachingLookup, timeLookup, fieldKey) {
  // فقط وضعیت کلی را برمی‌گردانیم (برای استفاده در کلاس‌های CSS)
  const overallStatus = getMatchStatus(item, teachingLookup, timeLookup);
  return overallStatus;
}

// ============================================================
// کامپوننت نمایش مراحل (Steps) - با نمایش جدولی و قابل فهم
// ============================================================
function StepsDisplay({ steps, instructorNameLookup = {}, courseNameLookup = {} }) {
  if (!steps || steps.length === 0) {
    return null;
  }

  const total = steps.length;
  const completed = steps.filter(s => s.status === 'success').length;
  const failed = steps.filter(s => s.status === 'failed').length;
  const running = steps.filter(s => s.status === 'running').length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  const stepBackendInfo = {
    "آماده‌سازی داده‌ها": {
      method: "_prepare_data()",
      description: "نرمال‌سازی کد دروس، استخراج شماره ترم و شماره گروه",
      file: "schedule_service.py",
      line: "حدود خط ۱۵۰"
    },
    "بارگذاری اطلاعات اساتید": {
      method: "_load_instructor_data()",
      description: "دریافت لیست اساتید، ترجیحات تدریس و ترجیحات زمانی از دیتابیس",
      file: "schedule_service.py",
      line: "حدود خط ۱۸۰"
    },
    "اولویت‌بندی دروس عادی": {
      method: "_score_and_sort_courses()",
      description: "محاسبه امتیاز اولویت بر اساس پیش‌نیاز، ترم جاری، تقاضا و واحد",
      file: "schedule_service.py",
      line: "حدود خط ۲۸۰"
    },
    "تخصیص استاد به دروس عادی": {
      method: "_assign_instructor_to_regular_courses()",
      description: "تخصیص استاد به دروس عادی بر اساس اولویت‌های تدریس و نوع همکاری (هیات علمی، مدعو، ...)",
      file: "schedule_service.py",
      line: "حدود خط ۳۵۰"
    },
    "زمان‌بندی کامل به ازای هر استاد": {
      method: "_assign_full_schedule_per_instructor()",
      description: "برای هر استاد، با افزایش تدریجی تساهل، دروس را به طور متوازن در روزهای ترجیحی تخصیص می‌دهد (سطوح: strict, tolerance, fallback)",
      file: "schedule_service.py",
      line: "حدود خط ۴۵۰"
    },
    "تخصیص استاد به کارآموزی/پروژه": {
      method: "_assign_internship_instructors()",
      description: "انتخاب اولین استاد از لیست اولویت‌ها برای دروس کارآموزی و پروژه (بدون زمان)",
      file: "schedule_service.py",
      line: "حدود خط ۵۵۰"
    },
    "گزارش نهایی": {
      method: "_generate_final_report()",
      description: "جمع‌بندی نتایج، ثبت لاگ و پاک‌سازی اطلاعات اتاق",
      file: "schedule_service.py",
      line: "حدود خط ۶۰۰"
    }
  };

  const renderCoursesTable = (courses, title, stepName) => {
    if (!courses || courses.length === 0) return null;

    let columns = [];
    const baseCols = [
      { key: 'course_name', label: 'درس' },
      { key: 'group_number', label: 'گروه' },
    ];

    if (stepName.includes('اولویت‌بندی دروس عادی')) {
      columns = [
        ...baseCols,
        { key: 'priority_score', label: 'امتیاز اولویت' },
        {
          key: 'score_components',
          label: 'جزئیات امتیاز',
          render: (row) => {
            const comps = row.score_components || {};
            const parts = [];
            if (comps.prerequisite) parts.push(`پیش‌نیاز: ${comps.prerequisite}`);
            if (comps.current_term) parts.push(`ترم جاری: ${comps.current_term}`);
            if (comps.demand) parts.push(`تقاضا: ${comps.demand}`);
            if (comps.units) parts.push(`واحد: ${comps.units}`);
            if (comps.repeat_penalty) parts.push(`جریمه تکرار: ${comps.repeat_penalty}`);
            return parts.length > 0 ? parts.join('، ') : '—';
          }
        },
        { key: 'units', label: 'واحد' },
        { key: 'level', label: 'مقطع' },
        { key: 'term', label: 'ترم' },
      ];
    } else if (stepName.includes('تخصیص استاد به دروس عادی') || stepName.includes('تخصیص استاد به کارآموزی/پروژه')) {
      columns = [
        ...baseCols,
        { key: 'instructor_code', label: 'کد استاد' },
        { key: 'instructor_name', label: 'استاد' },
        { key: 'instructor_priority', label: 'اولویت', render: (row) => row.instructor_priority || '—' },
        { key: 'priority_score', label: 'امتیاز اولویت', render: (row) => row.priority_score || '—' },
      ];
    } else if (stepName.includes('زمان‌بندی کامل به ازای هر استاد')) {
      columns = [
        ...baseCols,
        { key: 'instructor_name', label: 'استاد' },
        { key: 'day', label: 'روز', render: (row) => row.day !== undefined ? getDayName(row.day) : '—' },
        { key: 'start', label: 'شروع' },
        { key: 'end', label: 'پایان' },
        { key: 'priority_score', label: 'امتیاز اولویت', render: (row) => row.priority_score || '—' },
        {
          key: 'schedule_match_level',
          label: 'سطح تطابق',
          render: (row) => {
            const level = row.schedule_match_level;
            if (!level) return '—';
            const map = {
              'full': 'کامل',
              'start_inside_preference': 'شروع در بازه',
              'tolerance_60': 'تساهل ۶۰ دقیقه',
              'preferred_day_fallback': 'روز ترجیحی (پشتیبان)',
              'fallback_non_preferred_day': 'روز غیرترجیحی',
              'no_preference_default': 'پیش‌فرض (بدون مطلوبیت)',
              'unassigned': 'تخصیص‌نیافته',
            };
            return map[level] || level;
          }
        },
        {
          key: 'schedule_tolerance',
          label: 'تساهل (دقیقه)',
          render: (row) => row.schedule_tolerance !== undefined && row.schedule_tolerance !== null ? row.schedule_tolerance : '—'
        },
        {
          key: 'schedule_match_score',
          label: 'امتیاز تطابق',
          render: (row) => row.schedule_match_score !== undefined ? row.schedule_match_score : '—'
        },
        {
          key: 'schedule_fully_inside_preference',
          label: 'داخل بازه مطلوب',
          render: (row) => {
            if (row.schedule_fully_inside_preference === true) return '✅';
            if (row.schedule_fully_inside_preference === false) return '❌';
            return '—';
          }
        },
        {
          key: 'schedule_start_inside_preference',
          label: 'شروع در بازه مطلوب',
          render: (row) => {
            if (row.schedule_start_inside_preference === true) return '✅';
            if (row.schedule_start_inside_preference === false) return '❌';
            return '—';
          }
        }
      ];
    } else {
      columns = [
        ...baseCols,
        { key: 'instructor_name', label: 'استاد' },
        { key: 'day', label: 'روز', render: (row) => row.day !== undefined ? getDayName(row.day) : '—' },
        { key: 'start', label: 'شروع' },
        { key: 'end', label: 'پایان' },
        { key: 'instructor_priority', label: 'اولویت', render: (row) => row.instructor_priority || '—' },
        { key: 'priority_score', label: 'امتیاز اولویت', render: (row) => row.priority_score || '—' },
      ];
    }

    return (
      <div className="details-table">
        <h5>{title} ({courses.length})</h5>
        <div className="table-responsive">
          <table className="courses-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col.key}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {courses.map((row, idx) => (
                <tr key={idx}>
                  {columns.map(col => {
                    let value = row[col.key];
                    if (col.render) {
                      value = col.render(row);
                    } else if (value === undefined || value === null) {
                      value = '—';
                    }
                    return <td key={col.key}>{value}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderDetails = (details, stepName) => {
    if (!details || Object.keys(details).length === 0) return null;

    const specialKeys = ['instructor_usage', 'sample_teaching_prefs', 'sample_time_prefs', 'mismatch_details'];
    const simpleKeys = Object.keys(details).filter(key => !specialKeys.includes(key) && !key.startsWith('assigned_') && !key.startsWith('unassigned_'));

    const assignedKeys = Object.keys(details).filter(key => key.startsWith('assigned_') && Array.isArray(details[key]));
    const unassignedKeys = Object.keys(details).filter(key => key.startsWith('unassigned_') && Array.isArray(details[key]));

    const sampleScores = details.sample_scores || null;
    const mismatchDetails = details.mismatch_details || null;

    return (
      <div className="step-details">
        {simpleKeys.length > 0 && (
          <div className="details-simple-table">
            <table className="details-table-simple">
              <tbody>
                {simpleKeys.map(key => {
                  let value = details[key];
                  if (Array.isArray(value)) {
                    value = value.join('، ');
                  }
                  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                    value = JSON.stringify(value);
                  }
                  const keyMap = {
                    'total_courses': 'تعداد کل دروس',
                    'sample_codes': 'نمونه کدها',
                    'instructors_count': 'تعداد اساتید',
                    'teaching_prefs_count': 'تعداد ترجیحات تدریس',
                    'time_prefs_count': 'تعداد ترجیحات زمان',
                    'total_scheduled': 'تعداد زمان‌بندی‌شده',
                    'regular_count': 'تعداد دروس عادی',
                    'internship_count': 'تعداد کارآموزی/پروژه',
                    'assigned': 'تخصیص‌یافته',
                    'unassigned': 'بدون استاد',
                    'total_assigned': 'کل تخصیص‌یافته',
                    'total_unassigned': 'کل بدون استاد',
                    'success_rate': 'نرخ موفقیت'
                  };
                  const label = keyMap[key] || key;
                  return (
                    <tr key={key}>
                      <td className="detail-key">{label}</td>
                      <td className="detail-value">{value}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {sampleScores && sampleScores.length > 0 && (
          <div className="details-table">
            <h5>📊 نمونه دروس با امتیاز اولویت (۱۰ درس اول)</h5>
            <div className="table-responsive">
              <table className="pref-table">
                <thead>
                  <tr>
                    <th>درس</th>
                    <th>گروه</th>
                    <th>امتیاز کل</th>
                    <th>جزئیات امتیاز</th>
                  </tr>
                </thead>
                <tbody>
                  {sampleScores.map((item, idx) => {
                    const comps = item.score_components || {};
                    const parts = [];
                    if (comps.prerequisite) parts.push(`پیش‌نیاز: ${comps.prerequisite}`);
                    if (comps.current_term) parts.push(`ترم جاری: ${comps.current_term}`);
                    if (comps.demand) parts.push(`تقاضا: ${comps.demand}`);
                    if (comps.units) parts.push(`واحد: ${comps.units}`);
                    if (comps.repeat_penalty) parts.push(`جریمه تکرار: ${comps.repeat_penalty}`);
                    const detail = parts.length > 0 ? parts.join('، ') : '—';
                    return (
                      <tr key={idx}>
                        <td>{item.course_name || 'نامشخص'}</td>
                        <td>{item.group_number || '—'}</td>
                        <td>{item.priority_score || 0}</td>
                        <td>{detail}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {details.sample_teaching_prefs && details.sample_teaching_prefs.length > 0 && (
          <div className="details-table">
            <h5>📚 نمونه ترجیحات تدریس (۵ درس اول)</h5>
            <div className="table-responsive">
              <table className="pref-table">
                <thead>
                  <tr>
                    <th>کد درس</th>
                    <th>نام درس</th>
                    <th>اساتید اولویت‌دار (تا ۳ نفر)</th>
                  </tr>
                </thead>
                <tbody>
                  {details.sample_teaching_prefs.map((item, idx) => (
                    <tr key={idx}>
                      <td>{item.course_code}</td>
                      <td>{courseNameLookup[item.course_code] || 'نامشخص'}</td>
                      <td>
                        {item.instructors.map(inst => `${inst.name} (${inst.code})`).join('، ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {details.teaching_prefs_count > 5 && (
                <div className="table-note">و {details.teaching_prefs_count - 5} مورد دیگر ...</div>
              )}
            </div>
          </div>
        )}

        {details.sample_time_prefs && details.sample_time_prefs.length > 0 && (
          <div className="details-table">
            <h5>⏰ نمونه ترجیحات زمان (۵ استاد اول)</h5>
            <div className="table-responsive">
              <table className="pref-table">
                <thead>
                  <tr>
                    <th>استاد</th>
                    <th>روز</th>
                    <th>شروع</th>
                    <th>پایان</th>
                    <th>اولویت</th>
                  </tr>
                </thead>
                <tbody>
                  {details.sample_time_prefs.map((item, idx) => (
                    item.preferences.map((pref, pIdx) => (
                      <tr key={`${idx}-${pIdx}`}>
                        {pIdx === 0 && <td rowSpan={item.preferences.length}>{item.instructor_name} ({item.instructor_code})</td>}
                        <td>{pref.day}</td>
                        <td>{pref.start}</td>
                        <td>{pref.end}</td>
                        <td>{pref.priority}</td>
                      </tr>
                    ))
                  ))}
                </tbody>
              </table>
              {details.time_prefs_count > 5 && (
                <div className="table-note">و {details.time_prefs_count - 5} استاد دیگر ...</div>
              )}
            </div>
          </div>
        )}

        {assignedKeys.map(key => {
          const courses = details[key];
          const title = key.replace('assigned_', '').replace(/_/g, ' ') + ' (تخصیص‌یافته)';
          return renderCoursesTable(courses, title, stepName);
        })}

        {unassignedKeys.map(key => {
          const courses = details[key];
          const title = key.replace('unassigned_', '').replace(/_/g, ' ') + ' (تخصیص‌نیافته)';
          return renderCoursesTable(courses, title, stepName);
        })}

        {mismatchDetails && mismatchDetails.length > 0 && stepName.includes('گزارش نهایی') && (
          <div className="details-table">
            <h5>📋 دلایل عدم تطابق کامل ({mismatchDetails.length})</h5>
            <div className="table-responsive">
              <table className="conflicts-table">
                <thead>
                  <tr>
                    <th>درس</th>
                    <th>گروه</th>
                    <th>کد درس</th>
                    <th>مقطع</th>
                    <th>ترم</th>
                    <th>استاد</th>
                    <th>وضعیت تخصیص</th>
                    <th>دلیل</th>
                  </tr>
                </thead>
                <tbody>
                  {mismatchDetails.map((item, idx) => {
                    const statusMap = {
                      'full': 'تطابق کامل',
                      'partial': 'تطابق نسبی',
                      'none': 'بدون تطابق',
                      'unassigned': 'تخصیص نیافته',
                      'no_assignment': 'تخصیص ناقص'
                    };
                    const statusLabel = statusMap[item.status] || item.status;
                    const isAssigned = item.is_assigned ? 'تخصیص‌یافته' : 'تخصیص نیافته';
                    return (
                      <tr key={idx} className={`mismatch-row status-${item.status || 'unknown'}`}>
                        <td>{item.course_name || 'نامشخص'}</td>
                        <td>{item.group_number || '—'}</td>
                        <td>{item.unique_code || '—'}</td>
                        <td>{item.level || '—'}</td>
                        <td>{item.term || '—'}</td>
                        <td>{item.instructor_name ? `${item.instructor_name} (${item.instructor_code})` : '—'}</td>
                        <td>{isAssigned}</td>
                        <td>{item.reason || 'دلیل نامشخص'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {details.instructor_usage && (
          <div className="details-table">
            <h5>📊 استفاده از سقف واحد اساتید</h5>
            <div className="table-responsive">
              <table className="usage-table">
                <thead>
                  <tr>
                    <th>کد استاد</th>
                    <th>نام استاد</th>
                    <th>واحد استفاده‌شده</th>
                    <th>حداکثر واحد</th>
                    <th>درصد استفاده</th>
                    <th>وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(details.instructor_usage)
                    .sort((a, b) => b[1].percentage - a[1].percentage)
                    .map(([code, usage]) => {
                      const percent = usage.percentage;
                      let statusText = '';
                      let statusClass = '';
                      if (percent >= 100) {
                        statusText = 'پر';
                        statusClass = 'status-full';
                      } else if (percent >= 75) {
                        statusText = 'نزدیک به پر';
                        statusClass = 'status-high';
                      } else if (percent >= 50) {
                        statusText = 'متوسط';
                        statusClass = 'status-medium';
                      } else {
                        statusText = 'کم';
                        statusClass = 'status-low';
                      }
                      return (
                        <tr key={code}>
                          <td>{code}</td>
                          <td>{instructorNameLookup[code] || 'نامشخص'}</td>
                          <td>{usage.used}</td>
                          <td>{usage.max}</td>
                          <td>{percent}%</td>
                          <td className={statusClass}>{statusText}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="steps-container">
      <div className="steps-header">
        <h4>📋 مراحل اجرای الگوریتم</h4>
        <div className="steps-progress">
          <span>پیشرفت: {progress}%</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="steps-stats">
            {completed} موفق / {failed} خطا / {running} در حال اجرا
          </span>
        </div>
      </div>
      <div className="steps-list">
        {steps.map((step, index) => {
          const statusClass = `step-status-${step.status}`;
          const icon = step.status === 'success' ? '✅' :
                       step.status === 'failed' ? '❌' :
                       step.status === 'running' ? '⏳' : '⏸️';

          const backendInfo = stepBackendInfo[step.name] || null;

          return (
            <div key={index} className={`step-item ${statusClass}`}>
              <div className="step-number">{step.step}</div>
              <div className="step-content">
                <div className="step-title">
                  <span className="step-icon">{icon}</span>
                  <span className="step-name">{step.name}</span>
                  <span className="step-status-label">{step.status}</span>
                </div>
                {step.description && (
                  <div className="step-description">{step.description}</div>
                )}

                {backendInfo && (
                  <div className="step-backend-info">
                    <span className="backend-label">🖥️ بخش بک‌اند:</span>
                    <span className="backend-method">{backendInfo.method}</span>
                    <span className="backend-desc">({backendInfo.description})</span>
                    <span className="backend-file">📄 {backendInfo.file}</span>
                    <span className="backend-line">📍 {backendInfo.line}</span>
                  </div>
                )}

                {renderDetails(step.details, step.name)}
                {step.timestamp && (
                  <div className="step-timestamp">
                    {new Date(step.timestamp).toLocaleString('fa-IR')}
                    {step.timestamp_end && ` - ${new Date(step.timestamp_end).toLocaleString('fa-IR')}`}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت اصلی
// ============================================================
export default function InstructorTimePage({
  basketData,
  basketId,
  instructorTimeData,
  onProcess: onProcessParent,
  onClear,
  loading: loadingParent,
  onNext,
  workflowId,
  teachingPreferences = [],
  timePreferences = [],
  onNavigateToBasketList,
  instructorsData: instructorsDataProp = [],
}) {
  const [localBasketData, setLocalBasketData] = useState(null);
  const [basketMeta, setBasketMeta] = useState({ title: "", semester: "", year: "" });
  const [isLoadingBasket, setIsLoadingBasket] = useState(false);
  const [error, setError] = useState(null);
  const [loadingLocal, setLoadingLocal] = useState(false);

  // آمار قدیمی (برای سازگاری با بخش‌های دیگر مانند matrix/chart)
  const [stats, setStats] = useState({
    totalClasses: 0,
    teachingMatchCount: 0,
    dayMatchCount: 0,
    timeMatchCount: 0,
    bothMatchCount: 0,
  });

  const [instructorsData, setInstructorsData] = useState([]);
  const [loadingInstructors, setLoadingInstructors] = useState(false);

  const [manualMode, setManualMode] = useState(false);
  const [unassignedList, setUnassignedList] = useState([]);
  const [manualAssignments, setManualAssignments] = useState([]);
  const [isSavingManual, setIsSavingManual] = useState(false);
  const [manualResult, setManualResult] = useState(null);

  const [selectedDay, setSelectedDay] = useState(null);
  const dayNames = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];

  const [showBasket, setShowBasket] = useState(true);
  const [viewMode, setViewMode] = useState("table");
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");

  const [editingMode, setEditingMode] = useState(false);
  const [editedData, setEditedData] = useState([]);
  const [isSavingEdits, setIsSavingEdits] = useState(false);

  const [selectedInstructor, setSelectedInstructor] = useState("");
  const [selectedCourseCode, setSelectedCourseCode] = useState("");

  const [steps, setSteps] = useState([]);
  const [showSteps, setShowSteps] = useState(true);

  const loadingBasketRef = useRef(false);
  const hasLoadedBasket = useRef(false);
  const hasFetchedInstructors = useRef(false);
  const hasSetDefaultCourse = useRef(false);
  const hasSetDefaultInstructor = useRef(false);

  // ============================================================
  // واکشی لیست اساتید از بک‌اند (در صورت عدم وجود prop)
  // ============================================================
  useEffect(() => {
    if (instructorsDataProp && instructorsDataProp.length > 0) {
      setInstructorsData(instructorsDataProp);
      hasFetchedInstructors.current = true;
      return;
    }
    if (hasFetchedInstructors.current) return;

    const fetchInstructors = async () => {
      setLoadingInstructors(true);
      try {
        const response = await axios.get("http://localhost:8000/api/professors-rooms/instructors/list");
        const data = response.data;
        if (Array.isArray(data)) {
          setInstructorsData(data);
        } else {
          console.warn("فرمت پاسخ اساتید نامعتبر است:", data);
          setInstructorsData([]);
        }
        hasFetchedInstructors.current = true;
      } catch (err) {
        console.error("❌ خطا در واکشی اساتید:", err);
        setError("خطا در بارگذاری اطلاعات اساتید");
        setInstructorsData([]);
        hasFetchedInstructors.current = true;
      } finally {
        setLoadingInstructors(false);
      }
    };

    fetchInstructors();
  }, [instructorsDataProp]);

  // ============================================================
  // دبونس جستجو
  // ============================================================
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // ============================================================
  // واکشی سبد از دیتابیس (فقط یک بار)
  // ============================================================
  useEffect(() => {
    const loadBasket = async () => {
      if (hasLoadedBasket.current || loadingBasketRef.current) return;

      if (basketData && basketData.length > 0) {
        setLocalBasketData(basketData);
        hasLoadedBasket.current = true;
        if (basketId) {
          try {
            const response = await axios.get(`http://localhost:8000/api/baskets/${basketId}`);
            setBasketMeta({
              title: response.data.title || "",
              semester: response.data.semester || "",
              year: response.data.year || "",
            });
          } catch (err) {
            console.warn("خطا در واکشی متادیتای سبد:", err);
          }
        }
        return;
      }

      if (basketId) {
        loadingBasketRef.current = true;
        setIsLoadingBasket(true);
        setError(null);
        try {
          const response = await axios.get(`http://localhost:8000/api/baskets/${basketId}`);
          const basket = response.data;
          setBasketMeta({
            title: basket.title || "",
            semester: basket.semester || "",
            year: basket.year || "",
          });
          if (basket.items && basket.items.length > 0) {
            setLocalBasketData(basket.items);
          } else {
            setLocalBasketData(null);
          }
          hasLoadedBasket.current = true;
        } catch (err) {
          console.error("❌ خطا در واکشی سبد با شناسه:", err);
          setError("خطا در بارگذاری سبد از دیتابیس");
          setLocalBasketData(null);
        } finally {
          setIsLoadingBasket(false);
          loadingBasketRef.current = false;
        }
        return;
      }

      if (workflowId) {
        loadingBasketRef.current = true;
        setIsLoadingBasket(true);
        setError(null);
        try {
          const response = await axios.get(
            `http://localhost:8000/api/schedule/workflow/basket/${workflowId}`
          );
          const data = response.data;
          if (data.basket && data.basket.length > 0) {
            setLocalBasketData(data.basket);
            if (data.basket_meta) {
              setBasketMeta(data.basket_meta);
            } else {
              setBasketMeta({ title: "سبد (از workflow)", semester: "", year: "" });
            }
          } else {
            setLocalBasketData(null);
          }
          hasLoadedBasket.current = true;
        } catch (err) {
          console.error("❌ خطا در واکشی سبد:", err);
          if (err.response && err.response.status === 404) {
            setLocalBasketData(null);
          } else {
            setError("خطا در بارگذاری سبد از دیتابیس");
          }
        } finally {
          setIsLoadingBasket(false);
          loadingBasketRef.current = false;
        }
        return;
      }

      setLocalBasketData(null);
      setBasketMeta({ title: "", semester: "", year: "" });
      hasLoadedBasket.current = true;
    };

    loadBasket();
  }, [basketData, basketId, workflowId]);

  const effectiveBasketData = basketData && basketData.length > 0 ? basketData : localBasketData;

  // ============================================================
  // تابع محلی برای اجرای زمان‌بندی
  // ============================================================
  const handleLocalProcess = async () => {
    if (isLoadingBasket) {
      setError("در حال بارگذاری سبد، لطفاً صبر کنید...");
      return;
    }

    if (!effectiveBasketData || effectiveBasketData.length === 0) {
      setError("سبد دروس خالی است. لطفاً ابتدا سبد را پر کنید.");
      return;
    }

    setLoadingLocal(true);
    setError(null);
    setSteps([]);
    try {
      const result = await processSchedule({ basket: effectiveBasketData });
      setInstructorTimeDataLocal(result);
      if (result && result.steps) {
        setSteps(result.steps);
      } else {
        setSteps([]);
      }
      if (typeof onProcessParent === "function") {
        onProcessParent(result);
      }
      const assignedCount = result.assigned?.length || 0;
      const unassignedCount = result.unassigned?.length || 0;
      alert(`زمان‌بندی انجام شد. ${assignedCount} کلاس تخصیص یافت، ${unassignedCount} کلاس بدون استاد باقی ماند.`);
    } catch (err) {
      console.error("❌ خطا در زمان‌بندی:", err);
      setError(err.message || "خطا در اجرای زمان‌بندی");
      alert("خطا در زمان‌بندی: " + (err.message || "خطای ناشناخته"));
    } finally {
      setLoadingLocal(false);
    }
  };

  // ============================================================
  // state محلی برای نتیجه زمان‌بندی
  // ============================================================
  const [localInstructorTimeData, setInstructorTimeDataLocal] = useState(null);
  const effectiveInstructorTimeData = instructorTimeData || localInstructorTimeData;

  // ============================================================
  // استخراج داده‌ها و نرمال‌سازی
  // ============================================================
  const getData = () => {
    if (!effectiveInstructorTimeData) return { assigned: [], unassigned: [], all: [] };
    let rawData;
    if (Array.isArray(effectiveInstructorTimeData)) {
      rawData = { assigned: effectiveInstructorTimeData, unassigned: [], all: effectiveInstructorTimeData };
    } else {
      rawData = {
        assigned: effectiveInstructorTimeData.assigned || [],
        unassigned: effectiveInstructorTimeData.unassigned || [],
        all: effectiveInstructorTimeData.all || [],
      };
    }
    return rawData;
  };

  const rawData = getData();
  const { assigned, unassigned, all } = rawData;

  // ============================================================
  // lookup واحدهای درسی از سبد
  // ============================================================
  const unitsLookup = useMemo(() => {
    const lookup = {};
    const data = effectiveBasketData || [];
    data.forEach(item => {
      if (item.unique_code) {
        lookup[item.unique_code] = item.units || 2;
      }
    });
    return lookup;
  }, [effectiveBasketData]);

  // نرمال‌سازی با استفاده از unitsLookup
  const normalizedAll = useMemo(() => {
    return all.map(item => normalizeTimeSlot(item, unitsLookup));
  }, [all, unitsLookup]);

  const normalizedAssigned = useMemo(() => {
    return assigned.map(item => normalizeTimeSlot(item, unitsLookup));
  }, [assigned, unitsLookup]);

  const normalizedUnassigned = useMemo(() => {
    return unassigned.map(item => normalizeTimeSlot(item, unitsLookup));
  }, [unassigned, unitsLookup]);

  // ============================================================
  // lookup نام درس از کد یکتا
  // ============================================================
  const courseNameLookup = useMemo(() => {
    const lookup = {};
    const data = effectiveBasketData || [];
    data.forEach(item => {
      if (item.unique_code && item.course_name) {
        lookup[item.unique_code] = item.course_name;
      }
    });
    normalizedAll.forEach(item => {
      if (item.unique_code && item.course_name && !lookup[item.unique_code]) {
        lookup[item.unique_code] = item.course_name;
      }
    });
    return lookup;
  }, [effectiveBasketData, normalizedAll]);

  const instructorNameLookup = useMemo(() => {
    const lookup = {};
    normalizedAll.forEach(item => {
      if (item.instructor_code && item.instructor_name) {
        lookup[item.instructor_code] = item.instructor_name;
      }
    });
    instructorsData.forEach(inst => {
      if (inst.code && inst.name) {
        lookup[inst.code] = inst.name;
      }
    });
    return lookup;
  }, [normalizedAll, instructorsData]);

  // ============================================================
  // مقداردهی manualAssignments
  // ============================================================
  useEffect(() => {
    if (effectiveInstructorTimeData && typeof effectiveInstructorTimeData === "object") {
      if (effectiveInstructorTimeData.unassigned && effectiveInstructorTimeData.unassigned.length > 0) {
        const newAssignments = effectiveInstructorTimeData.unassigned.map((item) => {
          const units = unitsLookup[item.unique_code] || item.units || 2;
          const normalized = normalizeTimeSlot({ ...item, units }, unitsLookup);
          return {
            id: item.id || null,
            course_name: item.course_name || "",
            group_number: item.group_number || 1,
            level: item.level || "",
            term: item.term || "",
            unique_code: item.unique_code || "",
            units: units,
            instructor_code: "",
            day: normalized.day !== undefined ? normalized.day : 0,
            start: normalized.start || "07:30",
            end: normalized.end || "09:15",
          };
        });
        if (JSON.stringify(newAssignments) !== JSON.stringify(manualAssignments)) {
          setManualAssignments(newAssignments);
          setUnassignedList(effectiveInstructorTimeData.unassigned);
        }
      } else {
        if (manualAssignments.length > 0) {
          setManualAssignments([]);
          setUnassignedList([]);
        }
      }
    }
  }, [effectiveInstructorTimeData, unitsLookup]);

  // ============================================================
  // lookup مطلوبیت‌ها
  // ============================================================
  const teachingLookup = useMemo(() => {
    const lookup = {};
    teachingPreferences.forEach((pref) => {
      const courseCode = pref.unique_course_code;
      const instructorCode = pref.instructor_code;
      if (courseCode && instructorCode) {
        if (!lookup[courseCode]) lookup[courseCode] = new Set();
        lookup[courseCode].add(instructorCode);
      }
    });
    return lookup;
  }, [teachingPreferences]);

  // تابع نرمال‌سازی نام روز (مشابه بک‌اند)
  const normalizeDayName = (day) => {
    if (!day) return '';
    let normalized = day.replace(/\u200c/g, ' ');
    normalized = normalized.trim().replace(/\s+/g, ' ');
    return normalized.replace(/ /g, '');
  };

  const timeLookup = useMemo(() => {
    const lookup = {};
    const dayMap = {
      "شنبه": 0,
      "یکشنبه": 1,
      "دوشنبه": 2,
      "سه‌شنبه": 3,
      "سهشنبه": 3,
      "چهارشنبه": 4,
      "پنجشنبه": 5,
    };

    timePreferences.forEach((pref) => {
      const instructorCode = pref.instructor_code;
      if (!instructorCode) return;
      if (!lookup[instructorCode]) lookup[instructorCode] = [];

      const dayNorm = normalizeDayName(pref.day);
      const dayNum = dayMap[dayNorm];
      if (dayNum === undefined) {
        console.warn(`روز ناشناخته برای استاد ${instructorCode}: "${pref.day}" (نرمال‌شده: "${dayNorm}")`);
        return;
      }

      // نرمال‌سازی بازه مطلوب (۱۲-۱۶ -> ۱۳-۱۷) مشابه بک‌اند
      let start = pref.start_time;
      let end = pref.end_time;
      if (start === "12:00" && end === "16:00") {
        start = "13:00";
        end = "17:00";
      }

      lookup[instructorCode].push({
        day: dayNum,
        start: start,
        end: end,
        priority: pref.priority !== undefined ? pref.priority : null,
      });
    });

    for (const inst in lookup) {
      lookup[inst].sort((a, b) => (a.priority || 999) - (b.priority || 999));
    }

    return lookup;
  }, [timePreferences]);

  // ============================================================
  // استخراج اطلاعات دلایل عدم تطابق از steps (میدان mismatch_details)
  // ============================================================
  const mismatchReasons = useMemo(() => {
    if (!steps || steps.length === 0) return [];
    const finalStep = steps[steps.length - 1];
    if (finalStep && finalStep.details && finalStep.details.mismatch_details) {
      return finalStep.details.mismatch_details;
    }
    return [];
  }, [steps]);

  // ============================================================
  // محاسبه آمار تطابق (قدیمی - برای سازگاری با بخش‌های دیگر)
  // ============================================================
  useEffect(() => {
    const data = normalizedAll;
    if (!data || data.length === 0) {
      setStats({ totalClasses: 0, teachingMatchCount: 0, dayMatchCount: 0, timeMatchCount: 0, bothMatchCount: 0 });
      return;
    }
    let teachingMatch = 0, dayMatch = 0, timeMatch = 0, bothMatch = 0;
    data.forEach((row) => {
      const courseCode = row.unique_code;
      const instructorCode = row.instructor_code;
      const day = row.day;
      const start = row.start;
      const end = row.end;
      let teachOk = false;
      if (courseCode && instructorCode) {
        const preferred = teachingLookup[courseCode];
        if (preferred && preferred.has(instructorCode)) {
          teachOk = true;
          teachingMatch++;
        }
      }
      let dayOk = false, timeOk = false;
      if (instructorCode && day !== undefined) {
        const preferredSlots = timeLookup[instructorCode];
        if (preferredSlots && preferredSlots.length > 0) {
          if (preferredSlots.some((slot) => slot.day === day)) {
            dayOk = true;
            dayMatch++;
          }
          if (start && end) {
            if (preferredSlots.some(
              (slot) => slot.day === day && isTimeSlotMatchWithTolerance(start, end, slot.start, slot.end, 60)
            )) {
              timeOk = true;
              timeMatch++;
            }
          }
        }
      }
      if (teachOk && timeOk) bothMatch++;
    });
    setStats({ totalClasses: data.length, teachingMatchCount: teachingMatch, dayMatchCount: dayMatch, timeMatchCount: timeMatch, bothMatchCount: bothMatch });
  }, [normalizedAll, teachingLookup, timeLookup]);

  // ============================================================
  // محاسبه آمار جدید بر اساس mismatch_details (هماهنگ با بک‌اند)
  // ============================================================
  const assignedCount = normalizedAssigned.length;
  const unassignedCount = normalizedUnassigned.length;

  const matchStats = useMemo(() => {
    // اگر هیچ داده‌ای وجود ندارد، همه صفر
    if (assignedCount === 0 && unassignedCount === 0) {
      return { full: 0, partial: 0, none: 0, no_preference: 0, no_assignment: 0, unassigned: 0 };
    }

    let partial = 0, none = 0, no_preference = 0, no_assignment = 0, unassigned = 0;
    mismatchReasons.forEach(item => {
      const status = item.status || 'unknown';
      if (status === 'partial') partial++;
      else if (status === 'none') none++;
      else if (status === 'no_preference') no_preference++;
      else if (status === 'no_assignment') no_assignment++;
      else if (status === 'unassigned') unassigned++;
    });

    // تعداد موارد تخصیص‌یافته که در mismatchReasons هستند (یعنی مشکل دارند)
    const assignedWithIssues = mismatchReasons.filter(item => item.is_assigned === true).length;
    // تعداد تطابق کامل = کل تخصیص‌یافته - تعداد تخصیص‌یافته‌های مشکل‌دار
    const full = assignedCount - assignedWithIssues;

    return { full, partial, none, no_preference, no_assignment, unassigned };
  }, [mismatchReasons, assignedCount, unassignedCount]);

  // ============================================================
  // مدیریت تغییرات دستی
  // ============================================================
  const handleManualAssignmentChange = (index, field, value) => {
    const updated = [...manualAssignments];
    updated[index] = { ...updated[index], [field]: value };
    setManualAssignments(updated);
  };

  const saveManualAssignments = async () => {
    const invalid = manualAssignments.some((item) => !item.instructor_code);
    if (invalid) {
      alert("لطفاً برای همه کلاس‌ها استاد انتخاب کنید.");
      return;
    }
    setIsSavingManual(true);
    setError(null);
    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        { assignments: manualAssignments }
      );
      setManualResult(response.data);
      alert(`✅ ${response.data.success_count} کلاس با موفقیت تخصیص یافت.`);
      setManualMode(false);
      await handleLocalProcess();
    } catch (err) {
      console.error("❌ خطا در ذخیره تخصیص دستی:", err);
      setError(err.response?.data?.detail || "خطا در ذخیره تخصیص دستی");
      alert("خطا در ذخیره تخصیص دستی");
    } finally {
      setIsSavingManual(false);
    }
  };

  // ============================================================
  // مدیریت ویرایش مستقیم در جدول
  // ============================================================
  const startEditing = () => {
    const normalizedData = normalizedAssigned.map(row => {
      const units = row.units || 2;
      const validSlots = getValidSlots(units);
      const validStarts = validSlots.map(slot => slot[0]);

      let start = String(row.start || '');
      let end = String(row.end || '');

      if (!validStarts.includes(start)) {
        start = validStarts[0] || '';
        const foundSlot = validSlots.find(slot => slot[0] === start);
        end = foundSlot ? foundSlot[1] : '';
      }

      return {
        ...row,
        start,
        end
      };
    });
    setEditedData(normalizedData);
    setEditingMode(true);
  };

  const cancelEditing = () => {
    setEditingMode(false);
    setEditedData([]);
  };

  const getEndFromStart = (start, units) => {
    const slots = getValidSlots(units);
    const found = slots.find(slot => slot[0] === start);
    return found ? found[1] : null;
  };

  const handleStartBlur = (index) => {
    const row = editedData[index];
    if (row && row.start) {
      const units = row.units || 2;
      const end = getEndFromStart(row.start, units);
      if (end) {
        const updated = [...editedData];
        updated[index].end = String(end);
        setEditedData(updated);
      }
    }
  };

  const handleEditChange = (index, field, value) => {
    const updated = [...editedData];
    const row = updated[index];
    if (field === 'start') {
      const startStr = String(value);
      row.start = startStr;
      const units = row.units || 2;
      const end = getEndFromStart(startStr, units);
      if (end) {
        row.end = String(end);
      }
    } else {
      row[field] = value;
    }
    setEditedData(updated);
  };

  const saveEdits = async () => {
    const invalid = editedData.some(item => !item.instructor_code);
    if (invalid) {
      alert("لطفاً برای همه کلاس‌ها استاد انتخاب کنید.");
      return;
    }

    const assignments = editedData.map(item => ({
      course_name: item.course_name,
      group_number: item.group_number,
      level: item.level,
      term: item.term,
      instructor_code: item.instructor_code,
      day: item.day,
      start: item.start,
      end: item.end,
    }));

    setIsSavingEdits(true);
    setError(null);
    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        { assignments }
      );
      alert(`✅ ${response.data.success_count} کلاس با موفقیت ویرایش شد.`);
      setEditingMode(false);
      await handleLocalProcess();
    } catch (err) {
      console.error("❌ خطا در ذخیره ویرایش‌ها:", err);
      setError(err.response?.data?.detail || "خطا در ذخیره ویرایش‌ها");
      alert("خطا در ذخیره ویرایش‌ها");
    } finally {
      setIsSavingEdits(false);
    }
  };

  // ============================================================
  // ستون‌های جدول سبد (افزودن ستون "تعداد واحد")
  // ============================================================
  const basketColumns = [
    { key: "level", label: "مقطع" },
    { key: "term", label: "ترم" },
    { key: "course_name", label: "نام درس" },
    { key: "unique_code", label: "کد یکتا" },
    { key: "group_number", label: "گروه" },
    { key: "units", label: "تعداد واحد" },
    { key: "estimated_capacity", label: "برآورد ظرفیت" },
    { key: "required_classes", label: "کلاس مورد نیاز" },
  ];

  // ============================================================
  // ستون‌های جدول نتایج
  // ============================================================
  const tableColumns = [
    { key: "course_name", label: "درس" },
    { key: "units", label: "تعداد واحد" },
    { key: "instructor_name", label: "استاد" },
    { key: "instructor_code", label: "کد استاد" },
    { key: "day", label: "روز", render: (row) => getDayName(row.day) },
    { key: "start", label: "شروع" },
    { key: "end", label: "پایان" },
    { key: "group_number", label: "گروه" },
    { key: "level", label: "مقطع" },
    { key: "estimated_capacity", label: "ظرفیت" },
    { key: "final_score", label: "امتیاز نهایی", render: (row) => (row.final_score !== undefined ? row.final_score : "—") },
  ];

  // ============================================================
  // ستون‌های جدول برای تخصیص دستی
  // ============================================================
  const manualColumns = [
    { key: "course_name", label: "درس" },
    { key: "group_number", label: "گروه" },
    { key: "level", label: "مقطع" },
    { key: "term", label: "ترم" },
    {
      key: "instructor_code",
      label: "استاد (کد)",
      render: (row, index) => (
        <input
          type="text"
          value={row.instructor_code || ""}
          onChange={(e) => handleManualAssignmentChange(index, "instructor_code", e.target.value)}
          placeholder="کد استاد را وارد کنید"
          className="manual-input"
        />
      ),
    },
    {
      key: "day",
      label: "روز",
      render: (row, index) => (
        <select
          value={row.day !== undefined ? row.day : 0}
          onChange={(e) => handleManualAssignmentChange(index, "day", parseInt(e.target.value))}
          className="manual-select"
        >
          {dayNames.map((name, i) => <option key={i} value={i}>{name}</option>)}
        </select>
      ),
    },
    {
      key: "time_slot",
      label: "بازه زمانی",
      render: (row, index) => {
        const units = row.units || 2;
        const validSlots = getValidSlots(units);
        const currentSlot = `${row.start || ""}-${row.end || ""}`;
        const selectedValue = validSlots.includes(currentSlot) ? currentSlot : validSlots[0];
        return (
          <select
            value={selectedValue}
            onChange={(e) => {
              const slot = e.target.value;
              const [start, end] = slot.split('-');
              handleManualAssignmentChange(index, "start", start);
              handleManualAssignmentChange(index, "end", end);
            }}
            className="manual-select"
          >
            {validSlots.map((slot) => (
              <option key={slot} value={slot}>{slot.replace('-', ' - ')}</option>
            ))}
          </select>
        );
      },
    },
  ];

  // ============================================================
  // فیلتر بر اساس روز و جستجو
  // ============================================================
  const filterByDay = (data) => {
    if (selectedDay === null) return data;
    return data.filter(item => item.day === selectedDay);
  };

  const filterBySearch = (data) => {
    if (!debouncedSearchTerm.trim()) return data;
    const term = debouncedSearchTerm.trim().toLowerCase();
    return data.filter(item => {
      const searchable = [
        item.course_name,
        item.instructor_name,
        item.instructor_code,
        getDayName(item.day),
        item.start,
        item.end,
        String(item.group_number),
        item.level,
        String(item.estimated_capacity),
        item.unique_code,
      ].filter(Boolean).map(s => s.toString().toLowerCase());
      return searchable.some(field => field.includes(term));
    });
  };

  const filteredAssigned = filterBySearch(filterByDay(normalizedAssigned));
  const filteredAll = filterBySearch(filterByDay(normalizedAll));
  const filteredUnassigned = filterBySearch(filterByDay(normalizedUnassigned));
  const filteredManualAssignments = filterBySearch(filterByDay(manualAssignments));

  // ============================================================
  // محاسبه فراوانی‌ها (با داده‌های فیلتر شده)
  // ============================================================
  const computeFrequency = (data) => {
    if (!data || data.length === 0) return null;
    const courseFreq = {}, timeSlotFreq = {}, dayFreq = {}, instructorFreq = {}, levelFreq = {};
    data.forEach(item => {
      const course = item.course_name || 'نامشخص';
      courseFreq[course] = (courseFreq[course] || 0) + 1;
      const slot = `${item.start || ''} - ${item.end || ''}`;
      if (slot.trim()) timeSlotFreq[slot] = (timeSlotFreq[slot] || 0) + 1;
      const day = getDayName(item.day);
      dayFreq[day] = (dayFreq[day] || 0) + 1;
      const instructor = item.instructor_name || item.instructor_code || 'نامشخص';
      instructorFreq[instructor] = (instructorFreq[instructor] || 0) + 1;
      const level = item.level || 'نامشخص';
      levelFreq[level] = (levelFreq[level] || 0) + 1;
    });
    const sortDesc = (obj) => Object.entries(obj).sort((a, b) => b[1] - a[1]);
    return {
      course: sortDesc(courseFreq),
      timeSlot: sortDesc(timeSlotFreq),
      day: sortDesc(dayFreq),
      instructor: sortDesc(instructorFreq),
      level: sortDesc(levelFreq),
    };
  };

  const allDataForStats = filteredAll;
  const frequencyData = computeFrequency(allDataForStats);

  // ============================================================
  // استخراج لیست اساتید با نام و اطلاعات کامل
  // ============================================================
  const instructorList = useMemo(() => {
    if (instructorsData && instructorsData.length > 0) {
      return instructorsData.map(inst => ({
        code: inst.code,
        name: inst.name,
        cooperation_type: inst.cooperation_type || 'نامشخص',
        max_teaching_units: inst.max_teaching_units || 0,
      })).sort((a, b) => a.name.localeCompare(b.name));
    }
    const instructors = new Map();
    normalizedAll.forEach(item => {
      if (item.instructor_code && item.instructor_name) {
        instructors.set(item.instructor_code, item.instructor_name);
      }
    });
    return Array.from(instructors.entries())
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([code, name]) => ({ code, name, cooperation_type: 'نامشخص', max_teaching_units: 0 }));
  }, [instructorsData, normalizedAll]);

  // ============================================================
  // استخراج لیست دروس یکتا از سبد
  // ============================================================
  const courseList = useMemo(() => {
    if (!effectiveBasketData) return [];
    const courseMap = new Map();
    effectiveBasketData.forEach(item => {
      const code = item.unique_code;
      if (code && !courseMap.has(code)) {
        courseMap.set(code, {
          code: code,
          name: item.course_name || code,
          level: item.level || '',
          term: item.term || '',
          units: item.units || 2,
        });
      }
    });
    return Array.from(courseMap.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [effectiveBasketData]);

  // ============================================================
  // داده‌های مربوط به استاد انتخاب‌شده
  // ============================================================
  const instructorData = useMemo(() => {
    if (!selectedInstructor) return null;
    const classes = filteredAll.filter(item => item.instructor_code === selectedInstructor);
    const teachPrefs = teachingPreferences
      .filter(p => p.instructor_code === selectedInstructor)
      .map(p => p.unique_course_code);
    const timePrefs = timePreferences
      .filter(p => p.instructor_code === selectedInstructor)
      .map(p => ({
        day: getDayName(p.day),
        start: p.start_time,
        end: p.end_time,
        priority: p.priority !== undefined ? p.priority : null,
      }));

    const classStatus = classes.map(cls => {
      const status = getMatchStatus(cls, teachingLookup, timeLookup);
      const teachMatch = getFieldMatchStatus(cls, 'course_name', teachingLookup, timeLookup) === 'full';
      const dayMatch = getFieldMatchStatus(cls, 'day', teachingLookup, timeLookup) === 'full';
      const timeMatch = getFieldMatchStatus(cls, 'start', teachingLookup, timeLookup) === 'full';
      return { ...cls, status, teachMatch, dayMatch, timeMatch };
    });

    const fullCount = classStatus.filter(c => c.status === 'full').length;
    const partialCount = classStatus.filter(c => c.status === 'partial').length;
    const noneCount = classStatus.filter(c => c.status === 'none').length;
    const noPrefCount = classStatus.filter(c => c.status === 'no_preference').length;

    const instructorInfo = instructorList.find(inst => inst.code === selectedInstructor);

    return {
      classes: classStatus,
      teachPrefs,
      timePrefs,
      summary: { fullCount, partialCount, noneCount, noPrefCount, total: classes.length },
      instructorInfo,
    };
  }, [selectedInstructor, filteredAll, teachingPreferences, timePreferences, teachingLookup, timeLookup, instructorList]);

  // ============================================================
  // داده‌های مربوط به درس انتخاب‌شده (اضافه شدن مطلوبیت‌های تدریس)
  // ============================================================
  const courseData = useMemo(() => {
    if (!selectedCourseCode) return null;
    const classes = filteredAll.filter(item => item.unique_code === selectedCourseCode);
    const courseInfo = courseList.find(c => c.code === selectedCourseCode);

    const groups = classes.map(cls => {
      const status = getMatchStatus(cls, teachingLookup, timeLookup);
      const teachMatch = getFieldMatchStatus(cls, 'course_name', teachingLookup, timeLookup) === 'full';
      const dayMatch = getFieldMatchStatus(cls, 'day', teachingLookup, timeLookup) === 'full';
      const timeMatch = getFieldMatchStatus(cls, 'start', teachingLookup, timeLookup) === 'full';
      return {
        ...cls,
        status,
        teachMatch,
        dayMatch,
        timeMatch,
        hasInstructor: !!cls.instructor_code,
        hasTime: !!cls.start && !!cls.end,
      };
    });

    const total = groups.length;
    const assignedCount = groups.filter(g => g.hasInstructor && g.hasTime).length;
    const unassignedCount = total - assignedCount;
    const fullMatchCount = groups.filter(g => g.status === 'full').length;
    const partialMatchCount = groups.filter(g => g.status === 'partial').length;
    const noMatchCount = groups.filter(g => g.status === 'none').length;
    const noPrefCount = groups.filter(g => g.status === 'no_preference').length;

    const teachingPrefsForCourse = teachingPreferences
      .filter(pref => pref.unique_course_code === selectedCourseCode)
      .sort((a, b) => (a.priority || 999) - (b.priority || 999));

    const preferredInstructors = teachingPrefsForCourse.map(pref => ({
      instructor_code: pref.instructor_code,
      instructor_name: instructorNameLookup[pref.instructor_code] || pref.instructor_code,
      priority: pref.priority,
    }));

    return {
      courseInfo,
      groups,
      summary: { total, assignedCount, unassignedCount, fullMatchCount, partialMatchCount, noMatchCount, noPrefCount },
      preferredInstructors,
    };
  }, [selectedCourseCode, filteredAll, teachingLookup, timeLookup, courseList, teachingPreferences, instructorNameLookup]);

  // ============================================================
  // تشخیص تداخل‌های زمانی برای اساتید
  // ============================================================
  const findConflicts = (data) => {
    if (!data || data.length === 0) return [];

    const groups = {};
    data.forEach(item => {
      const instructor = item.instructor_code;
      const day = item.day;
      if (!instructor || day === undefined || day === null) return;
      const key = `${instructor}_${day}`;
      if (!groups[key]) {
        groups[key] = {
          instructor_code: instructor,
          instructor_name: instructorNameLookup[instructor] || instructor,
          day: day,
          dayName: getDayName(day),
          items: [],
        };
      }
      groups[key].items.push(item);
    });

    const conflicts = [];
    Object.values(groups).forEach(group => {
      const sorted = group.items.slice().sort((a, b) => {
        const aStart = timeToMinutes(a.start);
        const bStart = timeToMinutes(b.start);
        return aStart - bStart;
      });

      for (let i = 0; i < sorted.length; i++) {
        for (let j = i + 1; j < sorted.length; j++) {
          const a = sorted[i];
          const b = sorted[j];
          const aStart = timeToMinutes(a.start);
          const aEnd = timeToMinutes(a.end);
          const bStart = timeToMinutes(b.start);
          const bEnd = timeToMinutes(b.end);
          if (aStart < bEnd && bStart < aEnd) {
            conflicts.push({
              instructor_code: group.instructor_code,
              instructor_name: group.instructor_name,
              day: group.day,
              dayName: group.dayName,
              course1: a,
              course2: b,
            });
          }
        }
      }
    });

    return conflicts;
  };

  const conflictData = useMemo(() => {
    return findConflicts(filteredAssigned);
  }, [filteredAssigned]);

  // ============================================================
  // رندر نمای تداخل‌ها
  // ============================================================
  const renderConflictsView = () => {
    if (!conflictData || conflictData.length === 0) {
      return <div className="no-data-message">✅ هیچ تداخل زمانی برای اساتید یافت نشد.</div>;
    }

    return (
      <div className="conflicts-view">
        <h4>⚠️ تداخل‌های زمانی اساتید</h4>
        <p>تعداد تداخل‌های شناسایی‌شده: {conflictData.length}</p>
        <div className="table-responsive">
          <table className="conflicts-table">
            <thead>
              <tr>
                <th>استاد</th>
                <th>روز</th>
                <th>درس اول</th>
                <th>گروه</th>
                <th>بازه اول</th>
                <th>درس دوم</th>
                <th>گروه</th>
                <th>بازه دوم</th>
              </tr>
            </thead>
            <tbody>
              {conflictData.map((conf, idx) => (
                <tr key={idx} className="conflict-row">
                  <td>{conf.instructor_name} ({conf.instructor_code})</td>
                  <td>{conf.dayName}</td>
                  <td>{conf.course1.course_name}</td>
                  <td>{conf.course1.group_number}</td>
                  <td>{conf.course1.start} - {conf.course1.end}</td>
                  <td>{conf.course2.course_name}</td>
                  <td>{conf.course2.group_number}</td>
                  <td>{conf.course2.start} - {conf.course2.end}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر نمای دلایل عدم تطابق (شامل خلاصه آماری و جدول با رنگ‌بندی)
  // ============================================================
  const renderReasonsView = () => {
    if (!mismatchReasons || mismatchReasons.length === 0) {
      return <div className="no-data-message">✅ همه دروس با موفقیت تطابق کامل دارند.</div>;
    }

    // ------------------------------------------------------------
    // ۱. محاسبه آمار کلی
    // ------------------------------------------------------------
    const total = mismatchReasons.length;
    const assignedItems = mismatchReasons.filter(item => item.is_assigned === true);
    const unassignedItems = mismatchReasons.filter(item => item.is_assigned === false);

    const totalAssigned = assignedItems.length;
    const totalUnassigned = unassignedItems.length;

    // آمار وضعیت‌ها (از mismatchReasons)
    const statusCounts = {
      full: 0,
      partial: 0,
      none: 0,
      unassigned: 0,
      no_assignment: 0,
      no_preference: 0,
    };
    mismatchReasons.forEach(item => {
      const status = item.status || 'unknown';
      if (statusCounts.hasOwnProperty(status)) {
        statusCounts[status]++;
      }
    });

    // ------------------------------------------------------------
    // ۲. گروه‌بندی دلایل تخصیص‌نیافتگی (برای unassigned)
    // ------------------------------------------------------------
    const reasonGroups = {};
    unassignedItems.forEach(item => {
      const reason = item.reason || 'دلیل نامشخص';
      let groupKey = reason;
      if (reason.includes('unique_code')) groupKey = 'unique_code_invalid';
      else if (reason.includes('هیچ استاد واجد شرطی')) groupKey = 'no_preferred_instructor';
      else if (reason.includes('ظرفیت تدریس')) groupKey = 'capacity_exceeded';
      else if (reason.includes('گم شده')) groupKey = 'missing_in_process';
      else if (reason.includes('اسلات آزاد')) groupKey = 'no_free_slot';
      else groupKey = 'other';

      if (!reasonGroups[groupKey]) {
        reasonGroups[groupKey] = { count: 0, sample: [] };
      }
      reasonGroups[groupKey].count++;
      if (reasonGroups[groupKey].sample.length < 3) {
        reasonGroups[groupKey].sample.push({
          course: item.course_name,
          group: item.group_number,
          reason: reason,
        });
      }
    });

    const reasonLabels = {
      'unique_code_invalid': 'کد یکتا (unique_code) نامعتبر یا خالی',
      'no_preferred_instructor': 'هیچ استاد اولویت‌داری ثبت نشده است',
      'capacity_exceeded': 'تکمیل ظرفیت واحد اساتید',
      'missing_in_process': 'گم‌شدن در حین فرایند زمان‌بندی',
      'no_free_slot': 'عدم وجود اسلات زمانی آزاد',
      'other': 'سایر دلایل',
    };

    // ------------------------------------------------------------
    // ۳. رندر بخش خلاصه
    // ------------------------------------------------------------
    const renderSummary = () => (
      <div className="summary-section">
        <h4>📊 خلاصه وضعیت عدم تطابق</h4>

        <div className="summary-stats-grid">
          <div className="stat-card">
            <span className="stat-label">مجموع موارد عدم تطابق</span>
            <span className="stat-value">{total}</span>
          </div>
          <div className="stat-card assigned">
            <span className="stat-label">تخصیص‌یافته (با تطابق ناقص)</span>
            <span className="stat-value">{totalAssigned}</span>
          </div>
          <div className="stat-card unassigned">
            <span className="stat-label">تخصیص‌نیافته</span>
            <span className="stat-value">{totalUnassigned}</span>
          </div>
        </div>

        <div className="status-breakdown">
          <h5>وضعیت تطابق (برای دروس تخصیص‌یافته)</h5>
          <div className="status-bars">
            <div className="status-bar-item">
              <span className="status-label">تطابق نسبی</span>
              <div className="bar-track">
                <div className="bar-fill partial" style={{ width: `${(statusCounts.partial / totalAssigned) * 100 || 0}%` }}></div>
              </div>
              <span className="bar-count">{statusCounts.partial}</span>
            </div>
            <div className="status-bar-item">
              <span className="status-label">بدون تطابق</span>
              <div className="bar-track">
                <div className="bar-fill none" style={{ width: `${(statusCounts.none / totalAssigned) * 100 || 0}%` }}></div>
              </div>
              <span className="bar-count">{statusCounts.none}</span>
            </div>
            <div className="status-bar-item">
              <span className="status-label">بدون مطلوبیت</span>
              <div className="bar-track">
                <div className="bar-fill no-preference" style={{ width: `${(statusCounts.no_preference / totalAssigned) * 100 || 0}%` }}></div>
              </div>
              <span className="bar-count">{statusCounts.no_preference}</span>
            </div>
            <div className="status-bar-item">
              <span className="status-label">تخصیص ناقص</span>
              <div className="bar-track">
                <div className="bar-fill no-assignment" style={{ width: `${(statusCounts.no_assignment / totalAssigned) * 100 || 0}%` }}></div>
              </div>
              <span className="bar-count">{statusCounts.no_assignment}</span>
            </div>
          </div>
        </div>

        <div className="reason-breakdown">
          <h5>دلایل تخصیص‌نیافتگی</h5>
          <ul className="reason-list">
            {Object.entries(reasonGroups).map(([key, data]) => (
              <li key={key}>
                <span className="reason-label">{reasonLabels[key] || key}</span>
                <span className="reason-count">{data.count} درس</span>
                {data.sample.length > 0 && (
                  <span className="reason-sample">
                    (نمونه: {data.sample.map(s => `${s.course} (گروه ${s.group})`).join('، ')})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );

    // ------------------------------------------------------------
    // ۴. رندر جدول اصلی با کلاس‌های رنگ‌بندی
    // ------------------------------------------------------------
    const statusMap = {
      'full': 'تطابق کامل',
      'partial': 'تطابق نسبی',
      'none': 'بدون تطابق',
      'unassigned': 'تخصیص نیافته',
      'no_assignment': 'تخصیص ناقص',
      'no_preference': 'بدون مطلوبیت'
    };

    return (
      <div className="reasons-view">
        {renderSummary()}
        <div className="reasons-table-wrapper">
          <h4>📋 جزئیات عدم تطابق</h4>
          <div className="table-responsive">
            <table className="reasons-table">
              <thead>
                <tr>
                  <th>درس</th>
                  <th>گروه</th>
                  <th>کد درس</th>
                  <th>مقطع</th>
                  <th>ترم</th>
                  <th>استاد</th>
                  <th>وضعیت تخصیص</th>
                  <th>وضعیت تطابق</th>
                  <th>دلیل</th>
                </tr>
              </thead>
              <tbody>
                {mismatchReasons.map((item, idx) => {
                  const statusLabel = statusMap[item.status] || item.status;
                  const isAssigned = item.is_assigned ? 'تخصیص‌یافته' : 'تخصیص نیافته';
                  return (
                    <tr key={idx} className={`mismatch-row status-${item.status || 'unknown'}`}>
                      <td>{item.course_name || 'نامشخص'}</td>
                      <td>{item.group_number || '—'}</td>
                      <td>{item.unique_code || '—'}</td>
                      <td>{item.level || '—'}</td>
                      <td>{item.term || '—'}</td>
                      <td>{item.instructor_name ? `${item.instructor_name} (${item.instructor_code})` : '—'}</td>
                      <td>{isAssigned}</td>
                      <td>{statusLabel}</td>
                      <td>{item.reason || 'دلیل نامشخص'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // انتخاب اولین استاد به‌طور خودکار
  // ============================================================
  useEffect(() => {
    if (instructorList.length > 0 && !selectedInstructor && !hasSetDefaultInstructor.current) {
      setSelectedInstructor(instructorList[0].code);
      hasSetDefaultInstructor.current = true;
    }
  }, [instructorList, selectedInstructor]);

  // ============================================================
  // انتخاب اولین درس به‌طور خودکار
  // ============================================================
  useEffect(() => {
    if (courseList.length > 0 && !selectedCourseCode && !hasSetDefaultCourse.current) {
      setSelectedCourseCode(courseList[0].code);
      hasSetDefaultCourse.current = true;
    }
  }, [courseList, selectedCourseCode]);

  // ============================================================
  // رندر دکمه‌های فیلتر روز
  // ============================================================
  const renderDayFilters = () => (
    <div className="day-filters">
      <button
        className={`day-filter-btn ${selectedDay === null ? 'active' : ''}`}
        onClick={() => setSelectedDay(null)}
      >
        همه روزها
      </button>
      {dayNames.map((name, index) => (
        <button
          key={index}
          className={`day-filter-btn ${selectedDay === index ? 'active' : ''}`}
          onClick={() => setSelectedDay(index)}
        >
          {name}
        </button>
      ))}
    </div>
  );

  // ============================================================
  // رندر تب‌های تغییر View - اضافه کردن دکمه دلایل عدم تطابق
  // ============================================================
  const renderViewTabs = () => (
    <div className="view-tabs">
      <button
        className={`view-tab ${viewMode === 'table' ? 'active' : ''}`}
        onClick={() => setViewMode('table')}
      >
        📋 جدول
      </button>
      <button
        className={`view-tab ${viewMode === 'matrix' ? 'active' : ''}`}
        onClick={() => setViewMode('matrix')}
      >
        📊 ماتریس زمانی
      </button>
      <button
        className={`view-tab ${viewMode === 'chart' ? 'active' : ''}`}
        onClick={() => setViewMode('chart')}
      >
        📈 نمودار میله‌ای
      </button>
      <button
        className={`view-tab ${viewMode === 'calendar' ? 'active' : ''}`}
        onClick={() => setViewMode('calendar')}
      >
        📅 تقویم هفتگی
      </button>
      <button
        className={`view-tab ${viewMode === 'instructor' ? 'active' : ''}`}
        onClick={() => setViewMode('instructor')}
      >
        👨‍🏫 اطلاعات استاد
      </button>
      <button
        className={`view-tab ${viewMode === 'course' ? 'active' : ''}`}
        onClick={() => setViewMode('course')}
      >
        📚 اطلاعات درس
      </button>
      <button
        className={`view-tab ${viewMode === 'conflicts' ? 'active' : ''}`}
        onClick={() => setViewMode('conflicts')}
      >
        ⚠️ تداخل‌ها
      </button>
      <button
        className={`view-tab ${viewMode === 'reasons' ? 'active' : ''}`}
        onClick={() => setViewMode('reasons')}
      >
        ❓ دلایل عدم تطابق
      </button>
    </div>
  );

  // ============================================================
  // رندر جستجو
  // ============================================================
  const renderSearch = () => (
    <div className="table-search">
      <input
        type="text"
        placeholder="🔍 جستجو در جدول..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="search-input"
      />
      {searchTerm && (
        <button
          className="search-clear"
          onClick={() => {
            setSearchTerm("");
            setDebouncedSearchTerm("");
          }}
        >
          پاک کردن
        </button>
      )}
    </div>
  );

  // ============================================================
  // رندر اطلاعات استاد
  // ============================================================
  const renderInstructorInfo = () => {
    if (!instructorData) {
      return <div className="no-data-message">هیچ استادی انتخاب نشده است.</div>;
    }

    const { classes, teachPrefs, timePrefs, summary, instructorInfo } = instructorData;

    return (
      <div className="instructor-info-container">
        <div className="instructor-selector">
          <label>انتخاب استاد:</label>
          <select
            value={selectedInstructor}
            onChange={(e) => setSelectedInstructor(e.target.value)}
            className="instructor-select"
          >
            {instructorList.map(({ code, name }) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </div>

        <div className="instructor-details">
          <div className="instructor-info-card">
            <h4>👤 اطلاعات استاد</h4>
            {loadingInstructors ? (
              <div>در حال بارگذاری اطلاعات...</div>
            ) : (
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">نوع همکاری</span>
                  <span className="info-value">{instructorInfo?.cooperation_type || 'نامشخص'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">سقف واحد تدریس</span>
                  <span className="info-value">{instructorInfo?.max_teaching_units || 'نامشخص'}</span>
                </div>
              </div>
            )}
            {(!instructorsData || instructorsData.length === 0) && !loadingInstructors && (
              <div className="info-warning">⚠️ اطلاعات کامل استاد در دسترس نیست.</div>
            )}
          </div>

          <div className="preferences-section">
            <h4>مطلوبیت‌های تدریس</h4>
            {teachPrefs.length > 0 ? (
              <ul className="pref-list">
                {teachPrefs.map(courseCode => (
                  <li key={courseCode}>{courseNameLookup[courseCode] || courseCode}</li>
                ))}
              </ul>
            ) : (
              <span className="empty-message">هیچ مطلوبیت تدریسی ثبت نشده است.</span>
            )}
          </div>

          <div className="preferences-section">
            <h4>مطلوبیت‌های زمان</h4>
            {timePrefs.length > 0 ? (
              <table className="time-pref-table">
                <thead>
                  <tr>
                    <th>روز</th>
                    <th>شروع</th>
                    <th>پایان</th>
                    <th>اولویت</th>
                  </tr>
                </thead>
                <tbody>
                  {timePrefs.map((p, i) => (
                    <tr key={i}>
                      <td>{p.day}</td>
                      <td>{p.start}</td>
                      <td>{p.end}</td>
                      <td>{p.priority !== null ? p.priority : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="empty-message">هیچ مطلوبیت زمانی ثبت نشده است.</span>
            )}
          </div>

          <div className="summary-section">
            <h4>جمع‌بندی وضعیت کلاس‌ها</h4>
            <div className="summary-stats">
              <div className="stat-item">
                <span className="stat-label">مجموع کلاس‌ها</span>
                <span className="stat-value">{summary.total}</span>
              </div>
              <div className="stat-item" style={{ color: '#93c5fd' }}>
                <span className="stat-label">تطابق کامل</span>
                <span className="stat-value">{summary.fullCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#fcd34d' }}>
                <span className="stat-label">تطابق نسبی</span>
                <span className="stat-value">{summary.partialCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#fca5a5' }}>
                <span className="stat-label">بدون تطابق</span>
                <span className="stat-value">{summary.noneCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#e5e7eb' }}>
                <span className="stat-label">بدون مطلوبیت</span>
                <span className="stat-value">{summary.noPrefCount}</span>
              </div>
            </div>
          </div>

          <div className="classes-section">
            <h4>کلاس‌های تخصیص‌یافته</h4>
            {classes.length > 0 ? (
              <table className="classes-table">
                <thead>
                  <tr>
                    <th>درس</th>
                    <th>روز</th>
                    <th>شروع</th>
                    <th>پایان</th>
                    <th>تطابق درس</th>
                    <th>تطابق روز</th>
                    <th>تطابق زمان</th>
                    <th>وضعیت کلی</th>
                  </tr>
                </thead>
                <tbody>
                  {classes.map((cls, idx) => (
                    <tr key={idx} className={`row-status-${cls.status}`}>
                      <td>{cls.course_name}</td>
                      <td>{getDayName(cls.day)}</td>
                      <td>{cls.start}</td>
                      <td>{cls.end}</td>
                      <td>{cls.teachMatch ? '✅' : '❌'}</td>
                      <td>{cls.dayMatch ? '✅' : '❌'}</td>
                      <td>{cls.timeMatch ? '✅' : '❌'}</td>
                      <td>
                        <span className={`status-badge status-${cls.status}`}>
                          {cls.status === 'full' && 'کامل'}
                          {cls.status === 'partial' && 'نسبی'}
                          {cls.status === 'none' && 'نامطابق'}
                          {cls.status === 'no_preference' && 'بدون مطلوبیت'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="empty-message">هیچ کلاسی به این استاد تخصیص نیافته است.</span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر اطلاعات درس (با اضافه شدن بخش مطلوبیت‌های تدریس)
  // ============================================================
  const renderCourseInfo = () => {
    if (!courseData) {
      return <div className="no-data-message">هیچ درسی انتخاب نشده است.</div>;
    }

    const { courseInfo, groups, summary, preferredInstructors } = courseData;

    return (
      <div className="course-info-container">
        <div className="course-selector">
          <label>انتخاب درس:</label>
          <select
            value={selectedCourseCode}
            onChange={(e) => setSelectedCourseCode(e.target.value)}
            className="course-select"
          >
            {courseList.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name} ({c.code})
              </option>
            ))}
          </select>
        </div>

        <div className="course-details">
          <div className="course-info-card">
            <h4>📘 اطلاعات درس</h4>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">نام درس</span>
                <span className="info-value">{courseInfo?.name || 'نامشخص'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">کد یکتا</span>
                <span className="info-value">{courseInfo?.code || 'نامشخص'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">مقطع</span>
                <span className="info-value">{courseInfo?.level || 'نامشخص'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">ترم</span>
                <span className="info-value">{courseInfo?.term || 'نامشخص'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">تعداد واحد</span>
                <span className="info-value">{courseInfo?.units || 'نامشخص'}</span>
              </div>
            </div>
          </div>

          <div className="preferences-section">
            <h4>🎯 مطلوبیت‌های تدریس (اساتید اولویت‌دار)</h4>
            {preferredInstructors && preferredInstructors.length > 0 ? (
              <table className="time-pref-table">
                <thead>
                  <tr>
                    <th>کد استاد</th>
                    <th>نام استاد</th>
                    <th>اولویت</th>
                  </tr>
                </thead>
                <tbody>
                  {preferredInstructors.map((inst, idx) => (
                    <tr key={idx}>
                      <td>{inst.instructor_code}</td>
                      <td>{inst.instructor_name}</td>
                      <td>{inst.priority !== undefined ? inst.priority : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="empty-message">هیچ مطلوبیت تدریسی برای این درس ثبت نشده است.</span>
            )}
          </div>

          <div className="summary-section">
            <h4>📊 جمع‌بندی وضعیت گروه‌ها</h4>
            <div className="summary-stats">
              <div className="stat-item">
                <span className="stat-label">تعداد کل گروه‌ها</span>
                <span className="stat-value">{summary.total}</span>
              </div>
              <div className="stat-item" style={{ color: '#34d399' }}>
                <span className="stat-label">تخصیص‌یافته</span>
                <span className="stat-value">{summary.assignedCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#f87171' }}>
                <span className="stat-label">بدون تخصیص</span>
                <span className="stat-value">{summary.unassignedCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#93c5fd' }}>
                <span className="stat-label">تطابق کامل</span>
                <span className="stat-value">{summary.fullMatchCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#fcd34d' }}>
                <span className="stat-label">تطابق نسبی</span>
                <span className="stat-value">{summary.partialMatchCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#fca5a5' }}>
                <span className="stat-label">بدون تطابق</span>
                <span className="stat-value">{summary.noMatchCount}</span>
              </div>
              <div className="stat-item" style={{ color: '#e5e7eb' }}>
                <span className="stat-label">بدون مطلوبیت</span>
                <span className="stat-value">{summary.noPrefCount}</span>
              </div>
            </div>
          </div>

          <div className="groups-section">
            <h4>📋 گروه‌های این درس</h4>
            {groups.length > 0 ? (
              <table className="groups-table">
                <thead>
                  <tr>
                    <th>گروه</th>
                    <th>استاد</th>
                    <th>روز</th>
                    <th>شروع</th>
                    <th>پایان</th>
                    <th>تطابق درس</th>
                    <th>تطابق روز</th>
                    <th>تطابق زمان</th>
                    <th>وضعیت کلی</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((cls, idx) => (
                    <tr key={idx} className={`row-status-${cls.status}`}>
                      <td>{cls.group_number || '—'}</td>
                      <td>{cls.instructor_name || cls.instructor_code || '❌ تخصیص نیافته'}</td>
                      <td>{cls.day !== undefined ? getDayName(cls.day) : '—'}</td>
                      <td>{cls.start || '—'}</td>
                      <td>{cls.end || '—'}</td>
                      <td>{cls.teachMatch ? '✅' : '❌'}</td>
                      <td>{cls.dayMatch ? '✅' : '❌'}</td>
                      <td>{cls.timeMatch ? '✅' : '❌'}</td>
                      <td>
                        <span className={`status-badge status-${cls.status}`}>
                          {cls.status === 'full' && 'کامل'}
                          {cls.status === 'partial' && 'نسبی'}
                          {cls.status === 'none' && 'نامطابق'}
                          {cls.status === 'no_preference' && 'بدون مطلوبیت'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="empty-message">هیچ گروهی برای این درس یافت نشد.</span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر جدول سفارشی (با رنگ‌بندی سلول‌ها بر اساس وضعیت کلی)
  // ============================================================
  const renderCustomTable = (data, columns, showStatus = true, editable = false) => {
    const displayData = editable ? editedData : data;

    if (!displayData || displayData.length === 0) {
      const hasFilter = searchTerm.trim() !== "" || selectedDay !== null;
      if (hasFilter) {
        let message = "نتیجه‌ای برای جستجو";
        if (searchTerm.trim()) message += ` "${searchTerm.trim()}"`;
        if (selectedDay !== null) message += ` در روز ${dayNames[selectedDay]}`;
        message += " یافت نشد.";
        return <div className="no-data-message">{message}</div>;
      } else {
        return <div className="no-data-message">هیچ داده‌ای برای نمایش وجود ندارد.</div>;
      }
    }

    const coloredFields = ['course_name', 'day', 'start', 'end'];

    const getValidStarts = (units) => {
      const slots = getValidSlots(units);
      return slots.map(slot => slot[0]);
    };

    return (
      <div className="custom-table-wrapper">
        {renderSearch()}
        <table className="custom-table">
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col.key}>{col.label}</th>
              ))}
              {showStatus && <th>وضعیت تطابق</th>}
            </tr>
          </thead>
          <tbody>
            {displayData.map((row, idx) => {
              const overallStatus = getMatchStatus(row, teachingLookup, timeLookup);
              return (
                <tr key={idx} className={`row-status-${overallStatus}`}>
                  {columns.map(col => {
                    const fieldKey = col.key;
                    let cellClass = '';
                    if (coloredFields.includes(fieldKey)) {
                      const colorStatus = getCellColorStatus(row, teachingLookup, timeLookup, fieldKey);
                      let fieldType = fieldKey;
                      if (fieldKey === 'start' || fieldKey === 'end') {
                        fieldType = 'time';
                      }
                      cellClass = `cell-${fieldType}-${colorStatus}`;
                    }

                    const value = row[fieldKey];

                    if (editable && ['instructor_code', 'day', 'start'].includes(fieldKey)) {
                      let renderElement;

                      if (fieldKey === 'instructor_code') {
                        const instructorOptions = instructorList.map(inst => inst.code);
                        return (
                          <td key={col.key} className={cellClass}>
                            <select
                              value={value || ''}
                              onChange={(e) => handleEditChange(idx, fieldKey, e.target.value)}
                              className="edit-select"
                            >
                              <option value="">انتخاب استاد...</option>
                              {instructorOptions.map(code => (
                                <option key={code} value={code}>
                                  {code} ({instructorNameLookup[code] || ''})
                                </option>
                              ))}
                            </select>
                          </td>
                        );
                      } else if (fieldKey === 'day') {
                        renderElement = (
                          <select
                            value={value !== undefined ? value : 0}
                            onChange={(e) => handleEditChange(idx, fieldKey, parseInt(e.target.value))}
                            className="edit-select"
                          >
                            {dayNames.map((name, i) => <option key={i} value={i}>{name}</option>)}
                          </select>
                        );
                      } else if (fieldKey === 'start') {
                        const units = row.units || 2;
                        const validStarts = getValidStarts(units);
                        const startValue = value !== undefined && value !== null ? String(value) : '';
                        const safeValue = validStarts.includes(startValue) ? startValue : validStarts[0] || '';
                        const datalistId = `time-datalist-${idx}`;
                        renderElement = (
                          <>
                            <input
                              type="time"
                              list={datalistId}
                              value={safeValue}
                              onChange={(e) => handleEditChange(idx, fieldKey, e.target.value)}
                              onBlur={() => handleStartBlur(idx)}
                              className="edit-input"
                              step="60"
                            />
                            <datalist id={datalistId}>
                              {validStarts.map(start => (
                                <option key={start} value={start} />
                              ))}
                            </datalist>
                          </>
                        );
                      }
                      return (
                        <td key={col.key} className={cellClass}>
                          {renderElement}
                        </td>
                      );
                    }

                    const displayValue = col.render ? col.render(row) : (value !== undefined ? value : "—");
                    return (
                      <td key={col.key} className={cellClass}>
                        {displayValue}
                      </td>
                    );
                  })}
                  {showStatus && (
                    <td className="status-cell">
                      <span className={`status-badge status-${overallStatus}`}>
                        {overallStatus === 'full' && '✅ تطابق کامل'}
                        {overallStatus === 'partial' && '⚠️ تطابق نسبی'}
                        {overallStatus === 'none' && '❌ بدون تطابق'}
                        {overallStatus === 'no_preference' && '➖ بدون مطلوبیت'}
                      </span>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="table-footer">
          <span>تعداد کلاس‌ها: {displayData.length}</span>
          {editable && (
            <div className="edit-actions">
              <button onClick={saveEdits} disabled={isSavingEdits} className="btn-save-edits">
                {isSavingEdits ? "در حال ذخیره..." : "💾 ذخیره تغییرات"}
              </button>
              <button onClick={cancelEditing} className="btn-cancel-edits">انصراف</button>
            </div>
          )}
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر نمای ماتریس زمانی
  // ============================================================
  const renderMatrixView = () => {
    if (!filteredAssigned || filteredAssigned.length === 0) {
      return <div className="no-data-message">داده‌ای برای نمایش وجود ندارد.</div>;
    }
    const allSlots = [...new Set(filteredAll.map(item => `${item.start}-${item.end}`))].sort();
    const courseMap = {};
    filteredAssigned.forEach(item => {
      const key = `${item.course_name} (گروه ${item.group_number})`;
      if (!courseMap[key]) courseMap[key] = {};
      const slotKey = `${item.start}-${item.end}`;
      courseMap[key][slotKey] = item;
    });
    const courseNames = Object.keys(courseMap).sort();

    return (
      <div className="matrix-view">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>درس</th>
              {allSlots.map(slot => <th key={slot}>{slot.replace('-', ' - ')}</th>)}
            </tr>
          </thead>
          <tbody>
            {courseNames.map(course => (
              <tr key={course}>
                <td className="course-name">{course}</td>
                {allSlots.map(slot => {
                  const item = courseMap[course]?.[slot];
                  if (!item) {
                    return <td key={slot} className="empty-cell">—</td>;
                  }
                  const status = getMatchStatus(item, teachingLookup, timeLookup);
                  const statusClass = `match-${status}`;
                  const instructorName = item.instructor_name || item.instructor_code || '—';
                  return (
                    <td key={slot} className={`filled ${statusClass}`}>
                      {instructorName}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="matrix-legend">
          <span><span className="legend-box match-full"></span> تطابق کامل</span>
          <span><span className="legend-box match-partial"></span> تطابق نسبی</span>
          <span><span className="legend-box match-none"></span> بدون تطابق</span>
          <span><span className="legend-box match-no-preference"></span> بدون مطلوبیت</span>
          <span><span className="legend-box empty-cell"></span> خالی</span>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر نمودار میله‌ای
  // ============================================================
  const renderChartView = () => {
    if (!filteredAssigned || filteredAssigned.length === 0) {
      return <div className="no-data-message">داده‌ای برای نمودار وجود ندارد.</div>;
    }
    const slotStats = {};
    filteredAssigned.forEach(item => {
      const slot = `${item.start}-${item.end}`;
      if (!slotStats[slot]) slotStats[slot] = { full: 0, partial: 0, none: 0, no_preference: 0 };
      const status = getMatchStatus(item, teachingLookup, timeLookup);
      slotStats[slot][status] = (slotStats[slot][status] || 0) + 1;
    });
    const slots = Object.keys(slotStats).sort();
    const maxTotal = Math.max(...slots.map(s => Object.values(slotStats[s]).reduce((a, b) => a + b, 0)), 1);

    return (
      <div className="chart-view">
        <h4>📊 وضعیت تطابق در بازه‌های زمانی</h4>
        <div className="bar-chart stacked">
          {slots.map(slot => {
            const { full = 0, partial = 0, none = 0, no_preference = 0 } = slotStats[slot];
            const total = full + partial + none + no_preference;
            const fullPct = (full / maxTotal) * 100;
            const partialPct = (partial / maxTotal) * 100;
            const nonePct = (none / maxTotal) * 100;
            const noPrefPct = (no_preference / maxTotal) * 100;
            return (
              <div key={slot} className="bar-item">
                <span className="bar-label">{slot.replace('-', ' - ')}</span>
                <div className="bar-track stacked">
                  <div className="bar-segment match-full" style={{ width: `${fullPct}%` }}>
                    {full > 0 && <span className="bar-value">{full}</span>}
                  </div>
                  <div className="bar-segment match-partial" style={{ width: `${partialPct}%` }}>
                    {partial > 0 && <span className="bar-value">{partial}</span>}
                  </div>
                  <div className="bar-segment match-none" style={{ width: `${nonePct}%` }}>
                    {none > 0 && <span className="bar-value">{none}</span>}
                  </div>
                  {no_preference > 0 && (
                    <div className="bar-segment match-no-preference" style={{ width: `${noPrefPct}%` }}>
                      <span className="bar-value">{no_preference}</span>
                    </div>
                  )}
                </div>
                <span className="bar-total">{total}</span>
              </div>
            );
          })}
        </div>
        <div className="chart-legend">
          <span><span className="legend-box match-full"></span> تطابق کامل</span>
          <span><span className="legend-box match-partial"></span> تطابق نسبی</span>
          <span><span className="legend-box match-none"></span> بدون تطابق</span>
          <span><span className="legend-box match-no-preference"></span> بدون مطلوبیت</span>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر تقویم هفتگی
  // ============================================================
  const renderCalendarView = () => {
    if (!filteredAssigned || filteredAssigned.length === 0) {
      return <div className="no-data-message">داده‌ای برای تقویم وجود ندارد.</div>;
    }
    const allSlots = [...new Set(filteredAll.map(item => `${item.start}-${item.end}`))].sort();
    const calendar = {};
    dayNames.forEach((day, idx) => {
      calendar[idx] = {};
      allSlots.forEach(slot => {
        calendar[idx][slot] = [];
      });
    });
    filteredAssigned.forEach(item => {
      const day = item.day;
      const slot = `${item.start}-${item.end}`;
      if (calendar[day] && calendar[day][slot]) {
        calendar[day][slot].push(item);
      }
    });

    return (
      <div className="calendar-view">
        <table className="calendar-table">
          <thead>
            <tr>
              <th>بازه زمانی</th>
              {dayNames.map(day => <th key={day}>{day}</th>)}
            </tr>
          </thead>
          <tbody>
            {allSlots.map(slot => (
              <tr key={slot}>
                <td className="slot-label">{slot.replace('-', ' - ')}</td>
                {dayNames.map((_, idx) => {
                  const items = calendar[idx]?.[slot] || [];
                  return (
                    <td key={idx} className={items.length > 0 ? 'filled' : ''}>
                      {items.map((item, i) => {
                        const status = getMatchStatus(item, teachingLookup, timeLookup);
                        const statusClass = `match-${status}`;
                        const display = `${item.course_name}${item.instructor_name ? ` (${item.instructor_name})` : ''}`;
                        return (
                          <div key={i} className={`cell-item ${statusClass}`}>
                            {display}
                          </div>
                        );
                      })}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="calendar-legend">
          <span><span className="legend-box match-full"></span> تطابق کامل</span>
          <span><span className="legend-box match-partial"></span> تطابق نسبی</span>
          <span><span className="legend-box match-none"></span> بدون تطابق</span>
          <span><span className="legend-box match-no-preference"></span> بدون مطلوبیت</span>
        </div>
      </div>
    );
  };

  // ============================================================
  // رندر بخش آمار فراوانی
  // ============================================================
  const renderFrequency = () => {
    if (!frequencyData) return null;
    const { course, timeSlot, day, instructor, level } = frequencyData;
    return (
      <div className="frequency-section">
        <h4>📊 آمار فراوانی کلاس‌ها</h4>
        <div className="frequency-grid">
          <div className="freq-card">
            <h5>📚 فراوانی درس‌ها</h5>
            <ul>{course.map(([name, count]) => <li key={name}><span>{name}</span> <span className="count">{count}</span></li>)}</ul>
          </div>
          <div className="freq-card">
            <h5>⏰ فراوانی بازه‌های زمانی</h5>
            <ul>{timeSlot.map(([slot, count]) => <li key={slot}><span>{slot}</span> <span className="count">{count}</span></li>)}</ul>
          </div>
          <div className="freq-card">
            <h5>📅 فراوانی روزها</h5>
            <ul>{day.map(([d, count]) => <li key={d}><span>{d}</span> <span className="count">{count}</span></li>)}</ul>
          </div>
          <div className="freq-card">
            <h5>👨‍🏫 فراوانی اساتید</h5>
            <ul>{instructor.map(([name, count]) => <li key={name}><span>{name}</span> <span className="count">{count}</span></li>)}</ul>
          </div>
          <div className="freq-card">
            <h5>🎓 فراوانی مقاطع</h5>
            <ul>{level.map(([l, count]) => <li key={l}><span>{l}</span> <span className="count">{count}</span></li>)}</ul>
          </div>
        </div>
        <div className="freq-total">مجموع کلاس‌ها: <strong>{allDataForStats.length}</strong></div>
      </div>
    );
  };

  // ============================================================
  // رندر اصلی
  // ============================================================
  if (!effectiveBasketData || effectiveBasketData.length === 0) {
    return (
      <div className="process-page instructor-time-page">
        <div className="process-header">
          <div className="process-title">
            <span className="process-icon">⏳</span>
            <h2>زمان‌بندی استاد و درس</h2>
          </div>
          <p className="process-description">
            برای شروع زمان‌بندی، ابتدا باید یک سبد دروس انتخاب یا ایجاد کنید.
          </p>
        </div>
        <div className="process-body">
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <h3>سبد دروس انتخاب نشده است</h3>
            <p>لطفاً ابتدا یک سبد دروس را از لیست سبدها انتخاب کنید یا یک سبد جدید ایجاد کنید.</p>
            {typeof onNavigateToBasketList === "function" && (
              <button
                onClick={onNavigateToBasketList}
                className="btn-primary"
                style={{ marginTop: "1.5rem", padding: "0.75rem 2rem" }}
              >
                📋 رفتن به مدیریت سبدها
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="process-page instructor-time-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">⏳</span>
          <h2>زمان‌بندی استاد و درس</h2>
        </div>
        <div className="basket-info" style={{ marginTop: "0.5rem", fontSize: "0.95rem", color: "#4a5568" }}>
          <span className="basket-badge" style={{
            background: "#e2e8f0",
            padding: "0.25rem 0.75rem",
            borderRadius: "0.5rem",
            display: "inline-block"
          }}>
            📂 سبد دروس: {basketMeta.title || `شناسه ${basketId || ''}`}
            {basketMeta.semester && ` (${basketMeta.semester === "mehr" ? "مهر" : "بهمن"} ${basketMeta.year})`}
          </span>
        </div>
        <p className="process-description">
          در این مرحله برای هر درس، استاد مناسب و زمان برگزاری با رعایت محدودیت‌های تداخل
          و ترجیحات تدریس، روز و زمان اساتید تعیین می‌شود. تطابق زمان با تساهل ۶۰ دقیقه انجام می‌شود.
          {normalizedUnassigned.length > 0 && (
            <span style={{ color: "#e74c3c", fontWeight: "bold", display: "block", marginTop: "8px" }}>
              ⚠️ {normalizedUnassigned.length} کلاس بدون استاد باقی مانده‌اند. لطفاً مرحله دوم (تخصیص دستی) را اجرا کنید.
            </span>
          )}
        </p>
        {typeof onNavigateToBasketList === "function" && (
          <button
            onClick={onNavigateToBasketList}
            className="btn-secondary"
            style={{ marginTop: "10px" }}
          >
            ← بازگشت به لیست سبدها
          </button>
        )}
      </div>

      <div className="process-body">
        <div className="controls-bar">
          <button
            onClick={handleLocalProcess}
            disabled={!effectiveBasketData || effectiveBasketData.length === 0 || loadingLocal || isLoadingBasket}
            className="btn-process"
          >
            {loadingLocal ? "در حال اجرا..." : "اجرای زمان‌بندی"}
          </button>
          {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && (
            <button onClick={() => { onClear(); setShowBasket(true); setInstructorTimeDataLocal(null); setSteps([]); }} className="btn-clear">
              پاک کردن نتایج
            </button>
          )}
          {normalizedUnassigned.length > 0 && !manualMode && (
            <button onClick={() => setManualMode(true)} className="btn-manual">
              ✏️ مرحله دوم: تخصیص دستی
            </button>
          )}
          {manualMode && (
            <>
              <button onClick={saveManualAssignments} disabled={isSavingManual} className="btn-save-manual">
                {isSavingManual ? "در حال ذخیره..." : "💾 ذخیره تخصیص‌های دستی"}
              </button>
              <button onClick={() => setManualMode(false)} className="btn-cancel">انصراف</button>
            </>
          )}
          {normalizedAssigned.length > 0 && !manualMode && !editingMode && (
            <button onClick={startEditing} className="btn-edit-table">
              ✏️ ویرایش جدول
            </button>
          )}
          {workflowId && <span className="workflow-badge">شناسه جلسه: {workflowId}</span>}
        </div>

        {error && <div className="error-message">⚠️ {error}</div>}
        {isLoadingBasket && <div className="loading-state">در حال بارگذاری سبد...</div>}

        {showBasket && effectiveBasketData && effectiveBasketData.length > 0 && (
          <div className="basket-display">
            <h4>📋 لیست کلاس‌های سبد دروس</h4>
            <EditableDataTable data={effectiveBasketData} columns={basketColumns} title="" editable={false} />
            <div className="basket-summary">
              <div className="summary-grid">
                <div className="summary-item">
                  <span className="label">تعداد کل کلاس‌ها</span>
                  <span className="value">{effectiveBasketData.length}</span>
                </div>
                <div className="summary-item">
                  <span className="label">مقاطع</span>
                  <span className="value">
                    {[...new Set(effectiveBasketData.map(item => item.level))].filter(Boolean).join("، ")}
                  </span>
                </div>
                <div className="summary-item">
                  <span className="label">میانگین ظرفیت</span>
                  <span className="value">
                    {Math.round(effectiveBasketData.reduce((sum, c) => sum + (c.estimated_capacity || 0), 0) / effectiveBasketData.length)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && !manualMode && (
          <div className="result-container">
            <div className="result-header">
              <h4>✅ نتایج زمان‌بندی (تخصیص خودکار)</h4>
              {/* نمایش آمار جدید بر اساس matchStats */}
              <div className="result-stats">
                <span className="stat-badge">✅ تطابق کامل: {matchStats.full}</span>
                <span className="stat-badge">⚠️ تطابق نسبی: {matchStats.partial}</span>
                <span className="stat-badge">❌ بدون تطابق: {matchStats.none}</span>
                <span className="stat-badge">➖ بدون مطلوبیت: {matchStats.no_preference}</span>
                <span className="stat-badge">🚫 تخصیص ناقص: {matchStats.no_assignment}</span>
                <span className="stat-badge">📭 تخصیص‌نیافته: {matchStats.unassigned}</span>
              </div>
            </div>

            {renderDayFilters()}
            {renderViewTabs()}

            <div className="view-container">
              {viewMode === 'table' && renderCustomTable(
                filteredAssigned,
                tableColumns,
                true,
                editingMode
              )}
              {viewMode === 'matrix' && renderMatrixView()}
              {viewMode === 'chart' && renderChartView()}
              {viewMode === 'calendar' && renderCalendarView()}
              {viewMode === 'instructor' && renderInstructorInfo()}
              {viewMode === 'course' && renderCourseInfo()}
              {viewMode === 'conflicts' && renderConflictsView()}
              {viewMode === 'reasons' && renderReasonsView()}
            </div>

            <StepsDisplay steps={steps} instructorNameLookup={instructorNameLookup} courseNameLookup={courseNameLookup} />

            {!editingMode && renderFrequency()}
          </div>
        )}

        {!effectiveInstructorTimeData && effectiveBasketData && effectiveBasketData.length > 0 && (
          <div className="info-box info-warning" style={{ marginTop: '20px' }}>
            <span className="info-icon">ℹ️</span>
            <p>
              برای شروع زمان‌بندی، روی دکمه <strong>"اجرای زمان‌بندی"</strong> در نوار ابزار کلیک کنید.
              پس از اجرا، نتایج تخصیص استاد و زمان در این بخش نمایش داده می‌شود.
            </p>
          </div>
        )}

        {normalizedUnassigned.length > 0 && !manualMode && (
          <div className="unassigned-container">
            <div className="result-header warning">
              <h4>⚠️ کلاس‌های بدون استاد ({normalizedUnassigned.length} کلاس)</h4>
              <p className="hint-text">
                این کلاس‌ها در مرحله اول تخصیص نیافتند. لطفاً با کلیک روی دکمه "مرحله دوم: تخصیص دستی" استاد و زمان مناسب را به آنها اختصاص دهید.
              </p>
            </div>
            {renderDayFilters()}
            {renderCustomTable(filteredUnassigned, tableColumns.filter(col =>
              !['instructor_name', 'instructor_code', 'final_score'].includes(col.key)
            ), false)}
          </div>
        )}

        {manualMode && normalizedUnassigned.length > 0 && (
          <div className="manual-container">
            <div className="result-header">
              <h4>✏️ مرحله دوم: تخصیص دستی استاد</h4>
              <p className="hint-text">برای هر کلاس، استاد، روز و بازه زمانی مجاز را انتخاب کنید. سپس روی "ذخیره تخصیص‌های دستی" کلیک کنید.</p>
            </div>
            {renderDayFilters()}
            <EditableDataTable data={filteredManualAssignments} columns={manualColumns} title="" editable={true} />
            {filteredManualAssignments.length === 0 && selectedDay !== null && debouncedSearchTerm === "" && (
              <div className="no-data-message">هیچ کلاسی برای روز {dayNames[selectedDay]} در لیست تخصیص دستی وجود ندارد.</div>
            )}
            {filteredManualAssignments.length === 0 && debouncedSearchTerm !== "" && (
              <div className="no-data-message">نتیجه‌ای برای جستجوی "{debouncedSearchTerm}" یافت نشد.</div>
            )}
            <div className="manual-actions">
              <button onClick={saveManualAssignments} disabled={isSavingManual} className="btn-save-manual">
                {isSavingManual ? "در حال ذخیره..." : "💾 ذخیره تخصیص‌های دستی"}
              </button>
              <button onClick={() => setManualMode(false)} className="btn-cancel">انصراف</button>
            </div>
          </div>
        )}

        {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && !manualMode && (
          <div className="result-actions">
            <button onClick={onNext} className="btn-primary" disabled={loadingLocal || normalizedUnassigned.length > 0}>
              {loadingLocal ? "در حال..." : normalizedUnassigned.length > 0 ? "⚠️ ابتدا تخصیص دستی را کامل کنید" : "🏢 مرحله بعد: تخصیص اتاق"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}