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

export async function processRooms({ schedule }) {
  const response = await axios.post(`${API_BASE}/rooms`, {
    schedule,
  });
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