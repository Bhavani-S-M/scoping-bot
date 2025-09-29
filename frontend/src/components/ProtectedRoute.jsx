import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import authApi from "../api/authApi";

export default function ProtectedRoute({ children, requireSuperuser = false }) {
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setIsAuthenticated(false);
        setLoading(false);
        return;
      }

      try {
        const res = await authApi.getMe();
        const u = res?.data;
        if (u?.is_verified) {
          setUser(u);
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (err) {
        console.error("Auth check failed:", err);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return (
      <p className="text-center mt-10 text-gray-600">
        ⏳ Checking authentication...
      </p>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireSuperuser && !user?.is_superuser) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
