import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  FileSpreadsheet,
  Menu,
  History,
  Database,
  Wallet,   
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useProjects } from "../../contexts/ProjectContext";



export default function Sidebar({ isOpen, setIsOpen, mobileOpen }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { projects } = useProjects();

  const latestProjectId = projects?.length
    ? [...projects]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]?.id
    : null;

  // Base nav items (everyone)
  const baseNavItems = [
    { path: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-5 h-5" /> },
    { path: "/projects", label: "Projects", icon: <FolderKanban className="w-5 h-5" /> },
    { path: "/history", label: "Project History", icon: <History className="w-5 h-5" /> },
    {
      path: latestProjectId ? `/exports/${latestProjectId}` : "/exports",
      label: "Exports",
      icon: <FileSpreadsheet className="w-5 h-5" />,
    },
    { path: "/ratecards", label: "Pricing", icon: <Wallet className="w-5 h-5" /> },
  ];

  // Add Blob Manage only for superusers
  const navItems = user?.is_superuser
    ? [
        ...baseNavItems,
        { path: "/blobs", label: "Blob Manage", icon: <Database className="w-5 h-5" /> },
      ]
    : baseNavItems;

  const handleNavClick = () => {
    if (mobileOpen) setIsOpen(false);
  };

  const initials = user?.username?.[0]?.toUpperCase() || "?";

  return (
    <aside
      className={`fixed md:static left-0
        mt-14 md:mt-0
        h-[calc(100vh-56px)] md:h-screen
        flex flex-col justify-between
        ${isOpen ? "w-60" : "w-20"}
        bg-surface dark:bg-dark-surface shadow-lg border-r border-gray-200 dark:border-dark-muted
        transform transition-all duration-300 z-40
        ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
    >
      <div className="flex flex-col flex-1">
        {/* 🔹 Toggle */}
        <div className="flex justify-center items-center h-14 bg-primary dark:bg-dark-primary text-white">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="hidden md:flex items-center justify-center w-10 h-10 text-white hover:opacity-90 transition"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>

        {/* 🔹 Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={handleNavClick}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 ${
                  isActive
                    ? "bg-primary text-white font-medium shadow-sm"
                    : "text-muted dark:text-dark-muted hover:bg-gray-100 dark:hover:bg-dark-accent/30"
                }`
              }
            >
              {item.icon}
              <span
                className={`transition-all duration-300 origin-left ${
                  isOpen ? "opacity-100 scale-100" : "opacity-0 scale-0 hidden"
                }`}
              >
                {item.label}
              </span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* User Profile */}
      {user && (
        <div
          onClick={() => navigate("/profile")}
          className="flex items-center gap-3 px-3 py-3 cursor-pointer border-t border-gray-200 dark:border-dark-muted hover:bg-gray-100 dark:hover:bg-dark-accent/30 transition"
        >
          <div className="w-9 h-9 rounded-full bg-primary text-white font-bold flex items-center justify-center">
            {initials}
          </div>
          {isOpen && (
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-100">
                {user.username}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">View Profile</span>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
