import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import authApi from "../api/authApi";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Login and get tokens
      const res = await authApi.login(email, password);

      localStorage.setItem("access_token", res.data.access_token);
      if (res.data.refresh_token) {
        localStorage.setItem("refresh_token", res.data.refresh_token);
      }

      // Fetch user profile
      navigate("/dashboard");
    } catch (err) {
      console.error(" Login error:", err);
      alert(" Login failed. Check your credentials and try again.");
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
          Login
        </h1>

        <input
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          className="w-full border border-gray-300 dark:border-dark-muted rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary dark:focus:ring-dark-primary bg-gray-50 dark:bg-dark-surface text-gray-800 dark:text-white"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary hover:bg-secondary text-white py-2 rounded-lg transition font-semibold shadow-md disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Login"}
        </button>

        <div className="flex justify-between text-sm text-muted dark:text-dark-muted">
          <Link to="/register" className="text-primary hover:underline">
            Register
          </Link>
          <Link to="/forgot-password" className="text-primary hover:underline">
            Forgot Password?
          </Link>
        </div>
      </form>
    </div>
  );
}
