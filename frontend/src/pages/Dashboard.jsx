// frontend/src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import BaseInfoPages from "./BaseInfoPages";
import SchedulePages from "./SchedulePages";
import DashboardHome from "./DashboardHome";
import BasketListPage from "./BasketListPage";

// ===== APIهای اطلاعات پایه =====
import {
  getUniqueCourses,
  getOfferedCourses,
  getInstructorsList,
  getRoomsList,
  createUniqueCourse,
  updateUniqueCourse,
  deleteUniqueCourse,
  createOfferedCourse,
  updateOfferedCourse,
  deleteOfferedCourse,
  uploadExcelFile,
  createInstructor,
  updateInstructor,
  deleteInstructor,
  uploadInstructorsExcel,
  createRoom,
  updateRoom,
  deleteRoom,
  uploadRoomsExcel,
} from "../api/courseApi";

// ===== APIهای سوابق، دروس ترمیک و مطلوبیت‌ها =====
import { getHistoryList, createHistory, updateHistory, deleteHistory, uploadHistoryExcel } from "../api/scheduleHistoryApi";
import { getTermCourses, createTermCourse, updateTermCourse, deleteTermCourse, uploadTermCoursesExcel } from "../api/termCourseApi";
import { getTeachingPreferences, createTeachingPreference, updateTeachingPreference, deleteTeachingPreference, uploadTeachingPreferencesExcel } from "../api/teachingPreferenceApi";
import { getTimePreferences, createTimePreference, updateTimePreference, deleteTimePreference, uploadTimePreferencesExcel } from "../api/timePreferenceApi";

// ===== APIهای workflow =====
import {
  startWorkflow,
  runStep2,
  runStep3,
  runStep4,
  runStep5,
  finalizeWorkflow,
  updateWorkflowStep,
  processBasket,
  processSchedule,
  processRooms,
  processOptimize,
  getInitialBasket,
  addStatisticsToBasket,
} from "../api/workflowApi";

// ===== APIهای تولید برنامه =====
import { generateSchedule, getRankedCourses } from "../api/scheduleApi";

// ===== لیست مقاطع پیش‌فرض =====
const DEFAULT_LEVELS = ["پیوسته 1394", "پیوسته 1403", "ناپیوسته"];

