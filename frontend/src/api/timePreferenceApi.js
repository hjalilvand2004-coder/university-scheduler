// frontend/src/api/timePreferenceApi.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

export async function getTimePreferences() {
  const response = await api.get("/time-preferences/");
  return response.data;
}

export async function createTimePreference(data) {
  const response = await api.post("/time-preferences/", data);
  return response.data;
}

export async function updateTimePreference(id, data) {
  const response = await api.put(`/time-preferences/${id}`, data);
  return response.data;
}

export async function deleteTimePreference(id) {
  const response = await api.delete(`/time-preferences/${id}`);
  return response.data;
}

export async function uploadTimePreferencesExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/time-preferences/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}