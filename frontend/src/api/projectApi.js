import api from "./axiosClient";

// Helper to append only non-empty values
const appendIfPresent = (formData, key, value) => {
  if (value === undefined || value === null) return;
  const v = typeof value === "string" ? value.trim() : value;
  if (v !== "" && v !== null && v !== undefined) {
    formData.append(key, v);
  }
};

const projectApi = {
  // -------------------------------
  // Projects
  // -------------------------------
  getProjects: () => api.get("/projects"),
  getProject: (id) => api.get(`/projects/${id}`),

  createProject: (data) => {
    const formData = new FormData();
    appendIfPresent(formData, "name", data.name);
    appendIfPresent(formData, "domain", data.domain);
    appendIfPresent(formData, "complexity", data.complexity);
    appendIfPresent(formData, "tech_stack", data.tech_stack);
    appendIfPresent(formData, "use_cases", data.use_cases);

    if (Array.isArray(data.compliance)) {
      data.compliance.forEach((c) => formData.append("compliance", c));
    } else {
      appendIfPresent(formData, "compliance", data.compliance);
    }

    appendIfPresent(formData, "duration", data.duration);

    if (Array.isArray(data.files) && data.files.length > 0) {
      data.files.forEach((item) => {
        const fileObj = item?.file || item;
        if (fileObj instanceof File || fileObj instanceof Blob) {
          formData.append("files", fileObj);
        }
        if (item?.type) {
          formData.append("file_types", String(item.type));
        }
      });
    }

    return api.post("/projects", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  deleteProject: (id) => api.delete(`/projects/${id}`),
  deleteAllProjects: () => api.delete("/projects"),

  generateScope: (id) => api.get(`/projects/${id}/generate_scope`),
  finalizeScope: (id, scopeData) =>
    api.post(`/projects/${id}/finalize_scope`, scopeData, {
      headers: { "Content-Type": "application/json" },
    }),

  // -------------------------------
  // Blob helpers (URLs only)
  // -------------------------------
  getDownloadUrl: (filePath, base = "projects") =>
    `${api.defaults.baseURL}/blobs/download/${filePath}?base=${base}`,

  getPreviewUrl: (filePath, base = "projects") =>
    `${api.defaults.baseURL}/blobs/preview/${filePath}?base=${base}`,
};

export default projectApi;
