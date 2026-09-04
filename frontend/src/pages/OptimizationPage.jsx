// frontend/src/pages/OptimizationPage.jsx
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import axios from "axios";
import EditableDataTable from "../components/EditableDataTable";
import { getDayName } from "./InstructorTimeComponents";
import "./OptimizationPage.css";

// ==========================================================
// تعریف بازه‌های زمانی مطابق با بک‌اند (slot_times.py)
// ==========================================================

const SCHEDULES = {
  semester_1: {
    1: [
      "07:30-09:15", "09:16-11:00", "11:01-12:45",
      "13:00-14:45", "14:46-16:30", "16:31-18:15", "18:16-20:00"
    ],
    2: [
      "07:30-09:15", "09:16-11:00", "11:01-12:45",
      "13:00-14:45", "14:46-16:30", "16:31-18:15", "18:16-20:00"
    ],
    3: [
      "07:30-10:10", "10:11-12:50", "13:00-15:30",
      "15:31-18:00", "18:01-20:30"
    ],
    4: [
      "07:30-10:50", "12:00-16:45", "16:46-20:30"
    ]
  },
  semester_2: {
    1: [
      "07:30-09:05", "09:06-10:40", "10:41-12:10",
      "13:00-14:50", "14:51-16:40", "16:41-18:20", "18:21-20:00"
    ],
    2: [
      "07:30-09:05", "09:06-10:40", "10:41-12:10",
      "13:00-14:50", "14:51-16:40", "16:41-18:20", "18:21-20:00"
    ],
    3: [
      "07:30-09:50", "09:51-12:10", "13:00-15:40",
      "15:51-18:20", "18:21-20:50"
    ],
    4: [
      "07:30-10:40", "13:00-16:20", "16:41-20:20"
    ]
  },
  summer: {
    1: [
      "07:30-09:05", "09:06-10:40", "10:41-12:10",
      "13:00-14:50", "14:51-16:40", "16:41-18:20", "18:21-20:00"
    ],
    2: [
      "07:30-09:05", "09:06-10:40", "10:41-12:10",
      "13:00-14:50", "14:51-16:40", "16:41-18:20", "18:21-20:00"
    ],
    3: [
      "07:30-09:50", "09:51-12:10", "13:00-15:40",
      "15:51-18:20", "18:21-20:50"
    ],
    4: [
      "07:30-10:40", "13:00-16:20", "16:41-20:20"
    ]
  }
};

// ==========================================================
// توابع کمکی برای دریافت بازه‌های اصلی
// ==========================================================

function getMasterSlots(term, units) {
  const termKey = term || 'semester_1';

  console.log(`🔍 [getMasterSlots] term=${termKey}, units=${units}`);
  console.log(`   SCHEDULES[${termKey}] موجود است:`, !!SCHEDULES[termKey]);

  const normalizeTimeKey = (time) => {
    if (!time) return '';
    const parts = time.split(':');
    if (parts.length === 2) {
      return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
    }
    return time;
  };

  const normalizeSlot = (slot) => {
    const [start, end] = slot.split('-');
    return `${normalizeTimeKey(start)}-${normalizeTimeKey(end)}`;
  };

  if (units !== null && units !== undefined) {
    const slots = SCHEDULES[termKey]?.[units] || [];
    console.log(`   اسلات‌های ${units} واحدی برای ترم ${termKey}:`, slots);

    if (slots.length === 0) {
      console.warn(`⚠️ هیچ اسلاتی برای units=${units}, term=${termKey} یافت نشد`);
    }

    return slots.map(s => {
      const [start, end] = s.split('-');
      return {
        label: s,
        start: normalizeTimeKey(start),
        end: normalizeTimeKey(end),
        normalizedKey: normalizeSlot(s)
      };
    });
  } else {
    const allSlots = [];
    for (const u of [1, 2, 3, 4]) {
      const slots = SCHEDULES[termKey]?.[u] || [];
      allSlots.push(...slots);
    }
    const unique = [...new Set(allSlots)];
    console.log(`   همه اسلات‌های ترم ${termKey}:`, unique);

    return unique.map(s => {
      const [start, end] = s.split('-');
      return {
        label: s,
        start: normalizeTimeKey(start),
        end: normalizeTimeKey(end),
        normalizedKey: normalizeSlot(s)
      };
    }).sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end));
  }
}

// ==========================================================
// نرمال‌سازی ترم
// ==========================================================

const normalizeSemester = (term) => {
  if (!term) return "semester_1";

  const raw = String(term)
    .trim()
    .toLowerCase()
    .replace(/\u200c/g, " ")
    .replace(/ي/g, "ی")
    .replace(/ى/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/\s+/g, " ");

  const semester1Keywords = [
    "semester_1", "semester1", "semester 1",
    "mehr", "mهر", "مهر",
    "نیمسال اول", "نیم سال اول",
    "ترم اول", "ترم یک", "ترم ۱",
    "fall", "first", "first semester"
  ];

  const semester2Keywords = [
    "semester_2", "semester2", "semester 2",
    "bahman", "بهمن",
    "نیمسال دوم", "نیم سال دوم",
    "ترم دوم", "ترم دو", "ترم ۲",
    "spring", "second", "second semester"
  ];

  const summerKeywords = [
    "summer", "تابستان",
    "نیمسال تابستان", "نیم سال تابستان"
  ];

  if (semester1Keywords.some(keyword => raw.includes(keyword))) {
    return "semester_1";
  }
  if (semester2Keywords.some(keyword => raw.includes(keyword))) {
    return "semester_2";
  }
  if (summerKeywords.some(keyword => raw.includes(keyword))) {
    return "summer";
  }

  console.warn(`⚠️ ترم ناشناخته: "${term}"، استفاده از پیش‌فرض semester_1`);
  return "semester_1";
};

const dayNames = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];

// ==========================================================
// توابع کمکی برای زمان و هم‌پوشانی
// ==========================================================

const toMinutes = (time) => {
  if (!time) return 0;
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
};

const hasTimeOverlap = (start1, end1, start2, end2) => {
  const s1 = toMinutes(start1);
  const e1 = toMinutes(end1);
  const s2 = toMinutes(start2);
  const e2 = toMinutes(end2);
  return s1 < e2 && s2 < e1;
};

const getTimeOverlap = (start1, end1, start2, end2) => {
  const s1 = toMinutes(start1);
  const e1 = toMinutes(end1);
  const s2 = toMinutes(start2);
  const e2 = toMinutes(end2);
  if (s1 >= s2 && e1 <= e2) return 'full';
  if (s1 < e2 && e1 > s2) return 'partial';
  return 'none';
};

const getTimeGap = (start1, end1, start2, end2) => {
  const s1 = toMinutes(start1);
  const e1 = toMinutes(end1);
  const s2 = toMinutes(start2);
  const e2 = toMinutes(end2);
  if (s1 < e2 && e1 > s2) return 0;
  if (e1 <= s2) return s2 - e1;
  return s1 - e2;
};

// ==========================================================
// نرمال‌سازی زمان
// ==========================================================

const normalizeTime = (time) => {
  if (!time) return '';

  let cleaned = String(time).trim().replace(/\s+/g, '');

  const isPM = cleaned.toLowerCase().includes('pm');
  const isAM = cleaned.toLowerCase().includes('am');
  if (isPM || isAM) {
    const match = cleaned.match(/(\d+):?(\d*)\s*(am|pm)/i);
    if (match) {
      let hour = parseInt(match[1]);
      const minute = match[2] || '00';
      if (isPM && hour < 12) hour += 12;
      if (isAM && hour === 12) hour = 0;
      return `${String(hour).padStart(2, '0')}:${minute.padStart(2, '0')}`;
    }
  }

  const parts = cleaned.split(':');
  if (parts.length === 2) {
    const h = parts[0].padStart(2, '0');
    const m = parts[1].padStart(2, '0');
    return `${h}:${m}`;
  }

  return cleaned;
};

const getClassKey = (cls) => {
  if (cls.id) return `id:${String(cls.id)}`;
  const code = cls.course_code || cls.unique_code || '';
  const group = cls.group_number ?? 1;
  const instructor = cls.instructor_code || '';
  const day = cls.day ?? -1;
  const start = normalizeTime(cls.start || cls.start_time || '');
  const end = normalizeTime(cls.end || cls.end_time || '');
  return `code:${code}|group:${group}|inst:${instructor}|day:${day}|start:${start}|end:${end}`;
};

// ==========================================================
// ظرفیت‌ها
// ==========================================================

const getCourseCapacity = (cls, courseInfoMap = {}) => {
  if (!cls) return 0;
  if (cls.course_capacity !== undefined && cls.course_capacity !== null && cls.course_capacity >= 0) {
    return cls.course_capacity;
  }
  const info = courseInfoMap[cls.course_code];
  if (info && info.capacity !== undefined && info.capacity >= 0) return info.capacity;
  const raw = cls.predicted_students ?? cls.estimated_capacity ?? cls.student_count ?? cls.enrollment_capacity ?? cls.max_students ?? null;
  if (raw !== null && !isNaN(raw) && raw >= 0) return raw;
  return 0;
};

const getRoomCapacity = (roomOrClass, roomsData = []) => {
  if (!roomOrClass) return 0;
  if (roomOrClass.room_capacity !== undefined && roomOrClass.room_capacity !== null && roomOrClass.room_capacity >= 0) return roomOrClass.room_capacity;
  if (roomOrClass.capacity !== undefined && roomOrClass.capacity !== null && roomOrClass.capacity >= 0) return roomOrClass.capacity;
  if (roomOrClass.room_id) {
    const found = roomsData.find(r => String(r.id) === String(roomOrClass.room_id));
    if (found && found.capacity >= 0) return found.capacity;
  }
  if (roomOrClass.room_name) {
    const found = roomsData.find(r => r.name === roomOrClass.room_name);
    if (found && found.capacity >= 0) return found.capacity;
  }
  return 0;
};

// ==========================================================
// کلاس‌های دقیق در اسلات
// ==========================================================

const getInstructorClassesExactlyInSlot = (classes, instructorCode, day, slotStart, slotEnd) => {
  const normStart = normalizeTime(slotStart);
  const normEnd = normalizeTime(slotEnd);
  return classes.filter((item) => {
    if (item.instructor_code !== instructorCode) return false;
    if (Number(item.day) !== Number(day)) return false;
    const itemStart = normalizeTime(item.start_time || item.start);
    const itemEnd = normalizeTime(item.end_time || item.end);
    return itemStart === normStart && itemEnd === normEnd;
  });
};

const getActualConflictsForClass = (classes, classItem) => {
  const key = getClassKey(classItem);
  const classStart = normalizeTime(classItem.start_time || classItem.start);
  const classEnd = normalizeTime(classItem.end_time || classItem.end);
  return classes.filter((other) => {
    if (getClassKey(other) === key) return false;
    if (other.instructor_code !== classItem.instructor_code) return false;
    if (Number(other.day) !== Number(classItem.day)) return false;
    const otherStart = normalizeTime(other.start_time || other.start);
    const otherEnd = normalizeTime(other.end_time || other.end);
    return hasTimeOverlap(classStart, classEnd, otherStart, otherEnd);
  });
};

// ==========================================================
// اتاق‌های اشغال‌شده
// ==========================================================

const getOccupiedRoomKeys = (classes, day, slotStart, slotEnd, excludeClassKey = null) => {
  const occupied = new Set();
  const normStart = normalizeTime(slotStart);
  const normEnd = normalizeTime(slotEnd);
  classes.forEach((cls) => {
    if (excludeClassKey && getClassKey(cls) === excludeClassKey) return;
    if (!cls.room_id && !cls.room_name) return;
    if (Number(cls.day) !== Number(day)) return;
    const clsStart = normalizeTime(cls.start_time || cls.start);
    const clsEnd = normalizeTime(cls.end_time || cls.end);
    if (!hasTimeOverlap(normStart, normEnd, clsStart, clsEnd)) return;
    if (cls.room_id) occupied.add(`id:${String(cls.room_id)}`);
    if (cls.room_name) occupied.add(`name:${cls.room_name.trim().toLowerCase()}`);
  });
  return occupied;
};

// ==========================================================
// انتخاب پایدار اتاق خالی
// ==========================================================

const getStableAvailableRoom = (rooms, classes, day, slotStart, slotEnd, requiredCapacity = 0, excludeClassKey = null, seed = '') => {
  const normStart = normalizeTime(slotStart);
  const normEnd = normalizeTime(slotEnd);
  const occupied = getOccupiedRoomKeys(classes, day, normStart, normEnd, excludeClassKey);

  const available = rooms.filter((room) => {
    const idKey = `id:${String(room.id)}`;
    const nameKey = `name:${room.name.trim().toLowerCase()}`;
    if (occupied.has(idKey) || occupied.has(nameKey)) return false;
    const cap = getRoomCapacity(room);
    if (requiredCapacity > 0 && cap < requiredCapacity) return false;
    return true;
  });

  if (available.length === 0) return null;

  const sorted = [...available].sort((a, b) => {
    const aKey = a.name || String(a.id);
    const bKey = b.name || String(b.id);
    return aKey.localeCompare(bKey);
  });

  const combinedSeed = `${day}|${normStart}|${normEnd}|${requiredCapacity}|${seed}`;
  let hash = 0;
  for (let i = 0; i < combinedSeed.length; i++) {
    hash = (hash * 31 + combinedSeed.charCodeAt(i)) & 0xFFFFFFFF;
  }
  const index = Math.abs(hash) % sorted.length;
  return sorted[index];
};

// ==========================================================
// امتیاز
// ==========================================================

const formatScore = (value, fallback = '0.0') => {
  if (value === undefined || value === null || !Number.isFinite(value)) return fallback;
  return value.toFixed(1);
};

const getScoreColor = (score, type) => {
  let max = 0;
  let mediumThreshold = 0;
  switch(type) {
    case 'teaching': max = 10; mediumThreshold = 5; break;
    case 'day': max = 6; mediumThreshold = 3; break;
    case 'time': max = 6; mediumThreshold = 3; break;
    case 'room': max = 6; mediumThreshold = 3; break;
    case 'total': max = 28; mediumThreshold = 14; break;
    default: max = 10; mediumThreshold = 5;
  }
  if (score === 0) return '#f8d7da';
  if (score > 0 && score <= 2) return '#fff3cd';
  if (score >= mediumThreshold && score < max) return '#cfe2ff';
  if (score >= max) return '#d4edda';
  return '#e9ecef';
};

// ==========================================================
// محاسبه امتیاز تدریس
// ==========================================================

