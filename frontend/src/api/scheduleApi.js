// frontend/src/api/scheduleApi.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// ============================================
// تولید برنامه نمونه (با داده‌های نمونه)
// ============================================
export async function generateSampleSchedule(semester = "mehr") {
  const response = await api.post(
    `/schedules/generate-sample?semester=${semester}`
  );
  return response.data;
}

// ============================================
// تولید برنامه با داده‌های دیتابیس (جدید)
// ============================================
export async function generateSchedule(data) {
  const response = await api.post("/schedules/generate", data);
  return response.data;
}

// ============================================
// دریافت رتبه‌بندی دروس
// ============================================
export async function getRankedCourses(semester = "mehr") {
  const response = await api.get(
    `/courses/ranked?semester=${semester}`
  );
  return response.data;
}