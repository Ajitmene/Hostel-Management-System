import { api } from "./client.js";

export const auth = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  refresh: () => api.post("/auth/refresh"),
  changePassword: (current_password, new_password) =>
    api.post("/auth/change-password", { current_password, new_password }),
};

export const dashboard = { summary: () => api.get("/dashboard/summary") };

export const students = {
  list: (params) => api.get("/students", { params }),
  get: (id) => api.get(`/students/${id}`),
  summary: () => api.get("/students/summary"),
  create: (body) => api.post("/students", body),
  update: (id, body) => api.put(`/students/${id}`, body),
  setStatus: (id, status) => api.patch(`/students/${id}/status`, { status }),
};

export const rooms = {
  list: (params) => api.get("/rooms", { params }),
  summary: () => api.get("/rooms/summary"),
  available: () => api.get("/rooms/available"),
  get: (id) => api.get(`/rooms/${id}`),
  create: (body) => api.post("/rooms", body),
  update: (id, body) => api.put(`/rooms/${id}`, body),
  allocations: (params) => api.get("/rooms/allocations", { params }),
  allocate: (body) => api.post("/rooms/allocations", body),
  transfer: (id, body) => api.post(`/rooms/allocations/${id}/transfer`, body),
};

export const fees = {
  list: (params) => api.get("/fees", { params }),
  summary: () => api.get("/fees/summary"),
  pending: (params) => api.get("/fees/pending", { params }),
  get: (id) => api.get(`/fees/${id}`),
  create: (body) => api.post("/fees", body),
  structures: () => api.get("/fees/structures"),
  createStructure: (body) => api.post("/fees/structures", body),
  payments: (params) => api.get("/fees/payments", { params }),
  recordPayment: (body) => api.post("/fees/payments", body),
  receipt: (id) => api.get(`/fees/payments/${id}/receipt`),
};

export const attendance = {
  list: (params) => api.get("/attendance", { params }),
  roster: (date) => api.get("/attendance/roster", { params: { date } }),
  record: (body) => api.post("/attendance", body),
  summary: (params) => api.get("/attendance/summary", { params }),
  correct: (id, body) => api.put(`/attendance/${id}`, body),
};

export const employees = {
  list: (params) => api.get("/employees", { params }),
  get: (id) => api.get(`/employees/${id}`),
  create: (body) => api.post("/employees", body),
  update: (id, body) => api.put(`/employees/${id}`, body),
  setStatus: (id, is_active) => api.patch(`/employees/${id}/status`, { is_active }),
  resetPassword: (id, new_password) => api.post(`/employees/${id}/reset-password`, { new_password }),
};

export const reports = {
  get: (name, params) => api.get(`/reports/${name}`, { params }),
  csv: (name, params) =>
    api.get(`/reports/${name}`, { params: { ...params, format: "csv" }, responseType: "blob" }),
};