const calculateTeachingScore = (
  classItem,
  teachingPreferences = [],
  courseHistory = [],
  prerequisiteMap = {},
) => {
  const { instructor_code, course_name, course_code } = classItem || {};

  const effectiveCourseCode = course_code || course_name || '';

  const teachPrefs = teachingPreferences.filter(
    (p) => p.instructor_code === instructor_code && p.course_name === course_name
  );

  if (teachPrefs.length > 0) {
    return 10;
  }

  const historyMatch = courseHistory.some(
    (h) => h.instructor_code === instructor_code &&
           (h.course_name === course_name || h.course_code === course_code || h.course_code === effectiveCourseCode)
  );

  if (historyMatch) {
    return 7;
  }

  const isPrerequisiteOrCorequisite = () => {
    const prereqCourses = prerequisiteMap[effectiveCourseCode]?.prerequisites || [];
    if (prereqCourses.some(p => p.instructor_code === instructor_code)) {
      return true;
    }

    const coreqCourses = prerequisiteMap[effectiveCourseCode]?.corequisites || [];
    if (coreqCourses.some(c => c.instructor_code === instructor_code)) {
      return true;
    }

    for (const [otherCode, prereqInfo] of Object.entries(prerequisiteMap)) {
      if (otherCode === effectiveCourseCode) continue;

      const prereqList = prereqInfo.prerequisites || [];
      if (prereqList.some(p => p.course_code === effectiveCourseCode && p.instructor_code === instructor_code)) {
        return true;
      }

      const coreqList = prereqInfo.corequisites || [];
      if (coreqList.some(c => c.course_code === effectiveCourseCode && c.instructor_code === instructor_code)) {
        return true;
      }
    }

    return false;
  };

  if (isPrerequisiteOrCorequisite()) {
    return 4;
  }

  return 0;
};

const calculateUtilityDetails = (
  classItem,
  teachingPreferences = [],
  timePreferences = [],
  roomPreferences = [],
  instructorsData = [],
  courseInfoMap = {},
  courseHistory = [],
  prerequisiteMap = {},
) => {
  const effectiveEstimatedCapacity = getCourseCapacity(classItem, courseInfoMap) || 30;
  const effectiveRoomCapacity = getRoomCapacity(classItem) || 40;

  const teachingScore = calculateTeachingScore(
    classItem,
    teachingPreferences,
    courseHistory,
    prerequisiteMap
  );

  let timeDayScore = 0;
  let timeSlotScore = 0;
  let roomScore = 0;

  const { instructor_code, day, start, end } = classItem || {};

  const dayMap = { 'شنبه': 0, 'یکشنبه': 1, 'دوشنبه': 2, 'سه‌شنبه': 3, 'چهارشنبه': 4, 'پنجشنبه': 5, 'جمعه': 6 };
  const timePrefs = timePreferences.filter(
    (p) => p.instructor_code === instructor_code
  );

  const dayMatched = timePrefs.some((p) => dayMap[p.day] === day);
  if (dayMatched) timeDayScore = 6;

  if (timePrefs.length > 0) {
    let bestMatch = 'none';
    let minGap = Infinity;

    for (const pref of timePrefs) {
      const prefDayNum = dayMap[pref.day];
      if (prefDayNum !== day) continue;

      const overlap = getTimeOverlap(start, end, pref.start_time, pref.end_time);
      if (overlap === 'full') {
        bestMatch = 'full';
        break;
      } else if (overlap === 'partial' && bestMatch !== 'full') {
        bestMatch = 'partial';
      } else {
        const gap = getTimeGap(start, end, pref.start_time, pref.end_time);
        if (gap < minGap) minGap = gap;
      }
    }

    if (bestMatch === 'full') {
      timeSlotScore = 6;
    } else if (bestMatch === 'partial') {
      timeSlotScore = 4;
    } else if (minGap <= 120) {
      timeSlotScore = 2;
    }
  }

  if (effectiveRoomCapacity > 0) {
    const ratio = effectiveEstimatedCapacity / effectiveRoomCapacity;
    if (ratio > 1) {
      roomScore = -2;
    } else if (ratio >= 0.9 && ratio <= 1) {
      roomScore = 6;
    } else if (ratio >= 0.7 && ratio < 0.9) {
      roomScore = 3;
    } else if (ratio > 0 && ratio < 0.7) {
      roomScore = 1;
    } else {
      roomScore = 0;
    }
  }

  const total = teachingScore + timeDayScore + timeSlotScore + roomScore;

  return {
    teachingScore,
    timeDayScore,
    timeSlotScore,
    roomScore,
    total,
  };
};

const calculateUtility = (
  classItem,
  teachingPreferences = [],
  timePreferences = [],
  roomPreferences = [],
  instructorsData = [],
  courseInfoMap = {},
  courseHistory = [],
  prerequisiteMap = {},
) => {
  const details = calculateUtilityDetails(
    classItem,
    teachingPreferences,
    timePreferences,
    roomPreferences,
    instructorsData,
    courseInfoMap,
    courseHistory,
    prerequisiteMap
  );
  return details.total;
};

// ==========================================================
// نرمال‌سازی کلاس
// ==========================================================

const normalizeClassRecord = (cls, courseInfoMap = {}, roomsData = [], instructorsData = [], defaultTerm = 'semester_1') => {
  let roomId = cls.room_id ?? null;

  if (roomId !== null && roomId !== undefined) {
    roomId = typeof roomId === 'string' ? parseInt(roomId, 10) : roomId;
    if (isNaN(roomId)) roomId = null;
  }

  if (!roomId && cls.room_name) {
    const foundRoom = roomsData.find(r => r.name === cls.room_name);
    if (foundRoom) {
      roomId = foundRoom.id;
    } else {
      console.warn(`⚠️ room_name "${cls.room_name}" در لیست اتاق‌ها یافت نشد`);
    }
  }

  const start = cls.start ?? cls.start_time ?? null;
  const end = cls.end ?? cls.end_time ?? null;

  let roomCap = getRoomCapacity({ room_id: roomId, room_name: cls.room_name }, roomsData);
  if (roomCap === 0 && cls.room_capacity !== undefined && cls.room_capacity !== null) roomCap = cls.room_capacity;
  if (roomCap === 0 && cls.capacity !== undefined && cls.capacity !== null) roomCap = cls.capacity;

  const courseCode = cls.course_code || cls.unique_code || '';
  const courseInfo = courseInfoMap[courseCode] || {};

  let courseCap = 0;
  if (courseInfo.capacity !== undefined && courseInfo.capacity !== null && courseInfo.capacity >= 0) {
    courseCap = courseInfo.capacity;
  } else if (cls.course_capacity !== undefined && cls.course_capacity !== null && cls.course_capacity >= 0) {
    courseCap = cls.course_capacity;
  } else if (cls.estimated_capacity !== undefined && cls.estimated_capacity !== null && cls.estimated_capacity >= 0) {
    courseCap = cls.estimated_capacity;
  } else if (cls.predicted_students !== undefined && cls.predicted_students !== null && cls.predicted_students >= 0) {
    courseCap = cls.predicted_students;
  } else {
    courseCap = 30;
  }

  const units = cls.units ?? courseInfo.units ?? 2;

  let courseName = cls.course_name || cls.course_title || '';
  if (!courseName && courseInfo.name) courseName = courseInfo.name;
  if (!courseName) courseName = courseCode || `کلاس ${cls.id}`;

  const instructorName = cls.instructor_name || '';
  const instructorCode = cls.instructor_code || '';

  let term = defaultTerm;
  if (cls.term) {
    term = normalizeSemester(cls.term);
  } else if (cls.semester) {
    term = normalizeSemester(cls.semester);
  } else if (cls.term_name) {
    term = normalizeSemester(cls.term_name);
  }

  const normalizedStart = normalizeTime(start);
  const normalizedEnd = normalizeTime(end);

  return {
    id: cls.id,
    course_name: courseName,
    course_code: courseCode,
    course_title: cls.course_title || '',
    instructor_name: instructorName,
    instructor_code: instructorCode,
    day: Number(cls.day ?? 0),
    start: normalizedStart,
    end: normalizedEnd,
    start_time: normalizedStart,
    end_time: normalizedEnd,
    room_name: cls.room_name || null,
    room_id: roomId,
    room_capacity: roomCap,
    capacity: roomCap,
    course_capacity: courseCap,
    estimated_capacity: courseCap,
    predicted_students: courseCap,
    group_number: cls.group_number ?? 1,
    units: Number(units),
    level: cls.level || 'کارشناسی',
    term: term,
    utility: cls.utility ?? null,
  };
};

