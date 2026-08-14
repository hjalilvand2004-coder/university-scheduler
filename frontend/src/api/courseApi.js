import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// اضافه کردن اینترسپتور برای مدیریت خطاها (اختیاری)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============================================
// دروس یکتا (Unique Courses)
// ============================================
export async function getUniqueCourses() {
  const response = await api.get("/courses/unique");
  return response.data;
}

export async function getUniqueCourse(id) {
  const response = await api.get(`/courses/unique/${id}`);
  return response.data;
}

export async function createUniqueCourse(data) {
  // داده می‌تواند شامل فیلد estimated_capacity باشد
  const response = await api.post("/courses/unique", data);
  return response.data;
}

export async function updateUniqueCourse(id, data) {
  const response = await api.put(`/courses/unique/${id}`, data);
  return response.data;
}

export async function deleteUniqueCourse(id) {
  const response = await api.delete(`/courses/unique/${id}`);
  return response.data;
}

// ============================================
// دروس ارائه (Offered Courses)
// ============================================
export async function getOfferedCourses() {
  const response = await api.get("/courses/offered");
  return response.data;
}

export async function getOfferedCourse(id) {
  const response = await api.get(`/courses/offered/${id}`);
  return response.data;
}

export async function createOfferedCourse(data) {
  const response = await api.post("/courses/offered", data);
  return response.data;
}

export async function updateOfferedCourse(id, data) {
  const response = await api.put(`/courses/offered/${id}`, data);
  return response.data;
}

export async function deleteOfferedCourse(id) {
  const response = await api.delete(`/courses/offered/${id}`);
  return response.data;
}

// ============================================
// اساتید و سوابق تدریس (قدیمی)
// ============================================
export async function getInstructors() {
  const response = await api.get("/courses/instructors");
  return response.data;
}

export async function getTeachingHistory() {
  const response = await api.get("/courses/teaching-history");
  return response.data;
}

// ============================================
// بارگذاری اکسل (عمومی) - از مسیر /courses/upload/{type} استفاده می‌کند
// ============================================
export async function uploadExcelFile(file, type) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post(`/courses/upload/${type}`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

// ============================================
// APIهای اساتید (جدید) - مسیر /professors-rooms/instructors
// ============================================
export async function getInstructorsList() {
  const response = await api.get("/professors-rooms/instructors/list");
  return response.data;
}

export async function createInstructor(data) {
  const response = await api.post("/professors-rooms/instructors", data);
  return response.data;
}

export async function updateInstructor(id, data) {
  const response = await api.put(`/professors-rooms/instructors/${id}`, data);
  return response.data;
}

export async function deleteInstructor(id) {
  const response = await api.delete(`/professors-rooms/instructors/${id}`);
  return response.data;
}

export async function uploadInstructorsExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/professors-rooms/upload/instructors", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

// ============================================
// APIهای اتاق‌ها - مسیر /professors-rooms/rooms
// ============================================
export async function getRoomsList() {
  const response = await api.get("/professors-rooms/rooms/list");
  return response.data;
}

export async function createRoom(data) {
  const response = await api.post("/professors-rooms/rooms", data);
  return response.data;
}

export async function updateRoom(id, data) {
  const response = await api.put(`/professors-rooms/rooms/${id}`, data);
  return response.data;
}

export async function deleteRoom(id) {
  const response = await api.delete(`/professors-rooms/rooms/${id}`);
  return response.data;
}

export async function uploadRoomsExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/professors-rooms/upload/rooms", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

// ============================================
// توابع کمکی برای مدیریت برآورد ظرفیت (اختیاری)
// ============================================
export async function updateUniqueCourseCapacity(id, estimatedCapacity) {
  // به‌روزرسانی فقط فیلد estimated_capacity
  const response = await api.patch(`/courses/unique/${id}/capacity`, {
    estimated_capacity: estimatedCapacity,
  });
  return response.data;
}