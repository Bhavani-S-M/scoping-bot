import { useState } from "react";
import { Link } from "react-router-dom";
import authApi from "../api/authApi";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      await authApi.forgotPassword(email);
      setMessage("Password reset link sent to your email.");
    } catch (err) {
      console.error(" Forgot password error:", err);
      setMessage(" Failed to send reset link. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-dark-surface">
      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-dark-card p-8 rounded-xl shadow-lg w-96 space-y-6 border border-gray-200 dark:border-dark-muted"
      >
        <h1 className="text-2xl font-bold text-center text-primary dark:text-dark-primary">
          Forgot Password
        </h1>

        {/* Email Input */}
        <input
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
        />

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary hover:bg-secondary text-white py-2 rounded-lg transition font-semibold shadow-md disabled:opacity-50"
        >
          {loading ? "Sending..." : "Send Reset Link"}
        </button>

        {/* Status message */}
        {message && (
          <p className="text-center text-sm font-medium mt-2 text-gray-600 dark:text-dark-muted">
            {message}
          </p>
        )}

        {/* Back to Login */}
        <p className="text-center text-sm text-muted dark:text-dark-muted">
          Remembered your password?{" "}
          <Link to="/login" className="text-primary hover:underline">
            Back to Login
          </Link>
        </p>
      </form>
    </div>
  );
}
