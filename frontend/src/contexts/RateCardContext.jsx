import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import rateCardApi from "../api/rateCardApi";
import { toast } from "react-toastify";
import { useAuth } from "../contexts/AuthContext";

const RateCardContext = createContext();

export function RateCardProvider({ children }) {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [rateCards, setRateCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();

  // --- Load Rate Cards ---
  const loadRateCards = useCallback(async (companyId) => {
    if (!companyId) {
      setRateCards([]);
      return;
    }
    setLoading(true);
    try {
      const res = await rateCardApi.listRateCards(companyId);
      setRateCards(res.data || []);
    } catch (err) {
      console.error(" loadRateCards error:", err);
      toast.error("Failed to load rate cards");
    } finally {
      setLoading(false);
    }
  }, []);

  // --- Load Companies ---
  const loadCompanies = useCallback(async () => {
    try {
      const res = await rateCardApi.listCompanies();
      const list = res.data || [];

      const sorted = list.sort((a, b) => {
        if (a.name === "Sigmoid") return -1;
        if (b.name === "Sigmoid") return 1;
        return a.name.localeCompare(b.name);
      });

      setCompanies(sorted);

      if (!selectedCompany && sorted.length > 0) {
        const sigmoid = sorted.find((c) => c.name === "Sigmoid");
        if (sigmoid) {
          setSelectedCompany(sigmoid.id);
          await loadRateCards(sigmoid.id);
        }
      }
    } catch (err) {
      if (err?.response?.status === 401) {
        console.log("Skipping loadCompanies — user not logged in");
        return;
      }
      console.error(" loadCompanies error:", err);
      toast.error("Failed to load companies");
    }
  }, [selectedCompany, loadRateCards]);


  const createCompany = async (data) => {
    try {
      const res = await rateCardApi.createCompany(data);
      toast.success("Company created successfully");
      await loadCompanies();
      return res.data;
    } catch (err) {
      console.error(" createCompany error:", err);
      const msg =
        err?.response?.data?.detail || "Failed to create company. Try again.";
      toast.error(msg);
    }
  };

  const deleteCompany = async (companyId) => {
    const company = companies.find((c) => c.id === companyId);

    if (company?.name === "Sigmoid") {
      toast.error("Cannot delete the global Sigmoid company");
      return;
    }

    try {
      await rateCardApi.deleteCompany(companyId);
      toast.success(" Company deleted");
      await loadCompanies();
      setRateCards([]);

      if (selectedCompany === companyId) setSelectedCompany("");
    } catch (err) {
      console.error("❌ deleteCompany error:", err);
      const msg =
        err?.response?.data?.detail || "Failed to delete company. Try again.";
      toast.error(msg);
    }
  };

  // ADD RATE CARD
  const addRateCard = async (role_name, monthly_rate) => {
    if (!selectedCompany) return toast.error("Select a company first!");
    try {
      const res = await rateCardApi.createRateCard(selectedCompany, {
        role_name,
        monthly_rate,
      });
      toast.success(" Role added");
      await loadRateCards(selectedCompany);
      return res.data;
    } catch (err) {
      console.error(" addRateCard error:", err);
      const msg =
        err?.response?.data?.detail || "Failed to add rate card. Try again.";
      toast.error(msg);
    }
  };

  //  UPDATE RATE CARD
  const updateRateCard = async (rate_card_id, monthly_rate) => {
    try {
      await rateCardApi.updateRateCard(rate_card_id, { monthly_rate });
      toast.success(" Rate updated");
      await loadRateCards(selectedCompany);
    } catch (err) {
      console.error(" updateRateCard error:", err);
      const msg =
        err?.response?.data?.detail || "Failed to update rate card.";
      toast.error(msg);
    }
  };

  //  DELETE RATE CARD
  const deleteRateCard = async (rate_card_id) => {
    try {
      await rateCardApi.deleteRateCard(rate_card_id);
      toast.success(" Role deleted");
      await loadRateCards(selectedCompany);
    } catch (err) {
      console.error(" deleteRateCard error:", err);
      const msg =
        err?.response?.data?.detail || "Failed to delete rate card.";
      toast.error(msg);
    }
  };

  // AUTO LOAD COMPANIES ON LOGIN
  useEffect(() => {
    if (user) {
      console.log("User logged in, loading companies...");
      loadCompanies();
    } else {
      console.log("Skipping loadCompanies — no user yet");
    }
  }, [user, loadCompanies]);


  // PROVIDER VALUE
  return (
    <RateCardContext.Provider
      value={{
        companies,
        selectedCompany,
        setSelectedCompany,
        rateCards,
        setRateCards,
        loading,
        loadCompanies,
        loadRateCards,
        createCompany,
        deleteCompany,
        addRateCard,
        updateRateCard,
        deleteRateCard,
      }}
    >
      {children}
    </RateCardContext.Provider>
  );
}

export const useRateCards = () => {
  const context = useContext(RateCardContext);
  if (!context)
    throw new Error("useRateCards must be used within a RateCardProvider");
  return context;
};
