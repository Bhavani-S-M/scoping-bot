import { useEffect, useState, useMemo } from "react";
import { useProjects } from "../contexts/ProjectContext";
import {
  Eye,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Trash2,
  Folder,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function ProjectsHistory() {
  const { projects, fetchProjects, deleteAllProjects, deleteProject } = useProjects();
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [visibleCount, setVisibleCount] = useState(20);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const filtered = useMemo(() => {
    let list = [...projects];

    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (p) =>
          p.name?.toLowerCase().includes(q) ||
          p.domain?.toLowerCase().includes(q) ||
          String(p.duration || "").toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "created_at") {
        valA = new Date(a.created_at);
        valB = new Date(b.created_at);
      } else if (sortField === "duration") {
        valA = parseInt(a.duration || 0);
        valB = parseInt(b.duration || 0);
      } else {
        valA = String(valA || "").toLowerCase();
        valB = String(valB || "").toLowerCase();
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return list;
  }, [projects, query, sortField, sortOrder]);

  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + window.scrollY >=
        document.body.offsetHeight - 150
      ) {
        if (!loadingMore && visibleCount < filtered.length) {
          setLoadingMore(true);
          setTimeout(() => {
            setVisibleCount((prev) => prev + 20);
            setLoadingMore(false);
          }, 800);
        }
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [filtered.length, visibleCount, loadingMore]);

  const visible = filtered.slice(0, visibleCount);

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const handleDeleteAll = async () => {
    if (window.confirm("Are you sure you want to delete ALL projects?")) {
      await deleteAllProjects();
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this project?")) {
      await deleteProject(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-dark-surface rounded-xl shadow-md border border-gray-200 dark:border-dark-muted p-6">
        {/* Header row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          {/* Total */}
          <div className="flex items-center gap-2">
            <Folder className="w-6 h-6 text-gray-500 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-100">
              Total Projects: {projects.length}
            </h3>
          </div>

          {/* Search */}
          <div className="flex-1 flex justify-center">
            <div className="relative w-full max-w-lg">
              <Search className="absolute left-3 top-2.5 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search by name, domain, or duration..."
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setVisibleCount(20);
                }}
                className="w-full pl-10 pr-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 
                  bg-white dark:bg-dark-background text-gray-700 dark:text-gray-200 
                  placeholder-gray-400 focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              />
            </div>
          </div>

          {/* Delete All */}
          {projects.length > 0 && (
            <button
              onClick={handleDeleteAll}
              className="flex items-center gap-2 px-3 py-2 bg-primary text-white rounded-md hover:bg-secondary transition"
            >
              <Trash2 className="w-4 h-4" />
              Delete All
            </button>
          )}
        </div>

        {/* Table */}
        {visible.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">No projects found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm border border-gray-200 dark:border-dark-muted rounded-lg overflow-hidden">
              <thead className="bg-gray-100 dark:bg-dark-muted text-gray-700 dark:text-gray-300">
                <tr>
                  {["name", "domain", "duration", "created_at"].map((field) => (
                    <th
                      key={field}
                      className="px-4 py-2 text-left cursor-pointer select-none"
                      onClick={() => toggleSort(field)}
                    >
                      <div className="flex items-center gap-1">
                        {field === "created_at"
                          ? "Created"
                          : field[0].toUpperCase() + field.slice(1)}
                        {sortField === field ? (
                          sortOrder === "asc" ? (
                            <ArrowUp className="w-4 h-4" />
                          ) : (
                            <ArrowDown className="w-4 h-4" />
                          )
                        ) : (
                          <ArrowUpDown className="w-4 h-4 opacity-40" />
                        )}
                      </div>
                    </th>
                  ))}
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((p) => (
                  <tr
                    key={p.id}
                    className="border-t border-gray-200 dark:border-dark-muted hover:bg-gray-50 dark:hover:bg-dark-background transition"
                  >
                    <td className="px-4 py-2 font-semibold text-gray-800 dark:text-gray-100">
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
                      {p.duration || "-"}
                    </td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2 flex justify-end gap-3">
                      <Link
                        to={`/exports/${p.id}?mode=draft`}
                        className="flex items-center gap-1 text-primary hover:underline"
                      >
                        <Eye className="w-5 h-5" /> View
                      </Link>
                      <button
                        onClick={() => handleDelete(p.id)}
                        className="flex items-center gap-1 text-red-600 hover:text-red-800 transition"
                      >
                        <Trash2 className="w-4 h-4" /> Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {loadingMore && (
          <div className="flex justify-center py-4">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}
      </div>
    </div>
  );
}