// ============================================================
// کامپوننت آمار برای جدول (با تفکیک واحد)
// ============================================================
function TableStatistics({ data, title }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>📊 {title || 'آمار'}</div>
        <div style={{ color: '#6c757d' }}>هیچ داده‌ای برای نمایش وجود ندارد.</div>
      </div>
    );
  }

  const total = data.length;

  // توزیع امتیاز کل
  const utilityRanges = {
    'عالی (≥20)': 0,
    'خوب (14-19.9)': 0,
    'متوسط (10-13.9)': 0,
    'ضعیف (5-9.9)': 0,
    'بسیار ضعیف (<5)': 0,
  };

  let totalUtility = 0;
  let minUtility = Infinity;
  let maxUtility = -Infinity;

  data.forEach(item => {
    const u = item.utility || 0;
    totalUtility += u;
    if (u < minUtility) minUtility = u;
    if (u > maxUtility) maxUtility = u;

    if (u >= 20) utilityRanges['عالی (≥20)']++;
    else if (u >= 14) utilityRanges['خوب (14-19.9)']++;
    else if (u >= 10) utilityRanges['متوسط (10-13.9)']++;
    else if (u >= 5) utilityRanges['ضعیف (5-9.9)']++;
    else utilityRanges['بسیار ضعیف (<5)']++;
  });

  const avgUtility = total > 0 ? (totalUtility / total) : 0;

  // توزیع واحدها
  const unitsDistribution = {};
  data.forEach(item => {
    const units = item.units || 0;
    unitsDistribution[units] = (unitsDistribution[units] || 0) + 1;
  });

  // توزیع روزها
  const dayDistribution = {};
  data.forEach(item => {
    const day = item.day !== undefined && item.day !== null ? item.day : -1;
    const dayName = day >= 0 && day < dayNames.length ? dayNames[day] : 'نامشخص';
    dayDistribution[dayName] = (dayDistribution[dayName] || 0) + 1;
  });

  // ===== آمار تفکیکی بر اساس واحد =====
  const unitsUtilityStats = {};
  Object.keys(unitsDistribution).forEach(units => {
    const classes = data.filter(item => item.units === Number(units));
    if (classes.length > 0) {
      const totalUtil = classes.reduce((sum, cls) => sum + (cls.utility || 0), 0);
      unitsUtilityStats[units] = totalUtil / classes.length;
    } else {
      unitsUtilityStats[units] = 0;
    }
  });

  // توزیع امتیاز به تفکیک واحد
  const unitsUtilityRanges = {};
  Object.keys(unitsDistribution).forEach(units => {
    const classes = data.filter(item => item.units === Number(units));
    unitsUtilityRanges[units] = {
      'عالی (≥20)': 0,
      'خوب (14-19.9)': 0,
      'متوسط (10-13.9)': 0,
      'ضعیف (5-9.9)': 0,
      'بسیار ضعیف (<5)': 0,
    };
    classes.forEach(item => {
      const u = item.utility || 0;
      if (u >= 20) unitsUtilityRanges[units]['عالی (≥20)']++;
      else if (u >= 14) unitsUtilityRanges[units]['خوب (14-19.9)']++;
      else if (u >= 10) unitsUtilityRanges[units]['متوسط (10-13.9)']++;
      else if (u >= 5) unitsUtilityRanges[units]['ضعیف (5-9.9)']++;
      else unitsUtilityRanges[units]['بسیار ضعیف (<5)']++;
    });
  });

  return (
    <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6' }}>
      <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '12px' }}>📊 {title || 'آمار برنامه'}</div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>تعداد کل کلاس‌ها</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#007bff' }}>{total}</div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>میانگین امتیاز کل</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: avgUtility >= 14 ? '#28a745' : avgUtility >= 10 ? '#ffc107' : '#dc3545' }}>
            {formatScore(avgUtility)}
          </div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>بیشترین امتیاز</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#28a745' }}>{formatScore(maxUtility)}</div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>کمترین امتیاز</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#dc3545' }}>{formatScore(minUtility)}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px', marginTop: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع امتیاز کل</div>
          {Object.entries(utilityRanges).map(([range, count]) => (
            <div key={range} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '100px', fontSize: '0.85rem' }}>{range}</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${total > 0 ? (count / total * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#007bff' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع واحدها</div>
          {Object.entries(unitsDistribution).sort((a, b) => Number(a[0]) - Number(b[0])).map(([units, count]) => (
            <div key={units} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '60px', fontSize: '0.85rem' }}>{units} واحدی</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${total > 0 ? (count / total * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#28a745' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع روزها</div>
          {Object.entries(dayDistribution).map(([day, count]) => (
            <div key={day} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '60px', fontSize: '0.85rem' }}>{day}</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${total > 0 ? (count / total * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#17a2b8' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ===== بخش آمار تفکیکی بر اساس واحد ===== */}
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '2px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', fontSize: '1rem', marginBottom: '12px', color: '#495057' }}>
          📈 آمار تفکیکی بر اساس تعداد واحد
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => {
            const count = unitsDistribution[units];
            const avgUtil = unitsUtilityStats[units] || 0;
            const ranges = unitsUtilityRanges[units] || {};

            return (
              <div key={units} style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontWeight: 'bold', fontSize: '1rem', color: '#007bff', marginBottom: '8px' }}>
                  {units} واحدی
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>
                  تعداد: <strong>{count}</strong>
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '8px' }}>
                  میانگین امتیاز: <strong style={{ color: avgUtil >= 14 ? '#28a745' : avgUtil >= 10 ? '#ffc107' : '#dc3545' }}>
                    {formatScore(avgUtil)}
                  </strong>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>
                  {Object.entries(ranges).map(([range, rangeCount]) => (
                    <div key={range} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span style={{ width: '70px' }}>{range}</span>
                      <span style={{ fontWeight: 'bold' }}>{rangeCount}</span>
                      <span style={{ fontSize: '0.7rem', color: '#999' }}>
                        ({count > 0 ? ((rangeCount / count) * 100).toFixed(0) : 0}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت آمار برای ماتریس (با تفکیک واحد)
// ============================================================
function MatrixStatistics({ data, rooms, masterSlots, selectedDay, dayNames, title }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>📊 {title || 'آمار ماتریس'}</div>
        <div style={{ color: '#6c757d' }}>هیچ داده‌ای برای نمایش وجود ندارد.</div>
      </div>
    );
  }

  const totalClasses = data.length;

  // محاسبه پراکندگی کلاس‌ها در اتاق‌ها
  const roomDistribution = {};
  rooms.forEach(room => {
    const count = data.filter(cls => String(cls.room_id) === String(room.id)).length;
    roomDistribution[room.name] = count;
  });

  // محاسبه پراکندگی کلاس‌ها در اسلات‌ها
  const slotDistribution = {};
  masterSlots.forEach(slot => {
    const key = slot.normalizedKey || `${slot.start}-${slot.end}`;
    const count = data.filter(cls => {
      const clsKey = `${normalizeTime(cls.start)}-${normalizeTime(cls.end)}`;
      return clsKey === key;
    }).length;
    slotDistribution[slot.label] = count;
  });

  // محاسبه تعداد اسلات‌های پر و خالی
  const totalSlots = rooms.length * masterSlots.length;
  let usedSlots = 0;
  rooms.forEach(room => {
    masterSlots.forEach(slot => {
      const key = slot.normalizedKey || `${slot.start}-${slot.end}`;
      const hasClass = data.some(cls =>
        String(cls.room_id) === String(room.id) &&
        `${normalizeTime(cls.start)}-${normalizeTime(cls.end)}` === key
      );
      if (hasClass) usedSlots++;
    });
  });

  const emptySlots = totalSlots - usedSlots;
  const utilizationRate = totalSlots > 0 ? ((usedSlots / totalSlots) * 100) : 0;

  // محاسبه آمار امتیاز
  let totalUtility = 0;
  let minUtility = Infinity;
  let maxUtility = -Infinity;
  data.forEach(item => {
    const u = item.utility || 0;
    totalUtility += u;
    if (u < minUtility) minUtility = u;
    if (u > maxUtility) maxUtility = u;
  });
  const avgUtility = totalClasses > 0 ? (totalUtility / totalClasses) : 0;

  // ===== آمار تفکیکی بر اساس واحد =====
  const unitsDistribution = {};
  data.forEach(item => {
    const units = item.units || 0;
    unitsDistribution[units] = (unitsDistribution[units] || 0) + 1;
  });

  const unitsUtilityStats = {};
  Object.keys(unitsDistribution).forEach(units => {
    const classes = data.filter(item => item.units === Number(units));
    if (classes.length > 0) {
      const totalUtil = classes.reduce((sum, cls) => sum + (cls.utility || 0), 0);
      unitsUtilityStats[units] = totalUtil / classes.length;
    } else {
      unitsUtilityStats[units] = 0;
    }
  });

  return (
    <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6' }}>
      <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '12px' }}>
        📊 {title || `آمار ماتریس - روز ${dayNames[selectedDay] || selectedDay}`}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>تعداد کلاس‌ها</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#007bff' }}>{totalClasses}</div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>میانگین امتیاز</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: avgUtility >= 14 ? '#28a745' : avgUtility >= 10 ? '#ffc107' : '#dc3545' }}>
            {formatScore(avgUtility)}
          </div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>نرخ استفاده از اتاق‌ها</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: utilizationRate >= 70 ? '#28a745' : utilizationRate >= 40 ? '#ffc107' : '#dc3545' }}>
            {utilizationRate.toFixed(1)}%
          </div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>اسلات‌های خالی</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#6c757d' }}>{emptySlots}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px', marginTop: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع کلاس‌ها در اتاق‌ها</div>
          {Object.entries(roomDistribution).sort((a, b) => b[1] - a[1]).map(([room, count]) => (
            <div key={room} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '80px', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {room}
              </span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${totalClasses > 0 ? (count / totalClasses * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#007bff' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع کلاس‌ها در اسلات‌ها</div>
          {Object.entries(slotDistribution).sort((a, b) => b[1] - a[1]).map(([slot, count]) => (
            <div key={slot} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '80px', fontSize: '0.85rem' }}>{slot}</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${totalClasses > 0 ? (count / totalClasses * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#28a745' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ===== بخش آمار تفکیکی بر اساس واحد ===== */}
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '2px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', fontSize: '1rem', marginBottom: '12px', color: '#495057' }}>
          📈 آمار تفکیکی بر اساس تعداد واحد
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => {
            const count = unitsDistribution[units];
            const avgUtil = unitsUtilityStats[units] || 0;

            return (
              <div key={units} style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontWeight: 'bold', fontSize: '1rem', color: '#007bff', marginBottom: '8px' }}>
                  {units} واحدی
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>
                  تعداد: <strong>{count}</strong>
                </div>
                <div style={{ fontSize: '0.9rem' }}>
                  میانگین امتیاز: <strong style={{ color: avgUtil >= 14 ? '#28a745' : avgUtil >= 10 ? '#ffc107' : '#dc3545' }}>
                    {formatScore(avgUtil)}
                  </strong>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت آمار برای تقویم (با تفکیک واحد)
// ============================================================
function CalendarStatistics({ data, dayNames }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>📊 آمار تقویم</div>
        <div style={{ color: '#6c757d' }}>هیچ داده‌ای برای نمایش وجود ندارد.</div>
      </div>
    );
  }

  const totalClasses = data.length;

  // توزیع کلاس‌ها در روزها
  const dayDistribution = {};
  dayNames.forEach((day, idx) => {
    const count = data.filter(cls => Number(cls.day) === idx).length;
    dayDistribution[day] = count;
  });

  // محاسبه میانگین کلاس در روز
  const avgClassesPerDay = totalClasses / 7;

  // پراکندگی امتیاز در روزها
  const dayUtilityStats = {};
  dayNames.forEach((day, idx) => {
    const classes = data.filter(cls => Number(cls.day) === idx);
    if (classes.length > 0) {
      const totalUtil = classes.reduce((sum, cls) => sum + (cls.utility || 0), 0);
      dayUtilityStats[day] = totalUtil / classes.length;
    } else {
      dayUtilityStats[day] = 0;
    }
  });

  // ===== آمار تفکیکی بر اساس واحد =====
  const unitsDistribution = {};
  data.forEach(item => {
    const units = item.units || 0;
    unitsDistribution[units] = (unitsDistribution[units] || 0) + 1;
  });

  const unitsUtilityStats = {};
  Object.keys(unitsDistribution).forEach(units => {
    const classes = data.filter(item => item.units === Number(units));
    if (classes.length > 0) {
      const totalUtil = classes.reduce((sum, cls) => sum + (cls.utility || 0), 0);
      unitsUtilityStats[units] = totalUtil / classes.length;
    } else {
      unitsUtilityStats[units] = 0;
    }
  });

  // توزیع کلاس‌ها در روزها به تفکیک واحد
  const dayUnitsDistribution = {};
  dayNames.forEach((day, idx) => {
    dayUnitsDistribution[day] = {};
    Object.keys(unitsDistribution).forEach(units => {
      const count = data.filter(cls => Number(cls.day) === idx && cls.units === Number(units)).length;
      dayUnitsDistribution[day][units] = count;
    });
  });

  return (
    <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6' }}>
      <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '12px' }}>📊 آمار تقویم</div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>تعداد کل کلاس‌ها</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#007bff' }}>{totalClasses}</div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>میانگین کلاس در روز</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#17a2b8' }}>{avgClassesPerDay.toFixed(1)}</div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>شلوغ‌ترین روز</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#dc3545' }}>
            {Object.entries(dayDistribution).sort((a, b) => b[1] - a[1])[0]?.[0] || '-'}
            {' '}
            ({Object.entries(dayDistribution).sort((a, b) => b[1] - a[1])[0]?.[1] || 0})
          </div>
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d' }}>خلوت‌ترین روز</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#28a745' }}>
            {Object.entries(dayDistribution).sort((a, b) => a[1] - b[1])[0]?.[0] || '-'}
            {' '}
            ({Object.entries(dayDistribution).sort((a, b) => a[1] - b[1])[0]?.[1] || 0})
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px', marginTop: '12px' }}>
        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>توزیع کلاس‌ها در روزها</div>
          {Object.entries(dayDistribution).map(([day, count]) => (
            <div key={day} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '60px', fontSize: '0.85rem' }}>{day}</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${totalClasses > 0 ? (count / totalClasses * 100) : 0}%`,
                  height: '100%',
                  backgroundColor: count > 0 ? '#007bff' : '#e9ecef',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '35px' }}>{count}</span>
            </div>
          ))}
        </div>

        <div style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.85rem', color: '#6c757d', marginBottom: '4px' }}>میانگین امتیاز در روزها</div>
          {Object.entries(dayUtilityStats).map(([day, avg]) => (
            <div key={day} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <span style={{ width: '60px', fontSize: '0.85rem' }}>{day}</span>
              <div style={{ flex: 1, height: '20px', backgroundColor: '#e9ecef', borderRadius: '10px', overflow: 'hidden' }}>
                <div style={{
                  width: `${avg > 0 ? Math.min((avg / 28) * 100, 100) : 0}%`,
                  height: '100%',
                  backgroundColor: avg >= 14 ? '#28a745' : avg >= 10 ? '#ffc107' : '#dc3545',
                  transition: 'width 0.3s'
                }} />
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 'bold', minWidth: '50px' }}>{formatScore(avg)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ===== بخش آمار تفکیکی بر اساس واحد در روزها ===== */}
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '2px solid #dee2e6' }}>
        <div style={{ fontWeight: 'bold', fontSize: '1rem', marginBottom: '12px', color: '#495057' }}>
          📈 توزیع کلاس‌ها در روزها به تفکیک واحد
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', borderRadius: '6px', overflow: 'hidden' }}>
            <thead>
              <tr style={{ backgroundColor: '#e9ecef' }}>
                <th style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center' }}>روز</th>
                {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => (
                  <th key={units} style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center' }}>
                    {units} واحدی
                  </th>
                ))}
                <th style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center', backgroundColor: '#007bff', color: 'white' }}>
                  جمع
                </th>
              </tr>
            </thead>
            <tbody>
              {dayNames.map(day => {
                const unitsData = dayUnitsDistribution[day] || {};
                const totalDay = Object.values(unitsData).reduce((sum, val) => sum + val, 0);
                return (
                  <tr key={day}>
                    <td style={{ padding: '8px 12px', border: '1px solid #dee2e6', fontWeight: 'bold' }}>{day}</td>
                    {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => (
                      <td key={units} style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center' }}>
                        {unitsData[units] || 0}
                      </td>
                    ))}
                    <td style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center', fontWeight: 'bold', backgroundColor: '#e3f2fd' }}>
                      {totalDay}
                    </td>
                  </tr>
                );
              })}
              <tr style={{ backgroundColor: '#f8f9fa', fontWeight: 'bold' }}>
                <td style={{ padding: '8px 12px', border: '1px solid #dee2e6' }}>جمع کل</td>
                {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => (
                  <td key={units} style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center' }}>
                    {unitsDistribution[units] || 0}
                  </td>
                ))}
                <td style={{ padding: '8px 12px', border: '1px solid #dee2e6', textAlign: 'center', backgroundColor: '#007bff', color: 'white' }}>
                  {totalClasses}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {Object.keys(unitsDistribution).sort((a, b) => Number(a) - Number(b)).map(units => {
            const count = unitsDistribution[units];
            const avgUtil = unitsUtilityStats[units] || 0;

            return (
              <div key={units} style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontWeight: 'bold', fontSize: '1rem', color: '#007bff', marginBottom: '8px' }}>
                  {units} واحدی
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>
                  تعداد: <strong>{count}</strong>
                </div>
                <div style={{ fontSize: '0.9rem' }}>
                  میانگین امتیاز: <strong style={{ color: avgUtil >= 14 ? '#28a745' : avgUtil >= 10 ? '#ffc107' : '#dc3545' }}>
                    {formatScore(avgUtil)}
                  </strong>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت ماتریس استاد
// ============================================================
function InstructorTimeMatrix({
  data,
  instructors,
  masterSlots,
  dayNames,
  onClassMove,
  onClassEdit,
  getUtility,
  getClassColor,
  selectedInstructor,
  teachingPreferences,
  timePreferences,
  roomPreferences,
  instructorsData,
  roomsData,
  allData,
  filterUnits,
  onFilterChange,
  courseInfoMap,
  dominantTerm,
}) {
  const timeSlots = masterSlots;
  const [draggedClass, setDraggedClass] = useState(null);

  const selectedInstructorInfo = instructors.find(inst => inst.code === selectedInstructor);

  const filteredData = useMemo(() => {
    let result = data;
    if (selectedInstructor) {
      result = result.filter(cls => cls.instructor_code === selectedInstructor);
    }
    if (filterUnits !== null) {
      result = result.filter(cls => cls.units === filterUnits);
    }

    return result;
  }, [data, selectedInstructor, filterUnits]);

  const getAvailableRoom = (day, slotStart, slotEnd, requiredCapacity, excludeClassKey) => {
    return getStableAvailableRoom(
      roomsData,
      allData,
      day,
      slotStart,
      slotEnd,
      requiredCapacity,
      excludeClassKey,
      `${selectedInstructor}|${day}|${slotStart}|${slotEnd}`
    );
  };

  const handleDragStart = (e, cls) => {
    setDraggedClass(cls);
    e.dataTransfer.setData('text/plain', String(cls.id));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, dayIndex, slotStart, slotEnd) => {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData('text/plain');
    if (!draggedId) return;
    const draggedClassFromData = allData.find((c) => String(c.id) === String(draggedId));
    if (!draggedClassFromData) return;

    const start = draggedClassFromData.start ?? draggedClassFromData.start_time;
    const end = draggedClassFromData.end ?? draggedClassFromData.end_time;

    if (
      Number(draggedClassFromData.day) === Number(dayIndex) &&
      normalizeTime(start) === normalizeTime(slotStart) &&
      normalizeTime(end) === normalizeTime(slotEnd)
    ) {
      return;
    }

    const term = draggedClassFromData.term || dominantTerm || 'semester_1';
    const slotLabel = `${slotStart}-${slotEnd}`;
    const validSlots = SCHEDULES[term]?.[draggedClassFromData.units || 2] || [];
    if (!validSlots.includes(slotLabel)) {
      alert(`❌ بازه ${slotLabel} برای کلاس با ${draggedClassFromData.units || 2} واحد در ترم ${term} معتبر نیست.`);
      return;
    }

    const conflictCheck = getActualConflictsForClass(allData, {
      ...draggedClassFromData,
      day: dayIndex,
      start: slotStart,
      end: slotEnd,
    });
    if (conflictCheck.length > 0) {
      alert('❌ این بازه زمانی با کلاس دیگری برای این استاد تداخل دارد.');
      return;
    }

    const requiredCap = getCourseCapacity(draggedClassFromData, courseInfoMap) || 30;
    const excludeKey = getClassKey(draggedClassFromData);
    const availableRoom = getAvailableRoom(dayIndex, slotStart, slotEnd, requiredCap, excludeKey);
    if (!availableRoom) {
      alert('❌ هیچ اتاق خالی با ظرفیت مناسب در این بازه وجود ندارد.');
      return;
    }

    const newRoomId = availableRoom.id || availableRoom.room_id || null;
    const newInstructorCode = selectedInstructor || draggedClassFromData.instructor_code;
    onClassMove(draggedClassFromData, newInstructorCode, dayIndex, slotStart, slotEnd, newRoomId);
    setDraggedClass(null);
  };

  const handleEmptyCellClick = (dayIndex, slotStart, slotEnd) => {
    if (!draggedClass) {
      alert('ℹ️ ابتدا یک کلاس را با کشیدن (درگ) انتخاب کنید، سپس روی سلول خالی کلیک کنید.');
      return;
    }

    const term = draggedClass.term || dominantTerm || 'semester_1';
    const slotLabel = `${slotStart}-${slotEnd}`;
    const validSlots = SCHEDULES[term]?.[draggedClass.units || 2] || [];
    if (!validSlots.includes(slotLabel)) {
      alert(`❌ بازه ${slotLabel} برای کلاس با ${draggedClass.units || 2} واحد در ترم ${term} معتبر نیست.`);
      return;
    }

    const conflictCheck = getActualConflictsForClass(allData, {
      ...draggedClass,
      day: dayIndex,
      start: slotStart,
      end: slotEnd,
    });
    if (conflictCheck.length > 0) {
      alert('❌ این بازه زمانی با کلاس دیگری برای این استاد تداخل دارد.');
      return;
    }

    const requiredCap = getCourseCapacity(draggedClass, courseInfoMap) || 30;
    const excludeKey = getClassKey(draggedClass);
    const availableRoom = getAvailableRoom(dayIndex, slotStart, slotEnd, requiredCap, excludeKey);
    if (!availableRoom) {
      alert('❌ هیچ اتاق خالی با ظرفیت مناسب در این بازه وجود ندارد.');
      return;
    }

    const newRoomId = availableRoom.id || availableRoom.room_id || null;
    const newInstructorCode = selectedInstructor || draggedClass.instructor_code;
    onClassMove(draggedClass, newInstructorCode, dayIndex, slotStart, slotEnd, newRoomId);
    setDraggedClass(null);
  };

  const renderCell = (dayIndex, slot) => {
    const slotStart = slot.start;
    const slotEnd = slot.end;

    const matchedClasses = getInstructorClassesExactlyInSlot(
      filteredData,
      selectedInstructor,
      dayIndex,
      slotStart,
      slotEnd
    );

    if (matchedClasses.length > 1) {
      return (
        <td
          key={`${dayIndex}-${slotStart}-${slotEnd}`}
          style={{
            padding: '4px',
            border: '1px solid #ccc',
            backgroundColor: '#f8d7da',
            textAlign: 'center',
            verticalAlign: 'middle',
            fontSize: '0.7rem',
            minWidth: '100px',
            height: '85px',
            lineHeight: '1.35',
          }}
        >
          <div style={{ fontWeight: 'bold', color: '#721c24' }}>⚠️ تداخل واقعی استاد</div>
          {matchedClasses.map((cls) => (
            <div key={cls.id} style={{ fontSize: '0.65rem', marginTop: '3px' }}>
              📚 {cls.course_name || cls.course_code || 'بدون نام'}
              <br />
              🏠 {cls.room_name || 'بدون اتاق'}
            </div>
          ))}
        </td>
      );
    }

    if (matchedClasses.length === 1) {
      const cls = matchedClasses[0];
      const actualConflicts = getActualConflictsForClass(allData, cls);
      const utility = getUtility(cls);
      const color = actualConflicts.length > 0
        ? '#f8d7da'
        : getClassColor(utility);

      const courseCapacity = getCourseCapacity(cls, courseInfoMap) || '?';
      const roomCapacity = getRoomCapacity(cls, roomsData) || '?';

      return (
        <td
          key={`${dayIndex}-${slotStart}-${slotEnd}`}
          style={{
            padding: '4px',
            border: '1px solid #ccc',
            backgroundColor: color,
            textAlign: 'center',
            verticalAlign: 'middle',
            fontSize: '0.7rem',
            minWidth: '105px',
            height: '90px',
            cursor: 'grab',
            lineHeight: '1.35',
          }}
          draggable
          onDragStart={(e) => handleDragStart(e, cls)}
          onDragOver={handleDragOver}
          onClick={() => onClassEdit(cls)}
          title={`${cls.course_name || cls.course_code} | امتیاز: ${utility}`}
        >
          {actualConflicts.length > 0 && (
            <div style={{ fontWeight: 'bold', color: '#721c24', fontSize: '0.62rem', marginBottom: '3px' }}>
              ⚠️ تداخل واقعی با:{' '}
              {actualConflicts.map((item) => item.course_name || item.course_code).join('، ')}
            </div>
          )}
          <div style={{ fontWeight: 'bold' }}>
            📚 {cls.course_name || cls.course_code || 'بدون نام'}
          </div>
          <div style={{ fontSize: '0.62rem' }}>
            👤 {cls.instructor_name || cls.instructor_code || ''}
          </div>
          <div style={{ fontSize: '0.62rem' }}>
            👥 ظرفیت درس: {courseCapacity}
          </div>
          <div style={{ fontSize: '0.62rem' }}>
            🏠 {cls.room_name || 'بدون اتاق'} (ظرفیت: {roomCapacity})
          </div>
          <div style={{ fontSize: '0.62rem', fontWeight: 'bold' }}>
            امتیاز کل: {formatScore(utility)}
          </div>
        </td>
      );
    }

    const requiredCap = draggedClass ? getCourseCapacity(draggedClass, courseInfoMap) || 30 : 0;
    const excludeKey = draggedClass ? getClassKey(draggedClass) : null;
    const availableRoom = getAvailableRoom(dayIndex, slotStart, slotEnd, requiredCap, excludeKey);

    if (!availableRoom) {
      const msg = requiredCap > 0 ? 'اتاق خالی با ظرفیت کافی وجود ندارد' : 'همه اتاق‌ها پر هستند';
      return (
        <td
          key={`${dayIndex}-${slotStart}-${slotEnd}`}
          style={{
            padding: '4px',
            border: '1px solid #ccc',
            backgroundColor: '#f8d7da',
            textAlign: 'center',
            verticalAlign: 'middle',
            fontSize: '0.7rem',
            minWidth: '100px',
            height: '85px',
            lineHeight: '1.35',
          }}
        >
          <div style={{ fontWeight: 'bold', color: '#721c24' }}>🏢 {msg}</div>
        </td>
      );
    }

    const roomName = availableRoom.name || availableRoom.room_name || 'اتاق';
    const roomCap = getRoomCapacity(availableRoom) || '?';

    const draggedCourseName = draggedClass
      ? (draggedClass.course_name || draggedClass.course_code || 'درس انتخاب‌شده')
      : null;
    const draggedCourseCapacity = draggedClass
      ? getCourseCapacity(draggedClass, courseInfoMap) || '?'
      : null;

    let utility = null;
    if (draggedClass) {
      const dummyClass = {
        instructor_code: selectedInstructor,
        day: dayIndex,
        start: slotStart,
        end: slotEnd,
        estimated_capacity: getCourseCapacity(draggedClass, courseInfoMap) || 30,
        capacity: getRoomCapacity(availableRoom),
        course_name: draggedClass.course_name || '',
        room_id: availableRoom.id || null,
      };
      utility = calculateUtility(dummyClass, teachingPreferences, timePreferences, roomPreferences, instructorsData, courseInfoMap);
    }

    return (
      <td
        key={`${dayIndex}-${slotStart}-${slotEnd}`}
        style={{
          padding: '4px',
          border: '1px solid #ccc',
          backgroundColor: '#e9ecef',
          textAlign: 'center',
          verticalAlign: 'middle',
          fontSize: '0.7rem',
          minWidth: '100px',
          height: '85px',
          cursor: draggedClass ? 'pointer' : 'default',
          lineHeight: '1.35',
          opacity: draggedClass ? 1 : 0.6,
        }}
        onClick={() => {
          if (draggedClass) {
            handleEmptyCellClick(dayIndex, slotStart, slotEnd);
          }
        }}
        onDrop={(e) => handleDrop(e, dayIndex, slotStart, slotEnd)}
        onDragOver={handleDragOver}
      >
        <div style={{ fontWeight: 'bold', color: '#0066cc' }}>🏠 {roomName}</div>
        <div style={{ fontSize: '0.6rem' }}>ظرفیت اتاق: {roomCap}</div>

        {draggedClass && (
          <>
            <div style={{ fontSize: '0.6rem', marginTop: '3px' }}>
              📚 {draggedCourseName}
            </div>
            <div style={{ fontSize: '0.6rem' }}>
              👥 ظرفیت درس: {draggedCourseCapacity}
            </div>
          </>
        )}

        {utility !== null && (
          <div style={{ fontSize: '0.6rem', fontWeight: 'bold' }}>امتیاز: {formatScore(utility)}</div>
        )}

        {draggedClass && (
          <div style={{ fontSize: '0.55rem', color: '#28a745' }}>✓ قابل انتقال</div>
        )}
      </td>
    );
  };

  if (!selectedInstructor || !selectedInstructorInfo) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
        👈 لطفاً یک استاد را از لیست انتخاب کنید.
      </div>
    );
  }

  if (timeSlots.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
        ⚠️ هیچ بازه زمانی برای نمایش وجود ندارد.
      </div>
    );
  }

  const invalidSlots = filteredData.filter(cls => {
    const term = cls.term || dominantTerm || 'semester_1';
    const slot = `${normalizeTime(cls.start)}-${normalizeTime(cls.end)}`;
    const validSlots = SCHEDULES[term]?.[cls.units || 2] || [];
    return !validSlots.includes(slot);
  });

  const renderFilterButtons = () => (
    <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
      <span style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#555' }}>فیلتر واحد (استاد):</span>
      <button
        onClick={() => onFilterChange(null)}
        style={{
          padding: '4px 12px',
          borderRadius: '4px',
          border: '1px solid #ccc',
          backgroundColor: filterUnits === null ? '#4A90D9' : '#f0f0f0',
          color: filterUnits === null ? '#fff' : '#333',
          cursor: 'pointer',
          fontWeight: filterUnits === null ? 'bold' : 'normal',
        }}
      >
        همه
      </button>
      {[1, 2, 3, 4].map(u => (
        <button
          key={u}
          onClick={() => onFilterChange(u)}
          style={{
            padding: '4px 12px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            backgroundColor: filterUnits === u ? '#4A90D9' : '#f0f0f0',
            color: filterUnits === u ? '#fff' : '#333',
            cursor: 'pointer',
            fontWeight: filterUnits === u ? 'bold' : 'normal',
          }}
        >
          {u} واحدی
        </button>
      ))}
    </div>
  );

  return (
    <div className="matrix-container" style={{ overflowX: 'auto' }}>
      {renderFilterButtons()}

      <div style={{
        marginBottom: '16px',
        padding: '12px 16px',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6',
        direction: 'rtl',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 'bold', fontSize: '1rem', color: '#495057' }}>
            🕐 مطلوبیات زمانی استاد {selectedInstructorInfo.name}:
          </span>
          {timePreferences.filter(p => p.instructor_code === selectedInstructor).length === 0 ? (
            <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>
              هیچ ترجیح زمانی ثبت نشده است.
            </span>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {timePreferences.filter(p => p.instructor_code === selectedInstructor).map((pref, idx) => {
                const dayName = dayNames[Number(pref.day)] || pref.day;
                return (
                  <span
                    key={idx}
                    style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      backgroundColor: '#e9ecef',
                      borderRadius: '16px',
                      fontSize: '0.85rem',
                      color: '#212529',
                      border: '1px solid #ced4da',
                    }}
                  >
                    {dayName} {pref.start_time} - {pref.end_time}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <table className="instructor-time-matrix" style={{ borderCollapse: 'collapse', width: '100%', minWidth: '700px' }}>
        <thead>
          <tr>
            <th style={{ padding: '8px', border: '1px solid #ccc', backgroundColor: '#f0f0f0', textAlign: 'center' }}>
              زمان / روز
            </th>
            {dayNames.map((day, idx) => (
              <th key={idx} style={{ padding: '8px', border: '1px solid #ccc', backgroundColor: '#f0f0f0', textAlign: 'center' }}>
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {timeSlots.map((slot) => (
            <tr key={slot.label}>
              <td style={{ padding: '8px', border: '1px solid #ccc', backgroundColor: '#f9f9f9', fontWeight: 'bold', textAlign: 'center' }}>
                {slot.start} - {slot.end}
              </td>
              {dayNames.map((_, dayIndex) => renderCell(dayIndex, slot))}
            </tr>
          ))}
        </tbody>
      </table>

      {invalidSlots.length > 0 && (
        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '6px' }}>
          <div style={{ fontWeight: 'bold' }}>⚠️ کلاس‌های دارای اسلات نامعتبر:</div>
          <ul style={{ margin: '4px 0 0 16px', fontSize: '0.85rem' }}>
            {invalidSlots.map(cls => (
              <li key={cls.id}>
                {cls.course_name || cls.course_code} (گروه {cls.group_number}) - {dayNames[cls.day] || cls.day} {cls.start}-{cls.end} (واحد: {cls.units}) - {cls.room_name || 'بدون اتاق'}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* بخش آمار ماتریس استاد */}
      <MatrixStatistics
        data={filteredData}
        rooms={roomsData || []}
        masterSlots={masterSlots}
        selectedDay={0}
        dayNames={dayNames}
        title={`آمار کلاس‌های استاد ${selectedInstructorInfo.name}`}
      />
    </div>
  );
}

// ============================================================
// کامپوننت ماتریس اتاق
// ============================================================
function RoomTimeMatrix({
  data,
  rooms,
  masterSlots,
  dayNames,
  selectedDay,
  onClassMove,
  onClassEdit,
  getUtility,
  getClassColor,
  filterUnits,
  onFilterChange,
  allData,
  teachingPreferences,
  timePreferences,
  roomPreferences,
  instructorsData,
  courseInfoMap,
  roomsData,
  dominantTerm,
}) {
  console.log(`🏢 [RoomMatrix] ===== شروع رندر ماتریس اتاق =====`);
  console.log(`🏢 [RoomMatrix] تعداد کل داده‌ها: ${data.length}`);
  console.log(`🏢 [RoomMatrix] تعداد اتاق‌ها: ${rooms.length}`);
  console.log(`🏢 [RoomMatrix] روز انتخاب‌شده: ${dayNames[selectedDay]} (${selectedDay})`);
  console.log(`🏢 [RoomMatrix] فیلتر واحد: ${filterUnits}`);
  console.log(`🏢 [RoomMatrix] تعداد اسلات‌ها: ${masterSlots.length}`);

  console.log(`🏢 [RoomMatrix] اسلات‌های موجود در masterSlots:`, masterSlots.map(s => s.normalizedKey || s.label));

  const filteredData = useMemo(() => {
    let result = data.filter(cls => Number(cls.day) === Number(selectedDay));
    if (filterUnits !== null) {
      result = result.filter(cls => cls.units === filterUnits);
    }

    console.log(`🏢 [RoomMatrix] بعد از فیلتر کردن: ${result.length} کلاس برای روز ${dayNames[selectedDay]}`);

    result.forEach(cls => {
      const start = cls.start ?? cls.start_time;
      const end = cls.end ?? cls.end_time;
      const key = `${normalizeTime(start)}-${normalizeTime(end)}`;
      console.log(`   📝 کلاس ${cls.course_name} (id: ${cls.id}): term=${cls.term}, start=${start}, end=${end}, key=${key}`);
      if (!start || !end) {
        console.warn(`⚠️ [RoomMatrix] کلاس ${cls.course_name} (id: ${cls.id}) زمان نامعتبر دارد`);
      }
    });

    const keys = result.map(cls => {
      const start = cls.start ?? cls.start_time;
      const end = cls.end ?? cls.end_time;
      return `${normalizeTime(start)}-${normalizeTime(end)}`;
    });
    console.log(`🏢 [RoomMatrix] کلیدهای زمانی ساخته شده:`, [...new Set(keys)]);

    return result;
  }, [data, selectedDay, filterUnits]);

  const matrix = useMemo(() => {
    const result = {};

    const normalizedMasterSlots = masterSlots.map(slot => ({
      ...slot,
      normalizedKey: slot.normalizedKey || `${normalizeTime(slot.start)}-${normalizeTime(slot.end)}`
    }));

    console.log(`🏢 [RoomMatrix] masterSlots نرمال‌شده:`, normalizedMasterSlots.map(s => s.normalizedKey));

    rooms.forEach((room) => {
      const roomId = Number(room.id);
      result[roomId] = {};
      normalizedMasterSlots.forEach((slot) => {
        result[roomId][slot.normalizedKey] = null;
      });
    });

    console.log(`🏢 [RoomMatrix] ساختار ماتریس: ${Object.keys(result).length} اتاق، هر کدام با ${normalizedMasterSlots.length} اسلات`);

    const firstRoomId = Object.keys(result)[0];
    if (firstRoomId) {
      console.log(`🏢 [RoomMatrix] کلیدهای اسلات موجود در اتاق ${firstRoomId}:`, Object.keys(result[firstRoomId]));
    }

    let assignedCount = 0;
    let invalidCount = 0;

    filteredData.forEach((cls) => {
      const roomId = Number(cls.room_id);

      const start = cls.start ?? cls.start_time;
      const end = cls.end ?? cls.end_time;

      if (isNaN(roomId) || roomId <= 0) {
        console.warn('⚠️ [RoomMatrix] room_id نامعتبر است:', {
          classId: cls.id,
          course: cls.course_name,
          roomId: cls.room_id,
        });
        invalidCount++;
        return;
      }

      if (!start || !end) {
        console.warn('⚠️ [RoomMatrix] زمان کلاس خالی/نامعتبر است:', {
          classId: cls.id,
          course: cls.course_name,
          roomId,
          roomName: cls.room_name,
          start,
          end,
          start_time: cls.start_time,
          end_time: cls.end_time,
        });
        invalidCount++;
        return;
      }

      const key = `${normalizeTime(start)}-${normalizeTime(end)}`;
      console.log(`🔍 [RoomMatrix] بررسی کلاس ${cls.course_name}: roomId=${roomId}, key=${key}`);

      if (!result[roomId]) {
        console.warn('⚠️ [RoomMatrix] اتاق در ماتریس وجود ندارد:', {
          roomId,
          roomName: cls.room_name,
          availableRoomIds: Object.keys(result).map(Number),
        });
        invalidCount++;
        return;
      }

      const slotExists = Object.keys(result[roomId]).some(
        existingKey => existingKey === key
      );

      if (!slotExists) {
        console.warn('⚠️ [RoomMatrix] اسلات کلاس در ماتریس وجود ندارد:', {
          classId: cls.id,
          course: cls.course_name,
          roomId,
          roomName: cls.room_name,
          key,
          start,
          end,
          availableSlots: Object.keys(result[roomId]),
        });
        invalidCount++;
        return;
      }

      if (result[roomId][key] === null) {
        result[roomId][key] = {
          ...cls,
          room_id: roomId,
          start,
          end,
        };
        assignedCount++;
        console.log(`✅ [RoomMatrix] کلاس ${cls.course_name} در اتاق ${roomId}، اسلات ${key} قرار گرفت`);
      } else {
        const existing = result[roomId][key];
        if (existing.conflict) {
          existing.classes.push(cls);
        } else {
          result[roomId][key] = {
            conflict: true,
            classes: [existing, { ...cls, room_id: roomId, start, end }],
          };
        }
        console.warn(`⚠️ [RoomMatrix] تداخل در اتاق ${roomId}، اسلات ${key} برای کلاس ${cls.course_name}`);
      }
    });

    console.log('🏢 [RoomMatrix] خلاصه:', {
      assignedCount,
      filteredCount: filteredData.length,
      invalidCount,
    });

    if (assignedCount !== filteredData.length) {
      console.warn(`⚠️ [RoomMatrix] اختلاف در تعداد: ${filteredData.length - assignedCount} کلاس در ماتریس قرار نگرفته‌اند`);
    }

    return result;
  }, [filteredData, rooms, masterSlots]);

  const handleDrop = (e, roomId, slotStart, slotEnd) => {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData('text/plain');
    if (!draggedId) return;
    const draggedClass = allData.find((c) => String(c.id) === String(draggedId));
    if (!draggedClass) return;

    const start = draggedClass.start ?? draggedClass.start_time;
    const end = draggedClass.end ?? draggedClass.end_time;

    if (
      String(draggedClass.room_id) === String(roomId) &&
      normalizeTime(start) === normalizeTime(slotStart) &&
      normalizeTime(end) === normalizeTime(slotEnd)
    ) {
      return;
    }

    const term = draggedClass.term || dominantTerm || 'semester_1';
    const slotLabel = `${slotStart}-${slotEnd}`;
    const validSlots = SCHEDULES[term]?.[draggedClass.units || 2] || [];
    if (!validSlots.includes(slotLabel)) {
      alert(`❌ بازه ${slotLabel} برای کلاس با ${draggedClass.units || 2} واحد در ترم ${term} معتبر نیست.`);
      return;
    }

    const occupied = getOccupiedRoomKeys(allData, Number(selectedDay), slotStart, slotEnd, getClassKey(draggedClass));
    const roomIdKey = `id:${String(roomId)}`;
    const roomObj = roomsData.find(r => String(r.id) === String(roomId));
    const roomNameKey = roomObj ? `name:${roomObj.name.trim().toLowerCase()}` : null;
    if (occupied.has(roomIdKey) || (roomNameKey && occupied.has(roomNameKey))) {
      alert('❌ این اتاق در بازه موردنظر اشغال است.');
      return;
    }

    const requiredCap = getCourseCapacity(draggedClass, courseInfoMap) || 30;
    const roomCap = getRoomCapacity({ room_id: roomId }, roomsData);
    if (roomCap < requiredCap) {
      alert(`❌ ظرفیت اتاق (${roomCap}) کمتر از ظرفیت درس (${requiredCap}) است.`);
      return;
    }

    const conflicts = getActualConflictsForClass(allData, {
      ...draggedClass,
      day: selectedDay,
      start: slotStart,
      end: slotEnd,
    });
    if (conflicts.length > 0) {
      alert('❌ این بازه زمانی با کلاس دیگری برای این استاد تداخل دارد.');
      return;
    }

    onClassMove(draggedClass, null, selectedDay, slotStart, slotEnd, roomId);
  };

  const handleDragStart = (e, cls) => {
    e.dataTransfer.setData('text/plain', String(cls.id));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const renderFilterButtons = () => (
    <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
      <span style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#555' }}>فیلتر واحد (اتاق):</span>
      <button
        onClick={() => onFilterChange(null)}
        style={{
          padding: '4px 12px',
          borderRadius: '4px',
          border: '1px solid #ccc',
          backgroundColor: filterUnits === null ? '#4A90D9' : '#f0f0f0',
          color: filterUnits === null ? '#fff' : '#333',
          cursor: 'pointer',
          fontWeight: filterUnits === null ? 'bold' : 'normal',
        }}
      >
        همه
      </button>
      {[1, 2, 3, 4].map(u => (
        <button
          key={u}
          onClick={() => onFilterChange(u)}
          style={{
            padding: '4px 12px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            backgroundColor: filterUnits === u ? '#4A90D9' : '#f0f0f0',
            color: filterUnits === u ? '#fff' : '#333',
            cursor: 'pointer',
            fontWeight: filterUnits === u ? 'bold' : 'normal',
          }}
        >
          {u} واحدی
        </button>
      ))}
    </div>
  );

  const hasClasses = filteredData.length > 0;

  const invalidSlots = filteredData.filter(cls => {
    const term = cls.term || dominantTerm || 'semester_1';
    const slot = `${normalizeTime(cls.start)}-${normalizeTime(cls.end)}`;
    const validSlots = SCHEDULES[term]?.[cls.units || 2] || [];
    return !validSlots.includes(slot);
  });

  return (
    <div className="matrix-container" style={{ overflowX: 'auto' }}>
      {renderFilterButtons()}

      <div style={{
        padding: '10px 16px',
        backgroundColor: '#e9ecef',
        borderRadius: '6px',
        marginBottom: '12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '8px',
        direction: 'rtl',
      }}>
        <div>
          <span style={{ fontWeight: 'bold' }}>📊 آمار کلاس‌ها در روز {dayNames[selectedDay]}:</span>
          <span style={{ marginRight: '12px' }}>
            تعداد کل: <strong>{data.filter(cls => Number(cls.day) === Number(selectedDay)).length}</strong>
          </span>
          {filterUnits !== null && (
            <span style={{ marginRight: '12px' }}>
              با فیلتر {filterUnits} واحدی: <strong>{filteredData.length}</strong>
            </span>
          )}
          <span style={{ marginRight: '12px' }}>
            اتاق‌ها: <strong>{rooms.length}</strong>
          </span>
          <span style={{ marginRight: '12px' }}>
            اسلات‌ها: <strong>{masterSlots.length}</strong>
          </span>
        </div>
        <div style={{ fontSize: '0.9rem', color: '#555' }}>
          {filteredData.length > 0 ? '✅ کلاس‌ها نمایش داده می‌شوند' : '⚠️ کلاسی برای نمایش وجود ندارد'}
        </div>
      </div>

      {!hasClasses && (
        <div style={{ padding: '12px', backgroundColor: '#fff3cd', borderRadius: '6px', marginBottom: '12px', textAlign: 'center' }}>
          ⚠️ هیچ کلاسی برای روز {dayNames[selectedDay]} وجود ندارد.
          {filterUnits !== null && ` (فیلتر واحد: ${filterUnits})`}
        </div>
      )}

      {masterSlots.length === 0 && (
        <div style={{ padding: '12px', backgroundColor: '#f8d7da', borderRadius: '6px', marginBottom: '12px', textAlign: 'center' }}>
          ⚠️ هیچ بازه زمانی با فیلتر واحد انتخاب‌شده مطابقت ندارد. لطفاً فیلتر را تغییر دهید.
        </div>
      )}

      {hasClasses && masterSlots.length > 0 && (
        <table className="room-time-matrix" style={{ borderCollapse: 'collapse', width: '100%', minWidth: '700px' }}>
          <thead>
            <tr>
              <th style={{ padding: '8px', border: '1px solid #ccc', backgroundColor: '#f0f0f0', textAlign: 'right' }}>
                اتاق (ظرفیت)
              </th>
              {masterSlots.map((slot) => (
                <th key={slot.label} style={{ padding: '8px', border: '1px solid #ccc', backgroundColor: '#f0f0f0', textAlign: 'center' }}>
                  {slot.start}-{slot.end}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rooms.map((room) => {
              const roomCap = getRoomCapacity(room) || '?';
              const roomClassesCount = filteredData.filter(cls =>
                String(cls.room_id) === String(room.id)
              ).length;

              return (
                <tr key={room.id}>
                  <td style={{
                    padding: '8px',
                    border: '1px solid #ccc',
                    fontWeight: 'bold',
                    textAlign: 'right',
                    backgroundColor: '#fafafa',
                    fontSize: '0.8rem',
                  }}>
                    {room.name} ({roomCap})
                    {roomClassesCount > 0 && (
                      <span style={{
                        display: 'block',
                        fontSize: '0.7rem',
                        color: '#28a745',
                        fontWeight: 'normal',
                      }}>
                        📚 {roomClassesCount} کلاس
                      </span>
                    )}
                  </td>
                  {masterSlots.map((slot) => {
                    const key = slot.normalizedKey || `${slot.start}-${slot.end}`;
                    const cell = matrix[room.id]?.[key];
                    let content = '';
                    let bgColor = '#e9ecef';
                    let utility = null;
                    let draggable = false;
                    let classItem = null;
                    let isConflict = false;

                    if (cell) {
                      if (cell.conflict) {
                        isConflict = true;
                        bgColor = '#f8d7da';
                        content = '⚠️ تداخل';
                      } else {
                        classItem = cell;
                        draggable = true;
                        utility = getUtility(classItem);
                        const color = getClassColor(utility);
                        bgColor = color;
                        const courseDisplay = classItem.course_name || classItem.course_code || `کلاس ${classItem.id}`;
                        const instructorDisplay = classItem.instructor_name || classItem.instructor_code || '';
                        const capacity = getCourseCapacity(classItem, courseInfoMap) || '?';
                        content = `📚 ${courseDisplay}\n👤 ${instructorDisplay}\n👥 ظرفیت درس: ${capacity}\nامتیاز: ${formatScore(utility)}`;
                      }
                    }

                    return (
                      <td
                        key={key}
                        style={{
                          padding: '4px',
                          border: '1px solid #ccc',
                          backgroundColor: bgColor,
                          textAlign: 'center',
                          verticalAlign: 'middle',
                          fontSize: '0.7rem',
                          whiteSpace: 'pre-wrap',
                          minWidth: '80px',
                          height: '70px',
                          cursor: draggable ? 'grab' : 'default',
                          lineHeight: '1.3',
                        }}
                        draggable={draggable}
                        onDragStart={draggable ? (e) => handleDragStart(e, classItem) : undefined}
                        onDragOver={handleDragOver}
                        onDrop={(e) => handleDrop(e, room.id, slot.start, slot.end)}
                        onClick={() => {
                          if (classItem) {
                            onClassEdit(classItem);
                          }
                        }}
                        title={classItem ? `${classItem.course_name} (امتیاز: ${utility})` : 'خالی'}
                      >
                        {content}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {invalidSlots.length > 0 && (
        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '6px' }}>
          <div style={{ fontWeight: 'bold' }}>⚠️ کلاس‌های دارای اسلات نامعتبر در ماتریس اتاق:</div>
          <ul style={{ margin: '4px 0 0 16px', fontSize: '0.85rem' }}>
            {invalidSlots.map(cls => (
              <li key={cls.id}>
                {cls.course_name || cls.course_code} (گروه {cls.group_number}) - {dayNames[cls.day] || cls.day} {cls.start}-{cls.end} (واحد: {cls.units}) - {cls.room_name || 'بدون اتاق'}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* بخش آمار ماتریس اتاق */}
      <MatrixStatistics
        data={filteredData}
        rooms={rooms}
        masterSlots={masterSlots}
        selectedDay={selectedDay}
        dayNames={dayNames}
        title={`آمار اتاق‌ها - روز ${dayNames[selectedDay]}`}
      />
    </div>
  );
}

// ============================================================
// Helper برای آماده‌سازی داده‌های جدول
// ============================================================

const prepareTableRows = (rows, teachingPreferences, timePreferences, roomPreferences, instructorsData, courseInfoMap, courseHistory = [], prerequisiteMap = {}) => {
  return rows.map((item) => {
    const details = item.utilityDetails ?? calculateUtilityDetails(
      item,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
    const total = item.utility ?? details.total ?? 0;
    return {
      ...item,
      teachingScore: Number(details.teachingScore ?? 0),
      timeDayScore: Number(details.timeDayScore ?? 0),
      timeSlotScore: Number(details.timeSlotScore ?? 0),
      roomScore: Number(details.roomScore ?? 0),
      utility: Number(total),
      utilityDetails: details,
    };
  });
};

// ============================================================
// کامپوننت اصلی OptimizationPage
// ============================================================
export default function OptimizationPage({
  roomAllocationData,
  optimizedData: propOptimizedData,
  onProcess,
  onClear,
  loading,
  onNext,
  basketId: propBasketId,
  workflowId: propWorkflowId,
  teachingPreferences: propTeachingPreferences = [],
  timePreferences: propTimePreferences = [],
  roomPreferences: propRoomPreferences = [],
  instructorsData: propInstructorsData = [],
  roomsData: propRoomsData = [],
}) {
  const [data, setData] = useState([]);
  const [optimizedData, setOptimizedData] = useState(propOptimizedData || null);
  const [viewMode, setViewMode] = useState('table');
  const [selectedDay, setSelectedDay] = useState(0);
  const [selectedInstructor, setSelectedInstructor] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [changeLog, setChangeLog] = useState([]);
  const [basketId, setBasketId] = useState(propBasketId);
  const [workflowId, setWorkflowId] = useState(propWorkflowId);

  const [filterUnitsInstructor, setFilterUnitsInstructor] = useState(null);
  const [filterUnitsRoom, setFilterUnitsRoom] = useState(null);

  const [teachingPreferences, setTeachingPreferences] = useState(propTeachingPreferences);
  const [timePreferences, setTimePreferences] = useState(propTimePreferences);
  const [roomPreferences, setRoomPreferences] = useState(propRoomPreferences);
  const [instructorsData, setInstructorsData] = useState(propInstructorsData);
  const [roomsData, setRoomsData] = useState(propRoomsData);
  const [courseInfoMap, setCourseInfoMap] = useState({});
  const [courseHistory, setCourseHistory] = useState([]);
  const [prerequisiteMap, setPrerequisiteMap] = useState({});
  const [preferencesLoaded, setPreferencesLoaded] = useState(
    propTeachingPreferences.length > 0 ||
    propTimePreferences.length > 0 ||
    propInstructorsData.length > 0 ||
    propRoomsData.length > 0
  );

  const hasLoaded = useRef(false);
  const fetchDone = useRef(false);
  const dataLoadedFromServer = useRef(false);
  const appliedCourseInfoMapRef = useRef({});

  // ============================
  // بارگذاری ترجیحات و داده‌های کمکی
  // ============================
  useEffect(() => {
    if (fetchDone.current) return;

    const fetchAllData = async () => {
      try {
        const [teachRes, timeRes, instructorsRes, roomsRes, coursesRes] = await Promise.all([
          axios.get('http://localhost:8000/api/teaching-preferences/').catch(() => ({ data: [] })),
          axios.get('http://localhost:8000/api/time-preferences/').catch(() => ({ data: [] })),
          axios.get('http://localhost:8000/api/professors-rooms/instructors/list').catch(() => ({ data: [] })),
          axios.get('http://localhost:8000/api/professors-rooms/rooms/list').catch(() => ({ data: [] })),
          axios.get('http://localhost:8000/api/term-courses/').catch(() => ({ data: [] })),
        ]);

        let historyData = [];
        let prereqData = {};
        try {
          const historyRes = await axios.get('http://localhost:8000/api/teaching-history/');
          historyData = historyRes.data || [];
        } catch (e) {
          console.warn('⚠️ teaching-history API not available, using empty data');
        }

        try {
          const prereqRes = await axios.get('http://localhost:8000/api/prerequisite-map/');
          prereqData = prereqRes.data || {};
        } catch (e) {
          console.warn('⚠️ prerequisite-map API not available, using empty data');
        }

        setTeachingPreferences(teachRes.data || []);
        setTimePreferences(timeRes.data || []);
        setRoomPreferences([]);
        setInstructorsData(instructorsRes.data || []);
        setRoomsData(roomsRes.data || []);
        setCourseHistory(historyData);
        setPrerequisiteMap(prereqData);

        const map = {};
        if (Array.isArray(coursesRes.data)) {
          coursesRes.data.forEach(course => {
            const code = course.unique_course_code || course.course_code || course.code || course.unique_code;
            if (code) {
              map[code] = {
                capacity: course.capacity || course.estimated_capacity || 0,
                units: course.units || 2,
                name: course.course_name || course.name || course.title || code,
              };
            }
          });
        }
        setCourseInfoMap(map);
        console.log('📚 courseInfoMap ساخته شده:', Object.keys(map).length, 'درس');
        console.log('📚 courseHistory دریافت شده:', historyData.length, 'رکورد');
        console.log('📚 prerequisiteMap دریافت شده:', Object.keys(prereqData).length, 'درس');
        setPreferencesLoaded(true);
        fetchDone.current = true;
      } catch (err) {
        console.error('❌ خطا در بارگذاری داده‌ها:', err);
        setPreferencesLoaded(true);
        fetchDone.current = true;
      }
    };

    fetchAllData();
  }, []);

  // ============================
  // همگام‌سازی props
  // ============================
  useEffect(() => {
    if (propTeachingPreferences.length > 0) setTeachingPreferences(propTeachingPreferences);
    if (propTimePreferences.length > 0) setTimePreferences(propTimePreferences);
    if (propRoomPreferences.length > 0) setRoomPreferences(propRoomPreferences);
    if (propInstructorsData.length > 0) setInstructorsData(propInstructorsData);
    if (propRoomsData.length > 0) setRoomsData(propRoomsData);
  }, [propTeachingPreferences, propTimePreferences, propRoomPreferences, propInstructorsData, propRoomsData]);

  // ============================
  // ترم غالب
  // ============================
  const dominantTerm = useMemo(() => {
    if (!data || data.length === 0) return 'semester_1';
    const termCounts = {};
    data.forEach((cls) => {
      const t = cls.term || 'semester_1';
      termCounts[t] = (termCounts[t] || 0) + 1;
    });
    let maxCount = 0;
    let maxTerm = 'semester_1';
    Object.entries(termCounts).forEach(([term, count]) => {
      if (count > maxCount) {
        maxCount = count;
        maxTerm = term;
      }
    });
    console.log(`📊 [dominantTerm] ترم غالب: ${maxTerm} (${maxCount} کلاس از ${data.length})`);
    console.log(`📊 [dominantTerm] توزیع ترم‌ها:`, termCounts);
    return maxTerm;
  }, [data]);

  // ============================
  // بارگذاری داده از سرور
  // ============================
  const loadDataFromServer = useCallback(async (basketIdToUse, workflowIdToUse) => {
    if (!basketIdToUse && !workflowIdToUse) {
      setError('شناسه سبد یا workflow موجود نیست. لطفاً از صفحه مدیریت سبدها شروع کنید.');
      return;
    }

    if (!preferencesLoaded) {
      await new Promise((resolve) => {
        const check = () => {
          if (preferencesLoaded) {
            resolve();
          } else {
            setTimeout(check, 100);
          }
        };
        check();
      });
    }

    setIsLoadingData(true);
    setError(null);
    try {
      let url = '';
      if (basketIdToUse) {
        url = `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketIdToUse}`;
      } else if (workflowIdToUse) {
        url = `http://localhost:8000/api/schedule/workflow/${workflowIdToUse}/scheduled-classes`;
      } else {
        throw new Error('شناسه معتبری برای بارگذاری وجود ندارد.');
      }

      const response = await axios.get(url);
      const result = response.data;

      let defaultTerm = 'semester_1';
      if (result.term) {
        defaultTerm = normalizeSemester(result.term);
      } else if (result.semester) {
        defaultTerm = normalizeSemester(result.semester);
      } else if (basketIdToUse) {
        try {
          const basketRes = await axios.get(`http://localhost:8000/api/baskets/${basketIdToUse}`);
          if (basketRes.data && basketRes.data.semester) {
            defaultTerm = normalizeSemester(basketRes.data.semester);
          }
        } catch (e) { /* ignore */ }
      }

      console.log(`📊 [loadData] defaultTerm: ${defaultTerm}`);

      let classes = [];
      if (result.classes && result.classes.length > 0) {
        classes = result.classes.map((cls) => normalizeClassRecord(cls, courseInfoMap, roomsData, instructorsData, defaultTerm));
      }

      if (classes.length === 0) {
        setError('هیچ کلاس تخصیص‌یافته‌ای با اتاق پیدا نشد. لطفاً ابتدا تخصیص اتاق را انجام دهید.');
        setData([]);
        return;
      }

      console.log(`📊 [loadData] ${classes.length} کلاس از سرور دریافت شد`);

      const termStats = {};
      classes.forEach(cls => {
        const term = cls.term || defaultTerm;
        termStats[term] = (termStats[term] || 0) + 1;
        console.log(`   📝 کلاس ${cls.course_name} (id: ${cls.id}): term=${cls.term}, start=${cls.start}, end=${cls.end}, key=${cls.start}-${cls.end}`);
      });
      console.log(`📊 [loadData] توزیع ترم کلاس‌ها:`, termStats);

      const withUtility = classes.map((cls) => ({
        ...cls,
        utility: cls.utility ?? calculateUtility(
          cls,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
        utilityDetails: calculateUtilityDetails(
          cls,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
      }));

      appliedCourseInfoMapRef.current = {};
      setData(withUtility);
      dataLoadedFromServer.current = true;

      if (result.scenario_id) {
        setWorkflowId(result.scenario_id);
        localStorage.setItem('lastWorkflowId', String(result.scenario_id));
      }
      if (basketIdToUse) {
        localStorage.setItem('lastBasketId', String(basketIdToUse));
      }
    } catch (err) {
      console.error('خطا در بارگذاری داده از سرور:', err);
      if (err.response?.status === 404) {
        setError('زمان‌بندی یا تخصیص اتاق برای این سبد یافت نشد. لطفاً ابتدا مراحل قبلی را کامل کنید.');
      } else {
        setError('خطا در بارگذاری داده: ' + (err.response?.data?.detail || err.message));
      }
      setData([]);
    } finally {
      setIsLoadingData(false);
    }
  }, [preferencesLoaded, courseInfoMap, roomsData, instructorsData, teachingPreferences, timePreferences, roomPreferences, courseHistory, prerequisiteMap]);

  // ============================
  // بازنرمال‌سازی داده‌ها
  // ============================
  useEffect(() => {
    if (data.length === 0) return;
    if (Object.keys(courseInfoMap).length === 0) return;

    const currentMapKeys = Object.keys(courseInfoMap).sort().join(',');
    const appliedKeys = Object.keys(appliedCourseInfoMapRef.current).sort().join(',');
    if (currentMapKeys === appliedKeys) {
      return;
    }

    let needsUpdate = false;
    for (const cls of data) {
      const info = courseInfoMap[cls.course_code];
      if (info && (info.units && cls.units !== info.units || info.capacity && cls.course_capacity !== info.capacity)) {
        needsUpdate = true;
        break;
      }
    }

    if (!needsUpdate) {
      appliedCourseInfoMapRef.current = { ...courseInfoMap };
      return;
    }

    const updated = data.map(cls => {
      const norm = normalizeClassRecord(cls, courseInfoMap, roomsData, instructorsData, dominantTerm);
      return {
        ...norm,
        utility: norm.utility ?? calculateUtility(
          norm,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
        utilityDetails: calculateUtilityDetails(
          norm,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
      };
    });
    setData(updated);
    appliedCourseInfoMapRef.current = { ...courseInfoMap };
  }, [courseInfoMap, roomsData, instructorsData, teachingPreferences, timePreferences, roomPreferences, dominantTerm, data, courseHistory, prerequisiteMap]);

  // ============================
  // بارگذاری اولیه
  // ============================
  useEffect(() => {
    if (hasLoaded.current) return;
    if (data && data.length > 0) return;
    if (!preferencesLoaded) return;

    const effectiveBasketId = basketId || localStorage.getItem('lastBasketId');
    const effectiveWorkflowId = workflowId || localStorage.getItem('lastWorkflowId');

    if (effectiveBasketId || effectiveWorkflowId) {
      loadDataFromServer(effectiveBasketId, effectiveWorkflowId);
      hasLoaded.current = true;
    } else {
      setError('شناسه سبد یا workflow موجود نیست. لطفاً از صفحه مدیریت سبدها شروع کنید.');
    }
  }, [basketId, workflowId, preferencesLoaded, loadDataFromServer, data.length]);

  // ============================
  // استفاده از roomAllocationData
  // ============================
  useEffect(() => {
    if (dataLoadedFromServer.current) return;
    if (!roomAllocationData || roomAllocationData.length === 0) return;
    if (!preferencesLoaded) return;

    const normalized = roomAllocationData.map((cls) => {
      const norm = normalizeClassRecord(cls, courseInfoMap, roomsData, instructorsData, dominantTerm);
      return {
        ...norm,
        utility: norm.utility ?? calculateUtility(
          norm,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
        utilityDetails: calculateUtilityDetails(
          norm,
          teachingPreferences,
          timePreferences,
          roomPreferences,
          instructorsData,
          courseInfoMap,
          courseHistory,
          prerequisiteMap
        ),
      };
    });
    setData(normalized);
    hasLoaded.current = true;
  }, [roomAllocationData, courseInfoMap, roomsData, instructorsData, teachingPreferences, timePreferences, roomPreferences, preferencesLoaded, dataLoadedFromServer.current, dominantTerm, courseHistory, prerequisiteMap]);

  // ============================
  // optimizedData هم‌زمان‌سازی
  // ============================
  useEffect(() => {
    if (propOptimizedData && propOptimizedData.length > 0) {
      const normalized = propOptimizedData.map((cls) => {
        const norm = normalizeClassRecord(cls, courseInfoMap, roomsData, instructorsData, dominantTerm);
        return {
          ...norm,
          utility: norm.utility ?? calculateUtility(
            norm,
            teachingPreferences,
            timePreferences,
            roomPreferences,
            instructorsData,
            courseInfoMap,
            courseHistory,
            prerequisiteMap
          ),
          utilityDetails: calculateUtilityDetails(
            norm,
            teachingPreferences,
            timePreferences,
            roomPreferences,
            instructorsData,
            courseInfoMap,
            courseHistory,
            prerequisiteMap
          ),
        };
      });
      setOptimizedData(normalized);
    }
  }, [propOptimizedData, courseInfoMap, roomsData, instructorsData, teachingPreferences, timePreferences, roomPreferences, dominantTerm, courseHistory, prerequisiteMap]);

  // ============================
  // توابع اصلی
  // ============================

  const instructorList = useMemo(() => {
    if (instructorsData && instructorsData.length > 0) {
      return instructorsData.map((inst) => ({
        code: inst.code,
        name: inst.name,
      }));
    }
    const unique = new Map();
    data.forEach((cls) => {
      if (cls.instructor_code && cls.instructor_name) {
        unique.set(cls.instructor_code, cls.instructor_name);
      }
    });
    return Array.from(unique.entries()).map(([code, name]) => ({ code, name }));
  }, [data, instructorsData]);

  const roomList = useMemo(() => {
    if (roomsData && roomsData.length > 0) {
      return roomsData.map((r) => ({
        id: Number(r.id),
        name: r.name || r.room_name || `اتاق ${r.id}`,
        capacity: r.capacity || r.room_capacity || 30,
        room_name: r.name || r.room_name || `اتاق ${r.id}`,
        room_capacity: r.capacity || r.room_capacity || 30,
      }));
    }
    const unique = new Map();
    data.forEach((cls) => {
      if (cls.room_id && cls.room_name) {
        const id = typeof cls.room_id === 'string' ? parseInt(cls.room_id, 10) : cls.room_id;
        if (!isNaN(id) && id !== null && id !== undefined) {
          unique.set(id, cls.room_name);
        }
      }
    });
    return Array.from(unique.entries()).map(([id, name]) => ({
      id: Number(id),
      name,
      capacity: 30,
      room_name: name,
      room_capacity: 30
    }));
  }, [data, roomsData]);

  const masterSlotsInstructor = useMemo(() => {
    return getMasterSlots(dominantTerm, filterUnitsInstructor);
  }, [dominantTerm, filterUnitsInstructor]);

  const masterSlotsRoom = useMemo(() => {
    return getMasterSlots(dominantTerm, filterUnitsRoom);
  }, [dominantTerm, filterUnitsRoom]);

  // ============================
  // جستجو و فیلتر
  // ============================
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const filterData = (dataList) => {
    let filtered = dataList;
    if (debouncedSearchTerm) {
      const term = debouncedSearchTerm.toLowerCase();
      filtered = filtered.filter((cls) =>
        [cls.course_name, cls.instructor_name, cls.room_name, cls.instructor_code, cls.room_id, cls.course_code]
          .filter(Boolean)
          .some((field) => field.toString().toLowerCase().includes(term))
      );
    }
    return filtered;
  };

  const filteredData = filterData(data);

  // ============================
  // آماده‌سازی داده‌های جدول
  // ============================
  const tableData = useMemo(() => {
    return prepareTableRows(
      filteredData,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
  }, [filteredData, teachingPreferences, timePreferences, roomPreferences, instructorsData, courseInfoMap, courseHistory, prerequisiteMap]);

  const optimizedTableData = useMemo(() => {
    if (!optimizedData || optimizedData.length === 0) return [];
    return prepareTableRows(
      optimizedData,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
  }, [optimizedData, teachingPreferences, timePreferences, roomPreferences, instructorsData, courseInfoMap, courseHistory, prerequisiteMap]);

  // ============================
  // ستون‌های جدول
  // ============================
  const tableColumns = [
    { key: 'course_name', label: 'درس', render: (row) => <span style={{ fontSize: '0.6rem' }}>{row.course_name || row.course_code}</span> },
    { key: 'instructor_name', label: 'استاد', render: (row) => <span style={{ fontSize: '0.6rem' }}>{row.instructor_name}</span> },
    { key: 'day', label: 'روز', render: (row) => getDayName(row.day) },
    { key: 'start', label: 'شروع' },
    { key: 'end', label: 'پایان' },
    { key: 'room_name', label: 'اتاق' },
    { key: 'teachingScore', label: 'امتیاز تدریس', render: (row) => {
      const color = getScoreColor(row.teachingScore, 'teaching');
      return <span style={{ backgroundColor: color, padding: '2px 6px', borderRadius: '4px', fontWeight: '500' }}>{formatScore(row.teachingScore)}</span>;
    }},
    { key: 'timeDayScore', label: 'امتیاز روز', render: (row) => {
      const color = getScoreColor(row.timeDayScore, 'day');
      return <span style={{ backgroundColor: color, padding: '2px 6px', borderRadius: '4px', fontWeight: '500' }}>{formatScore(row.timeDayScore)}</span>;
    }},
    { key: 'timeSlotScore', label: 'امتیاز زمان', render: (row) => {
      const color = getScoreColor(row.timeSlotScore, 'time');
      return <span style={{ backgroundColor: color, padding: '2px 6px', borderRadius: '4px', fontWeight: '500' }}>{formatScore(row.timeSlotScore)}</span>;
    }},
    { key: 'roomScore', label: 'امتیاز اتاق', render: (row) => {
      const color = getScoreColor(row.roomScore, 'room');
      return <span style={{ backgroundColor: color, padding: '2px 6px', borderRadius: '4px', fontWeight: '500' }}>{formatScore(row.roomScore)}</span>;
    }},
    { key: 'utility', label: 'امتیاز کل', render: (row) => {
      const u = row.utility ?? 0;
      const color = getScoreColor(u, 'total');
      return <span style={{
        backgroundColor: color,
        padding: '4px 10px',
        borderRadius: '6px',
        fontWeight: '800',
        fontSize: '0.9rem',
        border: '2px solid rgba(0,0,0,0.08)',
        display: 'inline-block',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
      }}>{formatScore(u)}</span>;
    }},
  ];

  // ============================
  // توابع ذخیره‌سازی و جابجایی
  // ============================

  const getUtility = (classItem) => {
    if (classItem.utility !== undefined && classItem.utility !== null) return classItem.utility;
    return calculateUtility(
      classItem,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
  };

  const getUtilityDetails = (classItem) => {
    if (classItem.utilityDetails) return classItem.utilityDetails;
    return calculateUtilityDetails(
      classItem,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
  };

  const getClassColor = (utility) => {
    if (utility === null || utility === undefined || !Number.isFinite(utility)) return '#e9ecef';
    if (utility >= 20) return '#d4edda';
    if (utility >= 10) return '#fff3cd';
    if (utility >= 0) return '#f8d7da';
    return '#f5c6cb';
  };

  const saveClassUpdate = async (classItem) => {
    if (!workflowId && !basketId) {
      console.warn('شناسه workflow یا basket موجود نیست، تغییرات فقط در حافظه ذخیره شد.');
      return;
    }

    const requiredFields = ['id', 'course_name', 'instructor_code', 'day', 'start', 'end'];
    for (const field of requiredFields) {
      if (!classItem[field] && classItem[field] !== 0) {
        throw new Error(`فیلد ${field} برای کلاس ${classItem.id} پر نشده است.`);
      }
    }

    const payload = {
      assignments: [
        {
          id: classItem.id,
          course_name: classItem.course_name || '',
          group_number: classItem.group_number || 1,
          level: classItem.level || 'کارشناسی',
          term: normalizeSemester(classItem.term || 'semester_1'),
          instructor_code: classItem.instructor_code || '',
          day: Number(classItem.day),
          start: classItem.start || '',
          end: classItem.end || '',
          room_id: classItem.room_id ?? null,
        },
      ],
      basket_id: basketId ? Number(basketId) : null,
      workflow_id: workflowId ? Number(workflowId) : null,
    };

    try {
      const response = await axios.post('http://localhost:8000/api/schedule/workflow/schedule/manual', payload);
      if (classItem.room_id) {
        await axios.put(`http://localhost:8000/api/room-allocation/class/${classItem.id}/room`, {
          room_id: classItem.room_id,
        });
      }
      return response;
    } catch (err) {
      console.error('❌ خطا در ذخیره کلاس:', classItem.id, err.response?.data || err.message);
      const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || 'خطای ناشناخته';
      throw new Error(`خطا در ذخیره کلاس ${classItem.course_name}: ${errorMsg}`);
    }
  };

  const handleClassMove = async (classItem, newInstructorCode, newDay, newStart, newEnd, newRoomId) => {
    let newRoomName = null;
    let newRoomCapacity = null;
    if (newRoomId) {
      const foundRoom = roomsData.find(r => String(r.id) === String(newRoomId));
      if (foundRoom) {
        newRoomName = foundRoom.name;
        newRoomCapacity = foundRoom.capacity || 0;
      }
    }

    let newInstructorName = classItem.instructor_name;
    if (newInstructorCode && newInstructorCode !== classItem.instructor_code) {
      const foundInst = instructorsData.find(i => i.code === newInstructorCode);
      if (foundInst) newInstructorName = foundInst.name;
    }

    const updatedClass = {
      ...classItem,
      instructor_code: newInstructorCode !== undefined ? newInstructorCode : classItem.instructor_code,
      instructor_name: newInstructorName,
      day: newDay !== undefined ? Number(newDay) : classItem.day,
      start: newStart !== undefined ? normalizeTime(newStart) : classItem.start,
      end: newEnd !== undefined ? normalizeTime(newEnd) : classItem.end,
      room_id: newRoomId !== undefined ? newRoomId : classItem.room_id,
      room_name: newRoomName !== null ? newRoomName : classItem.room_name,
      room_capacity: newRoomCapacity !== null ? newRoomCapacity : classItem.room_capacity,
      capacity: newRoomCapacity !== null ? newRoomCapacity : classItem.capacity,
      course_capacity: classItem.course_capacity,
    };

    const newUtility = calculateUtility(
      updatedClass,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );
    updatedClass.utility = newUtility;
    updatedClass.utilityDetails = calculateUtilityDetails(
      updatedClass,
      teachingPreferences,
      timePreferences,
      roomPreferences,
      instructorsData,
      courseInfoMap,
      courseHistory,
      prerequisiteMap
    );

    const newData = data.map((cls) => (String(cls.id) === String(classItem.id) ? updatedClass : cls));
    setData(newData);

    setChangeLog((prev) => [
      ...prev,
      {
        id: classItem.id,
        course_name: classItem.course_name,
        oldUtility: classItem.utility,
        newUtility: newUtility,
        diff: newUtility - (classItem.utility ?? 0),
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);

    try {
      await saveClassUpdate(updatedClass);
      setSuccessMessage(`✅ کلاس ${classItem.course_name} با موفقیت ذخیره شد.`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleClassEdit = (classItem) => {
    alert(
      `ویرایش کلاس: ${classItem.course_name || classItem.course_code}\n` +
      `استاد: ${classItem.instructor_name || classItem.instructor_code}\n` +
      `روز: ${getDayName(classItem.day)}\n` +
      `زمان: ${classItem.start} - ${classItem.end}\n` +
      `اتاق: ${classItem.room_name || 'بدون اتاق'}\n` +
      `ظرفیت درس: ${classItem.course_capacity || '?'}\n` +
      `امتیاز مطلوبیت: ${classItem.utility ?? 'نامشخص'}`
    );
  };

  const handleOptimize = () => {
    if (typeof onProcess === 'function') {
      onProcess(data);
    } else {
      alert('تابع بهینه‌سازی تعریف نشده است.');
    }
  };

  const renderChangeLog = () => {
    if (changeLog.length === 0) return null;
    return (
      <div className="change-log" style={{ marginTop: '1rem', padding: '0.5rem', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px solid #dee2e6' }}>
        <h5>📝 تغییرات اخیر</h5>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {changeLog.slice(-5).map((log, idx) => (
            <li key={idx} style={{ padding: '4px 0', borderBottom: '1px solid #eee', fontSize: '0.9rem' }}>
              <span>{log.course_name}</span>
              <span style={{ margin: '0 10px', color: '#666' }}>
                امتیاز: {log.oldUtility ?? '?'} → {log.newUtility ?? '?'}
              </span>
              <span style={{ color: log.diff >= 0 ? 'green' : 'red', fontWeight: 'bold' }}>
                {log.diff >= 0 ? '▲' : '▼'} {Math.abs(log.diff).toFixed(1)}
              </span>
              <span style={{ marginLeft: '10px', fontSize: '0.8rem', color: '#999' }}>{log.timestamp}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  // ============================
  // رندر
  // ============================

  if (isLoadingData || !preferencesLoaded) {
    return (
      <div className="process-page optimization-page">
        <div className="process-header">
          <div className="process-title">
            <span className="process-icon">⚡</span>
            <h2>بهینه‌سازی برنامه</h2>
          </div>
          <p className="process-description">در حال بارگذاری داده‌های مورد نیاز...</p>
        </div>
        <div className="process-body">
          <div className="loading-state" style={{ padding: '40px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '16px' }}>⏳</div>
            <p>در حال بارگذاری برنامه زمان‌بندی و ترجیحات...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="process-page optimization-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">⚡</span>
          <h2>بهینه‌سازی برنامه</h2>
        </div>
        <p className="process-description">
          بهبود کیفیت برنامه با کاهش زمان‌های نامطلوب، تعادل روزها و استفاده بهتر از اتاق‌ها.
          هر کلاس دارای امتیاز مطلوبیت بر اساس ترجیحات استاد است.
          با کشیدن کلاس‌ها به سلول‌های دیگر، می‌توانید برنامه را بهینه کنید.
          تغییرات با رنگ‌بندی نشان داده می‌شوند: سبز (بهبود)، زرد (متوسط)، قرمز (کاهش).
        </p>
      </div>

      <div className="process-body">
        {/* نوار ابزار */}
        <div className="controls-bar" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={handleOptimize}
            disabled={!data || data.length === 0 || loading || isLoadingData}
            className="btn-process"
          >
            {loading ? 'در حال بهینه‌سازی...' : '⚡ بهینه‌سازی خودکار'}
          </button>
          {(optimizedData || changeLog.length > 0) && (
            <button onClick={() => { setOptimizedData(null); setChangeLog([]); if (onClear) onClear(); }} className="btn-clear">
              پاک کردن نتایج
            </button>
          )}
          <button
            onClick={async () => {
              setIsSaving(true);
              try {
                await Promise.all(data.map((cls) => saveClassUpdate(cls)));
                alert('✅ همه تغییرات با موفقیت ذخیره شد.');
                setChangeLog([]);
              } catch (err) {
                setError('خطا در ذخیره تغییرات: ' + err.message);
              } finally {
                setIsSaving(false);
              }
            }}
            disabled={isSaving || changeLog.length === 0}
            className="btn-save"
            style={{
              backgroundColor: '#28a745',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            {isSaving ? 'در حال ذخیره...' : '💾 ذخیره تغییرات'}
          </button>
          {onNext && (
            <button onClick={() => onNext(workflowId)} className="btn-primary">
              مرحله بعد: اتمام
            </button>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '6px' }}>
            <button
              className={`view-tab ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                backgroundColor: viewMode === 'table' ? '#4A90D9' : 'transparent',
                color: viewMode === 'table' ? '#fff' : '#333',
                cursor: 'pointer',
              }}
            >
              📋 جدول
            </button>
            <button
              className={`view-tab ${viewMode === 'instructorMatrix' ? 'active' : ''}`}
              onClick={() => setViewMode('instructorMatrix')}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                backgroundColor: viewMode === 'instructorMatrix' ? '#4A90D9' : 'transparent',
                color: viewMode === 'instructorMatrix' ? '#fff' : '#333',
                cursor: 'pointer',
              }}
            >
              👨‍🏫 ماتریس استاد
            </button>
            <button
              className={`view-tab ${viewMode === 'roomMatrix' ? 'active' : ''}`}
              onClick={() => setViewMode('roomMatrix')}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                backgroundColor: viewMode === 'roomMatrix' ? '#4A90D9' : 'transparent',
                color: viewMode === 'roomMatrix' ? '#fff' : '#333',
                cursor: 'pointer',
              }}
            >
              🏢 ماتریس اتاق
            </button>
            <button
              className={`view-tab ${viewMode === 'calendar' ? 'active' : ''}`}
              onClick={() => setViewMode('calendar')}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                backgroundColor: viewMode === 'calendar' ? '#4A90D9' : 'transparent',
                color: viewMode === 'calendar' ? '#fff' : '#333',
                cursor: 'pointer',
              }}
            >
              📅 تقویم
            </button>
          </div>
        </div>

        {/* پیام موفقیت */}
        {successMessage && (
          <div style={{ marginTop: '12px', padding: '10px 16px', backgroundColor: '#d4edda', color: '#155724', borderRadius: '6px', border: '1px solid #c3e6cb' }}>
            {successMessage}
          </div>
        )}

        {/* جستجو */}
        <div className="table-search" style={{ marginTop: '12px' }}>
          <input
            type="text"
            placeholder="🔍 جستجو در برنامه..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
            style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #ccc', width: '300px' }}
          />
          {searchTerm && (
            <button className="search-clear" onClick={() => { setSearchTerm(''); setDebouncedSearchTerm(''); }} style={{ marginLeft: '8px' }}>
              ✖
            </button>
          )}
        </div>

        {/* خطا */}
        {error && (
          <div className="error-message" style={{ color: '#721c24', marginTop: '12px', backgroundColor: '#f8d7da', padding: '12px', borderRadius: '6px', border: '1px solid #f5c6cb' }}>
            ⚠️ {error}
            {(error.includes('شناسه') || error.includes('وجود ندارد') || error.includes('یافت نشد')) && (
              <button
                onClick={() => {
                  const storedBasketId = localStorage.getItem('lastBasketId');
                  const storedWorkflowId = localStorage.getItem('lastWorkflowId');
                  if (storedBasketId || storedWorkflowId) {
                    loadDataFromServer(storedBasketId, storedWorkflowId);
                  } else {
                    alert('لطفاً ابتدا از صفحه مدیریت سبدها، یک سبد را انتخاب کنید.');
                  }
                }}
                style={{ marginLeft: '12px', padding: '4px 12px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              >
                🔄 تلاش مجدد
              </button>
            )}
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: '12px', padding: '4px 12px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              ✖ بستن
            </button>
          </div>
        )}

        {/* نمایش داده‌ها */}
        {data && data.length > 0 ? (
          <div className="result-container" style={{ marginTop: '20px' }}>
            {viewMode === 'table' && (
              <>
                <EditableDataTable
                  data={tableData}
                  columns={tableColumns}
                  title="برنامه زمان‌بندی با امتیاز مطلوبیت (جزئیات)"
                  editable={false}
                />
                <div className="legend" style={{ marginTop: '8px', display: 'flex', gap: '20px', fontSize: '0.85rem', flexWrap: 'wrap' }}>
                  <span><span style={{ display: 'inline-block', width: '16px', height: '16px', backgroundColor: '#d4edda', marginRight: '4px', borderRadius: '3px' }}></span> امتیاز سقف (عالی)</span>
                  <span><span style={{ display: 'inline-block', width: '16px', height: '16px', backgroundColor: '#cfe2ff', marginRight: '4px', borderRadius: '3px' }}></span> امتیاز متوسط</span>
                  <span><span style={{ display: 'inline-block', width: '16px', height: '16px', backgroundColor: '#fff3cd', marginRight: '4px', borderRadius: '3px' }}></span> امتیاز کم (1-2)</span>
                  <span><span style={{ display: 'inline-block', width: '16px', height: '16px', backgroundColor: '#f8d7da', marginRight: '4px', borderRadius: '3px' }}></span> امتیاز صفر</span>
                </div>
                <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#666' }}>
                  <strong>توضیح امتیازها:</strong>
                  امتیاز تدریس (بر اساس اولویت استاد برای تدریس این درس) +
                  امتیاز روز (اگر روز مورد نظر در ترجیحات باشد، ۶ امتیاز) +
                  امتیاز زمان (تطابق کامل: ۶، تداخل جزئی: ۴، فاصله کمتر از ۲ ساعت: ۲) +
                  امتیاز اتاق (نسبت ظرفیت: &gt;1: -2، 0.9-1: 6، 0.7-0.9: 3، &lt;0.7: 1)
                </div>

                {/* بخش آمار جدول */}
                <TableStatistics data={tableData} title="آمار کلاس‌های برنامه" />
              </>
            )}

            {viewMode === 'instructorMatrix' && (
              <>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '12px', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <label htmlFor="instructorSelect" style={{ fontWeight: 'bold' }}>انتخاب استاد:</label>
                    <select
                      id="instructorSelect"
                      value={selectedInstructor}
                      onChange={(e) => setSelectedInstructor(e.target.value)}
                      style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #ccc' }}
                    >
                      <option value="">-- انتخاب کنید --</option>
                      {instructorList.map((inst) => (
                        <option key={inst.code} value={inst.code}>
                          {inst.name} ({inst.code})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <InstructorTimeMatrix
                  data={filteredData}
                  instructors={instructorList}
                  masterSlots={masterSlotsInstructor}
                  dayNames={dayNames}
                  onClassMove={handleClassMove}
                  onClassEdit={handleClassEdit}
                  getUtility={getUtility}
                  getClassColor={getClassColor}
                  selectedInstructor={selectedInstructor}
                  teachingPreferences={teachingPreferences}
                  timePreferences={timePreferences}
                  roomPreferences={roomPreferences}
                  instructorsData={instructorsData}
                  roomsData={roomsData}
                  allData={data}
                  filterUnits={filterUnitsInstructor}
                  onFilterChange={setFilterUnitsInstructor}
                  courseInfoMap={courseInfoMap}
                  dominantTerm={dominantTerm}
                />
              </>
            )}

            {viewMode === 'roomMatrix' && (
              <>
                <div className="day-selector" style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                  {dayNames.map((name, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedDay(idx)}
                      style={{
                        padding: '6px 14px',
                        borderRadius: '4px',
                        border: '1px solid #ccc',
                        cursor: 'pointer',
                        backgroundColor: selectedDay === idx ? '#4A90D9' : '#f0f0f0',
                        color: selectedDay === idx ? '#fff' : '#333',
                        fontWeight: selectedDay === idx ? 'bold' : 'normal',
                      }}
                    >
                      {name}
                    </button>
                  ))}
                </div>
                <RoomTimeMatrix
                  data={data}
                  rooms={roomList}
                  masterSlots={masterSlotsRoom}
                  dayNames={dayNames}
                  selectedDay={selectedDay}
                  onClassMove={handleClassMove}
                  onClassEdit={handleClassEdit}
                  getUtility={getUtility}
                  getClassColor={getClassColor}
                  filterUnits={filterUnitsRoom}
                  onFilterChange={setFilterUnitsRoom}
                  allData={data}
                  teachingPreferences={teachingPreferences}
                  timePreferences={timePreferences}
                  roomPreferences={roomPreferences}
                  instructorsData={instructorsData}
                  courseInfoMap={courseInfoMap}
                  roomsData={roomsData}
                  dominantTerm={dominantTerm}
                />
              </>
            )}

            {viewMode === 'calendar' && (
              <>
                <div className="calendar-view" style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px' }}>
                  {dayNames.map((day, idx) => (
                    <div key={idx} style={{ border: '1px solid #ccc', borderRadius: '6px', padding: '8px', backgroundColor: '#f9f9f9' }}>
                      <h5 style={{ textAlign: 'center', margin: '0 0 8px 0' }}>{day}</h5>
                      {filteredData
                        .filter((cls) => cls.day === idx)
                        .sort((a, b) => a.start.localeCompare(b.start))
                        .map((cls) => {
                          const utility = getUtility(cls);
                          const color = getClassColor(utility);
                          return (
                            <div
                              key={cls.id}
                              style={{
                                backgroundColor: color,
                                padding: '4px 8px',
                                marginBottom: '4px',
                                borderRadius: '4px',
                                fontSize: '0.8rem',
                                cursor: 'pointer',
                                border: '1px solid #ddd',
                              }}
                              onClick={() => handleClassEdit(cls)}
                              draggable
                              onDragStart={(e) => e.dataTransfer.setData('text/plain', String(cls.id))}
                            >
                              <div>{cls.course_name || cls.course_code}</div>
                              <div style={{ fontSize: '0.7rem', color: '#555' }}>
                                {cls.start}-{cls.end} | {cls.room_name || 'بدون اتاق'}
                              </div>
                              <div style={{ fontSize: '0.7rem', fontWeight: 'bold' }}>امتیاز: {formatScore(utility)}</div>
                            </div>
                          );
                        })}
                      {filteredData.filter((cls) => cls.day === idx).length === 0 && (
                        <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>—</div>
                      )}
                    </div>
                  ))}
                </div>

                {/* بخش آمار تقویم */}
                <CalendarStatistics data={filteredData} dayNames={dayNames} />
              </>
            )}

            {renderChangeLog()}

            <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
              <button
                onClick={async () => {
                  setIsSaving(true);
                  try {
                    await Promise.all(data.map((cls) => saveClassUpdate(cls)));
                    alert('✅ همه تغییرات با موفقیت ذخیره شد.');
                    setChangeLog([]);
                  } catch (err) {
                    setError('خطا در ذخیره تغییرات: ' + err.message);
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving || changeLog.length === 0}
                className="btn-save"
                style={{
                  backgroundColor: '#28a745',
                  color: 'white',
                  padding: '10px 24px',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                }}
              >
                {isSaving ? 'در حال ذخیره...' : '💾 ذخیره همه تغییرات'}
              </button>
              {onNext && (
                <button onClick={() => onNext(workflowId)} className="btn-primary" style={{ padding: '10px 24px' }}>
                  🏁 تکمیل و پایان
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="info-box info-warning" style={{ marginTop: '20px', padding: '20px', backgroundColor: '#fff3cd', borderRadius: '8px', border: '1px solid #ffc107' }}>
            <span className="info-icon" style={{ fontSize: '1.5rem' }}>⚠️</span>
            <p style={{ marginTop: '8px' }}>
              <strong>هیچ داده‌ای برای بهینه‌سازی وجود ندارد.</strong>
              <br />
              این مشکل ممکن است به دلایل زیر رخ داده باشد:
              <br />
              • تخصیص اتاق انجام نشده است. لطفاً ابتدا مرحله تخصیص اتاق را کامل کنید.
              <br />
              • داده‌های تخصیص اتاق به درستی به این صفحه منتقل شده است.
              <br />
              • شناسه سبد یا workflow معتبر نیست.
              <br />
              <button
                onClick={() => {
                  const storedBasketId = localStorage.getItem('lastBasketId');
                  const storedWorkflowId = localStorage.getItem('lastWorkflowId');
                  if (storedBasketId || storedWorkflowId) {
                    loadDataFromServer(storedBasketId, storedWorkflowId);
                  } else {
                    alert('لطفاً ابتدا از صفحه مدیریت سبدها، یک سبد را انتخاب کنید.');
                  }
                }}
                style={{ marginTop: '12px', padding: '6px 18px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              >
                🔄 تلاش برای بارگذاری مجدد
              </button>
            </p>
          </div>
        )}

        {optimizedData && optimizedData.length > 0 && (
          <div style={{ marginTop: '30px', borderTop: '2px solid #4A90D9', paddingTop: '20px' }}>
            <h4>✅ نتیجه بهینه‌سازی خودکار</h4>
            <EditableDataTable
              data={optimizedTableData}
              columns={tableColumns}
              title="برنامه بهینه‌سازی‌شده"
              editable={false}
            />
            <div className="result-success" style={{ backgroundColor: '#d4edda', padding: '10px', borderRadius: '6px', marginTop: '12px' }}>
              <p style={{ margin: 0 }}>✅ برنامه با موفقیت بهینه‌سازی شد. می‌توانید تغییرات را بررسی و در صورت نیاز ویرایش کنید.</p>
            </div>

            {/* بخش آمار جدول بهینه‌سازی‌شده */}
            <TableStatistics data={optimizedTableData} title="آمار برنامه بهینه‌سازی‌شده" />
          </div>
        )}
      </div>
    </div>
  );
}