import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import projectApi from "../api/projectApi";
import { RefreshCw, Download, File } from "lucide-react";

export default function ProjectDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadProject = async () => {
      try {
        const res = await projectApi.getProject(id);
        setProject(res.data);
      } catch (err) {
        console.error("Failed to fetch project:", err);
      }
    };

    loadProject();
  }, [id]); 

  const regenerateScope = async () => {
    try {
      setLoading(true);
      const res = await projectApi.generateScope(id);
      navigate(`/exports/${id}`, { state: { draftScope: res.data } });
    } catch (err) {
      console.error("Failed to regenerate scope:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!project)
    return (
      <p className="text-gray-500 dark:text-gray-400 text-center mt-10">
        Loading project...
      </p>
    );

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Project Header */}
      <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
            {project.name}
          </h1>
          <button
            onClick={regenerateScope}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg shadow hover:bg-secondary transition disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Regenerating..." : "Regenerate Scope"}
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-4 text-gray-700 dark:text-gray-300">
          <p><strong>Domain:</strong> {project.domain || "-"}</p>
          <p><strong>Complexity:</strong> {project.complexity || "-"}</p>
          <p><strong>Tech Stack:</strong> {project.tech_stack || "-"}</p>
          <p><strong>Use Cases:</strong> {project.use_cases || "-"}</p>
          <p><strong>Compliance:</strong> {project.compliance || "-"}</p>
          <p><strong>Duration:</strong> {project.duration || "-"}</p>
        </div>
      </div>

      {/* Uploaded Files */}
      <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
        <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
          Uploaded Documents
        </h2>
        {project.files && project.files.length > 0 ? (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {project.files.map((file) => (
              <li
                key={file.id}
                className="flex justify-between items-center py-3 hover:bg-gray-50 dark:hover:bg-dark-background rounded-lg px-2 transition"
              >
                <div className="flex items-center gap-2">
                  <File className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {file.file_name}
                  </span>
                  {file.file_type && (
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      ({file.file_type})
                    </span>
                  )}
                </div>
                <a
                  href={projectApi.getDownloadUrl(file.file_path, "projects")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-primary hover:underline text-sm"
                >
                  <Download className="w-4 h-4" />
                  Download
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No documents uploaded.</p>
        )}
      </div>
    </div>
  );
}
