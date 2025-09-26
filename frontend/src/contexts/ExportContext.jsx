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

  // Finalized exports (from DB)
  const downloadExcel = (id) => handleExport(exportApi.exportToExcel, id);
  const downloadPdf = (id) => handleExport(exportApi.exportToPdf, id);
  const exportJson = (id, download = false) =>
    handleExport(exportApi.exportToJson, id, download);
  const getPdfBlob = (id) => handleExport(exportApi.getPdfBlob, id);

  //  Try getting finalized scope — returns null if not finalized
  const getFinalizedScope = async (id) => {
    try {
      return await handleExport(exportApi.exportToJson, id);
    } catch (err) {
      if (err?.response?.status === 400) return null; // not finalized
      throw err;
    }
  };

  // Preview exports

  const previewJson = async (id, scope) => {
    const finalScope = await getFinalizedScope(id);
    const data = finalScope || scope;
    if (!data || Object.keys(data).length === 0) return {};
    return handleExport(exportApi.previewJson, id, data);
  };

  const previewExcel = async (id, scope) => {
    const finalScope = await getFinalizedScope(id);
    const data = finalScope || scope;
    if (!data || Object.keys(data).length === 0) return null;
    return handleExport(exportApi.previewExcel, id, data);
  };

  const previewPdf = async (id, scope) => {
    const finalScope = await getFinalizedScope(id);
    const data = finalScope || scope;
    if (!data || Object.keys(data).length === 0) return null;
    return handleExport(exportApi.previewPdf, id, data);
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
        loading,
        error,
      }}
    >
      {children}
    </ExportContext.Provider>
  );
};

export const useExport = () => useContext(ExportContext);
