// frontend/src/api/teachingPreferenceApi.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

export async function getTeachingPreferences() {
  const response = await api.get("/teaching-preferences/");
  return response.data;
}

export async function createTeachingPreference(data) {
  const response = await api.post("/teaching-preferences/", data);
  return response.data;
}

export async function updateTeachingPreference(id, data) {
  const response = await api.put(`/teaching-preferences/${id}`, data);
  return response.data;
}

export async function deleteTeachingPreference(id) {
  const response = await api.delete(`/teaching-preferences/${id}`);
  return response.data;
}

export async function uploadTeachingPreferencesExcel(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/teaching-preferences/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}