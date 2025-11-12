// src/contexts/ProjectContext.js
import { createContext, useState, useContext, useCallback } from "react";
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

  const fetchProjects = useCallback(async () => {
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
  }, []);
  
  const getProjectById = async (id) => {
    try {
      const res = await projectApi.getProject(id);
      return res.data;
    } catch (err) {
      console.error(` Failed to fetch project ${id}:`, err);
      throw err;
    }
  };

  // ==========================================================
  // 🧱 Create Project (Only — no scope, no questions)
  // ==========================================================
  const createProject = async (data) => {
    try {
      //  1️⃣ Create project record only
      const res = await projectApi.createProject(data);
      const projectId = res.data.id;

      //  2️⃣ Refresh project list
      const fullProject = await getProjectById(projectId);
      setProjects((prev) => [fullProject, ...removeById(prev, projectId)]);
      localStorage.setItem("lastProjectId", projectId);

      console.log(`✅ Project created: ${projectId}`);
      return { projectId, project: fullProject };
    } catch (err) {
      console.error("❌ Failed to create project:", err);
      throw err;
    }
  };

  // ==========================================================
  // ⚡ Optional Quick Flow: Create + Auto-Generate Scope
  // ==========================================================
  const createProjectWithScope = async (data) => {
    try {
      const { projectId } = await createProject(data);

      // Auto generate scope
      const genRes = await projectApi.generateScope(projectId);
      const scope = genRes.data;

      // Generate export previews
      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(projectId, scope),
        exportApi.previewExcel(projectId, scope),
        exportApi.previewPdf(projectId, scope),
      ]);

      setLastPreviewScope(jsonPreview || scope);
      setLastRedirectUrl(`/exports/${projectId}`);

      return {
        projectId,
        scope,
        redirectUrl: `/exports/${projectId}`,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      console.error("❌ Failed to create project with scope:", err);
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

 // ==========================================================
  // 🔁 Regenerate Scope (with user instructions)
  // ==========================================================
  const regenerateScope = async (projectId, draftScope, instructions = "") => {
    try {
      if (!draftScope || Object.keys(draftScope).length === 0) {
        throw new Error("Missing draft scope data for regeneration.");
      }

      // 1️⃣ Call backend regeneration API
      const payload = { draft: draftScope, instructions };
      const res = await projectApi.regenerateScope(projectId, payload);
      const regenScope = res.data || {};

      console.log(`✅ Regenerated scope for project ${projectId}`);

      // 2️⃣ Generate export previews (JSON / Excel / PDF)
      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(projectId, regenScope),
        exportApi.previewExcel(projectId, regenScope),
        exportApi.previewPdf(projectId, regenScope),
      ]);

      // 3️⃣ Cache in context state
      setLastPreviewScope(jsonPreview || regenScope);
      setLastRedirectUrl(`/exports/${projectId}`);

      return {
        projectId,
        scope: regenScope,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      console.error(`❌ Failed to regenerate scope for ${projectId}:`, err);
      throw err;
    }
  };

  const finalizeScope = async (id, scopeData) => {
    try {
      const res = await projectApi.finalizeScope(id, scopeData);
      const finalizedScope = res.data?.scope || scopeData;

      const fullProject = await getProjectById(id);
      setProjects((cur) => replaceById(cur, id, fullProject));

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

  // Clarified Flow: Generate & Update Questions + Refined Scope
  const generateQuestions = async (id) => {
    try {
      const res = await projectApi.generateQuestions(id);

      //  Handle both possible backend responses:
      // Either returns { msg, questions: [...] } OR directly [ ... ]
      const questions = Array.isArray(res.data)
        ? res.data
        : res.data?.questions || [];

      console.log(
        ` Generated ${questions.length} categorized questions for project ${id}`
      );

      return questions;
    } catch (err) {
      console.error(` Failed to generate questions for ${id}:`, err);
      throw err;
    }
  };

  const updateQuestions = async (projectId, answers) => {
    try {
      const res = await projectApi.updateQuestions(projectId, answers);
      console.log(` Updated questions for project ${projectId}`);
      return res.data;
    } catch (err) {
      console.error(` Failed to update questions for ${projectId}:`, err);
      throw err;
    }
  };



  // Use answered questions to generate refined scope
  const generateRefinedScope = async (projectId, userAnswers = {}) => {
    try {
      //  Update the questions file with user answers
      if (Object.keys(userAnswers || {}).length > 0) {
        await projectApi.updateQuestions(projectId, userAnswers);
      }

      // Generate scope again (now enriched by Q&A)
      const genRes = await projectApi.generateScope(projectId);
      const scope = genRes.data;

      //  Generate export previews
      const [jsonPreview, excelPreview, pdfPreview] = await Promise.all([
        exportApi.previewJson(projectId, scope),
        exportApi.previewExcel(projectId, scope),
        exportApi.previewPdf(projectId, scope),
      ]);

      // Cache preview & redirect path
      setLastPreviewScope(jsonPreview || scope);
      setLastRedirectUrl(`/exports/${projectId}`);

      return {
        projectId,
        scope,
        previews: { jsonPreview, excelPreview, pdfPreview },
      };
    } catch (err) {
      console.error(` Failed to generate refined scope for ${projectId}:`, err);
      throw err;
    }
  };

  const getQuestions = async (id) => {
    try {
      const res = await projectApi.getQuestions(id);
      const questions = res.data?.questions || [];
      console.log(` Loaded ${questions.length} questions for project ${id}`);
      return questions;
    } catch (err) {
      if (err?.response?.status === 404) {
        console.warn(` No saved questions found for project ${id}`);
        return [];
      }
      console.error(` Failed to fetch questions for ${id}:`, err);
      throw err;
    }
  };


  const getFinalizedScope = async (id) => {
    try {
      const res = await projectApi.getFinalizedScope(id);
      return res.data || null;
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
        generateQuestions,
        getQuestions,
        updateQuestions,
        createProjectWithScope,
        generateRefinedScope,
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
