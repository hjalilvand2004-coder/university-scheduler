// frontend/src/pages/InstructorTimeComponents.jsx
import React, { useState, useMemo } from "react";
import axios from "axios";

// ============================================================
// توابع کمکی
// ============================================================

export function timeToMinutes(timeStr) {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  if (parts.length !== 2) return 0;
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  return h * 60 + m;
}

export function normalizePreferenceWindow(start, end) {
  if (start === "12:00" && end === "16:00") {
    return { start: "13:00", end: "17:00" };
  }
  return { start, end };
}

export function isTimeSlotMatchWithTolerance(
  slotStart,
  slotEnd,
  prefStart,
  prefEnd,
  toleranceMinutes = 60
) {
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

export function getDayName(dayNum) {
  const days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];
  return days[dayNum] || dayNum;
}

// ============================================================
// دریافت اسلات‌های معتبر (تابع همگام)
// ============================================================

export function getValidSlotsSync(units, validSlotsMap) {
  const slots = validSlotsMap?.[units];
  if (slots && slots.length > 0) {
    return slots;
  }
  // Fallback به لیست‌های ثابت (نیمسال اول) – فقط برای مواقع اضطراری
  if (units === 3) {
    return [
      "07:30-10:10",
      "10:11-12:50",
      "13:00-15:30",
      "15:31-18:00",
      "18:01-20:30",
    ];
  }
  return [
    "07:30-09:15",
    "09:16-11:00",
    "11:01-12:45",
    "13:00-14:45",
    "14:46-16:30",
    "16:31-18:15",
    "18:16-20:00",
  ];
}

// ============================================================
// توابع سازگاری با کدهای قدیمی (برای استفاده در سایر صفحات)
// ============================================================

export function getValidSlots(units) {
  return getValidSlotsSync(units, {});
}

export function normalizeTimeSlot(item, unitsLookup = {}) {
  if (!item) return item;
  const units = item.units || (item.unique_code && unitsLookup[item.unique_code]) || 2;
  const validSlots = getValidSlots(units);
  const currentSlot = `${item.start || ''}-${item.end || ''}`;

  if (validSlots.includes(currentSlot)) {
    return { ...item, units };
  }

  // اگر زمان اصلی در اسلات‌های معتبر وجود نداشت، از اولین اسلات استفاده کن
  const defaultSlot = validSlots[0] || "07:30-09:15";
  const [start, end] = defaultSlot.split('-');
  return { ...item, start, end, units };
}

// ============================================================
// نرمال‌سازی زمان با استفاده از کش اسلات‌ها (با validSlotsMap)
// ============================================================

export function normalizeTimeSlotWithCache(item, unitsLookup = {}, validSlotsMap = {}) {
  if (!item) return item;
  const units = item.units || (item.unique_code && unitsLookup[item.unique_code]) || 2;
  const validSlots = getValidSlotsSync(units, validSlotsMap);
  const currentSlot = `${item.start || ''}-${item.end || ''}`;

  if (validSlots.includes(currentSlot)) {
    return { ...item, units };
  }

  const defaultSlot = validSlots[0] || "07:30-09:15";
  const [start, end] = defaultSlot.split('-');
  return { ...item, start, end, units };
}

// ============================================================
// توابع تطابق (بدون Context)
// ============================================================

export function getMatchStatus(item, teachingLookup, timeLookup) {
  const instructorCode = item.instructor_code;
  const courseCode = item.unique_code;
  const day = item.day;
  const start = item.start;
  const end = item.end;

  const hasTeachPref = courseCode && teachingLookup[courseCode] && teachingLookup[courseCode].size > 0;
  const hasTimePref = instructorCode && timeLookup[instructorCode] && timeLookup[instructorCode].length > 0;

  if (!hasTeachPref && !hasTimePref) return 'no_preference';

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
        slot.day === day && isTimeSlotMatchWithTolerance(start, end, slot.start, slot.end, 60)
      );
    }
  }

  const matchCount = (teachMatch ? 1 : 0) + (dayMatch ? 1 : 0) + (timeMatch ? 1 : 0);
  if (matchCount === 3) return 'full';
  if (matchCount > 0) return 'partial';
  return 'none';
}

export function getCellColorStatus(item, teachingLookup, timeLookup, fieldKey) {
  return getMatchStatus(item, teachingLookup, timeLookup);
}

// ============================================================
// توابع localStorage
// ============================================================

function getUnassignedStorageKey(basketId, workflowId) {
  return `unassigned_${basketId || ''}_${workflowId || ''}`;
}

export function saveUnassignedToStorage(basketId, workflowId, unassignedData) {
  if (!basketId && !workflowId) return;
  const key = getUnassignedStorageKey(basketId, workflowId);
  try {
    localStorage.setItem(key, JSON.stringify(unassignedData));
  } catch (e) {
    console.warn('[saveUnassignedToStorage] خطا در ذخیره localStorage:', e);
  }
}

export function loadUnassignedFromStorage(basketId, workflowId) {
  if (!basketId && !workflowId) return null;
  const key = getUnassignedStorageKey(basketId, workflowId);
  try {
    const data = localStorage.getItem(key);
    if (data) return JSON.parse(data);
  } catch (e) {
    console.warn('[loadUnassignedFromStorage] خطا در بارگذاری localStorage:', e);
  }
  return null;
}

export function removeUnassignedFromStorage(basketId, workflowId) {
  if (!basketId && !workflowId) return;
  const key = getUnassignedStorageKey(basketId, workflowId);
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn('[removeUnassignedFromStorage] خطا در حذف localStorage:', e);
  }
}

// ============================================================
// کامپوننت نمایش مراحل
// ============================================================

