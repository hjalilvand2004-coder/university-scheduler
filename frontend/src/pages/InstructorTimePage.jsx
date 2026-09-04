// frontend/src/pages/InstructorTimePage.jsx
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import axios from "axios";
import EditableDataTable from "../components/EditableDataTable";
import TestReportModal from "../components/TestReportModal";
import { processSchedule } from "../api/workflowApi";
import "./InstructorTimePage.css";

// ============================
// کامپوننت‌های فرعی و توابع کمکی
// ============================
import {
  StepsDisplay,
  renderManualModal,
  renderEditModal,
  renderInstructorInfo,
  renderCourseInfo,
  renderConflictsView,
  renderReasonsView,
  renderMatrixView,
  renderChartView,
  renderCalendarView,
  renderFrequency,
  renderCustomTable,
  getValidSlots as getValidSlotsOriginal,
  normalizeTimeSlot,
  getDayName,
  getMatchStatus,
  getCellColorStatus,
  timeToMinutes,
  isTimeSlotMatchWithTolerance,
  saveUnassignedToStorage,
  loadUnassignedFromStorage,
  removeUnassignedFromStorage,
  InstructorWeeklyMatrix,
} from "./InstructorTimeComponents";

// ============================
// تابع کمکی برای دریافت اسلات‌های معتبر از API (با کش)
// ============================
const slotsCache = new Map();

async function fetchValidSlots(term, units) {
  if (!term) term = "semester_1";
  const key = `${term}_${units}`;
  if (slotsCache.has(key)) {
    return slotsCache.get(key);
  }
  try {
    const response = await axios.get("http://localhost:8000/slot-times/search", {
      params: { term, units }
    });
    const slots = response.data.slots || [];
    // ذخیره به صورت رشته‌های کامل (مثلاً "07:30-09:15") برای سازگاری
    const slotPairs = slots.map(s => `${s.start}-${s.end}`);
    slotsCache.set(key, slotPairs);
    return slotPairs;
  } catch (error) {
    console.error(`خطا در دریافت اسلات‌های ${units} واحدی برای ترم ${term}:`, error);
    return getValidSlotsOriginal(units);
  }
}

// ============================
// تابع نرمال‌سازی زمان با استفاده از کش اسلات‌های جاری
// ============================
function normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, defaultTerm) {
  if (!item) return item;
  const units = item.units || (item.unique_code && unitsLookup[item.unique_code]) || 2;

  // اگر زمان شروع و پایان موجود باشد، آنها را بدون تغییر نگه می‌داریم
  if (item.start && item.end) {
    // فقط واحد را به‌روز می‌کنیم
    return { ...item, units };
  }

  // در غیر این صورت، از اسلات پیش‌فرض معتبر استفاده می‌کنیم
  const validSlots = getValidSlotsSync(units, validSlotsMap);
  const defaultSlot = validSlots[0] || "07:30-09:15";
  const [start, end] = defaultSlot.split('-');
  return { ...item, start, end, units };
}

// ============================
// تابع همگام برای دریافت اسلات‌ها از کش (با fallback)
// ============================
function getValidSlotsSync(units, validSlotsMap) {
  const slots = validSlotsMap?.[units];
  if (slots && slots.length > 0) {
    return slots; // حالا این آرایه‌ای از رشته‌هاست
  }
  return getValidSlotsOriginal(units);
}

