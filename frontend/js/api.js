/**
 * api.js
 * Small wrapper around fetch() so every page talks to the Flask
 * backend the same way. `credentials: "include"` is what makes the
 * session cookie get sent/stored on every request.
 */

const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    // no JSON body (e.g. 204) - that's fine
  }

  if (!res.ok) {
    const message = (data && data.error) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

const api = {
  register: (username, email, password) =>
    apiRequest("/register", { method: "POST", body: JSON.stringify({ username, email, password }) }),

  login: (username, password) =>
    apiRequest("/login", { method: "POST", body: JSON.stringify({ username, password }) }),

  logout: () => apiRequest("/logout", { method: "POST" }),

  me: () => apiRequest("/me"),

  getTasks: (filters = {}) => {
    const params = new URLSearchParams(filters).toString();
    return apiRequest("/tasks" + (params ? `?${params}` : ""));
  },

  createTask: (task) => apiRequest("/tasks", { method: "POST", body: JSON.stringify(task) }),

  updateTask: (id, task) => apiRequest(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(task) }),

  toggleComplete: (id, completed) =>
    apiRequest(`/tasks/${id}/complete`, { method: "PATCH", body: JSON.stringify({ completed }) }),

  deleteTask: (id) => apiRequest(`/tasks/${id}`, { method: "DELETE" }),
};
