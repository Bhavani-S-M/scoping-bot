import { createContext, useContext, useState, useCallback } from "react";
import blobApi from "../api/blobApi";

const BlobContext = createContext();

export const BlobProvider = ({ children }) => {
  const [tree, setTree] = useState([]); 
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeBase, setActiveBase] = useState("knowledge_base");

  // Load full explorer tree
  const loadExplorer = useCallback(
    async (base = activeBase) => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await blobApi.explorer(base);
        setTree(data.children || []); 
        setActiveBase(base);
        return data.children || [];
      } catch (err) {
        console.error(" loadExplorer failed:", err);
        setError("Failed to load explorer");
        return [];
      } finally {
        setLoading(false);
      }
    },
    [activeBase]
  );
  

  //  Uploads
  const uploadFile = async (file, folder = "", base = activeBase) => {
    try {
      const { data } = await blobApi.uploadFile(file, folder, base);
      await loadExplorer(base); 
      return data;
    } catch (err) {
      setError("File upload failed");
      throw err;
    }
  };

  const uploadFolder = async (files, folder = "", base = activeBase) => {
    try {
      const { data } = await blobApi.uploadFolder(files, folder, base);
      await loadExplorer(base); 
      return data;
    } catch (err) {
      setError("Folder upload failed");
      throw err;
    }
  };

  //  Download & Preview
  const downloadFile = async (blobName, base = activeBase) => {
    try {
      const res = await blobApi.download(blobName, base);
      return res.data;
    } catch {
      setError("File download failed");
      return null;
    }
  };

  const previewFile = async (blobName, base = activeBase) => {
    try {
      const res = await blobApi.preview(blobName, base);
      const contentType =
        res.headers["content-type"] || "application/octet-stream";
      const blob = new Blob([res.data], { type: contentType });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch {
      setError("File preview failed");
    }
  };

  //  Deletions
  const deleteFile = async (name, base = activeBase) => {
    try {
      await blobApi.deleteFile(name, base);
      await loadExplorer(base); 
      return name;
    } catch {
      setError("File delete failed");
      return null;
    }
  };

  const deleteFolder = async (name, base = activeBase) => {
    try {
      const { data } = await blobApi.deleteFolder(name, base);
      await loadExplorer(base);
      return data.deleted;
    } catch {
      setError("Folder delete failed");
      return [];
    }
  };

  return (
    <BlobContext.Provider
      value={{
        tree,
        loading,
        error,
        activeBase,
        setActiveBase,
        loadExplorer,
        uploadFile,
        uploadFolder,
        downloadFile,
        previewFile,
        deleteFile,
        deleteFolder,
      }}
    >
      {children}
    </BlobContext.Provider>
  );
};

export const useBlobs = () => useContext(BlobContext);
