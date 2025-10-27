import { useEffect } from "react";
import { useProjects } from "../contexts/ProjectContext";
import { useAuth } from "../contexts/AuthContext";
import {
  Trash2,
  PlusCircle,
  Folder,
  Eye,
  History
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const { projects, fetchProjects, deleteProject } = useProjects();
  const { user } = useAuth();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);


  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this project?")) {
      await deleteProject(id);
    }
  };

  // Today's date
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  // Complexity breakdown
  const complexityData = ["Simple", "Medium", "Large"].map((c) => ({
    complexity: c,
    count: projects.filter((p) => p.complexity === c).length,
  }));

  //  Daily projects created
  const dailyData = projects.reduce((acc, p) => {
    const day = new Date(p.created_at).toLocaleDateString("en-US", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    const existing = acc.find((d) => d.day === day);
    if (existing) existing.count += 1;
    else acc.push({ day, count: 1 });
    return acc;
  }, []);

  // Sort chronologically
  dailyData.sort((a, b) => new Date(a.day) - new Date(b.day));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-800 dark:text-gray-100">
            Welcome {user ? `, ${user.username}` : ""}!
          </h1>
          <p className="text-gray-500 dark:text-gray-400">{today}</p>
          <p className="text-gray-500 dark:text-gray-400">
            Here’s a quick overview of your scoping activity.
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Complexity Bar */}
        <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
          <h2 className="text-lg font-semibold mb-4 text-gray-700 dark:text-gray-100">
            Projects by Complexity
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={complexityData}>
              <XAxis dataKey="complexity" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: "12px" }} />
              <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Daily Line */}
        <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
          <h2 className="text-lg font-semibold mb-4 text-gray-700 dark:text-gray-100">
            Projects Created per Day
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyData}>
              <XAxis dataKey="day" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: "12px" }} />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#14b8a6"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Link
          to="/projects"
          className="flex-1 flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-xl shadow hover:bg-secondary transition"
        >
          <PlusCircle className="w-5 h-5" />
          Create New Project
        </Link>
        <Link
          to="/history"
          className="flex-1 flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-xl shadow hover:bg-secondary transition"
        >
          <History className="w-5 h-5" />
          View History
        </Link>
      </div>

      {/* Recent Projects */}
      <div className="bg-white dark:bg-dark-surface rounded-xl shadow-md border border-gray-200 dark:border-dark-muted p-6">
        <div className="flex items-center gap-2 mb-4 justify-between">
          <div className="flex items-center gap-2">
            <Folder className="w-6 h-6 text-gray-500 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-100">
              Recent Projects
            </h3>
          </div>
        </div>

        {projects.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">
            No projects yet. Create one!
          </p>
        ) : (
          <table className="min-w-full text-sm border border-gray-200 dark:border-dark-muted rounded-lg overflow-hidden">
            <thead className="bg-gray-100 dark:bg-dark-muted text-gray-700 dark:text-gray-300">
              <tr>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Domain</th>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {[...projects]
                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                .slice(0, 5)
                .map((p) => (

                <tr
                  key={p.id}
                  className="border-t border-gray-200 dark:border-dark-muted hover:bg-gray-50 dark:hover:bg-dark-background transition"
                >
                  <td className="px-4 py-2 font-semibold">
                    <Link
                      to={`/exports/${p.id}?mode=draft`}
                      className="text-primary hover:underline"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {p.domain || "-"}
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {new Date(p.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 flex items-center gap-3 justify-end">
                    <Link
                      to={`/exports/${p.id}?mode=draft`}
                      className="flex items-center gap-1 text-primary hover:underline"
                    >
                      <Eye className="w-5 h-5" />
                      View
                    </Link>
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="flex items-center gap-1 text-red-600 hover:text-red-800 transition"
                    >
                      <Trash2 className="w-5 h-5" />
                      Delete
                    </button>
                  </td>
                </tr>
              ))}

            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
