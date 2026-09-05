// src/api/feedbackApi.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: ${API_BASE_URL}/api/feedback,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const submitFeedback = async (feedbackData) => {
  try {
    const response = await apiClient.post('/submit', feedbackData);
    return response.data;
  } catch (error) {
    console.error('❌ خطا در ارسال بازخورد:', error);
    throw error;
  }
};

export const getFeedbackAnalysis = async () => {
  try {
    const response = await apiClient.get('/analysis');
    return response.data;
  } catch (error) {
    console.error('❌ خطا در دریافت تحلیل بازخورد:', error);
    throw error;
  }
};

export const getWeightHistory = async () => {
  try {
    const response = await apiClient.get('/weight-history');
    return response.data;
  } catch (error) {
    console.error('❌ خطا در دریافت تاریخچه وزن‌ها:', error);
    throw error;
  }
};

export const getFeedbackStats = async () => {
  try {
    const response = await apiClient.get('/stats');
    return response.data;
  } catch (error) {
    console.error('❌ خطا در دریافت آمار بازخورد:', error);
    throw error;
  }
};
