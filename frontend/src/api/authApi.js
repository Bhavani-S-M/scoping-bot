import api from "./axiosClient";

const authApi = {
  // Authentication

  register: (data) => api.post("/auth/register", data),

  login: async (email, password) => {
    const res = await api.post(
      "/auth/jwt/login",
      new URLSearchParams({ username: email, password }),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );

    if (res.data.access_token) {
      localStorage.setItem("access_token", res.data.access_token);
    }
    if (res.data.refresh_token) {
      localStorage.setItem("refresh_token", res.data.refresh_token);
    }
    return res;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    return api.post("/auth/jwt/logout");
  },

  refresh: (refreshToken) =>
    api.post("/auth/jwt/refresh", { refresh_token: refreshToken }),

  // Get stored token (helper)
  getAccessToken: () => localStorage.getItem("access_token"),
  getRefreshToken: () => localStorage.getItem("refresh_token"),

  // Password Reset
  forgotPassword: (email) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token, password) =>
    api.post("/auth/reset-password", { token, password }),

  // Email Verification
  requestVerifyToken: (email) =>
    api.post("/auth/request-verify-token", { email }),
  verifyEmail: (token) => api.post("/auth/verify", { token }),

  // User Management
  getMe: () => api.get("/users/me"),
  updateMe: (data) => api.patch("/users/me", data), 
  getUser: (id) => api.get(`/users/${id}`),
  updateUser: (id, data) => api.patch(`/users/${id}`, data),
  deleteUser: (id) => api.delete(`/users/${id}`),
};

export default authApi;
