// frontend/src/api/scheduleApi.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// ============================================================
// ثابت‌های هماهنگ با بک‌اند
// ============================================================

/**
 * نرمال‌سازی ترم (تبدیل کلیدهای قدیمی به جدید)
 * @param {string} term - نام ترم (مثلاً "mehr", "bahman", "summer")
 * @returns {string} کلید استاندارد ترم (semester_1, semester_2, summer)
 */
const normalizeTerm = (term) => {
  if (!term) return "semester_1";
  const normalized = term.trim().toLowerCase();
  if (normalized === "mehr" || normalized === "semester_1") return "semester_1";
  if (normalized === "bahman" || normalized === "semester_2") return "semester_2";
  if (normalized === "summer" || normalized === "تابستان") return "summer";
  return "semester_1";
};

// ============================================================
// توابع موجود (قبلی) - با پشتیبانی از کلیدهای جدید
// ============================================================

/**
 * تولید برنامه نمونه (با داده‌های نمونه)
 * @param {string} semester - نام ترم (پیش‌فرض: "semester_1")
 * @returns {Promise<Object>} داده‌های برنامه نمونه
 */
export async function generateSampleSchedule(semester = "semester_1") {
  const normalizedSemester = normalizeTerm(semester);
  const response = await api.post(
    `/schedules/generate-sample?semester=${normalizedSemester}`
  );
  return response.data;
}

/**
 * تولید برنامه با داده‌های دیتابیس (جدید)
 * @param {Object} data - داده‌های مورد نیاز برای تولید
 * @returns {Promise<Object>} نتیجه تولید برنامه
 */
export async function generateSchedule(data) {
  // نرمال‌سازی ترم در داده‌های ورودی
  const normalizedData = { ...data };
  if (normalizedData.semester) {
    normalizedData.semester = normalizeTerm(normalizedData.semester);
  }
  const response = await api.post("/schedules/generate", normalizedData);
  return response.data;
}

/**
 * دریافت رتبه‌بندی دروس
 * @param {string} semester - نام ترم (پیش‌فرض: "semester_1")
 * @returns {Promise<Object>} لیست دروس رتبه‌بندی‌شده
 */
export async function getRankedCourses(semester = "semester_1") {
  const normalizedSemester = normalizeTerm(semester);
  const response = await api.get(
    `/courses/ranked?semester=${normalizedSemester}`
  );
  return response.data;
}

// ============================================================
// توابع جدید بر اساس slot_times.py
// ============================================================

/**
 * دریافت لیست ترم‌های معتبر و اطلاعات مربوطه
 * @returns {Promise<Object>} شامل لیست ترم‌ها، واحدهای مجاز و بازه‌های زمانی
 */
export async function getAvailableTerms() {
  const response = await api.get("/slot-times/terms");
  return response.data;
}

/**
 * دریافت برنامه کامل یک ترم بدون فیلتر
 * @param {string} term - نام ترم (مثلاً "semester_1", "semester_2", "summer")
 * @returns {Promise<Object>} برنامه کامل ترم
 */
export async function getFullSchedule(term) {
  const normalizedTerm = normalizeTerm(term);
  const response = await api.get("/slot-times/schedule", {
    params: { term: normalizedTerm },
  });
  return response.data;
}

/**
 * جستجوی اسلات‌ها با فیلترهای مختلف
 * @param {Object} params - پارامترهای جستجو
 * @param {string} params.term - نام ترم (اجباری)
 * @param {number} [params.units] - تعداد واحد (2, 3, 4)
 * @param {string} [params.period] - بازه زمانی (morning/afternoon/evening)
 * @param {string} [params.start_after] - شروع بعد از این ساعت (مثلاً "10:00")
 * @param {string} [params.end_before] - پایان قبل از این ساعت (مثلاً "14:00")
 * @returns {Promise<Object>} شامل لیست اسلات‌های یافت‌شده و اطلاعات فیلترها
 */
export async function searchSlots({ term, units, period, start_after, end_before }) {
  const normalizedTerm = normalizeTerm(term);
  const response = await api.get("/slot-times/search", {
    params: {
      term: normalizedTerm,
      units,
      period,
      start_after,
      end_before,
    },
  });
  return response.data;
}

/**
 * اعتبارسنجی یک اسلات مشخص برای ترم و واحد داده شده
 * @param {string} slot - اسلات به فرمت "HH:MM-HH:MM"
 * @param {string} term - نام ترم
 * @param {number} units - تعداد واحد
 * @returns {Promise<Object>} شامل وضعیت اعتبارسنجی
 */
export async function validateSlot({ slot, term, units }) {
  const normalizedTerm = normalizeTerm(term);
  const response = await api.get("/slot-times/validate", {
    params: { slot, term: normalizedTerm, units },
  });
  return response.data;
}

/**
 * پیدا کردن نزدیک‌ترین اسلات معتبر به یک زمان شروع مشخص
 * @param {string} start - زمان شروع مدنظر (HH:MM)
 * @param {string} term - نام ترم
 * @param {number} units - تعداد واحد
 * @param {number} [tolerance=30] - حداکثر تفاوت مجاز بر حسب دقیقه
 * @returns {Promise<Object>} شامل نزدیک‌ترین اسلات یا پیام عدم یافت
 */
export async function findClosestSlot({ start, term, units, tolerance = 30 }) {
  const normalizedTerm = normalizeTerm(term);
  const response = await api.get("/slot-times/closest", {
    params: { start, term: normalizedTerm, units, tolerance },
  });
  return response.data;
}

// ============================================================
// ایجاد شیء scheduleApi برای راحتی import (named export)
// ============================================================

/**
 * شیء حاوی تمام توابع API برای استفاده با import { scheduleApi }
 */
export const scheduleApi = {
  // توابع قدیمی
  generateSampleSchedule,
  generateSchedule,
  getRankedCourses,

  // توابع جدید slot-times
  getAvailableTerms,
  getFullSchedule,
  searchSlots,
  validateSlot,
  findClosestSlot,
};

// ============================================================
// Export پیش‌فرض برای استفاده با import scheduleApi
// ============================================================

export default scheduleApi;