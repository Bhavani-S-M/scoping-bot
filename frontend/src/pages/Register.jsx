import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import authApi from "../api/authApi";

export default function Register() {
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const allowedDomain = "sigmoidanalytics.com";
    const emailDomain = form.email.split("@")[1]?.toLowerCase();

    if (emailDomain !== allowedDomain) {
      alert(` Registration allowed only for ${allowedDomain} users.`);
      return;
    }

    if (form.password !== form.confirmPassword) {
      alert(" Passwords do not match!");
      return;
    }

    setLoading(true);
    try {
      await authApi.register({
        email: form.email,
        username: form.username,
        password: form.password,
      });

      alert(
        " Registration successful! Please check your email to verify your account before logging in."
      );
      navigate("/login");
    } catch (err) {
      console.error(" Registration failed:", err);
      if (err.response?.data?.detail) {
        alert(" " + JSON.stringify(err.response.data.detail));
      } else {
        alert(" Registration failed. Try again.");
      }
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
          Register
        </h1>

        {/* Username */}
        <input
          type="text"
          name="username"
          placeholder="Username"
          value={form.username}
          onChange={handleChange}
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          required
        />

        {/* Email */}
        <input
          type="email"
          name="email"
          placeholder="Email"
          value={form.email}
          onChange={handleChange}
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          required
        />

        {/* Password */}
        <input
          type="password"
          name="password"
          placeholder="Password"
          value={form.password}
          onChange={handleChange}
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          required
        />

        {/* Confirm Password */}
        <input
          type="password"
          name="confirmPassword"
          placeholder="Confirm Password"
          value={form.confirmPassword}
          onChange={handleChange}
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          required
        />

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary hover:bg-secondary text-white py-2 rounded-lg transition font-semibold shadow-md disabled:opacity-50"
        >
          {loading ? "Registering..." : "Register"}
        </button>

        {/* Links */}
        <div className="flex justify-between text-sm text-muted dark:text-dark-muted">
          <Link to="/login" className="text-primary hover:underline">
            Login
          </Link>
          <Link to="/forgot-password" className="text-primary hover:underline">
            Forgot Password?
          </Link>
        </div>
      </form>
    </div>
  );
}

