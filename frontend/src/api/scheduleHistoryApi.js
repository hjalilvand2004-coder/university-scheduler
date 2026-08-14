// frontend/src/api/scheduleHistoryApi.js
import axios from "axios";

// استفاده از همان baseURL که در سایر APIها تنظیم شده است
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// ============================================
// دریافت لیست تمام سوابق
// ============================================
export async function getHistoryList() {
  const response = await api.get("/schedule-history/");
  return response.data;
}

// ============================================
// ایجاد رکورد جدید
// ============================================
export async function createHistory(data) {
  const response = await api.post("/schedule-history/", data);
  return response.data;
}

// ============================================
// بروزرسانی رکورد
// ============================================
export async function updateHistory(id, data) {
  const response = await api.put(`/schedule-history/${id}`, data);
  return response.data;
}

// ============================================
// حذف رکورد
// ============================================
export async function deleteHistory(id) {
  const response = await api.delete(`/schedule-history/${id}`);
  return response.data;
}

// ============================================
// بارگذاری فایل اکسل
// ============================================
export async function uploadHistoryExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/schedule-history/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}