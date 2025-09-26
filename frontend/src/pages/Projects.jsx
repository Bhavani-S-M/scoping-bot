import { useNavigate } from "react-router-dom";
import ProjectForm from "../components/ProjectForm";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function Projects() {
  const navigate = useNavigate();

  const handleCreate = (response) => {
    const { projectId, scope, redirectUrl, previews } = response || {};

    toast.success("Project created successfully! Redirecting to preview...", {
      position: "top-center",
      autoClose: 1200,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: false,
      draggable: true,
    });

    setTimeout(() => {
      if (redirectUrl) {
        navigate(redirectUrl, { state: { draftScope: scope, previews } });
      } else if (projectId) {
        navigate(`/exports/${projectId}`, { state: { draftScope: scope, previews } });
      }
    }, 1200);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-3xl font-extrabold text-primary dark:text-dark-primary text-center">
        Generate a New Project Scope
      </h1>

      <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
        <ProjectForm onSubmit={handleCreate} />
      </div>

      <ToastContainer />
    </div>
  );
}
