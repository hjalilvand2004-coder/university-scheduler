// frontend/src/api/termCourseApi.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// ============================================
// دریافت لیست تمام دروس ترمیک
// ============================================
export async function getTermCourses() {
  const response = await api.get("/term-courses/");
  return response.data;
}

// ============================================
// ایجاد رکورد جدید
// ============================================
export async function createTermCourse(data) {
  const response = await api.post("/term-courses/", data);
  return response.data;
}

// ============================================
// بروزرسانی رکورد
// ============================================
export async function updateTermCourse(id, data) {
  const response = await api.put(`/term-courses/${id}`, data);
  return response.data;
}

// ============================================
// حذف رکورد
// ============================================
export async function deleteTermCourse(id) {
  const response = await api.delete(`/term-courses/${id}`);
  return response.data;
}

// ============================================
// بارگذاری فایل اکسل
// ============================================
export async function uploadTermCoursesExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/term-courses/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}