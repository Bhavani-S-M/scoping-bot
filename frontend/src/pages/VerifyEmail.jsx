import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import authApi from "../api/authApi";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setStatus("error");
      setMessage(" Verification token is missing.");
      return;
    }

    const verify = async () => {
      try {
        await authApi.verifyEmail(token);
        setStatus("success");
        setMessage(" Email verified successfully! You can now log in.");
        setTimeout(() => navigate("/login"), 2000); 
      } catch (err) {
        console.error("Verification failed:", err);
        if (err.response?.data?.detail) {
          setMessage( JSON.stringify(err.response.data.detail));
        } else {
          setMessage(" Verification failed. Please try again.");
        }
        setStatus("error");
      }
    };

    verify();
  }, [searchParams, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-primary to-secondary">
      <div className="bg-white p-8 rounded-lg shadow-md w-96 text-center space-y-4">
        <h1 className="text-2xl font-bold text-gray-800">Email Verification</h1>

        {status === "loading" && (
          <p className="text-gray-600">⏳ Verifying your email...</p>
        )}
        {status === "success" && (
          <p className="text-green-600 font-medium">{message}</p>
        )}
        {status === "error" && (
          <p className="text-red-600 font-medium">{message}</p>
        )}
      </div>
    </div>
  );
}
