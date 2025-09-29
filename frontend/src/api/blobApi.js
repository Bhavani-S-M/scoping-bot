// src/api/blobApi.js
import api from "./axiosClient";

// Helper: append only non-empty values
const appendIfPresent = (formData, key, value) => {
  if (value === undefined || value === null) return;
  const v = typeof value === "string" ? value.trim() : value;
  if (v !== "" && v !== null && v !== undefined) {
    formData.append(key, v);
  }
};

const blobApi = {

  // Uploads (base-aware)
  uploadFile: (file, folder = "", base = "knowledge_base") => {
    const form = new FormData();
    form.append("file", file);
    appendIfPresent(form, "folder", folder);
    appendIfPresent(form, "base", base);
    return api.post("/blobs/upload/file", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  uploadFolder: (files, folder = "", base = "knowledge_base") => {
    const form = new FormData();

    for (const f of files) {
      // Keep folder structure if user selected with webkitdirectory
      const relPath = f.webkitRelativePath || f.name;
      form.append("files", f, relPath);
    }

    appendIfPresent(form, "folder", folder);
    appendIfPresent(form, "base", base);

    return api.post("/blobs/upload/folder", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },


  // Listing (Explorer-style only)
  explorer: (base = "knowledge_base") =>
    api.get(`/blobs/explorer/${base}`),

  //  Download & Preview
  download: (blobName, base = "knowledge_base") =>
    api.get(`/blobs/download/${encodeURIComponent(blobName)}?base=${base}`, {
      responseType: "blob",
    }),

  preview: (blobName, base = "knowledge_base") =>
    api.get(`/blobs/preview/${encodeURIComponent(blobName)}?base=${base}`, {
      responseType: "blob",
    }),

  // Deletion
  deleteFile: (blobName, base = "knowledge_base") =>
    api.delete(`/blobs/delete/file/${encodeURIComponent(blobName)}?base=${base}`),

  deleteFolder: (folder, base = "knowledge_base") =>
    api.delete(`/blobs/delete/folder/${encodeURIComponent(folder)}?base=${base}`),

  // SAS Token
  getSasToken: (hours = 1) =>
    api.get(`/blobs/sas-token?hours=${hours}`),
};

export default blobApi;
