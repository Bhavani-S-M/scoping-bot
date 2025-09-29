import { createContext, useState, useContext } from "react";
import projectApi from "../api/projectApi";
import exportApi from "../api/exportApi";

const ProjectContext = createContext();

const replaceById = (list, id, next) =>
  list.map((p) => (p.id === id ? { ...p, ...next } : p));

const removeById = (list, id) => list.filter((p) => p.id !== id);

export const ProjectProvider = ({ children }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [lastPreviewScope, setLastPreviewScope] = useState(null);
  const [lastRedirectUrl, setLastRedirectUrl] = useState(null);

  // Fetch all projects
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await projectApi.getProjects();
      setProjects(res.data || []);
      setError(null);
    } catch (err) {
      console.error(" Failed to fetch projects:", err);
      setError("Failed to fetch projects");
    } finally {
      setLoading(false);
    }
  };

  // 🔹 Get single project
  const getProjectById = async (id) => {
    try {
      const res = await projectApi.getProject(id);
      return res.data;
    } catch (err) {
      console.error(` Failed to fetch project ${id}:`, err);
      throw err;
    }
  };

  // Create project + auto previews
  const createProject = async (data) => {
    const tempId = `temp-${Date.now()}`;
    const tempProject = { id: tempId, ...data, _optimistic: true };
    setProjects((prev) => [tempProject, ...prev]);

    try {
      const res = await projectApi.createProject(data);
      const { project_id, scope, redirect_url } = res.data;

      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(project_id, scope),
        exportApi.previewExcel(project_id, scope),
        exportApi.previewPdf(project_id, scope),
      ]);

      const full = await getProjectById(project_id);
      setProjects((prev) => [full, ...removeById(prev, tempId)]);

      setLastPreviewScope(jsonPreview || scope || null);
      setLastRedirectUrl(redirect_url || null);

      return {
        projectId: project_id,
        scope,
        redirectUrl: redirect_url,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      setProjects((prev) => removeById(prev, tempId));
      console.error(" Failed to create project:", err);
      throw err;
    }
  };

  // Update project
  const updateProject = async (id, data) => {
    const prev = projects;
    setProjects((cur) => replaceById(cur, id, data));

    try {
      const res = await projectApi.updateProject(id, data);
      setProjects((cur) => replaceById(cur, id, res.data || data));
      return res.data;
    } catch (err) {
      setProjects(prev);
      console.error(` Failed to update project ${id}:`, err);
      throw err;
    }
  };

  // Delete project
  const deleteProject = async (id) => {
    const prev = projects;
    setProjects((cur) => removeById(cur, id));

    try {
      await projectApi.deleteProject(id);
    } catch (err) {
      setProjects(prev);
      console.error(` Failed to delete project ${id}:`, err);
      throw err;
    }
  };

  // Delete ALL projects
  const deleteAllProjects = async () => {
    const prev = projects;
    setProjects([]);
    try {
      await projectApi.deleteAllProjects();
    } catch (err) {
      setProjects(prev);
      console.error(" Failed to delete all projects:", err);
      throw err;
    }
  };

  // Regenerate preview scope (auto-uses finalized if exists)
  const regenerateScope = async (id, draftScope = null) => {
    try {
      let scopeToUse = draftScope;
      try {
        scopeToUse = await exportApi.exportToJson(id); 
      } catch (err) {
        if (err?.response?.status === 400) {
          scopeToUse = draftScope || {}; 
        } else throw err;
      }

      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(id, scopeToUse),
        exportApi.previewExcel(id, scopeToUse),
        exportApi.previewPdf(id, scopeToUse),
      ]);

      setLastPreviewScope(jsonPreview || null);
      return jsonPreview;
    } catch (err) {
      console.error(` Failed to regenerate scope for ${id}:`, err);
      throw err;
    }
  };

  // Finalize scope (and auto-refresh previews)
const finalizeScope = async (id, scopeData) => {
  try {
    const res = await projectApi.finalizeScope(id, scopeData);
    const finalizedScope = res.data?.scope || scopeData;

    const full = await getProjectById(id);
    setProjects((cur) => replaceById(cur, id, full));

    // ⟳ Immediately refresh previews using finalized scope
    await regenerateScope(id, finalizedScope);

    return res.data;
  } catch (err) {
    console.error(` Failed to finalize scope for ${id}:`, err);
    throw err;
  }
};


  return (
    <ProjectContext.Provider
      value={{
        projects,
        loading,
        error,
        lastPreviewScope,
        lastRedirectUrl,
        fetchProjects,
        getProjectById,
        createProject,
        updateProject,
        deleteProject,
        deleteAllProjects,
        regenerateScope,
        finalizeScope,
        setLastPreviewScope,
        setLastRedirectUrl,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjects = () => useContext(ProjectContext);
