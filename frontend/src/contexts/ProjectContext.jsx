// src/contexts/ProjectContext.js
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

  const getProjectById = async (id) => {
    try {
      const res = await projectApi.getProject(id);
      return res.data;
    } catch (err) {
      console.error(` Failed to fetch project ${id}:`, err);
      throw err;
    }
  };

  /**
   * Create a new project and immediately generate its scope + previews.
   * Supports company_id (for ratecards context)
   */
  const createProject = async (data) => {
    try {
      //  1. Create project (includes company_id if present)
      const res = await projectApi.createProject(data);
      const projectId = res.data.id;

      //  2. Generate scope
      const genRes = await projectApi.generateScope(projectId);
      const scope = genRes.data;

      //  3. Generate export previews (JSON, Excel, PDF)
      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(projectId, scope),
        exportApi.previewExcel(projectId, scope),
        exportApi.previewPdf(projectId, scope),
      ]);

      //  4. Refresh full project details (to include company & files)
      const fullProject = await getProjectById(projectId);
      setProjects((prev) => [fullProject, ...removeById(prev, projectId)]);

      //  5. Cache last preview and redirect path
      setLastPreviewScope(jsonPreview || scope);
      setLastRedirectUrl(`/exports/${projectId}`);
      localStorage.setItem("lastProjectId", projectId);

      return {
        projectId,
        scope,
        redirectUrl: `/exports/${projectId}`,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      console.error(" Failed to create project:", err);
      throw err;
    }
  };

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

  const finalizeScope = async (id, scopeData) => {
    try {
      //  1. Finalize on backend
      const res = await projectApi.finalizeScope(id, scopeData);
      const finalizedScope = res.data?.scope || scopeData;

      //  2. Refresh project list
      const fullProject = await getProjectById(id);
      setProjects((cur) => replaceById(cur, id, fullProject));

      //  3. Regenerate previews
      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(id, finalizedScope),
        exportApi.previewExcel(id, finalizedScope),
        exportApi.previewPdf(id, finalizedScope),
      ]);

      setLastPreviewScope(jsonPreview || finalizedScope);
      setLastRedirectUrl(`/exports/${id}`);

      return {
        scope: finalizedScope,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      console.error(` Failed to finalize scope for ${id}:`, err);
      throw err;
    }
  };

  const getFinalizedScope = async (id) => {
    try {
      const res = await projectApi.getFinalizedScope(id);
      return res.data || null; // Backend returns `null` if not finalized
    } catch (err) {
      console.error(` Failed to fetch finalized scope for ${id}:`, err);
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
        getFinalizedScope,
        setLastPreviewScope,
        setLastRedirectUrl,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjects = () => useContext(ProjectContext);
