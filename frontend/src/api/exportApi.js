import api from "./axiosClient";

// Safe filename helper
const safeFileName = (name, ext) =>
  name.replace(/\s+/g, "_").toLowerCase() + `.${ext}`;

// Generic GET export (just return blob)
const fetchExportBlob = async (url) => {
  const res = await api.get(url, { responseType: "blob" });

  const contentType = res.headers["content-type"] || "";
  if (contentType.includes("application/json")) {
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

  // Preveiw
  previewJson: async (projectId, scope) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/json`,
      scope
    );
    return res.data;
  },

  previewExcel: async (projectId, scope) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/excel`,
      scope,
      { responseType: "blob" }
    );
    return res.data;
  },

  previewPdf: async (projectId, scope) => {
    const res = await api.post(
      `/projects/${projectId}/export/preview/pdf`,
      scope,
      { responseType: "blob" }
    );
    return res.data;
  },

  // Finalise
  finalizeScope: async (projectId, scope) => {
    const res = await api.post(
      `/projects/${projectId}/finalize_scope`,
      scope,
      { headers: { "Content-Type": "application/json" } }
    );
    return res.data; 
  },

  // Finalised Exports

  getPdfBlob: async (projectId) => {
    return fetchExportBlob(`/projects/${projectId}/export/pdf`);
  },

  exportToExcel: async (projectId) => {
    return fetchExportBlob(`/projects/${projectId}/export/excel`);
  },

  exportToPdf: async (projectId) => {
    return fetchExportBlob(`/projects/${projectId}/export/pdf`);
  },

  exportToJson: async (projectId) => {
    const res = await api.get(`/projects/${projectId}/export/json`);
    return res.data;
  },
};

export default exportApi;
