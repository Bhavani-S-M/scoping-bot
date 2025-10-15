// src/api/promptsApi.js
import api from "./axiosClient";

const promptsApi = {
  // Fetch all prompts for a project
  getPrompts: async (projectId) => {
    const res = await api.get(`/projects/${projectId}/prompts`);
    return res.data.prompts || [];
  },

  // Add a new prompt
  addPrompt: (projectId, message, role = "user") =>
    api.post(`/projects/${projectId}/prompts`, { message, role }),

  // Update existing prompt
  updatePrompt: (projectId, promptId, newMessage) =>
    api.put(`/projects/${projectId}/prompts/${promptId}`, { message: newMessage }),

  // Delete single prompt
  deletePrompt: (projectId, promptId) =>
    api.delete(`/projects/${projectId}/prompts/${promptId}`),

  // Clear all prompts for a project
  clearPrompts: (projectId) =>
    api.delete(`/projects/${projectId}/prompts/clear`),
};

export default promptsApi;
