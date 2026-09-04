// frontend/src/pages/RoomAllocationPage.jsx
import { useState, useEffect } from "react";
import axios from "axios";
import EditableDataTable from "../components/EditableDataTable";
import "./RoomAllocationPage.css";

const DAY_NAMES = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"];

// ============================================================
// ثابت‌های هماهنگ با بک‌اند (TERM_ALIASES)
// ============================================================
const TERM_DISPLAY = {
  semester_1: "مهر",
  semester_2: "بهمن",
  summer: "تابستان",
};

// تابع نرمال‌سازی ترم (تبدیل کلیدهای قدیمی به جدید)
const normalizeSemester = (term) => {
  if (!term) return "semester_1";
  const normalized = term.trim().toLowerCase();
  if (normalized === "mehr" || normalized === "semester_1") return "semester_1";
  if (normalized === "bahman" || normalized === "semester_2") return "semester_2";
  if (normalized === "summer" || normalized === "تابستان") return "summer";
  return "semester_1"; // پیش‌فرض
};

export default function RoomAllocationPage({
  instructorTimeData,
  roomAllocationData: propRoomAllocationData,
  onProcess,
  onClear,
  loading,
  onNext,
  basketId: propBasketId,
  workflowId: propWorkflowId,
  semester: propSemester,
  onInstructorDataLoaded,
}) {
  const [localInstructorData, setLocalInstructorData] = useState(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [basketId, setBasketId] = useState(propBasketId || null);
  const [workflowId, setWorkflowId] = useState(propWorkflowId || null);
  const [semester, setSemester] = useState(
    normalizeSemester(propSemester || localStorage.getItem('lastSemester') || "semester_1")
  );
  const [roomsList, setRoomsList] = useState([]);
  const [isLoadingRooms, setIsLoadingRooms] = useState(false);
  const [selectedDay, setSelectedDay] = useState(0);
  const [showMatrix, setShowMatrix] = useState(false);
  const [showTable, setShowTable] = useState(true);
  const [showSchedule, setShowSchedule] = useState(false);

  // داده‌های تخصیص اتاق (محلی)
  const [roomAllocationData, setRoomAllocationData] = useState(propRoomAllocationData || []);

  // وضعیت drag
  const [draggedClass, setDraggedClass] = useState(null);
  const [dragOverRoomId, setDragOverRoomId] = useState(null);

  // وضعیت تخصیص قبلی
  const [hasPreviousAllocation, setHasPreviousAllocation] = useState(false);
  const [previousAllocationData, setPreviousAllocationData] = useState([]);
  const [isCheckingPrevious, setIsCheckingPrevious] = useState(false);

  // همگام‌سازی با props
  useEffect(() => {
    if (propRoomAllocationData) {
      setRoomAllocationData(propRoomAllocationData);
    }
  }, [propRoomAllocationData]);

  // بارگذاری لیست اتاق‌ها
  useEffect(() => {
    const fetchRooms = async () => {
      setIsLoadingRooms(true);
      try {
        const response = await axios.get("http://localhost:8000/api/professors-rooms/rooms/list");
        setRoomsList(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        console.error("خطا در دریافت لیست اتاق‌ها:", err);
        setRoomsList([]);
      } finally {
        setIsLoadingRooms(false);
      }
    };
    fetchRooms();
  }, []);

  // بارگذاری تخصیص قبلی (اگر وجود داشته باشد)
  const checkPreviousAllocation = async (scenarioId) => {
    if (!scenarioId) return;
    setIsCheckingPrevious(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/room-allocation/${scenarioId}`);
      const data = response.data;
      if (data && data.length > 0) {
        // چک می‌کنیم که آیا حداقل یک کلاس اتاق دارد
        const hasRoom = data.some(item => item.room_name && item.room_name !== 'بدون اتاق' && item.room_name !== '—');
        if (hasRoom) {
          setHasPreviousAllocation(true);
          setPreviousAllocationData(data);
          console.log(`✅ تخصیص قبلی با ${data.length} کلاس یافت شد.`);
        } else {
          setHasPreviousAllocation(false);
          setPreviousAllocationData([]);
        }
      } else {
        setHasPreviousAllocation(false);
        setPreviousAllocationData([]);
      }
    } catch (error) {
      console.warn("⚠️ خطا در بررسی تخصیص قبلی:", error.message);
      setHasPreviousAllocation(false);
      setPreviousAllocationData([]);
    } finally {
      setIsCheckingPrevious(false);
    }
  };

  // وقتی workflowId مشخص شد، تخصیص قبلی را بررسی کن
  useEffect(() => {
    if (workflowId) {
      checkPreviousAllocation(workflowId);
    }
  }, [workflowId]);

  // بارگذاری تخصیص قبلی در صورت درخواست کاربر
  const loadPreviousAllocation = () => {
    if (previousAllocationData.length > 0) {
      setRoomAllocationData(previousAllocationData);
      setHasPreviousAllocation(false); // دیگر نیازی به نمایش پیام نیست
    }
  };

  const ensureCapacity = (classes) => {
    return classes.map(cls => ({
      ...cls,
      estimated_capacity: cls.estimated_capacity && cls.estimated_capacity > 0
        ? cls.estimated_capacity
        : 30
    }));
  };

  const loadDataFromServer = async (basketIdToUse) => {
    if (!basketIdToUse) {
      setLoadError("شناسه سبد موجود نیست. لطفاً دوباره تلاش کنید.");
      setLocalInstructorData(null);
      return;
    }

    setIsLoadingData(true);
    setLoadError(null);
    try {
      const response = await axios.get(
        `http://localhost:8000/api/schedule/workflow/scheduled-classes/by-basket/${basketIdToUse}`
      );
      const data = response.data;

      if (data.scenario_id) {
        setWorkflowId(data.scenario_id);
        localStorage.setItem('lastWorkflowId', String(data.scenario_id));
      }

      const assignedClasses = data.classes.map(cls => ({
        id: cls.id,
        course_name: cls.course_title || cls.course_name || cls.course_code,
        instructor_name: cls.instructor_name,
        instructor_code: cls.instructor_code,
        day: cls.day,
        start: cls.start_time,
        end: cls.end_time,
        group_number: cls.group_number || 1,
        units: cls.units || 2,
        level: cls.level || 'کارشناسی',
        term: cls.term || 'semester_1', // ← هماهنگ با کلیدهای جدید
        estimated_capacity: cls.room_capacity || cls.estimated_capacity || 30,
        match_status: cls.match_status || null,
        room_name: cls.room_name || null,
        room_id: cls.room_id || null,
        capacity: cls.room_capacity || null,
      }));

      if (assignedClasses.length === 0 && (!data.unassigned || data.unassigned.length === 0)) {
        setLocalInstructorData(null);
        setLoadError("هیچ کلاس زمان‌بندی‌شده‌ای برای این سبد یافت نشد.");
      } else {
        setLocalInstructorData({
          assigned: assignedClasses,
          unassigned: data.unassigned || [],
          all: assignedClasses,
        });
        localStorage.setItem('lastBasketId', String(basketIdToUse));
        if (data.scenario_id) {
          localStorage.setItem('lastWorkflowId', String(data.scenario_id));
        }
      }
    } catch (err) {
      console.error("خطا در بارگذاری زمان‌بندی:", err);
      if (err.response?.status === 404) {
        setLoadError("زمان‌بندی برای این سبد یافت نشد. لطفاً ابتدا زمان‌بندی را انجام دهید.");
      } else {
        setLoadError("خطا در بارگذاری اطلاعات زمان‌بندی. لطفاً دوباره تلاش کنید.");
      }
      setLocalInstructorData(null);
    } finally {
      setIsLoadingData(false);
    }
  };

  useEffect(() => {
    let effectiveBasketId = propBasketId;
    if (!effectiveBasketId) {
      const stored = localStorage.getItem('lastBasketId');
      if (stored) effectiveBasketId = stored;
    }
    if (effectiveBasketId) {
      setBasketId(effectiveBasketId);
      localStorage.setItem('lastBasketId', String(effectiveBasketId));
    }

    // نرمال‌سازی ترم از props یا localStorage
    const normalizedSemester = normalizeSemester(propSemester || localStorage.getItem('lastSemester') || "semester_1");
    setSemester(normalizedSemester);
    localStorage.setItem('lastSemester', normalizedSemester);

    if (instructorTimeData) {
      setLocalInstructorData(instructorTimeData);
      setLoadError(null);
      return;
    }

    if (effectiveBasketId) {
      loadDataFromServer(effectiveBasketId);
    } else {
      setLoadError("شناسه سبد موجود نیست. لطفاً یک سبد را انتخاب کنید.");
    }
  }, [instructorTimeData, propBasketId, propSemester]);

  useEffect(() => {
    if (localInstructorData && onInstructorDataLoaded) {
      onInstructorDataLoaded(localInstructorData);
    }
  }, [localInstructorData, onInstructorDataLoaded]);

  const effectiveInstructorData = instructorTimeData || localInstructorData;

  const handleRetryLoad = () => {
    const currentBasketId = basketId || localStorage.getItem('lastBasketId');
    if (currentBasketId) {
      setBasketId(currentBasketId);
      loadDataFromServer(currentBasketId);
    } else {
      setLoadError("شناسه سبد موجود نیست. لطفاً از صفحه مدیریت سبدها یک سبد را انتخاب کنید.");
    }
  };

  const handleProcess = () => {
    if (!effectiveInstructorData) {
      alert("داده‌های زمان‌بندی موجود نیست. لطفاً ابتدا زمان‌بندی را انجام دهید.");
      return;
    }

    const currentWorkflowId = workflowId || localStorage.getItem('lastWorkflowId');
    if (!currentWorkflowId) {
      alert("شناسه workflow موجود نیست. لطفاً ابتدا زمان‌بندی را انجام دهید.");
      return;
    }

    // بررسی وجود تخصیص قبلی
    if (hasPreviousAllocation) {
      const userConfirmed = window.confirm(
        "⚠️ شما قبلاً برای این سبد تخصیص اتاق انجام داده‌اید.\n\n" +
        "آیا می‌خواهید تخصیص جدید انجام دهید؟\n" +
        "(با انتخاب «بله» تخصیص جدید جایگزین تخصیص قبلی می‌شود.)\n" +
        "(با انتخاب «خیر» تخصیص قبلی بارگذاری می‌شود.)"
      );
      if (!userConfirmed) {
        // کاربر انتخاب کرد که تخصیص قبلی بارگذاری شود
        loadPreviousAllocation();
        return;
      }
      // کاربر انتخاب کرد که تخصیص جدید انجام شود
      // بنابراین ادامه می‌دهیم و تخصیص جدید انجام می‌شود
    }

    // ادامه فرآیند تخصیص جدید
    const currentSemester = semester || localStorage.getItem('lastSemester') || "semester_1";

    const dataForProcess = { ...effectiveInstructorData };
    if (dataForProcess.assigned) {
      dataForProcess.assigned = ensureCapacity(dataForProcess.assigned);
    }
    if (dataForProcess.all) {
      dataForProcess.all = ensureCapacity(dataForProcess.all);
    }

    console.log("📤 ارسال داده به تخصیص اتاق:", {
      totalClasses: dataForProcess.assigned?.length || 0,
      workflowId: currentWorkflowId,
      semester: currentSemester,
      sample: dataForProcess.assigned?.[0],
    });

    if (roomsList.length === 0) {
      alert("⚠️ هیچ اتاقی در سیستم ثبت نشده است. لطفاً ابتدا اتاق‌ها را اضافه کنید.");
      return;
    }

    if (typeof onProcess === 'function') {
      onProcess({
        schedule: dataForProcess.assigned || dataForProcess.all || [],
        workflowId: currentWorkflowId,
        semester: currentSemester,
        year: "1403"
      });
      // پس از انجام تخصیص جدید، تخصیص قبلی دیگر معتبر نیست
      setHasPreviousAllocation(false);
      setPreviousAllocationData([]);
    } else {
      console.warn("onProcess تعریف نشده است");
      alert("تابع تخصیص اتاق در دسترس نیست.");
    }
  };

  const hasRoomsAllocated = roomAllocationData.some(item => item.room_name && item.room_name !== 'بدون اتاق');

  // داده‌های کلاس‌ها (اولویت با roomAllocationData است)
  const classesData = roomAllocationData.length > 0 ? roomAllocationData : effectiveInstructorData?.assigned || [];

  // ============================================================
  // توابع تشخیص تداخل
  // ============================================================
  const checkConflict = (cls, allClasses) => {
    if (!cls.room_id || cls.room_name === 'بدون اتاق' || cls.room_name === '—') {
      return false;
    }
    return allClasses.some(other => {
      if (other.id === cls.id) return false;
      if (other.room_id !== cls.room_id) return false;
      if (other.day !== cls.day) return false;
      const toMinutes = (t) => {
        if (!t) return 0;
        const [h, m] = t.split(':').map(Number);
        return h * 60 + m;
      };
      const s1 = toMinutes(cls.start);
      const e1 = toMinutes(cls.end);
      const s2 = toMinutes(other.start);
      const e2 = toMinutes(other.end);
      return !(e1 <= s2 || e2 <= s1);
    });
  };

  const checkConflictForRoom = (classItem, newRoomId, allClasses) => {
    if (!newRoomId) return false;
    return allClasses.some(other => {
      if (other.id === classItem.id) return false;
      if (other.room_id !== newRoomId) return false;
      if (other.day !== classItem.day) return false;
      const toMinutes = (t) => {
        if (!t) return 0;
        const [h, m] = t.split(':').map(Number);
        return h * 60 + m;
      };
      const s1 = toMinutes(classItem.start);
      const e1 = toMinutes(classItem.end);
      const s2 = toMinutes(other.start);
      const e2 = toMinutes(other.end);
      return !(e1 <= s2 || e2 <= s1);
    });
  };

  const dataWithStatus = roomAllocationData.map(cls => ({
    ...cls,
    hasConflict: checkConflict(cls, roomAllocationData)
  }));

  // ============================================================
  // Drag & Drop Handlers
  // ============================================================
  const handleDragStart = (e, classItem) => {
    if (!classItem.id || !classItem.room_id) {
      e.preventDefault();
      return;
    }
    setDraggedClass({
      id: classItem.id,
      room_id: classItem.room_id,
      day: classItem.day,
      start: classItem.start,
      end: classItem.end,
      course_name: classItem.course_name,
    });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(classItem.id));
  };

  const handleDragEnd = (e) => {
    setDraggedClass(null);
    setDragOverRoomId(null);
  };

  const handleDragOver = (e, roomId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverRoomId(roomId);
  };

  const handleDragLeave = (e) => {
    setDragOverRoomId(null);
  };

  const handleDrop = async (e, targetRoomId, targetDay, targetSlotLabel) => {
    e.preventDefault();
    setDragOverRoomId(null);

    if (!draggedClass) {
      alert('ابتدا یک کلاس را بکشید.');
      return;
    }

    const [targetStart, targetEnd] = targetSlotLabel.split('-');

    if (draggedClass.room_id === targetRoomId) {
      alert('کلاس در همان اتاق قرار دارد.');
      return;
    }

    const hasConflict = checkConflictForRoom(
      { ...draggedClass, start: targetStart, end: targetEnd },
      targetRoomId,
      roomAllocationData
    );

    if (hasConflict) {
      alert(`❌ تداخل زمانی در اتاق انتخاب‌شده! یک کلاس دیگر در این بازه در این اتاق وجود دارد.`);
      return;
    }

    const classIndex = roomAllocationData.findIndex(c => c.id === draggedClass.id);
    if (classIndex === -1) {
      alert('کلاس مورد نظر یافت نشد.');
      return;
    }

    const targetRoom = roomsList.find(r => r.id === targetRoomId);
    if (!targetRoom) {
      alert('اتاق هدف یافت نشد.');
      return;
    }

    const updatedClass = {
      ...roomAllocationData[classIndex],
      room_id: targetRoomId,
      room_name: targetRoom.name,
      capacity: targetRoom.capacity,
    };

    const newData = [...roomAllocationData];
    newData[classIndex] = updatedClass;
    setRoomAllocationData(newData);

    try {
      const response = await axios.put(
        `http://localhost:8000/api/room-allocation/class/${draggedClass.id}/room`,
        { room_id: targetRoomId }
      );
      console.log('✅ اتاق با موفقیت به‌روزرسانی شد:', response.data);
      alert(`✅ اتاق کلاس "${draggedClass.course_name}" با موفقیت به "${targetRoom.name}" تغییر یافت.`);
    } catch (error) {
      console.error('❌ خطا در به‌روزرسانی اتاق:', error);
      setRoomAllocationData(roomAllocationData);
      alert(`❌ خطا در به‌روزرسانی: ${error.response?.data?.detail || error.message}`);
    }

    setDraggedClass(null);
  };

  // ============================================================
  // تابع ساخت ماتریس زمانی
  // ============================================================
  const buildRoomTimeMatrix = (day, roomsList, classesData) => {
    const dayClasses = classesData.filter(cls => cls.day === day);
    const intervalSet = new Set();
    dayClasses.forEach(cls => {
      if (cls.start && cls.end) {
        const key = `${cls.start}-${cls.end}`;
        intervalSet.add(key);
      }
    });
    const timeSlots = Array.from(intervalSet).map(key => {
      const [start, end] = key.split('-');
      return { label: key, start, end };
    }).sort((a, b) => a.start.localeCompare(b.start));

    let roomEntries = [];
    if (roomsList && roomsList.length > 0) {
      roomEntries = roomsList.map(room => ({
        room_id: room.id,
        room_name: room.name,
        capacity: room.capacity || 'نامشخص',
        room_type: room.room_type || room.type || 'عادی',
      }));
    } else {
      const roomMap = new Map();
      dayClasses.forEach(cls => {
        if (cls.room_id && cls.room_name && cls.room_name !== 'بدون اتاق' && cls.room_name !== '—') {
          if (!roomMap.has(cls.room_id)) {
            roomMap.set(cls.room_id, {
              room_id: cls.room_id,
              room_name: cls.room_name,
              capacity: cls.capacity || 'نامشخص',
              room_type: '',
            });
          }
        }
      });
      roomEntries = Array.from(roomMap.values());
      if (roomEntries.length === 0) {
        roomEntries = [{ room_id: 'no-room', room_name: 'بدون اتاق', capacity: '', room_type: '' }];
      }
    }

    const matrix = {};
    roomEntries.forEach(entry => {
      const key = entry.room_id;
      matrix[key] = {};
      timeSlots.forEach(slot => {
        matrix[key][slot.label] = [];
      });
    });

    dayClasses.forEach(cls => {
      const roomId = cls.room_id || 'no-room';
      if (!matrix[roomId]) {
        matrix[roomId] = {};
        timeSlots.forEach(slot => {
          matrix[roomId][slot.label] = [];
        });
        const exists = roomEntries.some(e => e.room_id === roomId);
        if (!exists) {
          roomEntries.push({
            room_id: roomId,
            room_name: cls.room_name || 'اتاق نامشخص',
            capacity: cls.capacity || 'نامشخص',
            room_type: '',
          });
        }
      }
      const slot = timeSlots.find(s => s.start === cls.start && s.end === cls.end);
      if (slot) {
        matrix[roomId][slot.label].push(cls);
      } else {
        console.warn(`⚠️ بازه زمانی برای کلاس ${cls.course_name} (${cls.start}-${cls.end}) در ماتریس یافت نشد`);
      }
    });

    return { roomEntries, matrix, timeSlots };
  };

  const { roomEntries, matrix, timeSlots } = buildRoomTimeMatrix(selectedDay, roomsList, classesData);

  // ============================================================
  // آمار تخصیص
  // ============================================================
  const stats = {
    total: roomAllocationData.length,
    withRoom: roomAllocationData.filter(c => c.room_name && c.room_name !== 'بدون اتاق' && c.room_name !== '—').length,
    withoutRoom: roomAllocationData.filter(c => !c.room_name || c.room_name === 'بدون اتاق' || c.room_name === '—').length,
    conflicts: roomAllocationData.filter(c => checkConflict(c, roomAllocationData)).length,
  };
  stats.coverage = stats.total > 0 ? Math.round((stats.withRoom / stats.total) * 100) : 0;

  // ============================================================
  // رندر
  // ============================================================
  return (
    <div className="process-page room-allocation-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">🏢</span>
          <h2>تخصیص اتاق</h2>
        </div>
        <p className="process-description">
          تخصیص اتاق‌های مناسب با در نظر گرفتن ظرفیت، نوع، تجهیزات و عدم تداخل هم‌زمان.
          برای تغییر اتاق یک کلاس، آن را با ماوس به سلول دیگر بکشید.
          {semester && (
            <span style={{ display: 'block', marginTop: '8px', fontSize: '0.9rem', color: '#4a5568' }}>
              📅 ترم جاری: {TERM_DISPLAY[semester] || semester}
            </span>
          )}
        </p>
      </div>

      <div className="process-body">
        <div className="controls-bar">
          <button
            onClick={handleProcess}
            disabled={!effectiveInstructorData || loading || isLoadingData || isLoadingRooms || isCheckingPrevious}
            className="btn-process"
          >
            {loading || isLoadingData || isCheckingPrevious ? "در حال بارگذاری..." : "تخصیص اتاق"}
          </button>
          {roomAllocationData.length > 0 && (
            <button onClick={onClear} className="btn-clear">
              پاک کردن نتایج
            </button>
          )}
          {!effectiveInstructorData && !isLoadingData && (
            <button onClick={handleRetryLoad} className="btn-secondary">
              🔄 تلاش مجدد
            </button>
          )}
          {/* دکمه بارگذاری تخصیص قبلی */}
          {hasPreviousAllocation && roomAllocationData.length === 0 && (
            <button onClick={loadPreviousAllocation} className="btn-secondary" style={{ backgroundColor: "#FFD700", color: "#333" }}>
              📂 بارگذاری تخصیص قبلی
            </button>
          )}
        </div>

        {/* پیام وجود تخصیص قبلی */}
        {hasPreviousAllocation && roomAllocationData.length === 0 && (
          <div className="info-box info-info" style={{ marginBottom: "1rem" }}>
            <span className="info-icon">ℹ️</span>
            <p>
              <strong>تخصیص قبلی برای این سبد وجود دارد.</strong>
              <br />
              برای بارگذاری آن، روی دکمه "بارگذاری تخصیص قبلی" کلیک کنید.
              <br />
              یا با کلیک روی "تخصیص اتاق"، تخصیص جدید انجام دهید (تخصیص قبلی بازنویسی می‌شود).
            </p>
          </div>
        )}

        {isLoadingData && (
          <div className="info-box info-info">
            <span className="info-icon">⏳</span>
            <p>در حال بارگذاری اطلاعات زمان‌بندی...</p>
          </div>
        )}

        {isLoadingRooms && (
          <div className="info-box info-info">
            <span className="info-icon">⏳</span>
            <p>در حال بارگذاری لیست اتاق‌ها...</p>
          </div>
        )}

        {isCheckingPrevious && (
          <div className="info-box info-info">
            <span className="info-icon">⏳</span>
            <p>در حال بررسی تخصیص قبلی...</p>
          </div>
        )}

        {loadError && !isLoadingData && (
          <div className="info-box info-error">
            <span className="info-icon">❌</span>
            <p>{loadError}</p>
          </div>
        )}

        {!effectiveInstructorData && !isLoadingData && !loadError && (
          <div className="info-box info-warning">
            <span className="info-icon">⚠️</span>
            <p>
              لطفاً ابتدا زمان‌بندی را انجام دهید. اگر زمان‌بندی قبلاً انجام شده،
              روی دکمه "تلاش مجدد" کلیک کنید.
            </p>
          </div>
        )}

        {roomsList.length === 0 && effectiveInstructorData && (
          <div className="info-box info-warning">
            <span className="info-icon">⚠️</span>
            <p>
              <strong>هیچ اتاقی در سیستم ثبت نشده است.</strong> لطفاً ابتدا از بخش "اتاق‌ها" اتاق‌های مورد نیاز را اضافه کنید.
            </p>
          </div>
        )}

        {/* نمایش برنامه زمان‌بندی اولیه */}
        {effectiveInstructorData && effectiveInstructorData.assigned?.length > 0 && (
          <div style={{ marginBottom: "2rem" }}>
            {!showSchedule ? (
              <button
                onClick={() => setShowSchedule(true)}
                className="btn-secondary"
                style={{
                  padding: "10px 20px",
                  borderRadius: "6px",
                  border: "1px solid #4A90D9",
                  backgroundColor: "#E8F0FE",
                  color: "#4A90D9",
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: "1rem",
                  transition: "all 0.2s",
                }}
              >
                📋 نمایش برنامه زمانبندی
              </button>
            ) : (
              <div className="schedule-preview">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <h4 style={{ margin: 0 }}>📋 برنامه زمانبندی فعلی (کلاس‌های دارای استاد و زمان)</h4>
                  <button
                    onClick={() => setShowSchedule(false)}
                    className="btn-secondary"
                    style={{
                      padding: "4px 12px",
                      borderRadius: "6px",
                      border: "1px solid #ccc",
                      backgroundColor: "#f5f5f5",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                    }}
                  >
                    ✖ بستن
                  </button>
                </div>
                <EditableDataTable
                  data={effectiveInstructorData.assigned}
                  columns={[
                    { key: "course_name", label: "درس" },
                    { key: "instructor_name", label: "استاد" },
                    { key: "day", label: "روز", render: (row) => DAY_NAMES[row.day] || row.day },
                    { key: "start", label: "شروع" },
                    { key: "end", label: "پایان" },
                    { key: "group_number", label: "گروه" },
                    { key: "estimated_capacity", label: "ظرفیت" },
                  ]}
                  title=""
                  editable={false}
                />
                <div style={{ fontSize: "0.9rem", color: "#555", marginTop: "0.5rem" }}>
                  تعداد کلاس‌های تخصیص‌یافته: {effectiveInstructorData.assigned.length}
                  {workflowId && ` | شناسه workflow: ${workflowId}`}
                  {basketId && ` | شناسه سبد: ${basketId}`}
                  {roomsList.length > 0 && ` | تعداد اتاق‌های موجود: ${roomsList.length}`}
                </div>
              </div>
            )}
          </div>
        )}

        {/* نتایج تخصیص */}
        {roomAllocationData.length > 0 && (
          <div className="result-container">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "8px" }}>
              <h4 style={{ margin: 0 }}>🏢 نتایج تخصیص اتاق</h4>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  onClick={() => { setShowTable(true); setShowMatrix(false); }}
                  className="btn-secondary"
                  style={{
                    padding: "8px 16px",
                    borderRadius: "6px",
                    border: "1px solid #4A90D9",
                    background: showTable && !showMatrix ? "#4A90D9" : "transparent",
                    color: showTable && !showMatrix ? "#fff" : "#4A90D9",
                    cursor: "pointer",
                    fontWeight: "bold",
                  }}
                >
                  📋 جدول تخصیص اتاق
                </button>
                <button
                  onClick={() => { setShowMatrix(true); setShowTable(false); }}
                  className="btn-secondary"
                  style={{
                    padding: "8px 16px",
                    borderRadius: "6px",
                    border: "1px solid #4A90D9",
                    background: showMatrix && !showTable ? "#4A90D9" : "transparent",
                    color: showMatrix && !showTable ? "#fff" : "#4A90D9",
                    cursor: "pointer",
                    fontWeight: "bold",
                  }}
                >
                  📊 ماتریس اتاق و زمان
                </button>
              </div>
            </div>

            {!hasRoomsAllocated && (
              <div className="info-box info-warning" style={{ marginBottom: "1rem" }}>
                <span className="info-icon">⚠️</span>
                <p>
                  <strong>هیچ اتاقی تخصیص داده نشده است.</strong> ممکن است دلیل آن یکی از موارد زیر باشد:
                  <br />
                  • اتاق‌های کافی در سیستم ثبت نشده باشد (تعداد اتاق‌های موجود: {roomsList.length}).
                  <br />
                  • ظرفیت اتاق‌ها با تعداد دانشجویان کلاس‌ها همخوانی نداشته باشد.
                  <br />
                  • تداخل زمانی بین کلاس‌ها باعث شده نتوان اتاق مناسبی پیدا کرد.
                  <br />
                  لطفاً لیست اتاق‌ها را بررسی کرده و در صورت نیاز اتاق‌های بیشتری اضافه کنید.
                  <br />
                  <strong>توجه:</strong> ظرفیت کلاس‌ها ممکن است به‌درستی تنظیم نشده باشد. از بخش مدیریت سبد، ظرفیت کلاس‌ها را بررسی کنید.
                </p>
              </div>
            )}

            {/* جدول نتایج تخصیص */}
            {showTable && (
              <EditableDataTable
                data={dataWithStatus}
                columns={[
                  { key: "course_name", label: "درس" },
                  { key: "instructor_name", label: "استاد" },
                  { key: "day", label: "روز" },
                  { key: "start", label: "شروع" },
                  { key: "end", label: "پایان" },
                  { key: "room_name", label: "اتاق" },
                  { key: "capacity", label: "ظرفیت" },
                  { key: "group_number", label: "گروه" },
                  {
                    key: "hasConflict",
                    label: "وضعیت",
                    render: (row) => {
                      const isConflict = row.hasConflict;
                      return (
                        <span style={{
                          display: "inline-block",
                          padding: "4px 10px",
                          borderRadius: "4px",
                          backgroundColor: isConflict ? "#FADBD8" : "#D5F5E3",
                          color: "#333",
                          fontWeight: "bold",
                          fontSize: "0.85rem"
                        }}>
                          {isConflict ? "⚠️ تداخل" : "✅ بدون تداخل"}
                        </span>
                      );
                    }
                  },
                ]}
                title="برنامه نهایی با اتاق"
                editable={false}
              />
            )}

            {/* ماتریس زمانی با Drag & Drop */}
            {showMatrix && (classesData.length > 0 || roomsList.length > 0) && (
              <div className="time-matrix-container" style={{ marginTop: "2rem", overflowX: "auto" }}>
                <h4>📅 ماتریس زمانی اتاق‌ها (برای تغییر اتاق، کلاس را بکشید)</h4>

                <div className="day-selector" style={{ display: "flex", gap: "8px", marginBottom: "1rem", flexWrap: "wrap" }}>
                  {DAY_NAMES.map((name, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedDay(index)}
                      style={{
                        padding: "8px 16px",
                        borderRadius: "6px",
                        border: "1px solid #ccc",
                        cursor: "pointer",
                        backgroundColor: selectedDay === index ? "#4A90D9" : "#f0f0f0",
                        color: selectedDay === index ? "#fff" : "#333",
                        fontWeight: selectedDay === index ? "bold" : "normal",
                        transition: "all 0.2s",
                      }}
                    >
                      {name}
                    </button>
                  ))}
                </div>

                {roomEntries.length > 0 ? (
                  <div style={{ overflowX: "auto" }}>
                    {timeSlots.length > 0 ? (
                      <table className="time-matrix" style={{ borderCollapse: "collapse", width: "100%", minWidth: "700px" }}>
                        <thead>
                          <tr>
                            <th style={{ padding: "8px", border: "1px solid #ccc", backgroundColor: "#f9f9f9", minWidth: "180px", textAlign: "right" }}>
                              اتاق (ظرفیت - نوع)
                            </th>
                            {timeSlots.map(slot => (
                              <th key={slot.label} style={{ padding: "8px", border: "1px solid #ccc", backgroundColor: "#f9f9f9", textAlign: "center", minWidth: "100px" }}>
                                {slot.label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {roomEntries.map(entry => {
                            const roomId = entry.room_id;
                            const row = matrix[roomId] || {};
                            const typeLabel = entry.room_type === 'lab' ? 'آزمایشگاه' : (entry.room_type === 'normal' ? 'عادی' : entry.room_type);
                            const headerText = `${entry.room_name} (${entry.capacity || '?'} - ${typeLabel || 'نامشخص'})`;
                            return (
                              <tr key={roomId}>
                                <td style={{ padding: "8px", border: "1px solid #ccc", fontWeight: "bold", textAlign: "right", backgroundColor: "#fafafa", fontSize: "0.9rem" }}>
                                  {headerText}
                                </td>
                                {timeSlots.map(slot => {
                                  const classesInSlot = row[slot.label] || [];
                                  const count = classesInSlot.length;
                                  const isDraggedOver = dragOverRoomId === roomId && draggedClass;

                                  let bgColor = "#D4E6F1";
                                  let content = "";
                                  let draggable = false;
                                  let classItem = null;

                                  if (count === 0) {
                                    bgColor = "#D4E6F1";
                                    content = "—";
                                  } else if (count === 1) {
                                    bgColor = "#D5F5E3";
                                    const cls = classesInSlot[0];
                                    classItem = cls;
                                    draggable = true;
                                    content = `${cls.instructor_name || "نامشخص"}\n${cls.course_name}`;
                                  } else {
                                    bgColor = "#FADBD8";
                                    const items = classesInSlot.map(cls =>
                                      `${cls.instructor_name || "نامشخص"} (${cls.course_name})`
                                    ).join(" / ");
                                    content = items;
                                    draggable = false;
                                  }

                                  if (count > 1) draggable = false;

                                  const dropBgColor = isDraggedOver ? "#D4EDDA" : bgColor;

                                  return (
                                    <td
                                      key={slot.label}
                                      style={{
                                        padding: "8px",
                                        border: "1px solid #ccc",
                                        backgroundColor: dropBgColor,
                                        textAlign: "center",
                                        verticalAlign: "middle",
                                        fontSize: "0.85rem",
                                        whiteSpace: "pre-wrap",
                                        wordBreak: "break-word",
                                        color: "#333",
                                        minHeight: "60px",
                                        cursor: draggable ? "grab" : "default",
                                        transition: "background-color 0.2s",
                                      }}
                                      title={count > 1 ? `تداخل: ${count} کلاس در این بازه` : (count === 1 ? classesInSlot[0].course_name : "خالی")}
                                      onDragOver={(e) => handleDragOver(e, roomId)}
                                      onDragLeave={handleDragLeave}
                                      onDrop={(e) => handleDrop(e, roomId, selectedDay, slot.label)}
                                      draggable={draggable}
                                      onDragStart={draggable ? (e) => handleDragStart(e, classItem) : undefined}
                                      onDragEnd={handleDragEnd}
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
                    ) : (
                      <div style={{ marginTop: "1rem" }}>
                        <p style={{ color: "#555", marginBottom: "0.5rem" }}>📌 هیچ کلاسی در این روز تخصیص داده نشده است، اما اتاق‌های موجود:</p>
                        <table style={{ borderCollapse: "collapse", width: "100%", border: "1px solid #ccc" }}>
                          <thead>
                            <tr>
                              <th style={{ padding: "8px", border: "1px solid #ccc", backgroundColor: "#f9f9f9", textAlign: "right" }}>نام اتاق</th>
                              <th style={{ padding: "8px", border: "1px solid #ccc", backgroundColor: "#f9f9f9", textAlign: "center" }}>ظرفیت</th>
                              <th style={{ padding: "8px", border: "1px solid #ccc", backgroundColor: "#f9f9f9", textAlign: "center" }}>نوع</th>
                            </tr>
                          </thead>
                          <tbody>
                            {roomEntries.map(entry => (
                              <tr key={entry.room_id}>
                                <td style={{ padding: "8px", border: "1px solid #ccc", textAlign: "right" }}>{entry.room_name}</td>
                                <td style={{ padding: "8px", border: "1px solid #ccc", textAlign: "center" }}>{entry.capacity || 'نامشخص'}</td>
                                <td style={{ padding: "8px", border: "1px solid #ccc", textAlign: "center" }}>
                                  {entry.room_type === 'lab' ? 'آزمایشگاه' : (entry.room_type === 'normal' ? 'عادی' : entry.room_type || 'نامشخص')}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="info-box info-info">
                    <span className="info-icon">ℹ️</span>
                    <p>هیچ اتاقی در سیستم ثبت نشده است.</p>
                  </div>
                )}

                <div style={{ fontSize: "0.85rem", color: "#555", marginTop: "0.5rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  <span><span style={{ display: "inline-block", width: "16px", height: "16px", backgroundColor: "#D5F5E3", border: "1px solid #aaa", marginRight: "4px" }}></span> بدون تداخل</span>
                  <span><span style={{ display: "inline-block", width: "16px", height: "16px", backgroundColor: "#FADBD8", border: "1px solid #aaa", marginRight: "4px" }}></span> تداخل</span>
                  <span><span style={{ display: "inline-block", width: "16px", height: "16px", backgroundColor: "#D4E6F1", border: "1px solid #aaa", marginRight: "4px" }}></span> خالی</span>
                  <span style={{ marginRight: "1rem" }}>🖱️ برای تغییر اتاق، کلاس را با ماوس بکشید.</span>
                </div>
              </div>
            )}

            {/* ========== بخش آمار ========== */}
            <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#f8f9fa", borderRadius: "8px", border: "1px solid #dee2e6" }}>
              <h4 style={{ margin: "0 0 0.5rem 0" }}>📊 آمار تخصیص اتاق</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem", fontSize: "0.95rem" }}>
                <div><strong>کل کلاس‌ها:</strong> {stats.total}</div>
                <div><strong>✅ دارای اتاق:</strong> {stats.withRoom} ({stats.coverage}%)</div>
                <div><strong>❌ بدون اتاق:</strong> {stats.withoutRoom}</div>
                <div><strong>⚠️ تداخل‌دار:</strong> {stats.conflicts}</div>
              </div>
              {stats.withoutRoom > 0 && (
                <div style={{ marginTop: "0.5rem", color: "#856404", backgroundColor: "#fff3cd", padding: "0.5rem", borderRadius: "4px" }}>
                  ⚠️ {stats.withoutRoom} کلاس هنوز اتاق ندارند. لطفاً با کشیدن آنها به اتاق مناسب، تخصیص را تکمیل کنید.
                </div>
              )}
              {stats.conflicts > 0 && (
                <div style={{ marginTop: "0.5rem", color: "#721c24", backgroundColor: "#f8d7da", padding: "0.5rem", borderRadius: "4px" }}>
                  ⚠️ {stats.conflicts} کلاس با تداخل زمانی در اتاق خود دارند. لطفاً آنها را به اتاق دیگری منتقل کنید.
                </div>
              )}
              {stats.withRoom === stats.total && stats.conflicts === 0 && stats.total > 0 && (
                <div style={{ marginTop: "0.5rem", color: "#155724", backgroundColor: "#d4edda", padding: "0.5rem", borderRadius: "4px" }}>
                  ✅ همه کلاس‌ها به‌درستی تخصیص یافته‌اند و هیچ تداخلی وجود ندارد.
                </div>
              )}
            </div>

            <div className="result-actions">
              <button onClick={onNext} className="btn-primary" disabled={loading}>
                {loading ? "در حال..." : "⚡ مرحله بعد: بهینه‌سازی"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}