export default function Dashboard() {
  // ===== وضعیت‌های عمومی =====
  const [activePage, setActivePage] = useState("basket-list"); // صفحه پیش‌فرض: لیست سبدها
  const [semester, setSemester] = useState("mehr");
  const [loading, setLoading] = useState(false);
  const [schedule, setSchedule] = useState(null);
  const [rankedCourses, setRankedCourses] = useState([]);

  // ===== داده‌های پایه =====
  const [uniqueCourses, setUniqueCourses] = useState([]);
  const [offeredCourses, setOfferedCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [historyRecords, setHistoryRecords] = useState([]);
  const [termCourses, setTermCourses] = useState([]);
  const [teachingPreferences, setTeachingPreferences] = useState([]);
  const [timePreferences, setTimePreferences] = useState([]);

  // ===== وضعیت‌های workflow قدیمی =====
  const [workflowId, setWorkflowId] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [workflowSteps, setWorkflowSteps] = useState([]);
  const [workflowLoading, setWorkflowLoading] = useState(false);

  // ===== وضعیت‌های فرایندهای چهارگانه جدید =====
  const [basketData, setBasketData] = useState(null);
  const [instructorTimeData, setInstructorTimeData] = useState(null);
  const [roomAllocationData, setRoomAllocationData] = useState(null);
  const [optimizedData, setOptimizedData] = useState(null);
  const [processLoading, setProcessLoading] = useState(false);
  const [currentBasketId, setCurrentBasketId] = useState(null);

  // ============================================================
  // بارگذاری داده‌های پایه
  // ============================================================
  async function loadBaseData() {
    setLoading(true);
    try {
      const [u, o, i, r, h, t, tp, tim] = await Promise.all([
        getUniqueCourses().catch(() => []),
        getOfferedCourses().catch(() => []),
        getInstructorsList().catch(() => []),
        getRoomsList().catch(() => []),
        getHistoryList().catch(() => []),
        getTermCourses().catch(() => []),
        getTeachingPreferences().catch(() => []),
        getTimePreferences().catch(() => []),
      ]);
      setUniqueCourses(u);
      setOfferedCourses(o);
      setInstructors(i);
      setRooms(r);
      setHistoryRecords(h);
      setTermCourses(t);
      setTeachingPreferences(tp);
      setTimePreferences(tim);
    } catch (error) {
      console.error("خطا در بارگذاری داده‌ها:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBaseData();
  }, [semester]);

  // ============================================================
  // توابع مدیریت اطلاعات پایه (جهت ارسال به BaseInfoPages)
  // ============================================================

  // ----- دروس یکتا -----
  const handleAddUnique = async (data) => {
    try {
      const result = await createUniqueCourse(data);
      setUniqueCourses([...uniqueCourses, result]);
    } catch (error) {
      console.error("خطا در افزودن درس یکتا:", error);
      alert("خطا در افزودن درس یکتا");
    }
  };
  const handleUpdateUnique = async (id, data) => {
    try {
      const result = await updateUniqueCourse(id, data);
      setUniqueCourses(uniqueCourses.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش درس یکتا:", error);
      alert("خطا در ویرایش درس یکتا");
    }
  };
  const handleDeleteUnique = async (id) => {
    if (window.confirm("آیا از حذف این درس مطمئن هستید؟")) {
      try {
        await deleteUniqueCourse(id);
        setUniqueCourses(uniqueCourses.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف درس یکتا:", error);
        alert("خطا در حذف درس یکتا");
      }
    }
  };
  const handleUploadUnique = async (file) => {
    try {
      const result = await uploadExcelFile(file, "unique");
      alert(`بارگذاری موفق. ${result.count} درس افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- دروس ارائه -----
  const handleAddOffered = async (data) => {
    try {
      const result = await createOfferedCourse(data);
      setOfferedCourses([...offeredCourses, result]);
    } catch (error) {
      console.error("خطا در افزودن درس ارائه:", error);
      alert("خطا در افزودن درس ارائه");
    }
  };
  const handleUpdateOffered = async (id, data) => {
    try {
      const result = await updateOfferedCourse(id, data);
      setOfferedCourses(offeredCourses.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش درس ارائه:", error);
      alert("خطا در ویرایش درس ارائه");
    }
  };
  const handleDeleteOffered = async (id) => {
    if (window.confirm("آیا از حذف این درس مطمئن هستید؟")) {
      try {
        await deleteOfferedCourse(id);
        setOfferedCourses(offeredCourses.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف درس ارائه:", error);
        alert("خطا در حذف درس ارائه");
      }
    }
  };
  const handleUploadOffered = async (file) => {
    try {
      const result = await uploadExcelFile(file, "offered");
      alert(`بارگذاری موفق. ${result.count} درس افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- اساتید -----
  const handleAddInstructor = async (data) => {
    try {
      const result = await createInstructor(data);
      setInstructors([...instructors, result]);
    } catch (error) {
      console.error("خطا در افزودن استاد:", error);
      alert("خطا در افزودن استاد");
    }
  };
  const handleUpdateInstructor = async (id, data) => {
    try {
      const result = await updateInstructor(id, data);
      setInstructors(instructors.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش استاد:", error);
      alert("خطا در ویرایش استاد");
    }
  };
  const handleDeleteInstructor = async (id) => {
    if (window.confirm("آیا از حذف این استاد مطمئن هستید؟")) {
      try {
        await deleteInstructor(id);
        setInstructors(instructors.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف استاد:", error);
        alert("خطا در حذف استاد");
      }
    }
  };
  const handleUploadInstructor = async (file) => {
    try {
      const result = await uploadInstructorsExcel(file);
      alert(`بارگذاری موفق. ${result.count} استاد افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل اساتید:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- اتاق‌ها -----
  const handleAddRoom = async (data) => {
    try {
      const result = await createRoom(data);
      setRooms([...rooms, result]);
    } catch (error) {
      console.error("خطا در افزودن اتاق:", error);
      alert("خطا در افزودن اتاق");
    }
  };
  const handleUpdateRoom = async (id, data) => {
    try {
      const result = await updateRoom(id, data);
      setRooms(rooms.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش اتاق:", error);
      alert("خطا در ویرایش اتاق");
    }
  };
  const handleDeleteRoom = async (id) => {
    if (window.confirm("آیا از حذف این اتاق مطمئن هستید؟")) {
      try {
        await deleteRoom(id);
        setRooms(rooms.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف اتاق:", error);
        alert("خطا در حذف اتاق");
      }
    }
  };
  const handleUploadRoom = async (file) => {
    try {
      const result = await uploadRoomsExcel(file);
      alert(`بارگذاری موفق. ${result.count} اتاق افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل اتاق‌ها:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- سوابق برنامه‌ریزی -----
  const handleAddHistory = async (data) => {
    try {
      const result = await createHistory(data);
      setHistoryRecords([...historyRecords, result]);
    } catch (error) {
      console.error("خطا در افزودن سابقه:", error);
      alert("خطا در افزودن سابقه");
    }
  };
  const handleUpdateHistory = async (id, data) => {
    try {
      const result = await updateHistory(id, data);
      setHistoryRecords(historyRecords.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش سابقه:", error);
      alert("خطا در ویرایش سابقه");
    }
  };
  const handleDeleteHistory = async (id) => {
    if (window.confirm("آیا از حذف این رکورد مطمئن هستید؟")) {
      try {
        await deleteHistory(id);
        setHistoryRecords(historyRecords.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف سابقه:", error);
        alert("خطا در حذف سابقه");
      }
    }
  };
  const handleUploadHistory = async (file) => {
    try {
      const result = await uploadHistoryExcel(file);
      alert(`بارگذاری موفق. ${result.count} رکورد افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل سوابق:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- دروس ترمیک -----
  const handleAddTermCourse = async (data) => {
    try {
      const result = await createTermCourse(data);
      setTermCourses([...termCourses, result]);
    } catch (error) {
      console.error("خطا در افزودن درس ترمیک:", error);
      alert("خطا در افزودن درس ترمیک");
    }
  };
  const handleUpdateTermCourse = async (id, data) => {
    try {
      const result = await updateTermCourse(id, data);
      setTermCourses(termCourses.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش درس ترمیک:", error);
      alert("خطا در ویرایش درس ترمیک");
    }
  };
  const handleDeleteTermCourse = async (id) => {
    if (window.confirm("آیا از حذف این درس ترمیک مطمئن هستید؟")) {
      try {
        await deleteTermCourse(id);
        setTermCourses(termCourses.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف درس ترمیک:", error);
        alert("خطا در حذف درس ترمیک");
      }
    }
  };
  const handleUploadTermCourse = async (file) => {
    try {
      const result = await uploadTermCoursesExcel(file);
      alert(`بارگذاری موفق. ${result.count} درس ترمیک افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل دروس ترمیک:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- مطلوبیت‌های تدریس -----
  const handleAddTeachingPref = async (data) => {
    try {
      const result = await createTeachingPreference(data);
      setTeachingPreferences([...teachingPreferences, result]);
    } catch (error) {
      console.error("خطا در افزودن مطلوبیت تدریس:", error);
      alert("خطا در افزودن مطلوبیت تدریس");
    }
  };
  const handleUpdateTeachingPref = async (id, data) => {
    try {
      const result = await updateTeachingPreference(id, data);
      setTeachingPreferences(teachingPreferences.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش مطلوبیت تدریس:", error);
      alert("خطا در ویرایش مطلوبیت تدریس");
    }
  };
  const handleDeleteTeachingPref = async (id) => {
    if (window.confirm("آیا از حذف این مطلوبیت تدریس مطمئن هستید؟")) {
      try {
        await deleteTeachingPreference(id);
        setTeachingPreferences(teachingPreferences.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف مطلوبیت تدریس:", error);
        alert("خطا در حذف مطلوبیت تدریس");
      }
    }
  };
  const handleUploadTeachingPref = async (file) => {
    try {
      const result = await uploadTeachingPreferencesExcel(file);
      alert(`بارگذاری موفق. ${result.count} مطلوبیت تدریس افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل مطلوبیت‌های تدریس:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ----- مطلوبیت‌های زمان‌بندی -----
  const handleAddTimePref = async (data) => {
    try {
      const result = await createTimePreference(data);
      setTimePreferences([...timePreferences, result]);
    } catch (error) {
      console.error("خطا در افزودن مطلوبیت زمان‌بندی:", error);
      alert("خطا در افزودن مطلوبیت زمان‌بندی");
    }
  };
  const handleUpdateTimePref = async (id, data) => {
    try {
      const result = await updateTimePreference(id, data);
      setTimePreferences(timePreferences.map((c) => (c.id === id ? result : c)));
    } catch (error) {
      console.error("خطا در ویرایش مطلوبیت زمان‌بندی:", error);
      alert("خطا در ویرایش مطلوبیت زمان‌بندی");
    }
  };
  const handleDeleteTimePref = async (id) => {
    if (window.confirm("آیا از حذف این مطلوبیت زمان‌بندی مطمئن هستید؟")) {
      try {
        await deleteTimePreference(id);
        setTimePreferences(timePreferences.filter((c) => c.id !== id));
      } catch (error) {
        console.error("خطا در حذف مطلوبیت زمان‌بندی:", error);
        alert("خطا در حذف مطلوبیت زمان‌بندی");
      }
    }
  };
  const handleUploadTimePref = async (file) => {
    try {
      const result = await uploadTimePreferencesExcel(file);
      alert(`بارگذاری موفق. ${result.count} مطلوبیت زمان‌بندی افزوده شد.`);
      loadBaseData();
    } catch (error) {
      console.error("خطا در بارگذاری اکسل مطلوبیت‌های زمان‌بندی:", error);
      alert("خطا در بارگذاری فایل اکسل");
    }
  };

  // ============================================================
  // توابع workflow قدیمی (۵ مرحله‌ای)
  // ============================================================
  const handleStartWorkflow = async () => {
    setWorkflowLoading(true);
    try {
      const data = await startWorkflow({
        semester,
        levels: DEFAULT_LEVELS,
        year: "1403",
      });
      setWorkflowId(data.workflow_id);
      const integrated = data.step1_data?.integrated_courses || [];
      setWorkflowSteps([{ data: integrated }]);
      setCurrentStep(0);
      alert("گام اول با موفقیت انجام شد.");
    } catch (e) {
      console.error("خطا در شروع فرایند:", e);
      alert("خطا در شروع فرایند: " + e.message);
    } finally {
      setWorkflowLoading(false);
    }
  };

  const handleUpdateStepData = async (stepIndex, newData, saveToServer = false) => {
    const newSteps = [...workflowSteps];
    newSteps[stepIndex] = { data: newData };
    setWorkflowSteps(newSteps);
    if (saveToServer && workflowId) {
      try {
        await updateWorkflowStep(workflowId, stepIndex + 1, newData);
        alert("تغییرات ذخیره شد.");
      } catch (error) {
        console.error("خطا در ذخیره‌سازی تغییرات:", error);
        alert("خطا در ذخیره‌سازی تغییرات");
      }
    }
  };

  const handleNextStep = async () => {
    if (!workflowId) return;
    setWorkflowLoading(true);
    try {
      if (currentStep === 1 || currentStep === 2) {
        const currentData = workflowSteps[currentStep]?.data || [];
        await handleUpdateStepData(currentStep, currentData, true);
      }
      let response;
      const nextIndex = currentStep + 1;
      if (currentStep === 0) response = await runStep2(workflowId);
      else if (currentStep === 1) response = await runStep3(workflowId);
      else if (currentStep === 2) response = await runStep4(workflowId);
      else if (currentStep === 3) response = await runStep5(workflowId);
      else throw new Error("مرحله نامعتبر");

      let dataArray = response;
      if (response && typeof response === "object" && !Array.isArray(response)) {
        const keys = Object.keys(response);
        for (const key of keys) {
          if (key.endsWith("_data") && Array.isArray(response[key])) {
            dataArray = response[key];
            break;
          }
        }
        if (!Array.isArray(dataArray)) dataArray = [response];
      }
      if (!Array.isArray(dataArray)) dataArray = [dataArray];

      const newSteps = [...workflowSteps];
      newSteps[nextIndex] = { data: dataArray };
      setWorkflowSteps(newSteps);
      setCurrentStep(nextIndex);
    } catch (e) {
      console.error("خطا در ادامه فرایند:", e);
      alert("خطا در اجرای مرحله: " + e.message);
    } finally {
      setWorkflowLoading(false);
    }
  };

  const handlePrevStep = () => {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  };

  const handleFinalize = async () => {
    if (!workflowId) return;
    setWorkflowLoading(true);
    try {
      const finalData = workflowSteps[4]?.data || [];
      const result = await finalizeWorkflow(workflowId, finalData);
      alert("✅ برنامه نهایی ذخیره شد.");
      setSchedule({ classes: result.data || finalData });
      setWorkflowId(null);
      setCurrentStep(0);
      setWorkflowSteps([]);
    } catch (e) {
      console.error("خطا در نهایی‌سازی:", e);
      alert("خطا در نهایی‌سازی: " + e.message);
    } finally {
      setWorkflowLoading(false);
    }
  };

  // ============================================================
  // تولید برنامه سریع (قدیمی)
  // ============================================================
  const handleGenerateSchedule = async () => {
    setLoading(true);
    try {
      const data = await generateSchedule({
        semester,
        levels: null,
        year: "1403",
        max_groups_per_course: 3,
        demand_threshold: 15,
        number_of_scenarios: 3,
        max_courses: 50,
      });
      setSchedule(data);
      if (data?.ranked_courses) setRankedCourses(data.ranked_courses);
    } catch (e) {
      console.error("خطا در تولید برنامه:", e);
      alert("خطا در تولید برنامه: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // فرایندهای چهارگانه جدید (با پشتیبانی از دو مرحله‌ای)
  // ============================================================
  const handleBasketComplete = (data) => {
    setBasketData(data);
    alert("سبد دروس تکمیل شد.");
  };

  const handleBasketCreated = (basketId) => {
    if (basketId === null) {
      // کاربر از دکمه "بازگشت به لیست سبدها" استفاده کرده است
      setActivePage("basket-list");
      setCurrentBasketId(null);
    } else {
      setCurrentBasketId(basketId);
    }
  };

  const handleProcessSchedule = async () => {
    if (!basketData) return alert("ابتدا سبد دروس را شناسایی کنید.");
    setProcessLoading(true);
    try {
      const result = await processSchedule({ basket: basketData });
      setInstructorTimeData(result);
      alert(`زمان‌بندی انجام شد. ${result.assigned?.length || 0} کلاس تخصیص یافت، ${result.unassigned?.length || 0} کلاس بدون استاد باقی ماند.`);
    } catch (e) {
      console.error("خطا در زمان‌بندی:", e);
      alert("خطا در زمان‌بندی: " + e.message);
    } finally {
      setProcessLoading(false);
    }
  };

  const handleManualAssignComplete = (updatedData) => {
    console.log("📋 تخصیص دستی تکمیل شد:", updatedData);
    if (updatedData && typeof updatedData === "object") {
      setInstructorTimeData(updatedData);
    }
  };

  const handleNextToRooms = () => {
    const unassignedCount = instructorTimeData?.unassigned?.length || 0;
    if (unassignedCount > 0) {
      const confirmMsg = `${unassignedCount} کلاس بدون استاد باقی مانده است. آیا مطمئن هستید که می‌خواهید به مرحله بعد بروید؟`;
      if (!window.confirm(confirmMsg)) {
        return;
      }
    }
    setActivePage("room-allocation");
  };

  const handleProcessRooms = async () => {
    if (!instructorTimeData) return alert("ابتدا زمان‌بندی را انجام دهید.");
    setProcessLoading(true);
    try {
      const allClasses = instructorTimeData.all || instructorTimeData.assigned || [];
      const result = await processRooms({ schedule: allClasses });
      setRoomAllocationData(result.allocated || result);
      alert("تخصیص اتاق انجام شد.");
    } catch (e) {
      console.error("خطا در تخصیص اتاق:", e);
      alert("خطا در تخصیص اتاق: " + e.message);
    } finally {
      setProcessLoading(false);
    }
  };

  const handleProcessOptimize = async () => {
    if (!roomAllocationData) return alert("ابتدا تخصیص اتاق را انجام دهید.");
    setProcessLoading(true);
    try {
      const result = await processOptimize({ schedule: roomAllocationData });
      setOptimizedData(result.optimized || result);
      alert("بهینه‌سازی انجام شد.");
    } catch (e) {
      console.error("خطا در بهینه‌سازی:", e);
      alert("خطا در بهینه‌سازی: " + e.message);
    } finally {
      setProcessLoading(false);
    }
  };

  const handleClearSchedule = () => setInstructorTimeData(null);
  const handleClearRooms = () => setRoomAllocationData(null);
  const handleClearOptimize = () => setOptimizedData(null);

  // ============================================================
  // تابع هدایت به لیست سبدها (برای استفاده در SchedulePages و InstructorTimePage)
  // ============================================================
  const handleNavigateToBasketList = () => {
    setActivePage("basket-list");
  };

  // ============================================================
  // رندر محتوای اصلی
  // ============================================================
  const renderContent = () => {
    // ===== صفحه‌ی جدید: لیست سبدها =====
    if (activePage === "basket-list") {
      return (
        <BasketListPage
          onNavigateToBasket={(basketId) => {
            setCurrentBasketId(basketId);
            setActivePage("basket");
          }}
          onNavigateToNewBasket={(newBasketId) => {
            setCurrentBasketId(newBasketId);
            setActivePage("basket");
          }}
        />
      );
    }

    // صفحات اطلاعات پایه
    const basePages = [
      "unique-courses",
      "offered-courses",
      "instructors",
      "rooms",
      "schedule-history",
      "term-courses",
      "teaching-preferences",
      "time-preferences",
    ];
    if (basePages.includes(activePage)) {
      return (
        <BaseInfoPages
          activePage={activePage}
          semester={semester}
          uniqueCourses={uniqueCourses}
          offeredCourses={offeredCourses}
          instructors={instructors}
          rooms={rooms}
          historyRecords={historyRecords}
          termCourses={termCourses}
          teachingPreferences={teachingPreferences}
          timePreferences={timePreferences}
          onDataChange={loadBaseData}
          onAddUnique={handleAddUnique}
          onUpdateUnique={handleUpdateUnique}
          onDeleteUnique={handleDeleteUnique}
          onUploadUnique={handleUploadUnique}
          onAddOffered={handleAddOffered}
          onUpdateOffered={handleUpdateOffered}
          onDeleteOffered={handleDeleteOffered}
          onUploadOffered={handleUploadOffered}
          onAddInstructor={handleAddInstructor}
          onUpdateInstructor={handleUpdateInstructor}
          onDeleteInstructor={handleDeleteInstructor}
          onUploadInstructor={handleUploadInstructor}
          onAddRoom={handleAddRoom}
          onUpdateRoom={handleUpdateRoom}
          onDeleteRoom={handleDeleteRoom}
          onUploadRoom={handleUploadRoom}
          onAddHistory={handleAddHistory}
          onUpdateHistory={handleUpdateHistory}
          onDeleteHistory={handleDeleteHistory}
          onUploadHistory={handleUploadHistory}
          onAddTermCourse={handleAddTermCourse}
          onUpdateTermCourse={handleUpdateTermCourse}
          onDeleteTermCourse={handleDeleteTermCourse}
          onUploadTermCourse={handleUploadTermCourse}
          onAddTeachingPref={handleAddTeachingPref}
          onUpdateTeachingPref={handleUpdateTeachingPref}
          onDeleteTeachingPref={handleDeleteTeachingPref}
          onUploadTeachingPref={handleUploadTeachingPref}
          onAddTimePref={handleAddTimePref}
          onUpdateTimePref={handleUpdateTimePref}
          onDeleteTimePref={handleDeleteTimePref}
          onUploadTimePref={handleUploadTimePref}
        />
      );
    }

    // صفحات تولید برنامه
    const schedulePages = ["basket", "instructor-time", "room-allocation", "optimization", "schedule"];
    if (schedulePages.includes(activePage)) {
      return (
        <SchedulePages
          activePage={activePage}
          semester={semester}
          setSemester={setSemester}
          levels={DEFAULT_LEVELS}
          uniqueCourses={uniqueCourses}
          termCourses={termCourses}
          offeredCourses={offeredCourses}
          basketData={basketData}
          instructorTimeData={instructorTimeData}
          roomAllocationData={roomAllocationData}
          optimizedData={optimizedData}
          processLoading={processLoading}
          onBasketComplete={handleBasketComplete}
          onBasketCreated={handleBasketCreated}
          basketId={currentBasketId}
          onProcessSchedule={handleProcessSchedule}
          onProcessRooms={handleProcessRooms}
          onProcessOptimize={handleProcessOptimize}
          onClearSchedule={handleClearSchedule}
          onClearRooms={handleClearRooms}
          onClearOptimize={handleClearOptimize}
          schedule={schedule}
          rankedCourses={rankedCourses}
          loading={loading}
          onGenerate={handleGenerateSchedule}
          workflowId={workflowId}
          workflowSteps={workflowSteps}
          currentStep={currentStep}
          workflowLoading={workflowLoading}
          onStartWorkflow={handleStartWorkflow}
          onNextStep={handleNextStep}
          onPrevStep={handlePrevStep}
          onFinalize={handleFinalize}
          onUpdateStepData={handleUpdateStepData}
          teachingPreferences={teachingPreferences}
          timePreferences={timePreferences}
          onNextToRooms={handleNextToRooms}
          onManualAssignComplete={handleManualAssignComplete}
          onNavigateToBasketList={handleNavigateToBasketList} // <-- اضافه شد
        />
      );
    }

    // صفحه اصلی داشبورد
    return (
      <DashboardHome
        uniqueCourses={uniqueCourses}
        offeredCourses={offeredCourses}
        instructors={instructors}
        rooms={rooms}
        historyRecords={historyRecords}
        termCourses={termCourses}
        teachingPreferences={teachingPreferences}
        timePreferences={timePreferences}
        schedule={schedule}
        rankedCourses={rankedCourses}
        onNavigate={setActivePage}
        loading={loading}
      />
    );
  };

  return (
    <div className="dashboard-container">
      <Sidebar onNavigate={setActivePage} activePage={activePage} />
      <div className="main-content">
        <header className="main-header">
          <h1>سامانه هوشمند برنامه‌ریزی درسی</h1>
          <div className="header-info">
            <span>ترم: {semester === "mehr" ? "مهر" : "بهمن"}</span>
            {/* دکمه‌ی موقت برای رفتن به لیست سبدها */}
            <button
              onClick={() => setActivePage("basket-list")}
              style={{
                marginRight: "1rem",
                padding: "0.3rem 1rem",
                background: "#6366f1",
                color: "#fff",
                border: "none",
                borderRadius: "0.5rem",
                cursor: "pointer",
              }}
            >
              📋 لیست سبدها
            </button>
          </div>
        </header>
        <div className="content-area">{renderContent()}</div>
      </div>
    </div>
  );
}