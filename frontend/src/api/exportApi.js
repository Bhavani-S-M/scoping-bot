// src/api/exportApi.js
import api from "./axiosClient";

// Safe filename helper
export const safeFileName = (name, ext) =>
  name.replace(/[^a-z0-9_\-]/gi, "_").toLowerCase() + `.${ext}`;

// Generic GET export with progress + abort support
const fetchExportBlob = async (url, { signal, onDownloadProgress } = {}) => {
  const res = await api.get(url, {
    responseType: "blob",
    signal,
    onDownloadProgress,
  });

  const contentType = res.headers["content-type"] || "";
  if (contentType.includes("application/json")) {
    // Handle backend error returned as JSON
    let errorMsg = "Export failed";
    try {
      const text = await new Response(res.data).text();
      errorMsg = JSON.parse(text).detail || errorMsg;
    } catch {
      errorMsg = typeof res.data === "string" ? res.data : errorMsg;
    }
    throw new Error(errorMsg);
  }

  return res.data;
};

const exportApi = {
  // ---------- Previews (Draft-only, before finalization) ----------
  previewJson: async (projectId, scope, { signal, onDownloadProgress } = {}) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/json`,
      scope,
      { signal, onDownloadProgress }
    );
    return res.data;
  },

  previewExcel: async (projectId, scope, { signal, onDownloadProgress } = {}) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/excel`,
      scope,
      { responseType: "blob", signal, onDownloadProgress }
    );
    console.log("Excel preview response:", res);
    console.log("Excel preview headers:", res.headers);
    console.log("Excel preview data type:", typeof res.data);
    console.log("Excel preview data:", res.data);
    return res.data;
  },

  previewPdf: async (projectId, scope, { signal, onDownloadProgress } = {}) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/pdf`,
      scope,
      { responseType: "blob", signal, onDownloadProgress }
    );
    return res.data;
  },

  // ---------- Finalize Scope ----------
  finalizeScope: async (projectId, scope, { signal } = {}) => {
    const res = await api.post(
      `/projects/${projectId}/finalize_scope`,
      scope,
      {
        headers: { "Content-Type": "application/json" },
        signal,
      }
    );
    return res.data;
  },

  // ---------- Regenerate Scope ----------
  regenerateScope: async (projectId, draft, instructions, { signal } = {}) => {
    const res = await api.post(
      `/projects/${projectId}/regenerate_scope`,
      { draft, instructions },
      {
        headers: { "Content-Type": "application/json" },
        signal,
      }
    );
    return res.data;
  },

  // ---------- Finalized Exports (Downloadables from DB) ----------
  getPdfBlob: async (projectId, { signal, onDownloadProgress } = {}) => {
    return fetchExportBlob(`/projects/${projectId}/export/pdf`, {
      signal,
      onDownloadProgress,
    });
  },

  exportToExcel: async (projectId, { signal, onDownloadProgress } = {}) => {
    return fetchExportBlob(`/projects/${projectId}/export/excel`, {
      signal,
      onDownloadProgress,
    });
  },

  exportToPdf: async (projectId, { signal, onDownloadProgress } = {}) => {
    return fetchExportBlob(`/projects/${projectId}/export/pdf`, {
      signal,
      onDownloadProgress,
    });
  },

  exportToJson: async (projectId, { signal, onDownloadProgress } = {}) => {
    const res = await api.get(`/projects/${projectId}/export/json`, {
      signal,
      onDownloadProgress,
    });
    return res.data;
  },

};

export default exportApi;
