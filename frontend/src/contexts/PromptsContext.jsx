import { createContext, useState, useContext, useCallback } from "react";
import promptsApi from "../api/promptsApi";
import { toast } from "react-toastify";

const PromptsContext = createContext();

export const PromptsProvider = ({ children }) => {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load all prompts for a project
  const loadPrompts = useCallback(async (projectId) => {
    try {
      setLoading(true);
      const data = await promptsApi.getPrompts(projectId);
      setPrompts(data);
      return data;
    } catch (err) {
      console.error("Failed to load prompts:", err);
      toast.error("Failed to load chat history");
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Add a new prompt
  const addPrompt = useCallback(async (projectId, message, role = "user") => {
    try {
      const res = await promptsApi.addPrompt(projectId, message, role);
      const newPrompt = res.data;
      setPrompts((prev) => [...prev, newPrompt]);
      return newPrompt;
    } catch (err) {
      console.error("Failed to add prompt:", err);
      toast.error("Failed to add message");
      throw err;
    }
  }, []);

  // Update a prompt
  const updatePrompt = useCallback(async (projectId, promptId, message) => {
    try {
      const res = await promptsApi.updatePrompt(projectId, promptId, message);
      const updated = res.data;
      setPrompts((prev) =>
        prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
      );
      return updated;
    } catch (err) {
      console.error("Failed to update prompt:", err);
      toast.error("Failed to update message");
      throw err;
    }
  }, []);

  // Delete a single prompt
  const deletePrompt = useCallback(async (projectId, promptId) => {
    try {
      const res = await promptsApi.deletePrompt(projectId, promptId);
      setPrompts((prev) => prev.filter((p) => p.id !== promptId));
      return res.data;
    } catch (err) {
      console.error("Failed to delete prompt:", err);
      toast.error("Failed to delete message");
      throw err;
    }
  }, []);

  // Clear all prompts for a project
  const clearPrompts = useCallback(async (projectId) => {
    try {
      const res = await promptsApi.clearPrompts(projectId);
      const ok = res?.status === 200 || res?.data?.status === "cleared";

      if (ok) toast.success("Chat history cleared");
      else toast.success("Chat history cleared (no response body)");

      setPrompts([]);
      return res.data;
    } catch (err) {
      console.error("Failed to clear prompts:", err);
      toast.error("Failed to clear chat history");
      throw err;
    }
  }, []);

  return (
    <PromptsContext.Provider
      value={{
        prompts,
        loading,
        loadPrompts,
        addPrompt,
        updatePrompt,
        deletePrompt,
        clearPrompts,
        setPrompts,
      }}
    >
      {children}
    </PromptsContext.Provider>
  );
};

export const usePrompts = () => {
  const context = useContext(PromptsContext);
  if (!context) {
    throw new Error("usePrompts must be used within a PromptsProvider");
  }
  return context;
};