export function StepsDisplay({ steps, instructorNameLookup = {}, courseNameLookup = {} }) {
  if (!steps || steps.length === 0) return null;

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
      description: "تخصیص استاد به دروس عادی بر اساس اولویت‌های تدریس و نوع همکاری",
      file: "schedule_service.py",
      line: "حدود خط ۳۵۰"
    },
    "زمان‌بندی کامل به ازای هر استاد": {
      method: "_assign_full_schedule_per_instructor()",
      description: "برای هر استاد، با افزایش تدریجی تساهل، دروس را به طور متوازن در روزهای ترجیحی تخصیص می‌دهد",
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
            <thead><tr>{columns.map(col => <th key={col.key}>{col.label}</th>)}</tr></thead>
            <tbody>
              {courses.map((row, idx) => (
                <tr key={idx}>
                  {columns.map(col => {
                    let value = row[col.key];
                    if (col.render) value = col.render(row);
                    else if (value === undefined || value === null) value = '—';
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

    return (
      <div className="step-details">
        {simpleKeys.length > 0 && (
          <div className="details-simple-table">
            <table className="details-table-simple">
              <tbody>
                {simpleKeys.map(key => {
                  let value = details[key];
                  if (Array.isArray(value)) value = value.join('، ');
                  if (typeof value === 'object' && value !== null && !Array.isArray(value)) value = JSON.stringify(value);
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
                  return <tr key={key}><td className="detail-key">{label}</td><td className="detail-value">{value}</td></tr>;
                })}
              </tbody>
            </table>
          </div>
        )}

        {details.sample_teaching_prefs && details.sample_teaching_prefs.length > 0 && (
          <div className="details-table">
            <h5>📚 نمونه ترجیحات تدریس (۵ درس اول)</h5>
            <div className="table-responsive">
              <table className="pref-table">
                <thead><tr><th>کد درس</th><th>نام درس</th><th>اساتید اولویت‌دار (تا ۳ نفر)</th></tr></thead>
                <tbody>
                  {details.sample_teaching_prefs.map((item, idx) => (
                    <tr key={idx}>
                      <td>{item.course_code}</td>
                      <td>{courseNameLookup[item.course_code] || 'نامشخص'}</td>
                      <td>{item.instructors.map(inst => `${inst.name} (${inst.code})`).join('، ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {details.teaching_prefs_count > 5 && <div className="table-note">و {details.teaching_prefs_count - 5} مورد دیگر ...</div>}
            </div>
          </div>
        )}

        {details.sample_time_prefs && details.sample_time_prefs.length > 0 && (
          <div className="details-table">
            <h5>⏰ نمونه ترجیحات زمان (۵ استاد اول)</h5>
            <div className="table-responsive">
              <table className="pref-table">
                <thead><tr><th>استاد</th><th>روز</th><th>شروع</th><th>پایان</th><th>اولویت</th></tr></thead>
                <tbody>
                  {details.sample_time_prefs.map((item, idx) => (
                    item.preferences.map((pref, pIdx) => (
                      <tr key={`${idx}-${pIdx}`}>
                        {pIdx === 0 && <td rowSpan={item.preferences.length}>{item.instructor_name} ({item.instructor_code})</td>}
                        <td>{pref.day}</td><td>{pref.start}</td><td>{pref.end}</td><td>{pref.priority}</td>
                      </tr>
                    ))
                  ))}
                </tbody>
              </table>
              {details.time_prefs_count > 5 && <div className="table-note">و {details.time_prefs_count - 5} استاد دیگر ...</div>}
            </div>
          </div>
        )}

        {assignedKeys.map(key => renderCoursesTable(details[key], key.replace('assigned_', '').replace(/_/g, ' ') + ' (تخصیص‌یافته)', stepName))}
        {unassignedKeys.map(key => renderCoursesTable(details[key], key.replace('unassigned_', '').replace(/_/g, ' ') + ' (تخصیص‌نیافته)', stepName))}

        {details.mismatch_details && details.mismatch_details.length > 0 && stepName.includes('گزارش نهایی') && (
          <div className="details-table">
            <h5>📋 دلایل عدم تطابق کامل ({details.mismatch_details.length})</h5>
            <div className="table-responsive">
              <table className="conflicts-table">
                <thead><tr><th>درس</th><th>گروه</th><th>کد درس</th><th>مقطع</th><th>ترم</th><th>استاد</th><th>وضعیت تخصیص</th><th>دلیل</th></tr></thead>
                <tbody>
                  {details.mismatch_details.map((item, idx) => {
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
                <thead><tr><th>کد استاد</th><th>نام استاد</th><th>واحد استفاده‌شده</th><th>حداکثر واحد</th><th>درصد استفاده</th><th>وضعیت</th></tr></thead>
                <tbody>
                  {Object.entries(details.instructor_usage).sort((a, b) => b[1].percentage - a[1].percentage).map(([code, usage]) => {
                    let statusText = '', statusClass = '';
                    const percent = usage.percentage;
                    if (percent >= 100) { statusText = 'پر'; statusClass = 'status-full'; }
                    else if (percent >= 75) { statusText = 'نزدیک به پر'; statusClass = 'status-high'; }
                    else if (percent >= 50) { statusText = 'متوسط'; statusClass = 'status-medium'; }
                    else { statusText = 'کم'; statusClass = 'status-low'; }
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
          <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%` }}></div></div>
          <span className="steps-stats">{completed} موفق / {failed} خطا / {running} در حال اجرا</span>
        </div>
      </div>
      <div className="steps-list">
        {steps.map((step, index) => {
          const statusClass = `step-status-${step.status}`;
          const icon = step.status === 'success' ? '✅' : step.status === 'failed' ? '❌' : step.status === 'running' ? '⏳' : '⏸️';
          const backendInfo = stepBackendInfo[step.name] || null;
          return (
            <div key={step.step || index} className={`step-item ${statusClass}`}>
              <div className="step-number">{step.step}</div>
              <div className="step-content">
                <div className="step-title">
                  <span className="step-icon">{icon}</span>
                  <span className="step-name">{step.name}</span>
                  <span className="step-status-label">{step.status}</span>
                </div>
                {step.description && <div className="step-description">{step.description}</div>}
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
// کامپوننت مودال تخصیص دستی (با validSlotsMap به عنوان prop)
// ============================================================

export function renderManualModal({
  isOpen,
  onClose,
  editingIndex,
  modalData,
  onModalChange,
  onModalSave,
  assignment,
  instructorList,
  dayNames,
  timePreferences = [],
  teachingPreferences = [],
  instructorNameLookup = {},
  getDayName = (d) => d,
  validSlotsMap = {},
}) {
  if (!isOpen || editingIndex === null || !assignment) return null;

  const units = assignment.units || 2;
  const validSlots = getValidSlotsSync(units, validSlotsMap);
  const start = modalData.start || "07:30";
  const end = modalData.end || "09:15";
  const currentSlot = `${start}-${end}`;
  const selectedSlot = validSlots.includes(currentSlot) ? currentSlot : validSlots[0];

  const selectedInstructorCode = modalData.instructor_code;
  const instructorTimePrefs = selectedInstructorCode
    ? timePreferences.filter(p => p.instructor_code === selectedInstructorCode)
    : [];
  const instructorTeachPrefs = selectedInstructorCode
    ? teachingPreferences.filter(p => p.instructor_code === selectedInstructorCode)
    : [];
  const instructorName = selectedInstructorCode
    ? instructorNameLookup[selectedInstructorCode] || selectedInstructorCode
    : '';

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
      padding: '20px',
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div className="modal-content" style={{
        backgroundColor: 'white',
        borderRadius: '16px',
        padding: '28px',
        maxWidth: '650px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        direction: 'rtl',
      }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0, borderBottom: '2px solid #3498db', paddingBottom: '14px', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '24px' }}>✏️</span> ویرایش تخصیص دستی
        </h3>

        <div className="modal-info" style={{
          marginBottom: '20px',
          background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
          padding: '16px',
          borderRadius: '10px',
          border: '1px solid #dee2e6',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px 20px',
        }}>
          <p style={{ margin: 0 }}><strong>📚 درس:</strong> {assignment.course_name}</p>
          <p style={{ margin: 0 }}><strong>🔢 گروه:</strong> {assignment.group_number}</p>
          <p style={{ margin: 0 }}><strong>🎓 مقطع:</strong> {assignment.level}</p>
          <p style={{ margin: 0 }}><strong>📅 ترم:</strong> {assignment.term}</p>
          <p style={{ margin: 0, gridColumn: 'span 2' }}><strong>📊 تعداد واحد:</strong> {assignment.units}</p>
        </div>

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>👨‍🏫 انتخاب استاد:</label>
          <select
            value={modalData.instructor_code}
            onChange={(e) => onModalChange('instructor_code', e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            <option value="">-- انتخاب استاد --</option>
            {instructorList.map(inst => (
              <option key={inst.code} value={inst.code}>
                {inst.name} ({inst.code})
              </option>
            ))}
          </select>
          {selectedInstructorCode && instructorName && (
            <div style={{ marginTop: '4px', fontSize: '13px', color: '#6c757d' }}>
              استاد انتخاب‌شده: <strong>{instructorName}</strong>
            </div>
          )}
        </div>

        {selectedInstructorCode && (
          <div style={{
            marginBottom: '16px',
            background: '#f0f7ff',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid #b8d4f0',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h5 style={{ margin: 0, color: '#2c3e50' }}>⏰ مطلوبیت‌های زمانی استاد</h5>
              <span style={{ fontSize: '13px', color: '#6c757d' }}>({instructorTimePrefs.length} مورد)</span>
            </div>
            {instructorTimePrefs.length > 0 ? (
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px',
                backgroundColor: 'white',
                borderRadius: '8px',
                overflow: 'hidden',
              }}>
                <thead style={{ backgroundColor: '#e3f0ff' }}>
                  <tr>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>روز</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>شروع</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>پایان</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>اولویت</th>
                  </tr>
                </thead>
                <tbody>
                  {instructorTimePrefs.map((pref, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '6px 10px' }}>{getDayName(pref.day)}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.start_time}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.end_time}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.priority !== undefined ? pref.priority : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ color: '#6c757d', fontSize: '14px', padding: '8px 0' }}>
                ⚠️ هیچ مطلوبیت زمانی برای این استاد ثبت نشده است.
              </div>
            )}
            {instructorTeachPrefs.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <div style={{ fontSize: '13px', color: '#495057' }}>
                  <strong>📚 دروس مورد تدریس:</strong>
                  <span style={{ marginRight: '8px' }}>
                    {instructorTeachPrefs.map(p => p.unique_course_code).join('، ')}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>📅 روز:</label>
          <select
            value={modalData.day !== undefined ? parseInt(modalData.day) : 0}
            onChange={(e) => onModalChange('day', parseInt(e.target.value))}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            {dayNames.map((name, i) => (
              <option key={i} value={i}>{name}</option>
            ))}
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>⏱️ بازه زمانی:</label>
          <select
            value={selectedSlot}
            onChange={(e) => {
              const slot = e.target.value;
              const [start, end] = slot.split('-');
              onModalChange('start', start);
              onModalChange('end', end);
            }}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            {validSlots.map(slot => (
              <option key={slot} value={slot}>{slot.replace('-', ' - ')}</option>
            ))}
          </select>
          <div style={{ marginTop: '4px', fontSize: '12px', color: '#6c757d' }}>
            {assignment.units === 3 ? 'بازه‌های ۳ واحدی' : 'بازه‌های ۲ واحدی'}
          </div>
        </div>

        <div className="modal-actions" style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px', borderTop: '1px solid #dee2e6', paddingTop: '20px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: '1px solid #ced4da',
              backgroundColor: '#f8f9fa',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#e9ecef'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#f8f9fa'}
          >
            انصراف
          </button>
          <button
            onClick={onModalSave}
            style={{
              padding: '10px 28px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#2ecc71',
              color: 'white',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '14px',
              transition: 'background-color 0.2s, transform 0.1s',
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#27ae60'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#2ecc71'}
          >
            💾 ذخیره تغییرات
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت مودال ویرایش کلاس‌های تخصیص‌یافته (با validSlotsMap prop)
// ============================================================

export function renderEditModal({
  isOpen,
  onClose,
  modalData,
  onModalChange,
  onModalSave,
  instructorList,
  dayNames,
  timePreferences = [],
  teachingPreferences = [],
  instructorNameLookup = {},
  getDayName = (d) => d,
  isSaving = false,
  validSlotsMap = {},
}) {
  if (!isOpen || !modalData) return null;

  const units = modalData.units || 2;
  const validSlots = getValidSlotsSync(units, validSlotsMap);
  const start = modalData.start || "07:30";
  const end = modalData.end || "09:15";
  const currentSlot = `${start}-${end}`;
  const selectedSlot = validSlots.includes(currentSlot) ? currentSlot : validSlots[0];

  const selectedInstructorCode = modalData.instructor_code;
  const instructorTimePrefs = selectedInstructorCode
    ? timePreferences.filter(p => p.instructor_code === selectedInstructorCode)
    : [];
  const instructorTeachPrefs = selectedInstructorCode
    ? teachingPreferences.filter(p => p.instructor_code === selectedInstructorCode)
    : [];
  const instructorName = selectedInstructorCode
    ? instructorNameLookup[selectedInstructorCode] || selectedInstructorCode
    : '';

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
      padding: '20px',
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div className="modal-content" style={{
        backgroundColor: 'white',
        borderRadius: '16px',
        padding: '28px',
        maxWidth: '650px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        direction: 'rtl',
      }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0, borderBottom: '2px solid #3498db', paddingBottom: '14px', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '24px' }}>✏️</span> ویرایش کلاس تخصیص‌یافته
        </h3>

        <div className="modal-info" style={{
          marginBottom: '20px',
          background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
          padding: '16px',
          borderRadius: '10px',
          border: '1px solid #dee2e6',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px 20px',
        }}>
          <p style={{ margin: 0 }}><strong>📚 درس:</strong> {modalData.course_name}</p>
          <p style={{ margin: 0 }}><strong>🔢 گروه:</strong> {modalData.group_number}</p>
          <p style={{ margin: 0 }}><strong>🎓 مقطع:</strong> {modalData.level}</p>
          <p style={{ margin: 0 }}><strong>📅 ترم:</strong> {modalData.term}</p>
          <p style={{ margin: 0, gridColumn: 'span 2' }}><strong>📊 تعداد واحد:</strong> {modalData.units}</p>
        </div>

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>👨‍🏫 انتخاب استاد:</label>
          <select
            value={modalData.instructor_code}
            onChange={(e) => onModalChange('instructor_code', e.target.value)}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            <option value="">-- انتخاب استاد --</option>
            {instructorList.map(inst => (
              <option key={inst.code} value={inst.code}>
                {inst.name} ({inst.code})
              </option>
            ))}
          </select>
          {selectedInstructorCode && instructorName && (
            <div style={{ marginTop: '4px', fontSize: '13px', color: '#6c757d' }}>
              استاد انتخاب‌شده: <strong>{instructorName}</strong>
            </div>
          )}
        </div>

        {selectedInstructorCode && (
          <div style={{
            marginBottom: '16px',
            background: '#f0f7ff',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid #b8d4f0',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h5 style={{ margin: 0, color: '#2c3e50' }}>⏰ مطلوبیت‌های زمانی استاد</h5>
              <span style={{ fontSize: '13px', color: '#6c757d' }}>({instructorTimePrefs.length} مورد)</span>
            </div>
            {instructorTimePrefs.length > 0 ? (
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px',
                backgroundColor: 'white',
                borderRadius: '8px',
                overflow: 'hidden',
              }}>
                <thead style={{ backgroundColor: '#e3f0ff' }}>
                  <tr>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>روز</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>شروع</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>پایان</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>اولویت</th>
                  </tr>
                </thead>
                <tbody>
                  {instructorTimePrefs.map((pref, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '6px 10px' }}>{getDayName(pref.day)}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.start_time}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.end_time}</td>
                      <td style={{ padding: '6px 10px' }}>{pref.priority !== undefined ? pref.priority : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ color: '#6c757d', fontSize: '14px', padding: '8px 0' }}>
                ⚠️ هیچ مطلوبیت زمانی برای این استاد ثبت نشده است.
              </div>
            )}
            {instructorTeachPrefs.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <div style={{ fontSize: '13px', color: '#495057' }}>
                  <strong>📚 دروس مورد تدریس:</strong>
                  <span style={{ marginRight: '8px' }}>
                    {instructorTeachPrefs.map(p => p.unique_course_code).join('، ')}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>📅 روز:</label>
          <select
            value={modalData.day !== undefined ? parseInt(modalData.day) : 0}
            onChange={(e) => onModalChange('day', parseInt(e.target.value))}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            {dayNames.map((name, i) => (
              <option key={i} value={i}>{name}</option>
            ))}
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold', color: '#2c3e50' }}>⏱️ بازه زمانی:</label>
          <select
            value={selectedSlot}
            onChange={(e) => {
              const slot = e.target.value;
              const [start, end] = slot.split('-');
              onModalChange('start', start);
              onModalChange('end', end);
            }}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '2px solid #ced4da',
              fontSize: '15px',
              backgroundColor: 'white',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = '#3498db'}
            onBlur={(e) => e.target.style.borderColor = '#ced4da'}
          >
            {validSlots.map(slot => (
              <option key={slot} value={slot}>{slot.replace('-', ' - ')}</option>
            ))}
          </select>
          <div style={{ marginTop: '4px', fontSize: '12px', color: '#6c757d' }}>
            {modalData.units === 3 ? 'بازه‌های ۳ واحدی' : 'بازه‌های ۲ واحدی'}
          </div>
        </div>

        <div className="modal-actions" style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px', borderTop: '1px solid #dee2e6', paddingTop: '20px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: '1px solid #ced4da',
              backgroundColor: '#f8f9fa',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#e9ecef'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#f8f9fa'}
          >
            انصراف
          </button>
          <button
            onClick={onModalSave}
            disabled={isSaving}
            style={{
              padding: '10px 28px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#2ecc71',
              color: 'white',
              cursor: isSaving ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              fontSize: '14px',
              opacity: isSaving ? 0.6 : 1,
              transition: 'background-color 0.2s, transform 0.1s',
            }}
            onMouseEnter={(e) => {
              if (!isSaving) e.target.style.backgroundColor = '#27ae60';
            }}
            onMouseLeave={(e) => {
              if (!isSaving) e.target.style.backgroundColor = '#2ecc71';
            }}
          >
            {isSaving ? 'در حال ذخیره...' : '💾 ذخیره تغییرات'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// ماتریس زمانی عمومی (با validSlotsMap prop)
// ============================================================

export function MatrixView({
  data,
  allData,
  getItemStatus,
  getDayName,
  selectedDay,
  onClassUpdate,
  instructorList,
  instructorNameLookup,
  validSlotsMap = {},
}) {
  const [draggingInstructor, setDraggingInstructor] = useState(null);

  const instructorSlotMap = useMemo(() => {
    const map = {};
    allData.forEach(item => {
      if (!item.instructor_code) return;
      const code = item.instructor_code;
      const day = item.day;
      const slot = `${item.start}-${item.end}`;
      const courseName = item.course_name || 'بدون نام';
      if (!map[code]) map[code] = {};
      if (!map[code][day]) map[code][day] = {};
      map[code][day][slot] = courseName;
    });
    return map;
  }, [allData]);

  function hasTimeConflict(start1, end1, start2, end2) {
    const s1 = timeToMinutes(start1);
    const e1 = timeToMinutes(end1);
    const s2 = timeToMinutes(start2);
    const e2 = timeToMinutes(end2);
    return s1 < e2 && s2 < e1;
  }

  const handleDragStart = (e, item) => {
    setDraggingInstructor(item.instructor_code);
    e.dataTransfer.setData('application/json', JSON.stringify({
      id: item.id,
      course_name: item.course_name,
      group_number: item.group_number,
      level: item.level || '',
      term: item.term || '',
      instructor_code: item.instructor_code,
      day: item.day,
      start: item.start,
      end: item.end,
      displayName: `${item.course_name} (گروه ${item.group_number})`
    }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    setDraggingInstructor(null);
  };

  const handleDragOver = (e, targetSlot, targetDay) => {
    e.preventDefault();
    if (draggingInstructor) {
      const hasConflict = instructorSlotMap[draggingInstructor]?.[targetDay]?.[targetSlot] !== undefined;
      if (hasConflict) {
        e.dataTransfer.dropEffect = 'none';
        return;
      }
    }
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, targetCourseKey, targetSlot) => {
    e.preventDefault();
    setDraggingInstructor(null);

    let sourceData;
    try {
      sourceData = JSON.parse(e.dataTransfer.getData('application/json'));
    } catch (err) {
      alert('خطا در دریافت داده‌های کلاس');
      return;
    }

    if (!sourceData || !sourceData.id) {
      alert('داده‌های کلاس معتبر نیست');
      return;
    }

    const [targetStart, targetEnd] = targetSlot.split('-');
    const targetDay = (selectedDay !== null && selectedDay !== undefined) ? selectedDay : sourceData.day;

    const hasConflict = data.some(item => {
      if (item.id === sourceData.id) return false;
      if (item.instructor_code !== sourceData.instructor_code) return false;
      if (parseInt(item.day) !== parseInt(targetDay)) return false;
      return hasTimeConflict(targetStart, targetEnd, item.start, item.end);
    });

    if (hasConflict) {
      const instructorName = instructorNameLookup?.[sourceData.instructor_code] || sourceData.instructor_code || 'نامشخص';
      alert(`❌ تداخل زمانی برای استاد ${instructorName} در روز ${getDayName(targetDay)} و بازه ${targetStart} - ${targetEnd} وجود دارد.`);
      return;
    }

    if (sourceData.day === targetDay && sourceData.start === targetStart && sourceData.end === targetEnd) {
      return;
    }

    const confirmMessage = `آیا از انتقال کلاس "${sourceData.course_name} (گروه ${sourceData.group_number})" از ${getDayName(sourceData.day)} ${sourceData.start}-${sourceData.end} به ${getDayName(targetDay)} ${targetStart}-${targetEnd} مطمئن هستید؟`;
    if (!window.confirm(confirmMessage)) return;

    if (typeof onClassUpdate === 'function') {
      onClassUpdate(sourceData, targetDay, targetStart, targetEnd);
    } else {
      alert('خطا: تابع به‌روزرسانی در دسترس نیست');
    }
  };

  const allSlots = useMemo(() => {
    const slotsSet = new Set();
    allData.forEach(item => {
      const slot = `${item.start}-${item.end}`;
      if (slot && slot !== '-') slotsSet.add(slot);
    });
    if (slotsSet.size === 0) {
      const units = 2;
      const validSlots = getValidSlotsSync(units, validSlotsMap);
      validSlots.forEach(slot => slotsSet.add(slot));
    }
    return Array.from(slotsSet).sort((a, b) => {
      const [startA] = a.split('-');
      const [startB] = b.split('-');
      return timeToMinutes(startA) - timeToMinutes(startB);
    });
  }, [allData, validSlotsMap]);

  const courseMap = {};
  data.forEach(item => {
    const key = `${item.course_name} (گروه ${item.group_number})`;
    if (!courseMap[key]) courseMap[key] = {};
    const slotKey = `${item.start}-${item.end}`;
    courseMap[key][slotKey] = item;
  });
  const courseNames = Object.keys(courseMap).sort();

  return (
    <div className="matrix-view">
      <div className="matrix-hint" style={{ marginBottom: '10px', color: '#666', fontSize: '14px' }}>
        💡 برای تغییر زمان یک کلاس، آن را با ماوس به خانه‌ی مقصد بکشید و رها کنید.
        {selectedDay !== null && selectedDay !== undefined && ` (روز جاری: ${getDayName(selectedDay)})`}
        {!onClassUpdate && <span style={{ color: 'red', marginRight: '10px' }}>⚠️ قابلیت به‌روزرسانی غیرفعال است</span>}
        {draggingInstructor && (
          <span style={{ marginRight: '10px', color: '#e67e22' }}>
            🔄 در حال جابه‌جایی استاد: {instructorNameLookup?.[draggingInstructor] || draggingInstructor}
          </span>
        )}
      </div>
      <table className="matrix-table">
        <thead>
          <tr>
            <th>درس</th>
            {allSlots.map(slot => (
              <th key={slot}>{slot.replace('-', ' - ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {courseNames.map(courseKey => {
            const courseSlots = courseMap[courseKey] || {};
            return (
              <tr key={courseKey}>
                <td className="course-name">{courseKey}</td>
                {allSlots.map(slot => {
                  const item = courseSlots[slot];
                  const isFilled = !!item;
                  const status = item ? getItemStatus(item) : null;
                  const statusClass = status ? `match-${status}` : '';

                  let conflictInfo = null;
                  if (!isFilled && draggingInstructor) {
                    const instructorCode = draggingInstructor;
                    const day = (selectedDay !== null && selectedDay !== undefined) ? selectedDay : null;
                    if (day !== null) {
                      const conflictingCourse = instructorSlotMap[instructorCode]?.[day]?.[slot];
                      if (conflictingCourse) {
                        conflictInfo = {
                          courseName: conflictingCourse,
                          instructorCode: instructorCode,
                          day: day,
                        };
                      }
                    }
                  }

                  if (isFilled) {
                    return (
                      <td
                        key={slot}
                        className={`filled ${statusClass}`}
                        draggable={!!onClassUpdate}
                        onDragStart={(e) => handleDragStart(e, item)}
                        onDragEnd={handleDragEnd}
                        style={{ cursor: onClassUpdate ? 'grab' : 'default' }}
                      >
                        <div style={{ fontSize: '13px' }}>
                          {item.instructor_name || item.instructor_code || '—'}
                        </div>
                        <div style={{ fontSize: '10px', color: '#666' }}>
                          {getDayName(item.day)}
                        </div>
                      </td>
                    );
                  } else if (conflictInfo) {
                    return (
                      <td
                        key={slot}
                        className="empty-cell conflict-cell"
                        style={{
                          backgroundColor: 'rgba(255, 0, 0, 0.08)',
                          border: '1px solid rgba(255, 0, 0, 0.2)',
                          minWidth: '80px',
                          height: '50px',
                          fontSize: '10px',
                          color: '#cc0000',
                          textAlign: 'center',
                          cursor: 'not-allowed',
                          padding: '2px',
                        }}
                      >
                        <div style={{ fontWeight: 'bold', fontSize: '9px' }}>
                          ⚠️ اشغال
                        </div>
                        <div style={{ fontSize: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {conflictInfo.courseName.length > 20
                            ? conflictInfo.courseName.substring(0, 18) + '…'
                            : conflictInfo.courseName}
                        </div>
                      </td>
                    );
                  } else {
                    return (
                      <td
                        key={slot}
                        className="empty-cell drop-target"
                        onDragOver={(e) => handleDragOver(e, slot, (selectedDay !== null && selectedDay !== undefined) ? selectedDay : -1)}
                        onDrop={(e) => onClassUpdate ? handleDrop(e, courseKey, slot) : null}
                        style={{
                          backgroundColor: '#f9f9f9',
                          minWidth: '80px',
                          height: '50px',
                          border: '1px dashed #ccc',
                          cursor: onClassUpdate ? 'pointer' : 'default',
                        }}
                      />
                    );
                  }
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="matrix-legend">
        <span><span className="legend-box match-full"></span> تطابق کامل</span>
        <span><span className="legend-box match-partial"></span> تطابق نسبی</span>
        <span><span className="legend-box match-none"></span> بدون تطابق</span>
        <span><span className="legend-box match-no-preference"></span> بدون مطلوبیت</span>
        <span><span className="legend-box match-unassigned"></span> تخصیص‌نیافته</span>
        <span><span className="legend-box empty-cell"></span> خالی (قابل رها کردن)</span>
        <span><span className="legend-box conflict-cell" style={{ backgroundColor: 'rgba(255,0,0,0.08)', border: '1px solid rgba(255,0,0,0.2)' }}></span> تداخل (غیرقابل رها کردن)</span>
      </div>
    </div>
  );
}

export function renderMatrixView(props) {
  return <MatrixView {...props} />;
}

// ============================================================
// ماتریس زمانی استاد (با validSlotsMap prop)
// ============================================================

export function InstructorWeeklyMatrix({
  selectedInstructor,
  allData,
  instructorNameLookup,
  timePreferences,
  getDayName,
  onClassUpdate,
  instructorList,
  isLoading,
  validSlotsMap = {},
}) {
  const [draggingInstructor, setDraggingInstructor] = useState(null);
  const dayNames = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];

  const allPossibleSlots = useMemo(() => {
    const allSlots = [];
    for (const units of [2, 3]) {
      const slots = getValidSlotsSync(units, validSlotsMap);
      slots.forEach(s => {
        if (!allSlots.includes(s)) allSlots.push(s);
      });
    }
    return allSlots.sort((a, b) => {
      const [startA] = a.split('-');
      const [startB] = b.split('-');
      return timeToMinutes(startA) - timeToMinutes(startB);
    });
  }, [validSlotsMap]);

  const instructorClasses = useMemo(() => {
    if (!selectedInstructor) return [];
    return allData.filter(item => item.instructor_code === selectedInstructor);
  }, [allData, selectedInstructor]);

  const classMap = useMemo(() => {
    const map = {};
    instructorClasses.forEach(item => {
      const day = item.day;
      const slot = `${item.start}-${item.end}`;
      if (!map[day]) map[day] = {};
      map[day][slot] = item;
    });
    return map;
  }, [instructorClasses]);

  const preferredSlots = useMemo(() => {
    if (!selectedInstructor) return {};
    const prefs = timePreferences.filter(p => p.instructor_code === selectedInstructor);
    const map = {};
    prefs.forEach(p => {
      const day = parseInt(p.day);
      if (isNaN(day)) return;
      const slot = `${p.start_time}-${p.end_time}`;
      if (!map[day]) map[day] = new Set();
      map[day].add(slot);
    });
    return map;
  }, [selectedInstructor, timePreferences]);

  const isPreferredSlot = (day, slot) => {
    if (!preferredSlots[day]) return false;
    const [start, end] = slot.split('-');
    for (const prefSlot of preferredSlots[day]) {
      const [prefStart, prefEnd] = prefSlot.split('-');
      if (isTimeSlotMatchWithTolerance(start, end, prefStart, prefEnd, 0)) {
        return true;
      }
    }
    return false;
  };

  function hasTimeConflict(start1, end1, start2, end2) {
    const s1 = timeToMinutes(start1);
    const e1 = timeToMinutes(end1);
    const s2 = timeToMinutes(start2);
    const e2 = timeToMinutes(end2);
    return s1 < e2 && s2 < e1;
  }

  const handleDragStart = (e, item) => {
    setDraggingInstructor(item.instructor_code);
    e.dataTransfer.setData('application/json', JSON.stringify({
      id: item.id,
      course_name: item.course_name,
      group_number: item.group_number,
      level: item.level || '',
      term: item.term || '',
      instructor_code: item.instructor_code,
      day: item.day,
      start: item.start,
      end: item.end,
      displayName: `${item.course_name} (گروه ${item.group_number})`
    }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    setDraggingInstructor(null);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, targetDay, targetSlot) => {
    e.preventDefault();
    setDraggingInstructor(null);

    let sourceData;
    try {
      sourceData = JSON.parse(e.dataTransfer.getData('application/json'));
    } catch (err) {
      alert('خطا در دریافت داده‌های کلاس');
      return;
    }
    if (!sourceData || !sourceData.id) {
      alert('داده‌های کلاس معتبر نیست');
      return;
    }

    const [targetStart, targetEnd] = targetSlot.split('-');

    const hasConflict = instructorClasses.some(item => {
      if (item.id === sourceData.id) return false;
      if (item.instructor_code !== sourceData.instructor_code) return false;
      if (parseInt(item.day) !== parseInt(targetDay)) return false;
      return hasTimeConflict(targetStart, targetEnd, item.start, item.end);
    });

    if (hasConflict) {
      const instructorName = instructorNameLookup?.[sourceData.instructor_code] || sourceData.instructor_code || 'نامشخص';
      alert(`❌ تداخل زمانی برای استاد ${instructorName} در روز ${getDayName(targetDay)} و بازه ${targetStart} - ${targetEnd} وجود دارد.`);
      return;
    }

    if (sourceData.day === targetDay && sourceData.start === targetStart && sourceData.end === targetEnd) {
      return;
    }

    const confirmMessage = `آیا از انتقال کلاس "${sourceData.course_name} (گروه ${sourceData.group_number})" از ${getDayName(sourceData.day)} ${sourceData.start}-${sourceData.end} به ${getDayName(targetDay)} ${targetStart}-${targetEnd} مطمئن هستید؟`;
    if (!window.confirm(confirmMessage)) return;

    if (typeof onClassUpdate === 'function') {
      onClassUpdate(sourceData, targetDay, targetStart, targetEnd);
    } else {
      alert('خطا: تابع به‌روزرسانی در دسترس نیست');
    }
  };

  if (!selectedInstructor) {
    return <div className="no-data-message">لطفاً یک استاد انتخاب کنید.</div>;
  }

  return (
    <div className="instructor-weekly-matrix">
      <div className="matrix-header" style={{ marginBottom: '10px' }}>
        <span style={{ fontWeight: 'bold', fontSize: '16px' }}>
          👨‍🏫 برنامه هفتگی استاد: {instructorNameLookup[selectedInstructor] || selectedInstructor}
        </span>
        {draggingInstructor && (
          <span style={{ marginRight: '10px', color: '#e67e22' }}>
            🔄 در حال جابه‌جایی ...
          </span>
        )}
        <div style={{ fontSize: '13px', color: '#888', marginTop: '4px' }}>
          💡 برای تغییر زمان یک کلاس، آن را به سلول مورد نظر بکشید و رها کنید.
        </div>
      </div>
      <div className="matrix-table-wrapper" style={{ overflowX: 'auto' }}>
        <table className="matrix-table instructor-weekly-table" style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ padding: '8px', border: '1px solid #ddd', backgroundColor: '#f2f2f2' }}>بازه زمانی</th>
              {dayNames.map((day, idx) => (
                <th key={idx} style={{ padding: '8px', border: '1px solid #ddd', backgroundColor: '#f2f2f2', minWidth: '120px' }}>
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allPossibleSlots.map(slot => {
              const [start, end] = slot.split('-');
              return (
                <tr key={slot}>
                  <td style={{ padding: '8px', border: '1px solid #ddd', fontWeight: 'bold', backgroundColor: '#fafafa', whiteSpace: 'nowrap' }}>
                    {start} - {end}
                  </td>
                  {dayNames.map((_, dayIndex) => {
                    const item = classMap[dayIndex]?.[slot];
                    const isPreferred = isPreferredSlot(dayIndex, slot);
                    const isFilled = !!item;

                    if (isFilled) {
                      const status = getMatchStatus(item, {}, {});
                      const statusClass = `match-${status}`;
                      return (
                        <td
                          key={dayIndex}
                          className={`filled ${statusClass}`}
                          draggable
                          onDragStart={(e) => handleDragStart(e, item)}
                          onDragEnd={handleDragEnd}
                          style={{
                            padding: '6px',
                            border: '1px solid #ddd',
                            textAlign: 'center',
                            backgroundColor: '#e6f3ff',
                            cursor: 'grab',
                            fontSize: '13px',
                          }}
                        >
                          <div>{item.course_name}</div>
                          <div style={{ fontSize: '11px', color: '#555' }}>گروه {item.group_number}</div>
                        </td>
                      );
                    } else {
                      return (
                        <td
                          key={dayIndex}
                          className="empty-cell drop-target"
                          onDragOver={handleDragOver}
                          onDrop={(e) => handleDrop(e, dayIndex, slot)}
                          style={{
                            padding: '6px',
                            border: '1px solid #ddd',
                            textAlign: 'center',
                            backgroundColor: isPreferred ? 'rgba(46, 204, 113, 0.25)' : '#f9f9f9',
                            minWidth: '100px',
                            height: '50px',
                            cursor: 'pointer',
                          }}
                        >
                          {isPreferred && <div style={{ fontSize: '10px', color: '#27ae60', fontWeight: 'bold' }}>✓ مطلوب</div>}
                        </td>
                      );
                    }
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="matrix-legend" style={{ marginTop: '10px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
        <span><span style={{ display: 'inline-block', width: '20px', height: '20px', backgroundColor: '#e6f3ff', border: '1px solid #ddd' }}></span> کلاس تخصیص‌یافته</span>
        <span><span style={{ display: 'inline-block', width: '20px', height: '20px', backgroundColor: 'rgba(46,204,113,0.25)', border: '1px solid #ddd' }}></span> زمان مطلوب استاد</span>
        <span><span style={{ display: 'inline-block', width: '20px', height: '20px', backgroundColor: '#f9f9f9', border: '1px dashed #ccc' }}></span> خالی (قابل رها کردن)</span>
      </div>
    </div>
  );
}

// ============================================================
// سایر Viewها (با validSlotsMap prop)
// ============================================================

export function renderChartView({ data, getItemStatus }) {
  if (!data || data.length === 0) return <div className="no-data-message">داده‌ای برای نمودار وجود ندارد.</div>;
  const slotStats = {};
  data.forEach(item => {
    const slot = `${item.start}-${item.end}`;
    if (!slotStats[slot]) slotStats[slot] = { full: 0, partial: 0, none: 0, no_preference: 0, unassigned: 0 };
    const status = getItemStatus(item);
    slotStats[slot][status] = (slotStats[slot][status] || 0) + 1;
  });
  const slots = Object.keys(slotStats).sort();
  const maxTotal = Math.max(...slots.map(s => Object.values(slotStats[s]).reduce((a, b) => a + b, 0)), 1);

  return (
    <div className="chart-view">
      <h4>📊 وضعیت تطابق در بازه‌های زمانی</h4>
      <div className="bar-chart stacked">
        {slots.map(slot => {
          const { full = 0, partial = 0, none = 0, no_preference = 0, unassigned = 0 } = slotStats[slot];
          const total = full + partial + none + no_preference + unassigned;
          const fullPct = (full / maxTotal) * 100, partialPct = (partial / maxTotal) * 100, nonePct = (none / maxTotal) * 100, noPrefPct = (no_preference / maxTotal) * 100, unassignedPct = (unassigned / maxTotal) * 100;
          return (
            <div key={slot} className="bar-item">
              <span className="bar-label">{slot.replace('-', ' - ')}</span>
              <div className="bar-track stacked">
                <div className="bar-segment match-full" style={{ width: `${fullPct}%` }}>{full > 0 && <span className="bar-value">{full}</span>}</div>
                <div className="bar-segment match-partial" style={{ width: `${partialPct}%` }}>{partial > 0 && <span className="bar-value">{partial}</span>}</div>
                <div className="bar-segment match-none" style={{ width: `${nonePct}%` }}>{none > 0 && <span className="bar-value">{none}</span>}</div>
                <div className="bar-segment match-no-preference" style={{ width: `${noPrefPct}%` }}>{no_preference > 0 && <span className="bar-value">{no_preference}</span>}</div>
                <div className="bar-segment match-unassigned" style={{ width: `${unassignedPct}%` }}>{unassigned > 0 && <span className="bar-value">{unassigned}</span>}</div>
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
        <span><span className="legend-box match-unassigned"></span> تخصیص‌نیافته</span>
      </div>
    </div>
  );
}

export function renderCalendarView({ data, allData, getItemStatus, getDayName, dayNames }) {
  if (!data || data.length === 0) return <div className="no-data-message">داده‌ای برای تقویم وجود ندارد.</div>;
  const allSlots = [...new Set(allData.map(item => `${item.start}-${item.end}`))].sort();
  const calendar = {};
  dayNames.forEach((day, idx) => {
    calendar[idx] = {};
    allSlots.forEach(slot => { calendar[idx][slot] = []; });
  });
  data.forEach(item => {
    const day = item.day;
    const slot = `${item.start}-${item.end}`;
    if (calendar[day] && calendar[day][slot]) calendar[day][slot].push(item);
  });

  return (
    <div className="calendar-view">
      <table className="calendar-table">
        <thead><tr><th>بازه زمانی</th>{dayNames.map(day => <th key={day}>{day}</th>)}</tr></thead>
        <tbody>
          {allSlots.map(slot => (
            <tr key={slot}>
              <td className="slot-label">{slot.replace('-', ' - ')}</td>
              {dayNames.map((_, idx) => {
                const items = calendar[idx]?.[slot] || [];
                return (
                  <td key={idx} className={items.length > 0 ? 'filled' : ''}>
                    {items.map((item, i) => {
                      const status = getItemStatus(item);
                      const statusClass = `match-${status}`;
                      return <div key={i} className={`cell-item ${statusClass}`}>{item.course_name}{item.instructor_name ? ` (${item.instructor_name})` : ''}</div>;
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
        <span><span className="legend-box match-unassigned"></span> تخصیص‌نیافته</span>
      </div>
    </div>
  );
}

export function renderInstructorInfo({ instructorData, instructorList, selectedInstructor, setSelectedInstructor, loadingInstructors, courseNameLookup, getDayName }) {
  if (!instructorData) return <div className="no-data-message">هیچ استادی انتخاب نشده است.</div>;
  const { classes, teachPrefs, timePrefs, summary, instructorInfo } = instructorData;

  return (
    <div className="instructor-info-container">
      <div className="instructor-selector">
        <label>انتخاب استاد:</label>
        <select value={selectedInstructor} onChange={(e) => setSelectedInstructor(e.target.value)} className="instructor-select">
          {instructorList.map(({ code, name }) => <option key={code} value={code}>{name}</option>)}
        </select>
      </div>
      <div className="instructor-details">
        <div className="instructor-info-card">
          <h4>👤 اطلاعات استاد</h4>
          {loadingInstructors ? <div>در حال بارگذاری اطلاعات...</div> : (
            <div className="info-grid">
              <div className="info-item"><span className="info-label">نوع همکاری</span><span className="info-value">{instructorInfo?.cooperation_type || 'نامشخص'}</span></div>
              <div className="info-item"><span className="info-label">سقف واحد تدریس</span><span className="info-value">{instructorInfo?.max_teaching_units || 'نامشخص'}</span></div>
            </div>
          )}
          {(!instructorInfo && !loadingInstructors) && <div className="info-warning">⚠️ اطلاعات کامل استاد در دسترس نیست.</div>}
        </div>
        <div className="preferences-section">
          <h4>مطلوبیت‌های تدریس</h4>
          {teachPrefs.length > 0 ? <ul className="pref-list">{teachPrefs.map(courseCode => <li key={courseCode}>{courseNameLookup[courseCode] || courseCode}</li>)}</ul> : <span className="empty-message">هیچ مطلوبیت تدریسی ثبت نشده است.</span>}
        </div>
        <div className="preferences-section">
          <h4>مطلوبیت‌های زمان</h4>
          {timePrefs.length > 0 ? (
            <table className="time-pref-table"><thead><tr><th>روز</th><th>شروع</th><th>پایان</th><th>اولویت</th></tr></thead>
            <tbody>{timePrefs.map((p, i) => <tr key={i}><td>{p.day}</td><td>{p.start}</td><td>{p.end}</td><td>{p.priority !== null ? p.priority : '—'}</td></tr>)}</tbody></table>
          ) : <span className="empty-message">هیچ مطلوبیت زمانی ثبت نشده است.</span>}
        </div>
        <div className="summary-section">
          <h4>جمع‌بندی وضعیت کلاس‌ها</h4>
          <div className="summary-stats">
            <div className="stat-item"><span className="stat-label">مجموع کلاس‌ها</span><span className="stat-value">{summary.total}</span></div>
            <div className="stat-item" style={{ color: '#93c5fd' }}><span className="stat-label">تطابق کامل</span><span className="stat-value">{summary.fullCount}</span></div>
            <div className="stat-item" style={{ color: '#fcd34d' }}><span className="stat-label">تطابق نسبی</span><span className="stat-value">{summary.partialCount}</span></div>
            <div className="stat-item" style={{ color: '#fca5a5' }}><span className="stat-label">بدون تطابق</span><span className="stat-value">{summary.noneCount}</span></div>
            <div className="stat-item" style={{ color: '#e5e7eb' }}><span className="stat-label">بدون مطلوبیت</span><span className="stat-value">{summary.noPrefCount}</span></div>
          </div>
        </div>
        <div className="classes-section">
          <h4>کلاس‌های تخصیص‌یافته</h4>
          {classes.length > 0 ? (
            <table className="classes-table"><thead><tr><th>درس</th><th>روز</th><th>شروع</th><th>پایان</th><th>تطابق درس</th><th>تطابق روز</th><th>تطابق زمان</th><th>وضعیت کلی</th></tr></thead>
            <tbody>{classes.map((cls, idx) => (
              <tr key={idx} className={`row-status-${cls.status}`}>
                <td>{cls.course_name}</td><td>{getDayName(cls.day)}</td><td>{cls.start}</td><td>{cls.end}</td>
                <td>{cls.teachMatch ? '✅' : '❌'}</td><td>{cls.dayMatch ? '✅' : '❌'}</td><td>{cls.timeMatch ? '✅' : '❌'}</td>
                <td><span className={`status-badge status-${cls.status}`}>{cls.status === 'full' ? 'کامل' : cls.status === 'partial' ? 'نسبی' : cls.status === 'none' ? 'نامطابق' : 'بدون مطلوبیت'}</span></td>
              </tr>
            ))}</tbody></table>
          ) : <span className="empty-message">هیچ کلاسی به این استاد تخصیص نیافته است.</span>}
        </div>
      </div>
    </div>
  );
}

export function renderCourseInfo({ courseData, courseList, selectedCourseCode, setSelectedCourseCode, getDayName }) {
  if (!courseData) return <div className="no-data-message">هیچ درسی انتخاب نشده است.</div>;
  const { courseInfo, groups, summary, preferredInstructors } = courseData;

  return (
    <div className="course-info-container">
      <div className="course-selector">
        <label>انتخاب درس:</label>
        <select value={selectedCourseCode} onChange={(e) => setSelectedCourseCode(e.target.value)} className="course-select">
          {courseList.map(c => <option key={c.code} value={c.code}>{c.name} ({c.code})</option>)}
        </select>
      </div>
      <div className="course-details">
        <div className="course-info-card">
          <h4>📘 اطلاعات درس</h4>
          <div className="info-grid">
            <div className="info-item"><span className="info-label">نام درس</span><span className="info-value">{courseInfo?.name || 'نامشخص'}</span></div>
            <div className="info-item"><span className="info-label">کد یکتا</span><span className="info-value">{courseInfo?.code || 'نامشخص'}</span></div>
            <div className="info-item"><span className="info-label">مقطع</span><span className="info-value">{courseInfo?.level || 'نامشخص'}</span></div>
            <div className="info-item"><span className="info-label">ترم</span><span className="info-value">{courseInfo?.term || 'نامشخص'}</span></div>
            <div className="info-item"><span className="info-label">تعداد واحد</span><span className="info-value">{courseInfo?.units || 'نامشخص'}</span></div>
          </div>
        </div>
        <div className="preferences-section">
          <h4>🎯 مطلوبیت‌های تدریس (اساتید اولویت‌دار)</h4>
          {preferredInstructors && preferredInstructors.length > 0 ? (
            <table className="time-pref-table"><thead><tr><th>کد استاد</th><th>نام استاد</th><th>اولویت</th></tr></thead>
            <tbody>{preferredInstructors.map((inst, idx) => <tr key={idx}><td>{inst.instructor_code}</td><td>{inst.instructor_name}</td><td>{inst.priority !== undefined ? inst.priority : '—'}</td></tr>)}</tbody></table>
          ) : <span className="empty-message">هیچ مطلوبیت تدریسی برای این درس ثبت نشده است.</span>}
        </div>
        <div className="summary-section">
          <h4>📊 جمع‌بندی وضعیت گروه‌ها</h4>
          <div className="summary-stats">
            <div className="stat-item"><span className="stat-label">تعداد کل گروه‌ها</span><span className="stat-value">{summary.total}</span></div>
            <div className="stat-item" style={{ color: '#34d399' }}><span className="stat-label">تخصیص‌یافته</span><span className="stat-value">{summary.assignedCount}</span></div>
            <div className="stat-item" style={{ color: '#f87171' }}><span className="stat-label">بدون تخصیص</span><span className="stat-value">{summary.unassignedCount}</span></div>
            <div className="stat-item" style={{ color: '#93c5fd' }}><span className="stat-label">تطابق کامل</span><span className="stat-value">{summary.fullMatchCount}</span></div>
            <div className="stat-item" style={{ color: '#fcd34d' }}><span className="stat-label">تطابق نسبی</span><span className="stat-value">{summary.partialMatchCount}</span></div>
            <div className="stat-item" style={{ color: '#fca5a5' }}><span className="stat-label">بدون تطابق</span><span className="stat-value">{summary.noMatchCount}</span></div>
            <div className="stat-item" style={{ color: '#e5e7eb' }}><span className="stat-label">بدون مطلوبیت</span><span className="stat-value">{summary.noPrefCount}</span></div>
          </div>
        </div>
        <div className="groups-section">
          <h4>📋 گروه‌های این درس</h4>
          {groups.length > 0 ? (
            <table className="groups-table"><thead><tr><th>گروه</th><th>استاد</th><th>روز</th><th>شروع</th><th>پایان</th><th>تطابق درس</th><th>تطابق روز</th><th>تطابق زمان</th><th>وضعیت کلی</th></tr></thead>
            <tbody>{groups.map((cls, idx) => (
              <tr key={idx} className={`row-status-${cls.status}`}>
                <td>{cls.group_number || '—'}</td>
                <td>{cls.instructor_name || cls.instructor_code || '❌ تخصیص نیافته'}</td>
                <td>{cls.day !== undefined ? getDayName(cls.day) : '—'}</td>
                <td>{cls.start || '—'}</td><td>{cls.end || '—'}</td>
                <td>{cls.teachMatch ? '✅' : '❌'}</td><td>{cls.dayMatch ? '✅' : '❌'}</td><td>{cls.timeMatch ? '✅' : '❌'}</td>
                <td><span className={`status-badge status-${cls.status}`}>{cls.status === 'full' ? 'کامل' : cls.status === 'partial' ? 'نسبی' : cls.status === 'none' ? 'نامطابق' : 'بدون مطلوبیت'}</span></td>
              </tr>
            ))}</tbody></table>
          ) : <span className="empty-message">هیچ گروهی برای این درس یافت نشد.</span>}
        </div>
      </div>
    </div>
  );
}

export function renderConflictsView({ conflicts }) {
  if (!conflicts || conflicts.length === 0) return <div className="no-data-message">✅ هیچ تداخل زمانی برای اساتید یافت نشد.</div>;
  return (
    <div className="conflicts-view">
      <h4>⚠️ تداخل‌های زمانی اساتید</h4>
      <p>تعداد تداخل‌های شناسایی‌شده: {conflicts.length}</p>
      <div className="table-responsive">
        <table className="conflicts-table">
          <thead><tr><th>استاد</th><th>روز</th><th>درس اول</th><th>گروه</th><th>بازه اول</th><th>درس دوم</th><th>گروه</th><th>بازه دوم</th></tr></thead>
          <tbody>
            {conflicts.map((conf, idx) => (
              <tr key={idx} className="conflict-row">
                <td>{conf.instructor_name} ({conf.instructor_code})</td>
                <td>{conf.dayName}</td>
                <td>{conf.course1.course_name}</td><td>{conf.course1.group_number}</td><td>{conf.course1.start} - {conf.course1.end}</td>
                <td>{conf.course2.course_name}</td><td>{conf.course2.group_number}</td><td>{conf.course2.start} - {conf.course2.end}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function renderReasonsView({ mismatchReasons }) {
  if (!mismatchReasons || mismatchReasons.length === 0) return <div className="no-data-message">✅ همه دروس با موفقیت تطابق کامل دارند.</div>;
  const total = mismatchReasons.length;
  const assignedItems = mismatchReasons.filter(item => item.is_assigned === true);
  const unassignedItems = mismatchReasons.filter(item => item.is_assigned === false);
  const totalAssigned = assignedItems.length;
  const totalUnassigned = unassignedItems.length;
  const statusCounts = { full: 0, partial: 0, none: 0, unassigned: 0, no_assignment: 0, no_preference: 0 };
  mismatchReasons.forEach(item => { if (statusCounts.hasOwnProperty(item.status)) statusCounts[item.status]++; });
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
    if (!reasonGroups[groupKey]) reasonGroups[groupKey] = { count: 0, sample: [] };
    reasonGroups[groupKey].count++;
    if (reasonGroups[groupKey].sample.length < 3) reasonGroups[groupKey].sample.push({ course: item.course_name, group: item.group_number, reason });
  });
  const reasonLabels = {
    'unique_code_invalid': 'کد یکتا (unique_code) نامعتبر یا خالی',
    'no_preferred_instructor': 'هیچ استاد اولویت‌داری ثبت نشده است',
    'capacity_exceeded': 'تکمیل ظرفیت واحد اساتید',
    'missing_in_process': 'گم‌شدن در حین فرایند زمان‌بندی',
    'no_free_slot': 'عدم وجود اسلات زمانی آزاد',
    'other': 'سایر دلایل',
  };
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
      <div className="summary-section">
        <h4>📊 خلاصه وضعیت عدم تطابق</h4>
        <div className="summary-stats-grid">
          <div className="stat-card"><span className="stat-label">مجموع موارد عدم تطابق</span><span className="stat-value">{total}</span></div>
          <div className="stat-card assigned"><span className="stat-label">تخصیص‌یافته (با تطابق ناقص)</span><span className="stat-value">{totalAssigned}</span></div>
          <div className="stat-card unassigned"><span className="stat-label">تخصیص‌نیافته</span><span className="stat-value">{totalUnassigned}</span></div>
        </div>
        <div className="status-breakdown">
          <h5>وضعیت تطابق (برای دروس تخصیص‌یافته)</h5>
          <div className="status-bars">
            {Object.entries(statusCounts).filter(([key]) => key !== 'unassigned').map(([key, count]) => (
              <div key={key} className="status-bar-item">
                <span className="status-label">{statusMap[key]}</span>
                <div className="bar-track"><div className={`bar-fill ${key}`} style={{ width: `${(count / totalAssigned) * 100 || 0}%` }}></div></div>
                <span className="bar-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="reason-breakdown">
          <h5>دلایل تخصیص‌نیافتگی</h5>
          <ul className="reason-list">
            {Object.entries(reasonGroups).map(([key, data]) => (
              <li key={key}><span className="reason-label">{reasonLabels[key] || key}</span><span className="reason-count">{data.count} درس</span>
                {data.sample.length > 0 && <span className="reason-sample">(نمونه: {data.sample.map(s => `${s.course} (گروه ${s.group})`).join('، ')} )</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="reasons-table-wrapper">
        <h4>📋 جزئیات عدم تطابق</h4>
        <div className="table-responsive">
          <table className="reasons-table">
            <thead><tr><th>درس</th><th>گروه</th><th>کد درس</th><th>مقطع</th><th>ترم</th><th>استاد</th><th>وضعیت تخصیص</th><th>وضعیت تطابق</th><th>دلیل</th></tr></thead>
            <tbody>
              {mismatchReasons.map((item, idx) => {
                const statusLabel = statusMap[item.status] || item.status;
                const isAssigned = item.is_assigned ? 'تخصیص‌یافته' : 'تخصیص نیافته';
                return (
                  <tr key={idx} className={`mismatch-row status-${item.status || 'unknown'}`}>
                    <td>{item.course_name || 'نامشخص'}</td><td>{item.group_number || '—'}</td><td>{item.unique_code || '—'}</td>
                    <td>{item.level || '—'}</td><td>{item.term || '—'}</td>
                    <td>{item.instructor_name ? `${item.instructor_name} (${item.instructor_code})` : '—'}</td>
                    <td>{isAssigned}</td><td>{statusLabel}</td><td>{item.reason || 'دلیل نامشخص'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function renderFrequency({ data }) {
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
  const frequencyData = {
    course: sortDesc(courseFreq),
    timeSlot: sortDesc(timeSlotFreq),
    day: sortDesc(dayFreq),
    instructor: sortDesc(instructorFreq),
    level: sortDesc(levelFreq),
  };

  return (
    <div className="frequency-section">
      <h4>📊 آمار فراوانی کلاس‌ها</h4>
      <div className="frequency-grid">
        <div className="freq-card"><h5>📚 فراوانی درس‌ها</h5><ul>{frequencyData.course.map(([name, count]) => <li key={name}><span>{name}</span> <span className="count">{count}</span></li>)}</ul></div>
        <div className="freq-card"><h5>⏰ فراوانی بازه‌های زمانی</h5><ul>{frequencyData.timeSlot.map(([slot, count]) => <li key={slot}><span>{slot}</span> <span className="count">{count}</span></li>)}</ul></div>
        <div className="freq-card"><h5>📅 فراوانی روزها</h5><ul>{frequencyData.day.map(([d, count]) => <li key={d}><span>{d}</span> <span className="count">{count}</span></li>)}</ul></div>
        <div className="freq-card"><h5>👨‍🏫 فراوانی اساتید</h5><ul>{frequencyData.instructor.map(([name, count]) => <li key={name}><span>{name}</span> <span className="count">{count}</span></li>)}</ul></div>
        <div className="freq-card"><h5>🎓 فراوانی مقاطع</h5><ul>{frequencyData.level.map(([l, count]) => <li key={l}><span>{l}</span> <span className="count">{count}</span></li>)}</ul></div>
      </div>
      <div className="freq-total">مجموع کلاس‌ها: <strong>{data.length}</strong></div>
    </div>
  );
}

// ============================================================
// رندر جدول سفارشی (با validSlotsMap prop)
// ============================================================

export function renderCustomTable({
  data,
  columns,
  showStatus = true,
  editable = false,
  editedData = [],
  handleEditChange,
  handleStartBlur,
  instructorList,
  instructorNameLookup,
  dayNames,
  teachingLookup,
  timeLookup,
  getItemStatus,
  getCellColorStatus,
  renderSearch,
  isSavingEdits,
  saveEdits,
  cancelEditing,
  onEditRow,
  validSlotsMap = {},
}) {
  const displayData = editable ? editedData : data;

  if (!displayData || displayData.length === 0) {
    return <div className="no-data-message">هیچ داده‌ای برای نمایش وجود ندارد.</div>;
  }

  const coloredFields = ['course_name', 'day', 'start', 'end'];

  const getValidStarts = (units) => {
    const slots = getValidSlotsSync(units, validSlotsMap);
    return slots.map(slot => slot[0]);
  };

  return (
    <div className="custom-table-wrapper">
      {renderSearch && renderSearch()}
      <table className="custom-table">
        <thead>
          <tr>
            {columns.map(col => <th key={col.key}>{col.label}</th>)}
            {showStatus && <th>وضعیت تطابق</th>}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, idx) => {
            const overallStatus = getItemStatus ? getItemStatus(row) : 'unknown';
            return (
              <tr key={idx} className={`row-status-${overallStatus}`}>
                {columns.map(col => {
                  const fieldKey = col.key;
                  let cellClass = '';
                  if (coloredFields.includes(fieldKey) && getCellColorStatus) {
                    const colorStatus = getCellColorStatus(row, teachingLookup, timeLookup, fieldKey);
                    let fieldType = fieldKey;
                    if (fieldKey === 'start' || fieldKey === 'end') fieldType = 'time';
                    cellClass = `cell-${fieldType}-${colorStatus}`;
                  }
                  const value = row[fieldKey];

                  if (fieldKey === 'actions' && onEditRow && !editable) {
                    return (
                      <td key={col.key} className={cellClass}>
                        <button
                          onClick={() => onEditRow(idx)}
                          className="btn-edit-modal"
                          style={{
                            background: '#3498db',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '4px 12px',
                            cursor: 'pointer',
                            fontSize: '13px',
                          }}
                        >
                          ✏️ ویرایش
                        </button>
                      </td>
                    );
                  }

                  if (editable && ['instructor_code', 'day', 'start'].includes(fieldKey) && handleEditChange) {
                    let renderElement;
                    if (fieldKey === 'instructor_code') {
                      return (
                        <td key={col.key} className={cellClass}>
                          <select value={value || ''} onChange={(e) => handleEditChange(idx, fieldKey, e.target.value)} className="edit-select">
                            <option value="">انتخاب استاد...</option>
                            {instructorList.map(inst => <option key={inst.code} value={inst.code}>{inst.code} ({instructorNameLookup?.[inst.code] || ''})</option>)}
                          </select>
                        </td>
                      );
                    } else if (fieldKey === 'day') {
                      renderElement = <select value={value !== undefined ? value : 0} onChange={(e) => handleEditChange(idx, fieldKey, parseInt(e.target.value))} className="edit-select">{dayNames.map((name, i) => <option key={i} value={i}>{name}</option>)}</select>;
                    } else if (fieldKey === 'start') {
                      const units = row.units || 2;
                      const validStarts = getValidStarts(units);
                      const startValue = value !== undefined && value !== null ? String(value) : '';
                      const safeValue = validStarts.includes(startValue) ? startValue : validStarts[0] || '';
                      const datalistId = `time-datalist-${fieldKey}-${idx}`;
                      renderElement = (
                        <>
                          <input type="time" list={datalistId} value={safeValue} onChange={(e) => handleEditChange(idx, fieldKey, e.target.value)} onBlur={() => handleStartBlur && handleStartBlur(idx)} className="edit-input" step="60" />
                          <datalist id={datalistId}>
                            {validStarts.map(start => <option key={start} value={start} />)}
                          </datalist>
                        </>
                      );
                    }
                    return <td key={col.key} className={cellClass}>{renderElement}</td>;
                  }

                  const displayValue = col.render ? col.render(row) : (value !== undefined ? value : "—");
                  return <td key={col.key} className={cellClass}>{displayValue}</td>;
                })}
                {showStatus && (
                  <td className="status-cell">
                    <span className={`status-badge status-${overallStatus}`}>
                      {overallStatus === 'full' && '✅ تطابق کامل'}
                      {overallStatus === 'partial' && '⚠️ تطابق نسبی'}
                      {overallStatus === 'none' && '❌ بدون تطابق'}
                      {overallStatus === 'no_preference' && '➖ بدون مطلوبیت'}
                      {overallStatus === 'no_assignment' && '🚫 تخصیص ناقص'}
                      {overallStatus === 'unassigned' && '📭 تخصیص‌نیافته'}
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
            <button onClick={saveEdits} disabled={isSavingEdits} className="btn-save-edits">{isSavingEdits ? "در حال ذخیره..." : "💾 ذخیره تغییرات"}</button>
            <button onClick={cancelEditing} className="btn-cancel-edits">انصراف</button>
          </div>
        )}
      </div>
    </div>
  );
}