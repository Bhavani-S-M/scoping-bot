import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import authApi from "../api/authApi";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");

    if (password !== confirmPassword) {
      setMessage(" Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setMessage(" Password has been reset successfully.");
      setTimeout(() => navigate("/login"), 2000); 
    } catch (err) {
      console.error(" Reset password error:", err);
      setMessage(" Failed to reset password. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-dark-surface">
        <div className="bg-white dark:bg-dark-card p-8 rounded-xl shadow-lg w-96 text-center border border-gray-200 dark:border-dark-muted">
          <h1 className="text-xl font-bold text-red-500">Invalid Reset Link</h1>
          <p className="mt-2 text-gray-600 dark:text-dark-muted">
            Please request a new reset link from{" "}
            <Link to="/forgot-password" className="text-primary hover:underline">
              Forgot Password
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-dark-surface">
      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-dark-card p-8 rounded-xl shadow-lg w-96 space-y-6 border border-gray-200 dark:border-dark-muted"
      >
        <h1 className="text-2xl font-bold text-center text-primary dark:text-dark-primary">
          Reset Password
        </h1>

        <input
          type="password"
          placeholder="New Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
        />

        <input
          type="password"
          placeholder="Confirm New Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary hover:bg-secondary text-white py-2 rounded-lg transition font-semibold shadow-md disabled:opacity-50"
        >
          {loading ? "Resetting..." : "Reset Password"}
        </button>

        {message && (
          <p className="text-center text-sm mt-2 font-medium text-gray-600 dark:text-dark-muted">
            {message}
          </p>
        )}
      </form>
    </div>
  );
}
