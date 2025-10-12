import api from "./axiosClient";

const rateCardApi = {
  listCompanies: () => api.get("/companies"),

  createCompany: (data) =>
    api.post("/companies", {
      name: data.name.trim(),
      currency: data.currency || "USD", 
    }),

  deleteCompany: (companyId) => api.delete(`/companies/${companyId}`),

  listRateCards: (companyId) => {
    if (!companyId) return api.get("/companies/standard/ratecards");
    return api.get(`/companies/${companyId}/ratecards`);
  },

  createRateCard: (companyId, data) =>
    api.post(`/companies/${companyId}/ratecards`, {
      role_name: data.role_name.trim(),
      monthly_rate: parseFloat(data.monthly_rate),
    }),


  updateRateCard: (rateCardId, data) =>
    api.put(`/companies/ratecards/${rateCardId}`, {
      monthly_rate: parseFloat(data.monthly_rate),
    }),

  deleteRateCard: (rateCardId) =>
    api.delete(`/companies/ratecards/${rateCardId}`),
};

export default rateCardApi;
