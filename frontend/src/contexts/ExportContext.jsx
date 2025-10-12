// src/contexts/ExportContext.js
import { createContext, useContext, useState } from "react";
import exportApi from "../api/exportApi";

const ExportContext = createContext();

export const ExportProvider = ({ children }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleExport = async (fn, ...args) => {
    try {
      setLoading(true);
      setError(null);
      return await fn(...args);
    } catch (err) {
      console.error(" Export failed:", err);
      const message =
        err?.message ||
        err?.response?.data?.detail ||
        "Export failed. Please try again.";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // ---------- Finalized exports (from DB) ----------
  const downloadExcel = (id, opts = {}) =>
    handleExport(exportApi.exportToExcel, id, opts);

  const downloadPdf = (id, opts = {}) =>
    handleExport(exportApi.exportToPdf, id, opts);

  const exportJson = (id, opts = {}) =>
    handleExport(exportApi.exportToJson, id, opts);

  const getPdfBlob = (id, opts = {}) =>
    handleExport(exportApi.getPdfBlob, id, opts);

  // ---------- Previews (draft-only, before finalization) ----------
  const previewJson = (id, scope, opts = {}) => {
    if (!scope || Object.keys(scope).length === 0) return {};
    console.log("JSON preview scope:", scope);
    console.log("JSON preview opts:", opts);
    return handleExport(exportApi.previewJson, id, scope, opts);

  };

  const previewExcel = (id, scope, opts = {}) => {
    if (!scope || Object.keys(scope).length === 0) return null;
    console.log("Excel preview scope:", scope);

    return handleExport(exportApi.previewExcel, id, scope, opts);
  };

  const previewPdf = (id, scope, opts = {}) => {
    if (!scope || Object.keys(scope).length === 0) return null;
    return handleExport(exportApi.previewPdf, id, scope, opts);
  };

  // ---------- Regenerate scope ----------
  const regenerateScope = (id, draft, instructions, opts = {}) => {
    if (!draft || Object.keys(draft).length === 0) return null;
    return handleExport(exportApi.regenerateScope, id, draft, instructions, opts);
  };

  return (
    <ExportContext.Provider
      value={{
        downloadExcel,
        downloadPdf,
        exportJson,
        getPdfBlob,
        previewJson,
        previewExcel,
        previewPdf,
        regenerateScope,
        loading,
        error,
      }}
    >
      {children}
    </ExportContext.Provider>
  );
};

export const useExport = () => useContext(ExportContext);
