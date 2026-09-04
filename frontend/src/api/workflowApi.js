// frontend/src/api/workflowApi.js
import axios from "axios";

const API_BASE = "http://localhost:8000/api/schedule/workflow";

// ============================================================
// گام‌های workflow قدیمی (۵ مرحله‌ای)
// ============================================================
export async function startWorkflow({ semester, levels, year }) {
  const response = await axios.post(`${API_BASE}/step1`, {
    semester,
    levels,
    year,
  });
  return response.data;
}

export async function runStep2(workflowId) {
  const response = await axios.post(`${API_BASE}/step2/${workflowId}`);
  return response.data;
}

export async function runStep3(workflowId) {
  const response = await axios.post(`${API_BASE}/step3/${workflowId}`);
  return response.data;
}

export async function runStep4(workflowId) {
  const response = await axios.post(`${API_BASE}/step4/${workflowId}`);
  return response.data;
}

export async function runStep5(workflowId) {
  const response = await axios.post(`${API_BASE}/step5/${workflowId}`);
  return response.data;
}

export async function finalizeWorkflow(workflowId, updatedData) {
  const response = await axios.put(`${API_BASE}/step5/manual/${workflowId}`, {
    updated_data: updatedData,
  });
  return response.data;
}

export async function updateWorkflowStep(workflowId, stepNumber, data) {
  const response = await axios.put(`${API_BASE}/${workflowId}/step`, {
    step_number: stepNumber,
    data: data,
  });
  return response.data;
}

export async function getWorkflowStatus(workflowId) {
  const response = await axios.get(`${API_BASE}/${workflowId}`);
  return response.data;
}

export async function getAllWorkflows() {
  const response = await axios.get(`${API_BASE}/list/all`);
  return response.data;
}

export async function deleteWorkflow(workflowId) {
  const response = await axios.delete(`${API_BASE}/${workflowId}`);
  return response.data;
}

// ============================================================
// فرایندهای چهارگانه جدید (یکجا)
// ============================================================
export async function processBasket({ semester, levels, year }) {
  const response = await axios.post(`${API_BASE}/basket`, {
    semester,
    levels,
    year,
  });
  return response.data;
}

export async function processSchedule({ basket }) {
  const response = await axios.post(`${API_BASE}/schedule`, {
    basket,
  });
  return response.data;
}

/**
 * تخصیص اتاق به کلاس‌های زمان‌بندی شده
 * @param {Object} params
 * @param {Array} params.schedule - لیست کلاس‌های زمان‌بندی شده
 * @param {number} params.workflowId - شناسه workflow جاری (اجباری)
 * @param {string} params.semester - نیمسال (mehr/bahman) (اجباری)
 * @param {string} params.year - سال تحصیلی (پیش‌فرض 1403)
 * @returns {Promise<Object>} پاسخ سرور شامل داده‌های تخصیص‌یافته
 */
export async function processRooms({ schedule, workflowId, semester, year = "1403" }) {
  // بررسی وجود پارامترهای اجباری
  if (!workflowId) {
    throw new Error("workflowId الزامی است برای تخصیص اتاق");
  }
  if (!semester) {
    throw new Error("semester الزامی است برای تخصیص اتاق");
  }

  const url = `${API_BASE}/rooms?workflow_id=${workflowId}&semester=${semester}&year=${year}`;
  const response = await axios.post(url, { schedule });
  return response.data;
}

export async function processOptimize({ schedule }) {
  const response = await axios.post(`${API_BASE}/optimize`, {
    schedule,
  });
  return response.data;
}

// ============================================================
// توابع جدید برای سبد دو مرحله‌ای (مخصوص BasketWizard)
// ============================================================

/**
 * مرحله اول: دریافت لیست اولیه دروس (بدون آمار)
 * @param {Object} params - شامل semester, levels, year
 * @returns {Promise<Object>} پاسخ شامل basket (لیست اولیه)
 */
export async function getInitialBasket({ semester, levels, year }) {
  const response = await axios.post(`${API_BASE}/basket/initial`, {
    semester,
    levels,
    year,
  });
  return response.data;
}

/**
 * مرحله دوم: افزودن آمار فراوانی و ظرفیت به سبد
 * @param {Object} params - شامل basket (لیست دروس مرحله اول)
 * @returns {Promise<Object>} پاسخ شامل basket (سبد کامل با آمار)
 */
export async function addStatisticsToBasket({ basket }) {
  const response = await axios.post(`${API_BASE}/basket/statistics`, {
    basket,
  });
  return response.data;
}

// ============================================================
// توابع ذخیره و بازیابی سبد
// ============================================================