// ============================
// کامپوننت اصلی
// ============================
export default function InstructorTimePage({
  basketData,
  basketId,
  instructorTimeData,
  onProcess: onProcessParent,
  onClear,
  loading: loadingParent,
  onNext,
  workflowId: propWorkflowId,
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
  const [workflowId, setWorkflowId] = useState(propWorkflowId || null);

  const [isScheduleSaved, setIsScheduleSaved] = useState(false);
  const [scheduleExists, setScheduleExists] = useState(false);
  const [isLoadingExistingSchedule, setIsLoadingExistingSchedule] = useState(false);
  const [existingScheduleLoaded, setExistingScheduleLoaded] = useState(false);

  const [instructorsData, setInstructorsData] = useState([]);
  const [loadingInstructors, setLoadingInstructors] = useState(false);

  const [manualMode, setManualMode] = useState(false);
  const [unassignedList, setUnassignedList] = useState([]);
  const [manualAssignments, setManualAssignments] = useState([]);
  const [isSavingManual, setIsSavingManual] = useState(false);
  const [manualResult, setManualResult] = useState(null);

  const [selectedDay, setSelectedDay] = useState(null);
  const dayNames = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];

  const [showBasket, setShowBasket] = useState(false);
  const [viewMode, setViewMode] = useState("table");
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");

  const [editingMode, setEditingMode] = useState(false);
  const [editedData, setEditedData] = useState([]);
  const [isSavingEdits, setIsSavingEdits] = useState(false);

  const [selectedInstructor, setSelectedInstructor] = useState("");
  const [selectedCourseCode, setSelectedCourseCode] = useState("");

  const [steps, setSteps] = useState([]);
  const [showSteps, setShowSteps] = useState(false);
  const [showFrequency, setShowFrequency] = useState(false);

  const [showTestReport, setShowTestReport] = useState(false);
  const [filterStatus, setFilterStatus] = useState(null);

  // ===== state for manual assignment modal (unassigned) =====
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAssignmentIndex, setEditingAssignmentIndex] = useState(null);
  const [modalAssignmentData, setModalAssignmentData] = useState({
    instructor_code: "",
    day: 0,
    start: "",
    end: "",
  });

  // ===== state for edit modal (assigned classes) =====
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingClassIndex, setEditingClassIndex] = useState(null);
  const [editModalData, setEditModalData] = useState({
    id: null,
    course_name: "",
    group_number: 1,
    level: "",
    term: "",
    unique_code: "",
    units: 2,
    instructor_code: "",
    day: 0,
    start: "07:30",
    end: "09:15",
  });

  // ===== force update for stats =====
  const [updateCounter, setUpdateCounter] = useState(0);

  // ===== کش اسلات‌های معتبر بر اساس ترم و واحد =====
  const [validSlotsMap, setValidSlotsMap] = useState({});

  const loadingBasketRef = useRef(false);
  const hasLoadedBasket = useRef(false);
  const hasFetchedInstructors = useRef(false);
  const hasSetDefaultCourse = useRef(false);
  const hasSetDefaultInstructor = useRef(false);
  const hasLoadedExistingSchedule = useRef(false);

  // ===== ref برای جلوگیری از حلقه بی‌نهایت در useEffect manualAssignments =====
  const prevInstructorTimeDataRef = useRef(null);

  // ============================
  // تابع دریافت اسلات‌های معتبر با کش (محلی) – async
  // ============================
  const getValidSlotsForTerm = useCallback(async (units) => {
    const term = basketMeta.semester || "semester_1";
    return await fetchValidSlots(term, units);
  }, [basketMeta.semester]);

  // ============================
  // پر کردن کش اسلات‌ها برای تمام واحدها بر اساس ترم جاری
  // ============================
  useEffect(() => {
    const loadAllSlots = async () => {
      const term = basketMeta.semester || "semester_1";
      const unitsList = [1, 2, 3, 4];
      const newMap = {};
      for (const units of unitsList) {
        newMap[units] = await fetchValidSlots(term, units);
      }
      setValidSlotsMap(newMap);
    };
    loadAllSlots();
  }, [basketMeta.semester]); // وابسته به ترم

  // ============================
  // تابع همگام برای دریافت اسلات‌ها از کش (با fallback) – برای استفاده درون کامپوننت
  // ============================
  const getValidSlotsSyncLocal = useCallback((units) => {
    return getValidSlotsSync(units, validSlotsMap);
  }, [validSlotsMap]);

  // ============================
  // واکشی لیست اساتید
  // ============================
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
          setInstructorsData([]);
        }
        hasFetchedInstructors.current = true;
      } catch (err) {
        console.error("[fetchInstructors] خطا:", err);
        setError("خطا در بارگذاری اطلاعات اساتید");
        setInstructorsData([]);
        hasFetchedInstructors.current = true;
      } finally {
        setLoadingInstructors(false);
      }
    };

    fetchInstructors();
  }, [instructorsDataProp]);

  // ============================
  // دبونس جستجو
  // ============================
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // ============================
  // واکشی سبد از دیتابیس
  // ============================
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
            console.warn("[loadBasket] خطا در واکشی متادیتا:", err);
          }
        } else {
          let semester = "semester_1";
          let year = "1403";
          if (basketData.length > 0 && basketData[0].term) {
            const term = basketData[0].term;
            if (term && typeof term === "string") {
              const lower = term.toLowerCase();
              if (lower.includes("semester_2") || lower.includes("بهمن") || lower.includes("bahman")) {
                semester = "semester_2";
              } else if (lower.includes("summer") || lower.includes("تابستان")) {
                semester = "summer";
              }
            }
          }
          setBasketMeta({
            title: "سبد (از props)",
            semester,
            year,
          });
        }
        return;
      }

      if (basketId) {
        loadingBasketRef.current = true;
        setIsLoadingBasket(true);
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
          console.error("[loadBasket] خطا:", err);
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
        try {
          const response = await axios.get(
            `http://localhost:8000/api/schedule/workflow/basket/${workflowId}`
          );
          const data = response.data;
          if (data.basket && data.basket.length > 0) {
            setLocalBasketData(data.basket);
            if (data.basket_meta) setBasketMeta(data.basket_meta);
            else setBasketMeta({ title: "سبد (از workflow)", semester: "", year: "" });
          } else {
            setLocalBasketData(null);
          }
          hasLoadedBasket.current = true;
        } catch (err) {
          console.error("[loadBasket] خطا:", err);
          setError("خطا در بارگذاری سبد از دیتابیس");
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

  // ============================
  // توابع بررسی و بارگذاری برنامه قبلی
  // ============================
  const checkExistingScheduleForBasket = async (basketId) => {
    if (!basketId) return null;
    try {
      const response = await axios.get(
        `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketId}`
      );
      return response.data;
    } catch (err) {
      if (err.response && err.response.status === 404) return null;
      throw err;
    }
  };

  // ============================
  // تابع بارگذاری برنامه قبلی (با استفاده از تابع نرمال‌سازی سفارشی که زمان را حفظ می‌کند)
  // ============================
  const loadExistingScheduleForBasket = async (basketId) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketId}`
      );
      const data = response.data;
      if (data.scenario_id) setWorkflowId(data.scenario_id);

      const apiUnassigned = (data.unassigned || []).map(item => ({
        ...item,
        course_name: item.course_title || item.course_name || '—',
        unique_code: item.course_code || item.unique_code,
        start: item.start_time || item.start || '',
        end: item.end_time || item.end || '',
        day: item.day !== undefined ? parseInt(item.day) : 0,
        units: item.units || 2,
        level: item.level || 'کارشناسی',
        term: item.term || 'semester_1',
        estimated_capacity: item.estimated_capacity || 0,
        group_number: item.group_number ? parseInt(item.group_number) : 1,
      }));

      if (data.total === 0 && data.classes.length === 0 && apiUnassigned.length === 0) {
        removeUnassignedFromStorage(basketId, workflowId);
        setInstructorTimeDataLocal({
          assigned: [],
          unassigned: [],
          all: [],
        });
        setIsScheduleSaved(false);
        setScheduleExists(false);
        setExistingScheduleLoaded(true);
        return false;
      }

      if (apiUnassigned.length > 0) {
        saveUnassignedToStorage(basketId, workflowId, apiUnassigned);
      } else {
        removeUnassignedFromStorage(basketId, workflowId);
      }

      const unitsLookup = {};
      (effectiveBasketData || []).forEach(item => {
        if (item.unique_code) unitsLookup[item.unique_code] = item.units || 2;
      });

      // نرمال‌سازی کلاس‌ها با استفاده از تابع سفارشی که زمان اصلی را حفظ می‌کند
      const mappedClasses = data.classes.map(cls => {
        const item = {
          ...cls,
          course_name: cls.course_title || cls.course_name || cls.course_code,
          unique_code: cls.course_code,
          group_number: cls.group_number || 1,
          instructor_name: cls.instructor_name,
          instructor_code: cls.instructor_code,
          day: cls.day,
          start: cls.start_time,
          end: cls.end_time,
          units: cls.units || 2,
          level: cls.level || 'کارشناسی',
          term: cls.term || 'semester_1',
          estimated_capacity: cls.room_capacity || 0,
          match_status: cls.match_status || null,
        };
        return normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1');
      });

      const assignedItems = [];
      const unassignedItemsFromClasses = [];
      mappedClasses.forEach(item => {
        if (item.instructor_code) assignedItems.push(item);
        else unassignedItemsFromClasses.push(item);
      });

      const combinedUnassigned = [...unassignedItemsFromClasses, ...apiUnassigned];
      const uniqueCombined = [];
      const seenCombined = new Set();
      combinedUnassigned.forEach(item => {
        const key = `${item.unique_code || item.course_code}_${item.group_number}`;
        if (!seenCombined.has(key)) {
          seenCombined.add(key);
          uniqueCombined.push(item);
        }
      });

      const allItems = [...assignedItems, ...uniqueCombined];
      setInstructorTimeDataLocal({
        assigned: assignedItems,
        unassigned: uniqueCombined,
        all: allItems,
      });
      setIsScheduleSaved(true);
      setScheduleExists(true);
      setExistingScheduleLoaded(true);
      return true;
    } catch (err) {
      console.error("[loadExistingScheduleForBasket] خطا:", err);
      setError("خطا در بارگذاری برنامه قبلی");
      return false;
    }
  };

  // ============================
  // بارگذاری بر اساس basketId
  // ============================
  useEffect(() => {
    const loadScheduleByBasket = async () => {
      if (!basketId || hasLoadedExistingSchedule.current || isLoadingExistingSchedule) return;
      setIsLoadingExistingSchedule(true);
      setScheduleExists(false);
      setExistingScheduleLoaded(false);
      try {
        const data = await checkExistingScheduleForBasket(basketId);
        if (data && (data.total > 0 || (data.unassigned && data.unassigned.length > 0))) {
          await loadExistingScheduleForBasket(basketId);
        } else {
          removeUnassignedFromStorage(basketId, workflowId);
          setInstructorTimeDataLocal({
            assigned: [],
            unassigned: [],
            all: [],
          });
          setIsScheduleSaved(false);
          setScheduleExists(false);
          setExistingScheduleLoaded(true);
        }
      } catch (err) {
        console.error("[loadScheduleByBasket] خطا:", err);
        setError("خطا در بارگذاری زمان‌بندی قبلی");
        removeUnassignedFromStorage(basketId, workflowId);
        setInstructorTimeDataLocal({
          assigned: [],
          unassigned: [],
          all: [],
        });
        setExistingScheduleLoaded(true);
      } finally {
        setIsLoadingExistingSchedule(false);
        hasLoadedExistingSchedule.current = true;
      }
    };
    loadScheduleByBasket();
  }, [basketId]);

  // ============================
  // بارگذاری بر اساس workflowId
  // ============================
  useEffect(() => {
    if (basketId) return;
    const loadExistingSchedule = async () => {
      if (!workflowId || hasLoadedExistingSchedule.current || isLoadingExistingSchedule) return;
      setIsLoadingExistingSchedule(true);
      try {
        const response = await axios.get(
          `http://localhost:8000/api/schedule/workflow/${workflowId}/scheduled-classes`
        );
        const data = response.data;

        if (data.total === 0 && data.classes.length === 0 && (!data.unassigned || data.unassigned.length === 0)) {
          removeUnassignedFromStorage(basketId, workflowId);
          setInstructorTimeDataLocal({
            assigned: [],
            unassigned: [],
            all: [],
          });
          setIsScheduleSaved(false);
          setScheduleExists(false);
          setExistingScheduleLoaded(true);
          return;
        }

        const storedUnassigned = loadUnassignedFromStorage(basketId, workflowId) || [];
        const apiUnassigned = (data.unassigned || []).map(item => ({
          ...item,
          course_name: item.course_title || item.course_name || '—',
          unique_code: item.course_code || item.unique_code,
          start: item.start_time || item.start || '',
          end: item.end_time || item.end || '',
          day: item.day !== undefined ? parseInt(item.day) : 0,
          units: item.units || 2,
          level: item.level || 'کارشناسی',
          term: item.term || 'semester_1',
          estimated_capacity: item.estimated_capacity || 0,
          group_number: item.group_number ? parseInt(item.group_number) : 1,
        }));

        const allUnassigned = [...apiUnassigned, ...storedUnassigned];
        const uniqueUnassigned = [];
        const seen = new Set();
        allUnassigned.forEach(item => {
          const key = `${item.unique_code || item.course_code}_${item.group_number}`;
          if (!seen.has(key)) {
            seen.add(key);
            if (!item.unique_code && item.course_code) item.unique_code = item.course_code;
            uniqueUnassigned.push(item);
          }
        });

        if (uniqueUnassigned.length > 0) {
          saveUnassignedToStorage(basketId, workflowId, uniqueUnassigned);
        } else {
          removeUnassignedFromStorage(basketId, workflowId);
        }

        if (data.total > 0 && data.classes.length > 0) {
          const unitsLookup = {};
          (effectiveBasketData || []).forEach(item => {
            if (item.unique_code) unitsLookup[item.unique_code] = item.units || 2;
          });

          const mappedClasses = data.classes.map(cls => {
            const item = {
              ...cls,
              course_name: cls.course_title || cls.course_name || cls.course_code,
              unique_code: cls.course_code,
              group_number: cls.group_number || 1,
              instructor_name: cls.instructor_name,
              instructor_code: cls.instructor_code,
              day: cls.day,
              start: cls.start_time,
              end: cls.end_time,
              units: cls.units || 2,
              level: cls.level || 'کارشناسی',
              term: cls.term || 'semester_1',
              estimated_capacity: cls.room_capacity || 0,
              match_status: cls.match_status || null,
            };
            return normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1');
          });

          const assignedItems = [];
          const unassignedItemsFromClasses = [];
          mappedClasses.forEach(item => {
            if (item.instructor_code) assignedItems.push(item);
            else unassignedItemsFromClasses.push(item);
          });

          const combinedUnassigned = [...unassignedItemsFromClasses, ...uniqueUnassigned];
          const uniqueCombined = [];
          const seenCombined = new Set();
          combinedUnassigned.forEach(item => {
            const key = `${item.unique_code || item.course_code}_${item.group_number}`;
            if (!seenCombined.has(key)) {
              seenCombined.add(key);
              uniqueCombined.push(item);
            }
          });

          const allItems = [...assignedItems, ...uniqueCombined];
          setInstructorTimeDataLocal({
            assigned: assignedItems,
            unassigned: uniqueCombined,
            all: allItems,
          });
          setIsScheduleSaved(true);
          setScheduleExists(true);
          setExistingScheduleLoaded(true);
        } else {
          if (uniqueUnassigned.length > 0) {
            setInstructorTimeDataLocal({
              assigned: [],
              unassigned: uniqueUnassigned,
              all: uniqueUnassigned,
            });
            setIsScheduleSaved(true);
            setScheduleExists(true);
            setExistingScheduleLoaded(true);
          } else {
            setScheduleExists(false);
            setExistingScheduleLoaded(true);
          }
        }
      } catch (err) {
        console.error("[loadScheduleByWorkflow] خطا:", err);
        setError("خطا در بارگذاری زمان‌بندی قبلی");
        removeUnassignedFromStorage(basketId, workflowId);
        setInstructorTimeDataLocal({
          assigned: [],
          unassigned: [],
          all: [],
        });
        setExistingScheduleLoaded(true);
      } finally {
        setIsLoadingExistingSchedule(false);
        hasLoadedExistingSchedule.current = true;
      }
    };
    loadExistingSchedule();
  }, [workflowId, basketId]);

  const effectiveBasketData = basketData && basketData.length > 0 ? basketData : localBasketData;

  // ============================
  // ایجاد workflow
  // ============================
  const createWorkflow = async () => {
    try {
      const response = await axios.post("http://localhost:8000/api/schedule/workflow/step1", {
        semester: basketMeta.semester || "semester_1",
        levels: ["کارشناسی"],
        year: basketMeta.year || "1403",
      });
      const newWorkflowId = response.data.workflow_id;
      setWorkflowId(newWorkflowId);
      return newWorkflowId;
    } catch (err) {
      console.error("[createWorkflow] خطا:", err);
      setError("خطا در ایجاد جلسه. لطفاً دوباره تلاش کنید.");
      return null;
    }
  };

  // ============================
  // حذف زمان‌بندی
  // ============================
  const handleDeleteSchedule = async () => {
    if (!workflowId) return;
    const confirmDelete = window.confirm(
      "آیا از حذف زمان‌بندی فعلی مطمئن هستید؟ این کار غیرقابل بازگشت است."
    );
    if (!confirmDelete) return;

    try {
      await axios.delete(`http://localhost:8000/api/schedule/workflow/${workflowId}`);
      removeUnassignedFromStorage(basketId, workflowId);
      setInstructorTimeDataLocal(null);
      setIsScheduleSaved(false);
      setScheduleExists(false);
      setExistingScheduleLoaded(false);
      hasLoadedExistingSchedule.current = false;
      setSteps([]);
      setWorkflowId(null);
      setError(null);
      alert("✅ زمان‌بندی با موفقیت حذف شد.");
    } catch (err) {
      console.error("[handleDeleteSchedule] خطا:", err);
      setError("خطا در حذف زمان‌بندی: " + (err.response?.data?.detail || err.message));
      alert("خطا در حذف زمان‌بندی");
    }
  };

  // ============================
  // اجرای زمان‌بندی
  // ============================
  const handleLocalProcess = async () => {
    console.log("🚀 [handleLocalProcess] شروع شد.");
    console.log("📦 effectiveBasketData:", effectiveBasketData?.length);

    if (isLoadingBasket) {
      setError("در حال بارگذاری سبد، لطفاً صبر کنید...");
      return;
    }
    if (!effectiveBasketData || effectiveBasketData.length === 0) {
      setError("سبد دروس خالی است. لطفاً ابتدا سبد را پر کنید.");
      return;
    }

    let currentWorkflowId = workflowId;
    if (!currentWorkflowId) {
      currentWorkflowId = await createWorkflow();
      if (!currentWorkflowId) return;
    }

    setLoadingLocal(true);
    setError(null);
    setSteps([]);
    setIsScheduleSaved(false);

    try {
      const result = await processSchedule({ basket: effectiveBasketData });
      console.log("📋 نتیجه زمان‌بندی دریافت شد:", result);

      setInstructorTimeDataLocal(result);
      if (typeof onProcessParent === "function") {
        onProcessParent(result);
      }

      if (result && result.steps) setSteps(result.steps);
      else setSteps([]);

      const unassignedData = result.unassigned || [];
      saveUnassignedToStorage(basketId, currentWorkflowId, unassignedData);

      let shouldOverwrite = false;
      if (basketId) {
        const existingData = await checkExistingScheduleForBasket(basketId);
        if (existingData && (existingData.total > 0 || (existingData.unassigned && existingData.unassigned.length > 0))) {
          const userConfirmed = window.confirm(
            `⚠️ قبلاً برای این سبد (${basketId}) برنامه زمان‌بندی ثبت شده است.\n` +
            `آیا می‌خواهید برنامه قبلی را با برنامه جدید جایگزین کنید؟`
          );
          if (!userConfirmed) {
            setError("عملیات ذخیره‌سازی لغو شد. برنامه قبلی نمایش داده می‌شود.");
            await loadExistingScheduleForBasket(basketId);
            setLoadingLocal(false);
            return;
          }
          shouldOverwrite = true;
        }
      }

      console.log("💾 [handleLocalProcess] در حال ذخیره در دیتابیس...");
      const savePayload = {
        classes: (result.assigned || []).map(cls => ({
          ...cls,
          basket_id: basketId,
          instructor_code: cls.instructor_code,
        })),
        unassigned: result.unassigned || [],
        basket_id: basketId,
        workflow_id: currentWorkflowId,
        semester: basketMeta.semester || "semester_1",
        year: basketMeta.year || "1403",
        overwrite: shouldOverwrite,
      };
      await axios.post("http://localhost:8000/api/schedule/workflow/save-schedule", savePayload);
      console.log("✅ [handleLocalProcess] ذخیره با موفقیت انجام شد.");

      setIsScheduleSaved(true);
      setScheduleExists(true);
      setExistingScheduleLoaded(true);
      hasLoadedExistingSchedule.current = true;

      console.log("📌 [handleLocalProcess] stateها تنظیم شدند:", {
        isScheduleSaved: true,
        scheduleExists: true,
      });

      const assignedCount = result.assigned?.length || 0;
      const unassignedCount = result.unassigned?.length || 0;
      alert(`زمان‌بندی انجام شد. ${assignedCount} کلاس تخصیص یافت، ${unassignedCount} کلاس بدون استاد باقی ماند.`);

      setUpdateCounter(prev => prev + 1);
      console.log("✅ [handleLocalProcess] پایان موفق.");
    } catch (err) {
      console.error("❌ [handleLocalProcess] خطا:", err);
      if (err.response && err.response.status === 409) {
        setError("⚠️ برای این سبد قبلاً برنامه ثبت شده است. لطفاً جایگزینی را تأیید کنید.");
        alert("⚠️ برای این سبد قبلاً برنامه ثبت شده است. دوباره تلاش کنید و جایگزینی را تأیید کنید.");
      } else {
        setError(err.message || "خطا در اجرای زمان‌بندی");
        alert("خطا در زمان‌بندی: " + (err.message || "خطای ناشناخته"));
      }
      setIsScheduleSaved(false);
    } finally {
      setLoadingLocal(false);
    }
  };

  // ============================
  // پاک کردن نتایج
  // ============================
  const handleClear = () => {
    if (typeof onClear === "function") onClear();
    setShowBasket(false);
    removeUnassignedFromStorage(basketId, workflowId);
    setInstructorTimeDataLocal(null);
    setSteps([]);
    setIsScheduleSaved(false);
    setScheduleExists(false);
    setExistingScheduleLoaded(false);
    hasLoadedExistingSchedule.current = false;
    setFilterStatus(null);
    setUpdateCounter(prev => prev + 1);
  };

  // ============================
  // state محلی
  // ============================
  const [localInstructorTimeData, setInstructorTimeDataLocal] = useState(null);
  const effectiveInstructorTimeData = localInstructorTimeData || instructorTimeData;

  // ============================
  // استخراج داده‌ها
  // ============================
  const getData = () => {
    if (!effectiveInstructorTimeData) return { assigned: [], unassigned: [], all: [] };
    if (Array.isArray(effectiveInstructorTimeData)) {
      return { assigned: effectiveInstructorTimeData, unassigned: [], all: effectiveInstructorTimeData };
    }
    return {
      assigned: effectiveInstructorTimeData.assigned || [],
      unassigned: effectiveInstructorTimeData.unassigned || [],
      all: effectiveInstructorTimeData.all || [],
    };
  };
  const rawData = getData();
  const { assigned, unassigned, all } = rawData;

  const unitsLookup = useMemo(() => {
    const lookup = {};
    (effectiveBasketData || []).forEach(item => {
      if (item.unique_code) lookup[item.unique_code] = item.units || 2;
    });
    return lookup;
  }, [effectiveBasketData]);

  // ============================
  // نرمال‌سازی داده‌ها با استفاده از تابع سفارشی که زمان اصلی را حفظ می‌کند
  // ============================
  const normalizedAll = useMemo(() => {
    return all.map(item => normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1'));
  }, [all, unitsLookup, validSlotsMap, basketMeta.semester]);

  const normalizedAssigned = useMemo(() => {
    return assigned.map(item => normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1'));
  }, [assigned, unitsLookup, validSlotsMap, basketMeta.semester]);

  const normalizedUnassigned = useMemo(() => {
    return unassigned.map(item => normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1'));
  }, [unassigned, unitsLookup, validSlotsMap, basketMeta.semester]);

  // بقیه قسمت‌های کد بدون تغییر می‌مانند (courseNameLookup, instructorNameLookup, teachingLookup, etc.)
  // ...

  // ============================
  // ادامه کد (همانند قبل از اینجا)
  // ============================
  const courseNameLookup = useMemo(() => {
    const lookup = {};
    (effectiveBasketData || []).forEach(item => {
      if (item.unique_code && item.course_name) lookup[item.unique_code] = item.course_name;
    });
    normalizedAll.forEach(item => {
      if (item.unique_code && item.course_name && !lookup[item.unique_code]) lookup[item.unique_code] = item.course_name;
    });
    return lookup;
  }, [effectiveBasketData, normalizedAll]);

  const instructorNameLookup = useMemo(() => {
    const lookup = {};
    normalizedAll.forEach(item => {
      if (item.instructor_code && item.instructor_name) lookup[item.instructor_code] = item.instructor_name;
    });
    instructorsData.forEach(inst => {
      if (inst.code && inst.name) lookup[inst.code] = inst.name;
    });
    return lookup;
  }, [normalizedAll, instructorsData]);

  const teachingLookup = useMemo(() => {
    const lookup = {};
    teachingPreferences.forEach(pref => {
      const courseCode = pref.unique_course_code;
      const instructorCode = pref.instructor_code;
      if (courseCode && instructorCode) {
        if (!lookup[courseCode]) lookup[courseCode] = new Set();
        lookup[courseCode].add(instructorCode);
      }
    });
    return lookup;
  }, [teachingPreferences]);

  const normalizeDayName = (day) => {
    if (!day) return '';
    let normalized = day.replace(/\u200c/g, ' ').trim().replace(/\s+/g, ' ');
    return normalized.replace(/ /g, '');
  };

  const timeLookup = useMemo(() => {
    const lookup = {};
    const dayMap = {
      "شنبه": 0, "یکشنبه": 1, "دوشنبه": 2, "سه‌شنبه": 3, "سهشنبه": 3, "چهارشنبه": 4, "پنجشنبه": 5,
    };
    timePreferences.forEach(pref => {
      const instructorCode = pref.instructor_code;
      if (!instructorCode) return;
      if (!lookup[instructorCode]) lookup[instructorCode] = [];
      const dayNorm = normalizeDayName(pref.day);
      const dayNum = dayMap[dayNorm];
      if (dayNum === undefined) return;
      let start = pref.start_time, end = pref.end_time;
      if (start === "12:00" && end === "16:00") { start = "13:00"; end = "17:00"; }
      lookup[instructorCode].push({
        day: dayNum,
        start,
        end,
        priority: pref.priority !== undefined ? pref.priority : null,
      });
    });
    for (const inst in lookup) lookup[inst].sort((a, b) => (a.priority || 999) - (b.priority || 999));
    return lookup;
  }, [timePreferences]);

  const getItemStatus = (item) => {
    if (!item.instructor_code || !item.start || !item.end) return 'unassigned';
    if (item.match_status && ['full','partial','none','no_preference','no_assignment'].includes(item.match_status)) {
      return item.match_status;
    }
    return getMatchStatus(item, teachingLookup, timeLookup);
  };

  // ============================
  // آمار تطابق (با useMemo)
  // ============================
  const stats = useMemo(() => {
    const data = normalizedAll;
    if (!data || data.length === 0) {
      return { totalClasses: 0, teachingMatchCount: 0, dayMatchCount: 0, timeMatchCount: 0, bothMatchCount: 0 };
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
        if (preferred && preferred.has(instructorCode)) { teachOk = true; teachingMatch++; }
      }
      let dayOk = false, timeOk = false;
      if (instructorCode && day !== undefined) {
        const preferredSlots = timeLookup[instructorCode];
        if (preferredSlots && preferredSlots.length > 0) {
          if (preferredSlots.some(slot => slot.day === day)) { dayOk = true; dayMatch++; }
          if (start && end) {
            if (preferredSlots.some(slot => slot.day === day && isTimeSlotMatchWithTolerance(start, end, slot.start, slot.end, 60))) {
              timeOk = true; timeMatch++;
            }
          }
        }
      }
      if (teachOk && timeOk) bothMatch++;
    });
    return { totalClasses: data.length, teachingMatchCount: teachingMatch, dayMatchCount: dayMatch, timeMatchCount: timeMatch, bothMatchCount: bothMatch };
  }, [normalizedAll, teachingLookup, timeLookup]);

  // ============================
  // آمار تطابق مستقیم (با useMemo)
  // ============================
  const directMatchStats = useMemo(() => {
    const data = normalizedAll;
    if (!data || data.length === 0) {
      return { full: 0, partial: 0, none: 0, no_preference: 0, no_assignment: 0, unassigned: 0 };
    }
    let full = 0, partial = 0, none = 0, no_preference = 0, no_assignment = 0, unassigned = 0;
    data.forEach(item => {
      const hasInstructor = !!item.instructor_code;
      const hasTime = !!item.start && !!item.end;
      if (!hasInstructor || !hasTime) { unassigned++; return; }
      const status = getItemStatus(item);
      if (status === 'full') full++;
      else if (status === 'partial') partial++;
      else if (status === 'none') none++;
      else if (status === 'no_preference') no_preference++;
      else if (status === 'no_assignment') no_assignment++;
      else unassigned++;
    });
    return { full, partial, none, no_preference, no_assignment, unassigned };
  }, [normalizedAll, teachingLookup, timeLookup, updateCounter]);

  // ============================
  // مقداردهی manualAssignments (رفع حلقه بی‌نهایت)
  // ============================
  useEffect(() => {
    if (!effectiveInstructorTimeData || typeof effectiveInstructorTimeData !== "object") {
      if (manualAssignments.length > 0) {
        setManualAssignments([]);
        setUnassignedList([]);
      }
      return;
    }

    const currentData = effectiveInstructorTimeData.unassigned || [];
    const prevData = prevInstructorTimeDataRef.current;
    if (prevData && JSON.stringify(prevData) === JSON.stringify(currentData)) {
      return;
    }
    prevInstructorTimeDataRef.current = currentData;

    if (currentData.length > 0) {
      const newAssignments = currentData.map((item) => {
        const units = unitsLookup[item.unique_code] || item.units || 2;
        const normalized = normalizeTimeSlotWithCache({ ...item, units }, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1');
        return {
          id: item.id || null,
          course_name: item.course_name || "",
          group_number: item.group_number ? parseInt(item.group_number) : 1,
          level: item.level || "",
          term: item.term || "",
          unique_code: item.unique_code || "",
          units: units,
          instructor_code: "",
          day: item.day !== undefined ? parseInt(item.day) : 0,
          start: normalized.start || "07:30",
          end: normalized.end || "09:15",
        };
      });
      if (JSON.stringify(newAssignments) !== JSON.stringify(manualAssignments)) {
        setManualAssignments(newAssignments);
        setUnassignedList(currentData);
      }
    } else {
      if (manualAssignments.length > 0) {
        setManualAssignments([]);
        setUnassignedList([]);
      }
    }
  }, [effectiveInstructorTimeData, unitsLookup, validSlotsMap, basketMeta.semester, manualAssignments]);

  // ============================
  // استخراج mismatchReasons
  // ============================
  const mismatchReasons = useMemo(() => {
    if (!steps || steps.length === 0) return [];
    const finalStep = steps[steps.length - 1];
    if (finalStep && finalStep.details && finalStep.details.mismatch_details) {
      return finalStep.details.mismatch_details;
    }
    return [];
  }, [steps]);

  // ============================
  // توابع مودال تخصیص دستی
  // ============================
  const openModalForAssignment = (index) => {
    const assignment = manualAssignments[index];
    if (!assignment) return;
    setEditingAssignmentIndex(index);
    setModalAssignmentData({
      instructor_code: assignment.instructor_code || "",
      day: assignment.day !== undefined ? parseInt(assignment.day) : 0,
      start: assignment.start || "07:30",
      end: assignment.end || "09:15",
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingAssignmentIndex(null);
  };

  const handleModalChange = (field, value) => {
    setModalAssignmentData(prev => ({ ...prev, [field]: value }));
  };

  const handleModalSave = async () => {
    if (editingAssignmentIndex === null) return;
    const updated = [...manualAssignments];
    const units = updated[editingAssignmentIndex].units || 2;
    let start = modalAssignmentData.start;
    let end = modalAssignmentData.end;
    if (start) {
      const validSlots = getValidSlotsSyncLocal(units);
      const foundSlot = validSlots.find(slot => slot.startsWith(start));
      if (foundSlot) {
        const [s, e] = foundSlot.split('-');
        end = e;
      }
    }
    updated[editingAssignmentIndex] = {
      ...updated[editingAssignmentIndex],
      instructor_code: modalAssignmentData.instructor_code,
      day: parseInt(modalAssignmentData.day),
      start: start,
      end: end,
    };
    setManualAssignments(updated);
    closeModal();
  };

  // ============================
  // توابع مودال ویرایش کلاس‌های تخصیص‌یافته
  // ============================
  const openEditModal = (index) => {
    const classData = filteredAssigned[index];
    if (!classData) return;
    setEditingClassIndex(index);
    setEditModalData({
      id: classData.id || null,
      course_name: classData.course_name || "",
      group_number: classData.group_number ? parseInt(classData.group_number) : 1,
      level: classData.level || "",
      term: classData.term || "",
      unique_code: classData.unique_code || "",
      units: classData.units || 2,
      instructor_code: classData.instructor_code || "",
      day: classData.day !== undefined ? parseInt(classData.day) : 0,
      start: classData.start || "07:30",
      end: classData.end || "09:15",
    });
    setIsEditModalOpen(true);
  };

  const closeEditModal = () => {
    setIsEditModalOpen(false);
    setEditingClassIndex(null);
  };

  const handleEditModalChange = (field, value) => {
    setEditModalData(prev => ({ ...prev, [field]: value }));
  };

  const handleEditModalSave = async () => {
    if (editingClassIndex === null) return;

    if (!editModalData.id) {
      alert("خطا: شناسه کلاس (id) وجود ندارد. لطفاً صفحه را دوباره بارگذاری کنید.");
      return;
    }

    if (!editModalData.instructor_code) {
      alert("لطفاً استاد را انتخاب کنید.");
      return;
    }
    if (!editModalData.start || !editModalData.end) {
      alert("لطفاً بازه زمانی را انتخاب کنید.");
      return;
    }

    const validWorkflowId = parseInt(workflowId);
    if (isNaN(validWorkflowId) || validWorkflowId <= 0) {
      alert("خطا: شناسه جلسه (workflow) معتبر نیست.");
      return;
    }

    const payload = {
      assignments: [{
        id: editModalData.id,
        course_name: editModalData.course_name,
        group_number: parseInt(editModalData.group_number) || 1,
        level: editModalData.level || "",
        term: editModalData.term || "",
        instructor_code: editModalData.instructor_code,
        day: parseInt(editModalData.day) || 0,
        start: editModalData.start,
        end: editModalData.end,
      }],
      basket_id: parseInt(basketId),
      workflow_id: validWorkflowId
    };

    setIsSavingEdits(true);
    setError(null);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        payload
      );
      alert(`✅ ${response.data.success_count} کلاس با موفقیت ویرایش شد.`);
      closeEditModal();

      const reloaded = await reloadScheduleData();
      if (!reloaded) {
        setError("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
        alert("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
      } else {
        console.log("✅ داده‌های زمان‌بندی پس از ویرایش به‌روز شد.");
        setUpdateCounter(prev => prev + 1);
      }
    } catch (err) {
      console.error("[handleEditModalSave] خطا:", err);
      let errorMsg = "خطا در ویرایش کلاس";
      if (err.response) {
        errorMsg = err.response.data?.detail || err.response.statusText || errorMsg;
        if (typeof errorMsg === 'object') errorMsg = JSON.stringify(errorMsg);
      } else {
        errorMsg = err.message || errorMsg;
      }
      setError(errorMsg);
      alert("خطا در ویرایش کلاس: " + errorMsg);
    } finally {
      setIsSavingEdits(false);
    }
  };

  const handleMatrixClassUpdate = async (classData, newDay, newStart, newEnd) => {
    if (!classData.id) {
      alert("خطا: شناسه کلاس وجود ندارد.");
      return;
    }

    if (!classData.instructor_code) {
      alert("این کلاس استاد ندارد، لطفاً ابتدا استاد را تعیین کنید.");
      return;
    }

    const validWorkflowId = parseInt(workflowId);
    if (isNaN(validWorkflowId) || validWorkflowId <= 0) {
      alert("خطا: شناسه جلسه (workflow) معتبر نیست.");
      return;
    }

    const payload = {
      assignments: [{
        id: classData.id,
        course_name: classData.course_name,
        group_number: parseInt(classData.group_number) || 1,
        level: classData.level || "",
        term: classData.term || "",
        instructor_code: classData.instructor_code,
        day: parseInt(newDay) || 0,
        start: newStart,
        end: newEnd,
      }],
      basket_id: parseInt(basketId),
      workflow_id: validWorkflowId
    };

    setIsSavingEdits(true);
    setError(null);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        payload
      );
      alert(`✅ کلاس با موفقیت به روز و زمان جدید منتقل شد.`);

      const reloaded = await reloadScheduleData();
      if (!reloaded) {
        setError("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
        alert("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
      } else {
        console.log("✅ داده‌های زمان‌بندی پس از انتقال به‌روز شد.");
        setUpdateCounter(prev => prev + 1);
      }
    } catch (err) {
      console.error("[handleMatrixClassUpdate] خطا:", err);
      let errorMsg = "خطا در انتقال کلاس";
      if (err.response) {
        errorMsg = err.response.data?.detail || err.response.statusText || errorMsg;
        if (typeof errorMsg === 'object') errorMsg = JSON.stringify(errorMsg);
      } else {
        errorMsg = err.message || errorMsg;
      }
      setError(errorMsg);
      alert("خطا در انتقال کلاس: " + errorMsg);
    } finally {
      setIsSavingEdits(false);
    }
  };

  // ============================
  // تابع کمکی برای بارگذاری مجدد داده‌ها از API
  // ============================
  const reloadScheduleData = async () => {
    if (!basketId) return false;
    try {
      const response = await axios.get(
        `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketId}`
      );
      const data = response.data;
      if (data.scenario_id) setWorkflowId(data.scenario_id);

      const apiUnassigned = (data.unassigned || []).map(item => ({
        ...item,
        course_name: item.course_title || item.course_name || '—',
        unique_code: item.course_code || item.unique_code,
        start: item.start_time || item.start || '',
        end: item.end_time || item.end || '',
        day: item.day !== undefined ? parseInt(item.day) : 0,
        units: item.units || 2,
        level: item.level || 'کارشناسی',
        term: item.term || 'semester_1',
        estimated_capacity: item.estimated_capacity || 0,
        group_number: item.group_number ? parseInt(item.group_number) : 1,
      }));

      if (data.total === 0 && data.classes.length === 0 && apiUnassigned.length === 0) {
        removeUnassignedFromStorage(basketId, workflowId);
        setInstructorTimeDataLocal({
          assigned: [],
          unassigned: [],
          all: [],
        });
        setIsScheduleSaved(false);
        setScheduleExists(false);
        setExistingScheduleLoaded(true);
        setUpdateCounter(prev => prev + 1);
        return false;
      }

      if (apiUnassigned.length > 0) {
        saveUnassignedToStorage(basketId, workflowId, apiUnassigned);
      } else {
        removeUnassignedFromStorage(basketId, workflowId);
      }

      const unitsLookup = {};
      (effectiveBasketData || []).forEach(item => {
        if (item.unique_code) unitsLookup[item.unique_code] = item.units || 2;
      });

      const mappedClasses = data.classes.map(cls => {
        const item = {
          ...cls,
          course_name: cls.course_title || cls.course_name || cls.course_code,
          unique_code: cls.course_code,
          group_number: cls.group_number || 1,
          instructor_name: cls.instructor_name,
          instructor_code: cls.instructor_code,
          day: cls.day,
          start: cls.start_time,
          end: cls.end_time,
          units: cls.units || 2,
          level: cls.level || 'کارشناسی',
          term: cls.term || 'semester_1',
          estimated_capacity: cls.room_capacity || 0,
          match_status: cls.match_status || null,
        };
        return normalizeTimeSlotWithCache(item, unitsLookup, validSlotsMap, basketMeta.semester || 'semester_1');
      });

      const assignedItems = [];
      const unassignedItemsFromClasses = [];
      mappedClasses.forEach(item => {
        if (item.instructor_code) assignedItems.push(item);
        else unassignedItemsFromClasses.push(item);
      });

      const combinedUnassigned = [...unassignedItemsFromClasses, ...apiUnassigned];
      const uniqueCombined = [];
      const seenCombined = new Set();
      combinedUnassigned.forEach(item => {
        const key = `${item.unique_code || item.course_code}_${item.group_number}`;
        if (!seenCombined.has(key)) {
          seenCombined.add(key);
          uniqueCombined.push(item);
        }
      });

      const allItems = [...assignedItems, ...uniqueCombined];
      setInstructorTimeDataLocal({
        assigned: assignedItems,
        unassigned: uniqueCombined,
        all: allItems,
      });
      setIsScheduleSaved(true);
      setScheduleExists(true);
      setExistingScheduleLoaded(true);
      setUpdateCounter(prev => prev + 1);
      return true;
    } catch (err) {
      console.error("[reloadScheduleData] خطا در بارگذاری مجدد:", err);
      return false;
    }
  };

  // ============================
  // ذخیره تخصیص دستی
  // ============================
  const saveManualAssignments = async () => {
    const completedAssignments = manualAssignments.filter(item => item.instructor_code && item.instructor_code.trim() !== "");
    if (completedAssignments.length === 0) {
      alert("هیچ کلاسی برای ذخیره وجود ندارد. لطفاً ابتدا استاد را برای حداقل یک کلاس انتخاب کنید.");
      return;
    }

    const validWorkflowId = parseInt(workflowId);
    if (isNaN(validWorkflowId) || validWorkflowId <= 0) {
      alert("خطا: شناسه جلسه (workflow) معتبر نیست. لطفاً ابتدا زمان‌بندی را اجرا کنید.");
      return;
    }

    const payloadAssignments = completedAssignments.map(item => ({
      course_name: item.course_name || "",
      group_number: parseInt(item.group_number) || 1,
      level: item.level || "",
      term: item.term || "",
      instructor_code: item.instructor_code || "",
      day: parseInt(item.day) || 0,
      start: item.start || "07:30",
      end: item.end || "09:15",
    }));

    setIsSavingManual(true);
    setError(null);
    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        {
          assignments: payloadAssignments,
          basket_id: parseInt(basketId),
          workflow_id: validWorkflowId
        }
      );
      setManualResult(response.data);
      alert(`✅ ${response.data.success_count} کلاس با موفقیت تخصیص یافت.`);

      const assignedCodes = new Set(completedAssignments.map(item => `${item.unique_code}_${item.group_number}`));
      const remainingAssignments = manualAssignments.filter(
        item => !assignedCodes.has(`${item.unique_code}_${item.group_number}`)
      );
      setManualAssignments(remainingAssignments);
      setUnassignedList(remainingAssignments);

      const reloaded = await reloadScheduleData();
      if (reloaded) {
        setManualMode(false);
        console.log("✅ داده‌های زمان‌بندی پس از تخصیص دستی به‌روز شد.");
      } else {
        setError("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
        alert("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
      }
    } catch (err) {
      console.error("[saveManualAssignments] خطا:", err);
      const errorMsg = err.response?.data?.detail || err.message || "خطا در ذخیره تخصیص دستی";
      setError(typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg);
      alert("خطا در ذخیره تخصیص دستی: " + (typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg));
    } finally {
      setIsSavingManual(false);
    }
  };

  // ============================
  // ویرایش جدول (حالت قدیمی - درون جدول)
  // ============================
  const startEditing = () => {
    const normalizedData = normalizedAssigned.map(row => {
      const units = row.units || 2;
      const validSlots = getValidSlotsSyncLocal(units);
      const validStarts = validSlots.map(slot => slot.split('-')[0]);
      let start = String(row.start || '');
      let end = String(row.end || '');
      if (!validStarts.includes(start)) {
        start = validStarts[0] || '';
        const foundSlot = validSlots.find(slot => slot.startsWith(start));
        end = foundSlot ? foundSlot.split('-')[1] : '';
      }
      return { ...row, start, end };
    });
    setEditedData(normalizedData);
    setEditingMode(true);
  };

  const cancelEditing = () => {
    setEditingMode(false);
    setEditedData([]);
  };

  const getEndFromStart = (start, units) => {
    const slots = getValidSlotsSyncLocal(units);
    const found = slots.find(slot => slot.startsWith(start));
    return found ? found.split('-')[1] : null;
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
      if (end) row.end = String(end);
    } else {
      row[field] = value;
    }
    setEditedData(updated);
  };

  // ============================
  // ذخیره ویرایش‌ها (حالت قدیمی)
  // ============================
  const saveEdits = async () => {
    const invalid = editedData.some(item => !item.instructor_code);
    if (invalid) {
      alert("لطفاً برای همه کلاس‌ها استاد انتخاب کنید.");
      return;
    }

    const validWorkflowId = parseInt(workflowId);
    if (isNaN(validWorkflowId) || validWorkflowId <= 0) {
      alert("خطا: شناسه جلسه (workflow) معتبر نیست.");
      return;
    }

    const assignments = editedData.map(item => ({
      course_name: item.course_name,
      group_number: parseInt(item.group_number) || 1,
      level: item.level || "",
      term: item.term || "",
      instructor_code: item.instructor_code,
      day: parseInt(item.day) || 0,
      start: item.start || "07:30",
      end: item.end || "09:15",
    }));

    setIsSavingEdits(true);
    setError(null);
    try {
      const response = await axios.post(
        "http://localhost:8000/api/schedule/workflow/schedule/manual",
        {
          assignments: assignments,
          basket_id: parseInt(basketId),
          workflow_id: validWorkflowId
        }
      );
      alert(`✅ ${response.data.success_count} کلاس با موفقیت ویرایش شد.`);
      setEditingMode(false);

      const reloaded = await reloadScheduleData();
      if (!reloaded) {
        setError("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
        alert("بارگذاری مجدد داده‌ها با مشکل مواجه شد. لطفاً صفحه را رفرش کنید.");
      } else {
        console.log("✅ داده‌های زمان‌بندی پس از ویرایش به‌روز شد.");
      }
    } catch (err) {
      console.error("[saveEdits] خطا:", err);
      const errorMsg = err.response?.data?.detail || err.message || "خطا در ذخیره ویرایش‌ها";
      setError(typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg);
      alert("خطا در ذخیره ویرایش‌ها: " + (typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg));
    } finally {
      setIsSavingEdits(false);
    }
  };

  // ============================
  // ستون‌های جدول
  // ============================
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
    {
      key: "actions",
      label: "عملیات",
      render: (row, index) => {
        if (editingMode || viewMode !== 'table') return null;
        return (
          <button
            onClick={() => openEditModal(index)}
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
        );
      },
    },
  ];

  const manualColumns = [
    { key: "course_name", label: "درس" },
    { key: "group_number", label: "گروه" },
    { key: "level", label: "مقطع" },
    { key: "term", label: "ترم" },
    {
      key: "instructor_code",
      label: "استاد (کد)",
      render: (row, index) => {
        const instructorName = instructorNameLookup[row.instructor_code] || row.instructor_code || 'انتخاب نشده';
        return <span style={{ cursor: 'pointer', color: '#3498db', fontWeight: 'bold' }} onClick={() => openModalForAssignment(index)}>{instructorName}</span>;
      },
    },
    {
      key: "day",
      label: "روز",
      render: (row, index) => {
        const dayName = row.day !== undefined ? getDayName(parseInt(row.day)) : '—';
        return <span style={{ cursor: 'pointer', color: '#3498db' }} onClick={() => openModalForAssignment(index)}>{dayName}</span>;
      },
    },
    {
      key: "time_slot",
      label: "بازه زمانی",
      render: (row, index) => {
        const slot = `${row.start || ''} - ${row.end || ''}`;
        return <span style={{ cursor: 'pointer', color: '#3498db' }} onClick={() => openModalForAssignment(index)}>{slot || '—'}</span>;
      },
    },
    {
      key: "actions",
      label: "عملیات",
      render: (row, index) => (
        <button onClick={() => openModalForAssignment(index)} className="btn-edit" style={{ background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', padding: '4px 12px', cursor: 'pointer' }}>
          ✏️ ویرایش
        </button>
      ),
    },
  ];

  // ============================
  // تابع تشخیص تداخل‌های زمانی
  // ============================
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

  // ============================
  // فیلترها
  // ============================
  const filterByDay = (data) => {
    if (selectedDay === null) return data;
    return data.filter(item => parseInt(item.day) === selectedDay);
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
  const filterByStatusFn = (data) => {
    if (!filterStatus) return data;
    return data.filter(item => getItemStatus(item) === filterStatus);
  };

  const filteredAssigned = useMemo(() => filterByStatusFn(filterBySearch(filterByDay(normalizedAssigned))), [normalizedAssigned, filterStatus, debouncedSearchTerm, selectedDay]);
  const filteredAll = useMemo(() => filterByStatusFn(filterBySearch(filterByDay(normalizedAll))), [normalizedAll, filterStatus, debouncedSearchTerm, selectedDay]);
  const filteredUnassigned = useMemo(() => filterByStatusFn(filterBySearch(filterByDay(normalizedUnassigned))), [normalizedUnassigned, filterStatus, debouncedSearchTerm, selectedDay]);
  const filteredManualAssignments = useMemo(() => filterByStatusFn(filterBySearch(filterByDay(manualAssignments))), [manualAssignments, filterStatus, debouncedSearchTerm, selectedDay]);

  const conflictData = useMemo(() => {
    return findConflicts(filteredAssigned);
  }, [filteredAssigned]);

  // ============================
  // داده‌های استاد و درس
  // ============================
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
    return Array.from(instructors.entries()).sort((a, b) => a[1].localeCompare(b[1])).map(([code, name]) => ({
      code,
      name,
      cooperation_type: 'نامشخص',
      max_teaching_units: 0,
    }));
  }, [instructorsData, normalizedAll]);

  const courseList = useMemo(() => {
    if (!effectiveBasketData) return [];
    const courseMap = new Map();
    effectiveBasketData.forEach(item => {
      const code = item.unique_code;
      if (code && !courseMap.has(code)) {
        courseMap.set(code, {
          code,
          name: item.course_name || code,
          level: item.level || '',
          term: item.term || '',
          units: item.units || 2,
        });
      }
    });
    return Array.from(courseMap.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [effectiveBasketData]);

  const instructorData = useMemo(() => {
    if (!selectedInstructor) return null;
    const classes = filteredAll.filter(item => item.instructor_code === selectedInstructor);
    const teachPrefs = teachingPreferences.filter(p => p.instructor_code === selectedInstructor).map(p => p.unique_course_code);
    const timePrefs = timePreferences.filter(p => p.instructor_code === selectedInstructor).map(p => ({
      day: getDayName(p.day),
      start: p.start_time,
      end: p.end_time,
      priority: p.priority !== undefined ? p.priority : null,
    }));
    const classStatus = classes.map(cls => {
      const status = getMatchStatus(cls, teachingLookup, timeLookup);
      const teachMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
      const dayMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
      const timeMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
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

  const courseData = useMemo(() => {
    if (!selectedCourseCode) return null;
    const classes = filteredAll.filter(item => item.unique_code === selectedCourseCode);
    const courseInfo = courseList.find(c => c.code === selectedCourseCode);
    const groups = classes.map(cls => {
      const status = getMatchStatus(cls, teachingLookup, timeLookup);
      const teachMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
      const dayMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
      const timeMatch = getMatchStatus(cls, teachingLookup, timeLookup) === 'full';
      return { ...cls, status, teachMatch, dayMatch, timeMatch, hasInstructor: !!cls.instructor_code, hasTime: !!cls.start && !!cls.end };
    });
    const total = groups.length;
    const assignedCount = groups.filter(g => g.hasInstructor && g.hasTime).length;
    const unassignedCount = total - assignedCount;
    const fullMatchCount = groups.filter(g => g.status === 'full').length;
    const partialMatchCount = groups.filter(g => g.status === 'partial').length;
    const noMatchCount = groups.filter(g => g.status === 'none').length;
    const noPrefCount = groups.filter(g => g.status === 'no_preference').length;
    const teachingPrefsForCourse = teachingPreferences.filter(pref => pref.unique_course_code === selectedCourseCode).sort((a, b) => (a.priority || 999) - (b.priority || 999));
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

  // ============================
  // انتخاب خودکار اولین استاد و درس
  // ============================
  useEffect(() => {
    if (instructorList.length > 0 && !selectedInstructor && !hasSetDefaultInstructor.current) {
      setSelectedInstructor(instructorList[0].code);
      hasSetDefaultInstructor.current = true;
    }
  }, [instructorList, selectedInstructor]);

  useEffect(() => {
    if (courseList.length > 0 && !selectedCourseCode && !hasSetDefaultCourse.current) {
      setSelectedCourseCode(courseList[0].code);
      hasSetDefaultCourse.current = true;
    }
  }, [courseList, selectedCourseCode]);

  // ============================
  // توابع رندرینگ
  // ============================
  const renderDayFilters = () => (
    <div className="day-filters">
      <button className={`day-filter-btn ${selectedDay === null ? 'active' : ''}`} onClick={() => setSelectedDay(null)}>همه روزها</button>
      {dayNames.map((name, index) => (
        <button key={index} className={`day-filter-btn ${selectedDay === index ? 'active' : ''}`} onClick={() => setSelectedDay(index)}>{name}</button>
      ))}
    </div>
  );

  const renderViewTabs = () => (
    <div className="view-tabs">
      <button className={`view-tab ${viewMode === 'table' ? 'active' : ''}`} onClick={() => setViewMode('table')}>📋 جدول</button>
      <button className={`view-tab ${viewMode === 'matrix' ? 'active' : ''}`} onClick={() => setViewMode('matrix')}>📊 ماتریس زمانی</button>
      <button className={`view-tab ${viewMode === 'instructorMatrix' ? 'active' : ''}`} onClick={() => setViewMode('instructorMatrix')}>👨‍🏫 ماتریس زمانی استاد</button>
      <button className={`view-tab ${viewMode === 'chart' ? 'active' : ''}`} onClick={() => setViewMode('chart')}>📈 نمودار میله‌ای</button>
      <button className={`view-tab ${viewMode === 'calendar' ? 'active' : ''}`} onClick={() => setViewMode('calendar')}>📅 تقویم هفتگی</button>
      <button className={`view-tab ${viewMode === 'instructor' ? 'active' : ''}`} onClick={() => setViewMode('instructor')}>👨‍🏫 اطلاعات استاد</button>
      <button className={`view-tab ${viewMode === 'course' ? 'active' : ''}`} onClick={() => setViewMode('course')}>📚 اطلاعات درس</button>
      <button className={`view-tab ${viewMode === 'conflicts' ? 'active' : ''}`} onClick={() => setViewMode('conflicts')}>⚠️ تداخل‌ها</button>
      <button className={`view-tab ${viewMode === 'reasons' ? 'active' : ''}`} onClick={() => setViewMode('reasons')}>❓ دلایل عدم تطابق</button>
    </div>
  );

  const renderSearch = () => (
    <div className="table-search">
      <input type="text" placeholder="🔍 جستجو در جدول..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="search-input" />
      {searchTerm && <button className="search-clear" onClick={() => { setSearchTerm(""); setDebouncedSearchTerm(""); }}>پاک کردن</button>}
    </div>
  );

  // ============================
  // رندر اصلی
  // ============================
  if (!effectiveBasketData || effectiveBasketData.length === 0) {
    return (
      <div className="process-page instructor-time-page">
        <div className="process-header">
          <div className="process-title">
            <span className="process-icon">⏳</span>
            <h2>زمان‌بندی استاد و درس</h2>
          </div>
          <p className="process-description">برای شروع زمان‌بندی، ابتدا باید یک سبد دروس انتخاب یا ایجاد کنید.</p>
        </div>
        <div className="process-body">
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <h3>سبد دروس انتخاب نشده است</h3>
            <p>لطفاً ابتدا یک سبد دروس را از لیست سبدها انتخاب کنید یا یک سبد جدید ایجاد کنید.</p>
            {typeof onNavigateToBasketList === "function" && (
              <button onClick={onNavigateToBasketList} className="btn-primary" style={{ marginTop: "1.5rem", padding: "0.75rem 2rem" }}>
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
          <span className="basket-badge" style={{ background: "#e2e8f0", padding: "0.25rem 0.75rem", borderRadius: "0.5rem", display: "inline-block" }}>
            📂 سبد دروس: {basketMeta.title || `شناسه ${basketId || ''}`}
            {basketMeta.semester && ` (${basketMeta.semester === "semester_1" ? "مهر" : basketMeta.semester === "semester_2" ? "بهمن" : basketMeta.semester === "summer" ? "تابستان" : basketMeta.semester} ${basketMeta.year})`}
          </span>
        </div>
        <p className="process-description">
          {scheduleExists ? (
            <span style={{ color: "#2ecc71", fontWeight: "bold", display: "block", marginTop: "8px" }}>✅ این سبد قبلاً زمان‌بندی شده است. زمان‌بندی فعلی نمایش داده می‌شود.</span>
          ) : (
            <span style={{ color: "#f39c12", fontWeight: "bold", display: "block", marginTop: "8px" }}>⏳ این سبد هنوز زمان‌بندی نشده است. برای ایجاد زمان‌بندی، روی "اجرای زمان‌بندی" کلیک کنید.</span>
          )}
          {isLoadingExistingSchedule && <span style={{ color: "#f39c12", display: "block", marginTop: "8px" }}>⏳ در حال بارگذاری زمان‌بندی...</span>}
          {existingScheduleLoaded && scheduleExists && normalizedAssigned.length > 0 && (
            <span style={{ color: "#2ecc71", display: "block", marginTop: "8px" }}>
              ✅ زمان‌بندی قبلی با {normalizedAssigned.length} کلاس تخصیص‌یافته و {normalizedUnassigned.length} کلاس بدون استاد بارگذاری شد.
            </span>
          )}
          {existingScheduleLoaded && !scheduleExists && (
            <span style={{ color: "#95a5a6", display: "block", marginTop: "8px" }}>ℹ️ هیچ زمان‌بندی برای این سبد یافت نشد. برای ایجاد جدید، روی "اجرای زمان‌بندی" کلیک کنید.</span>
          )}
        </p>
        {typeof onNavigateToBasketList === "function" && (
          <button onClick={onNavigateToBasketList} className="btn-secondary" style={{ marginTop: "10px" }}>← بازگشت به لیست سبدها</button>
        )}
      </div>

      <div className="process-body">
        <div className="controls-bar">
          <button onClick={handleLocalProcess} disabled={!effectiveBasketData || effectiveBasketData.length === 0 || loadingLocal || isLoadingBasket || isLoadingExistingSchedule} className="btn-process">
            {loadingLocal ? "در حال اجرا..." : "اجرای زمان‌بندی"}
          </button>
          {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && (
            <button onClick={handleClear} className="btn-clear">پاک کردن نتایج</button>
          )}
          {workflowId && existingScheduleLoaded && scheduleExists && normalizedAssigned.length > 0 && (
            <button onClick={handleDeleteSchedule} className="btn-delete">🗑️ حذف زمان‌بندی</button>
          )}
          {normalizedUnassigned.length > 0 && !manualMode && (
            <button onClick={() => setManualMode(true)} className="btn-manual">✏️ مرحله دوم: تخصیص دستی</button>
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
            <button onClick={startEditing} className="btn-edit-table">✏️ ویرایش جدول (درون‌جدولی)</button>
          )}
          <button onClick={() => setShowTestReport(true)} className="btn-test-report">📊 گزارش تست‌ها</button>
          <button onClick={() => setShowBasket(!showBasket)} className="btn-toggle-basket" style={{ background: showBasket ? '#e74c3c' : '#2ecc71', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}>
            {showBasket ? '📋 مخفی کردن سبد دروس' : '📋 نمایش سبد دروس'}
          </button>
          <button onClick={() => setShowSteps(!showSteps)} className="btn-toggle-steps" style={{ background: showSteps ? '#f39c12' : '#3498db', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', cursor: 'pointer', fontWeight: 'bold', marginRight: '8px' }}>
            {showSteps ? '📋 مخفی کردن مراحل' : '📋 نمایش مراحل'}
          </button>
          <button onClick={() => setShowFrequency(!showFrequency)} className="btn-toggle-frequency" style={{ background: showFrequency ? '#f39c12' : '#2ecc71', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', border: 'none', cursor: 'pointer', fontWeight: 'bold', marginRight: '8px' }}>
            {showFrequency ? '📊 مخفی کردن آمار' : '📊 نمایش آمار'}
          </button>
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
                <div className="summary-item"><span className="label">تعداد کل کلاس‌ها</span><span className="value">{effectiveBasketData.length}</span></div>
                <div className="summary-item"><span className="label">مقاطع</span><span className="value">{[...new Set(effectiveBasketData.map(item => item.level))].filter(Boolean).join("، ")}</span></div>
                <div className="summary-item"><span className="label">میانگین ظرفیت</span><span className="value">{Math.round(effectiveBasketData.reduce((sum, c) => sum + (c.estimated_capacity || 0), 0) / effectiveBasketData.length)}</span></div>
              </div>
            </div>
          </div>
        )}

        {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && !manualMode && (
          <div className="result-container">
            <div className="result-header">
              <h4>✅ نتایج زمان‌بندی (تخصیص خودکار)</h4>
              <div className="result-stats">
                <button className={`stat-badge filter-btn ${filterStatus === 'full' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'full' ? null : 'full')}>✅ تطابق کامل: {directMatchStats.full}</button>
                <button className={`stat-badge filter-btn ${filterStatus === 'partial' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'partial' ? null : 'partial')}>⚠️ تطابق نسبی: {directMatchStats.partial}</button>
                <button className={`stat-badge filter-btn ${filterStatus === 'none' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'none' ? null : 'none')}>❌ بدون تطابق: {directMatchStats.none}</button>
                <button className={`stat-badge filter-btn ${filterStatus === 'no_preference' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'no_preference' ? null : 'no_preference')}>➖ بدون مطلوبیت: {directMatchStats.no_preference}</button>
                <button className={`stat-badge filter-btn ${filterStatus === 'no_assignment' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'no_assignment' ? null : 'no_assignment')}>🚫 تخصیص ناقص: {directMatchStats.no_assignment}</button>
                <button className={`stat-badge filter-btn ${filterStatus === 'unassigned' ? 'active' : ''}`} onClick={() => setFilterStatus(filterStatus === 'unassigned' ? null : 'unassigned')}>📭 تخصیص‌نیافته: {directMatchStats.unassigned}</button>
                {filterStatus && <button className="stat-badge filter-clear" onClick={() => setFilterStatus(null)}>✖ پاک کردن فیلتر</button>}
              </div>
            </div>

            {renderDayFilters()}
            {renderViewTabs()}

            <div className="view-container">
              {viewMode === 'table' && renderCustomTable({
                data: filteredAssigned,
                columns: tableColumns,
                showStatus: true,
                editable: editingMode,
                editedData,
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
                onEditRow: openEditModal,
                validSlotsMap: validSlotsMap,
              })}
              {viewMode === 'matrix' && renderMatrixView({
                data: filteredAssigned,
                allData: filteredAll,
                getItemStatus,
                getDayName,
                selectedDay: selectedDay,
                onClassUpdate: handleMatrixClassUpdate,
                instructorList: instructorList,
                instructorNameLookup: instructorNameLookup,
                validSlotsMap: validSlotsMap,
              })}
              {viewMode === 'instructorMatrix' && (
                <div className="instructor-matrix-view">
                  <div className="instructor-selector" style={{ marginBottom: '16px' }}>
                    <label style={{ marginLeft: '8px', fontWeight: 'bold' }}>انتخاب استاد:</label>
                    <select
                      value={selectedInstructor}
                      onChange={(e) => setSelectedInstructor(e.target.value)}
                      className="instructor-select"
                      style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ccc' }}
                    >
                      {instructorList.map(({ code, name }) => (
                        <option key={code} value={code}>{name} ({code})</option>
                      ))}
                    </select>
                  </div>
                  <InstructorWeeklyMatrix
                    selectedInstructor={selectedInstructor}
                    allData={filteredAll}
                    instructorNameLookup={instructorNameLookup}
                    timePreferences={timePreferences}
                    getDayName={getDayName}
                    onClassUpdate={handleMatrixClassUpdate}
                    instructorList={instructorList}
                    isLoading={loadingInstructors}
                    validSlotsMap={validSlotsMap}
                  />
                </div>
              )}
              {viewMode === 'chart' && renderChartView({ data: filteredAssigned, getItemStatus, getDayName })}
              {viewMode === 'calendar' && renderCalendarView({ data: filteredAssigned, allData: filteredAll, getItemStatus, getDayName, dayNames })}
              {viewMode === 'instructor' && renderInstructorInfo({ instructorData, instructorList, selectedInstructor, setSelectedInstructor, loadingInstructors, courseNameLookup, getDayName })}
              {viewMode === 'course' && renderCourseInfo({ courseData, courseList, selectedCourseCode, setSelectedCourseCode, getDayName })}
              {viewMode === 'conflicts' && renderConflictsView({ conflicts: conflictData })}
              {viewMode === 'reasons' && renderReasonsView({ mismatchReasons })}
            </div>

            {showSteps && <StepsDisplay steps={steps} instructorNameLookup={instructorNameLookup} courseNameLookup={courseNameLookup} />}
            {!editingMode && showFrequency && renderFrequency({ data: filteredAll })}
          </div>
        )}

        {!effectiveInstructorTimeData && effectiveBasketData && effectiveBasketData.length > 0 && !isLoadingExistingSchedule && !existingScheduleLoaded && (
          <div className="info-box info-warning" style={{ marginTop: '20px' }}>
            <span className="info-icon">ℹ️</span>
            <p>برای شروع زمان‌بندی، روی دکمه <strong>"اجرای زمان‌بندی"</strong> در نوار ابزار کلیک کنید. پس از اجرا، نتایج تخصیص استاد و زمان در این بخش نمایش داده می‌شود.</p>
          </div>
        )}

        {normalizedUnassigned.length > 0 && !manualMode && (
          <div className="unassigned-container">
            <div className="result-header warning">
              <h4>⚠️ کلاس‌های بدون استاد ({normalizedUnassigned.length} کلاس)</h4>
              <p className="hint-text">این کلاس‌ها در مرحله اول تخصیص نیافتند. لطفاً با کلیک روی دکمه "مرحله دوم: تخصیص دستی" استاد و زمان مناسب را به آنها اختصاص دهید.</p>
            </div>
            {renderCustomTable({
              data: filteredUnassigned,
              columns: tableColumns.filter(col => !['instructor_name', 'instructor_code', 'final_score', 'actions'].includes(col.key)),
              showStatus: false,
              editable: false,
              renderSearch,
              validSlotsMap: validSlotsMap,
            })}
          </div>
        )}

        {manualMode && normalizedUnassigned.length > 0 && (
          <div className="manual-container">
            <div className="result-header">
              <h4>✏️ مرحله دوم: تخصیص دستی استاد</h4>
              <p className="hint-text">برای هر کلاس، استاد، روز و بازه زمانی مجاز را انتخاب کنید. سپس روی "ذخیره تخصیص‌های دستی" کلیک کنید.</p>
            </div>
            {renderDayFilters()}
            <EditableDataTable data={filteredManualAssignments} columns={manualColumns} title="" editable={false} />
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

        {/* ===== بخش دکمه "مرحله بعد: تخصیص اتاق" ===== */}
        {effectiveInstructorTimeData && (normalizedAssigned.length > 0 || normalizedUnassigned.length > 0) && !manualMode && (
          <div className="result-actions">
            <button
              onClick={async () => {
                console.log("🔘 [NextStep] کلیک شد.");
                console.log("📌 workflowId:", workflowId);
                console.log("📌 basketId:", basketId);
                console.log("📌 scheduleExists:", scheduleExists);
                console.log("📌 isScheduleSaved:", isScheduleSaved);
                console.log("📌 normalizedAssigned.length:", normalizedAssigned.length);
                console.log("📌 normalizedUnassigned.length:", normalizedUnassigned.length);

                if (!workflowId) {
                  alert("شناسه جلسه (workflow) یافت نشد. لطفاً زمان‌بندی را مجدداً اجرا کنید.");
                  return;
                }

                if (scheduleExists || isScheduleSaved) {
                  console.log("✅ [NextStep] scheduleExists یا isScheduleSaved true → رفتن به مرحله بعد");
                  if (typeof onNext === "function") {
                    onNext(workflowId);
                  }
                  return;
                }

                console.log("🔍 [NextStep] stateها false هستند، از سرور بررسی می‌شود...");
                try {
                  const response = await axios.get(
                    `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketId}`
                  );
                  console.log("📡 [NextStep] پاسخ سرور:", response.data);
                  const data = response.data;
                  if (data && (data.total > 0 || (data.unassigned && data.unassigned.length > 0))) {
                    console.log("✅ [NextStep] برنامه در سرور وجود دارد. به‌روزرسانی state و رفتن به مرحله بعد");
                    setScheduleExists(true);
                    setIsScheduleSaved(true);
                    setExistingScheduleLoaded(true);
                    if (typeof onNext === "function") {
                      onNext(workflowId);
                    }
                  } else {
                    console.warn("⚠️ [NextStep] برنامه در سرور وجود ندارد.");
                    alert("هیچ برنامه زمان‌بندی برای این سبد یافت نشد. لطفاً ابتدا زمان‌بندی را اجرا کنید.");
                  }
                } catch (err) {
                  console.error("❌ [NextStep] خطا در بررسی وجود برنامه:", err);
                  if (err.response?.status === 404) {
                    alert("هیچ برنامه زمان‌بندی برای این سبد یافت نشد. لطفاً ابتدا زمان‌بندی را اجرا کنید.");
                  } else {
                    alert("خطا در بررسی وضعیت زمان‌بندی. لطفاً دوباره تلاش کنید.");
                  }
                }
              }}
              className="btn-primary"
              disabled={loadingLocal || !workflowId}
              style={{
                opacity: (!workflowId) ? 0.5 : 1,
                cursor: (!workflowId) ? 'not-allowed' : 'pointer',
              }}
            >
              {loadingLocal ? "در حال..." :
               !workflowId ? "⏳ ابتدا جلسه را ایجاد کنید" :
               "🏢 مرحله بعد: تخصیص اتاق"}
            </button>
          </div>
        )}

        {/* مودال تخصیص دستی */}
        {renderManualModal({
          isOpen: isModalOpen,
          onClose: closeModal,
          editingIndex: editingAssignmentIndex,
          modalData: modalAssignmentData,
          onModalChange: handleModalChange,
          onModalSave: handleModalSave,
          assignment: manualAssignments[editingAssignmentIndex],
          instructorList,
          dayNames,
          getValidSlots: getValidSlotsSyncLocal,
          timePreferences,
          teachingPreferences,
          instructorNameLookup,
          getDayName,
          term: basketMeta.semester || "semester_1",
          validSlotsMap: validSlotsMap,
        })}

        {/* مودال ویرایش کلاس‌های تخصیص‌یافته */}
        {renderEditModal({
          isOpen: isEditModalOpen,
          onClose: closeEditModal,
          modalData: editModalData,
          onModalChange: handleEditModalChange,
          onModalSave: handleEditModalSave,
          instructorList,
          dayNames,
          getValidSlots: getValidSlotsSyncLocal,
          timePreferences,
          teachingPreferences,
          instructorNameLookup,
          getDayName,
          isSaving: isSavingEdits,
          term: basketMeta.semester || "semester_1",
          validSlotsMap: validSlotsMap,
        })}

        {showTestReport && (
          <TestReportModal
            onClose={() => setShowTestReport(false)}
            teachingPreferences={teachingPreferences}
            timePreferences={timePreferences}
            instructorsData={instructorsData}
          />
        )}
      </div>
    </div>
  );
}