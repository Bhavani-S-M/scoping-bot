import { createContext, useState, useEffect, useContext } from "react";
import authApi from "../api/authApi";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("access_token") || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (token) fetchUser();
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await authApi.getMe();
      setUser(res.data);
    } catch (err) {
      console.error("Failed to fetch user:", err);
      setUser(null);
    }
  };

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      const { access_token, refresh_token } = res.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      setToken(access_token);
      await fetchUser();
    } catch (err) {
      console.error("Login failed:", err);
      setError("Invalid credentials");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    setToken(null);
    setUser(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  };

  const refreshAccessToken = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return logout();

    try {
      const res = await authApi.refresh(refreshToken);
      const { access_token, refresh_token } = res.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      setToken(access_token);
      return access_token;
    } catch (err) {
      console.error("Token refresh failed:", err);
      await logout();
      throw err;
    }
  };

  // update current user profile
  const updateUserProfile = async (updates) => {
    try {
      const res = await authApi.updateMe(updates);
      setUser(res.data);
      return res.data;
    } catch (err) {
      console.error("Profile update failed:", err);
      throw err;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        fetchUser,
        refreshAccessToken,
        updateUserProfile,  
        loading,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