/**
 * ذخیره سبد دروس در دیتابیس
 * @param {Object} params
 * @param {Array} params.basket - لیست آیتم‌های سبد
 * @param {number} params.workflowId - شناسه workflow (اختیاری)
 * @param {string} params.semester - نیمسال
 * @returns {Promise<Object>} پاسخ سرور
 */
export async function saveBasket({ basket, workflowId, semester }) {
  const response = await axios.post(`${API_BASE}/basket/save`, {
    basket,
    workflow_id: workflowId,
    semester,
  });
  return response.data;
}

/**
 * دریافت سبد بر اساس workflowId
 * @param {number} workflowId
 * @returns {Promise<Object>} پاسخ شامل basket و count
 */
export async function getBasketByWorkflow(workflowId) {
  const response = await axios.get(`${API_BASE}/basket/${workflowId}`);
  return response.data;
}

/**
 * دریافت سبد بر اساس semester و level (اختیاری)
 * @param {string} semester
 * @param {string} level - اختیاری
 * @returns {Promise<Object>} پاسخ شامل basket و count
 */
export async function getBasketBySemester(semester, level = null) {
  let url = `${API_BASE}/basket?semester=${semester}`;
  if (level) {
    url += `&level=${level}`;
  }
  const response = await axios.get(url);
  return response.data;
}

/**
 * حذف سبد بر اساس workflowId
 * @param {number} workflowId
 * @returns {Promise<Object>} پاسخ شامل status و deleted_count
 */
export async function deleteBasketByWorkflow(workflowId) {
  const response = await axios.delete(`${API_BASE}/basket/${workflowId}`);
  return response.data;
}

/**
 * به‌روزرسانی یک آیتم سبد
 * @param {number} itemId - شناسه آیتم
 * @param {Object} data - شامل required_classes یا from_manager
 * @returns {Promise<Object>} پاسخ شامل آیتم به‌روز شده
 */
export async function updateBasketItem(itemId, data) {
  const response = await axios.put(`${API_BASE}/basket/item/${itemId}`, data);
  return response.data;
}

// ============================================================
// توابع ذخیره و بازیابی برنامه زمان‌بندی شده
// ============================================================

/**
 * ذخیره برنامه زمان‌بندی (کلاس‌های تخصیص‌یافته و بدون استاد)
 * @param {Object} params
 * @param {Array} params.classes - لیست کلاس‌های تخصیص‌یافته
 * @param {Array} params.unassigned - لیست کلاس‌های بدون استاد
 * @param {number} params.basketId - شناسه سبد (اختیاری)
 * @param {number} params.workflowId - شناسه workflow
 * @param {string} params.semester - نیمسال
 * @param {string} params.year - سال (پیش‌فرض 1403)
 * @param {boolean} params.overwrite - آیا برنامه قبلی بازنویسی شود؟
 * @returns {Promise<Object>} پاسخ سرور
 */
export async function saveSchedule({
  classes,
  unassigned = [],
  basketId = null,
  workflowId,
  semester,
  year = "1403",
  overwrite = false,
}) {
  const response = await axios.post(`${API_BASE}/save-schedule`, {
    classes,
    unassigned,
    basket_id: basketId,
    workflow_id: workflowId,
    semester,
    year,
    overwrite,
  });
  return response.data;
}

/**
 * دریافت کلاس‌های زمان‌بندی شده برای یک workflow
 * @param {number} workflowId
 * @returns {Promise<Object>} پاسخ شامل لیست کلاس‌ها
 */
export async function getScheduledClasses(workflowId) {
  const response = await axios.get(`${API_BASE}/${workflowId}/scheduled-classes`);
  return response.data;
}

/**
 * دریافت جدیدترین برنامه زمان‌بندی برای یک سبد
 * @param {number} basketId
 * @returns {Promise<Object>} پاسخ شامل کلاس‌های تخصیص‌یافته و بدون استاد
 */
export async function getScheduledClassesByBasket(basketId) {
  const response = await axios.get(`${API_BASE}/scheduled-classes/by-basket/${basketId}`);
  return response.data;
}

// ============================================================
// تخصیص دستی استاد (با بررسی تداخل)
// ============================================================

/**
 * تخصیص دستی استاد به کلاس‌ها
 * @param {Object} params
 * @param {Array} params.assignments - لیست تخصیص‌ها (هر آیتم شامل id, course_name, group_number, level, term, instructor_code, day, start, end)
 * @param {number} params.basketId - شناسه سبد
 * @param {number} params.workflowId - شناسه workflow
 * @returns {Promise<Object>} پاسخ شامل success_count و errors
 */
export async function manualAssignInstructors({ assignments, basketId, workflowId }) {
  const response = await axios.post(`${API_BASE}/schedule/manual`, {
    assignments,
    basket_id: basketId,
    workflow_id: workflowId,
  });
  return response.data;
}