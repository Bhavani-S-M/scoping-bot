import { useState } from "react";
import authApi from "../api/authApi";

export default function ResendVerification() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      await authApi.requestVerifyToken(email);
      setMessage("Verification email sent! Check your inbox.");
    } catch (err) {
      console.error(" Resend failed:", err);
      if (err.response?.data?.detail) {
        setMessage( JSON.stringify(err.response.data.detail));
      } else {
        setMessage(" Failed to resend verification email.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-primary to-secondary">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-lg shadow-md w-96 space-y-4"
      >
        <h1 className="text-2xl font-bold text-center text-gray-800">
          Resend Verification Email
        </h1>

        <input
          type="email"
          name="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary hover:bg-blue-700 text-white py-2 rounded transition disabled:opacity-50"
        >
          {loading ? "Sending..." : "Resend Email"}
        </button>

        {message && (
          <p className="text-center text-sm mt-2 text-gray-700">{message}</p>
        )}
      </form>
    </div>
  );
}
