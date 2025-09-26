import { useState, useRef, useEffect } from "react";
import { Sun, Moon, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Header({ onToggleSidebar, isSidebarOpen }) {
  const [darkMode, setDarkMode] = useState(
    document.documentElement.classList.contains("dark")
  );
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle("dark");
    setDarkMode(!darkMode);
  };

  const openProfile = () => {
    navigate("/profile");
    setDropdownOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials = user?.username?.[0]?.toUpperCase() || "?";

  return (
    <header className="flex justify-between items-center h-14 
      bg-primary dark:bg-dark-primary 
      text-white shadow-sm px-4 md:px-6 border-b border-gray-200 dark:border-gray-700"
    >
      <div className="flex items-center gap-3">
        {/*  Mobile Sidebar Toggle */}
        <button
          onClick={onToggleSidebar}
          className="md:hidden flex items-center justify-center w-10 h-10 rounded-lg hover:bg-primary/80 dark:hover:bg-dark-primary/80 transition"
        >
          {isSidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>

        <img
          src="/bot.png"
          alt="icon"
          className="w-10 h-10"
        />

        <h1 className="text-xl font-extrabold font-heading text-white">
          Project Scoping Bot
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {/*  Profile Dropdown */}
        {user ? (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 opacity-80 hover:opacity-100 transition"
            >
              <div className="w-9 h-9 rounded-full bg-white text-primary font-bold flex items-center justify-center">
                {initials}
              </div>
              <span className="hidden md:inline"> {user.username}</span>
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden z-50">
                <button
                  onClick={openProfile}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Profile
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        ) : (
          <span className="italic opacity-70">Not logged in</span>
        )}

        {/*  Theme toggle */}
        <button
          onClick={toggleDarkMode}
          aria-label="Toggle theme"
          className="flex items-center gap-1 bg-white text-primary 
            dark:bg-gray-900 dark:text-dark-primary 
            px-3 py-1.5 rounded-lg shadow hover:opacity-90 transition"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
}

