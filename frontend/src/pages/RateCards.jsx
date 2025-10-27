import { useState, useEffect } from "react";
import { Loader2, Plus, Save, Building2, X, Trash2 } from "lucide-react";
import { useRateCards } from "../contexts/RateCardContext";
import { toast } from "react-toastify";

export default function RateCardPreview() {
  const {
    companies,
    selectedCompany,
    setSelectedCompany,
    rateCards,
    setRateCards,
    loading,
    createCompany,
    addRateCard,
    updateRateCard,
    deleteRateCard,
    loadRateCards,
    deleteCompany,
  } = useRateCards();

  const [showAddCompany, setShowAddCompany] = useState(false);
  const [newCompany, setNewCompany] = useState({ name: "", currency: "USD" });
  const [saving, setSaving] = useState(false);
  const [addingCompany, setAddingCompany] = useState(false);

  useEffect(() => {
    if (selectedCompany) loadRateCards(selectedCompany);
  }, [selectedCompany, loadRateCards]);

  //  Add editable blank row
  const addRow = () => {
    if (!selectedCompany) return toast.error("Select a company first!");
    setRateCards([
      ...rateCards,
      { id: null, role_name: "", monthly_rate: "", isNew: true },
    ]);
  };

  //  Save changes
  const saveChanges = async () => {
    if (!selectedCompany) return toast.error("Select a company first!");
    setSaving(true);
    try {
      for (const rc of rateCards) {
        if (rc.isNew && rc.role_name.trim() && rc.monthly_rate) {
          await addRateCard(rc.role_name, rc.monthly_rate);
        } else if (rc._updated && rc.id) {
          await updateRateCard(rc.id, rc.monthly_rate);
        }
      }
      toast.success("Saved successfully!");
      await loadRateCards(selectedCompany);
    } catch (err) {
      console.error(err);
      toast.error(" Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  //  Add new company
  const handleAddCompany = async () => {
    if (!newCompany.name.trim()) return toast.error("Company name required!");
    setAddingCompany(true);
    try {
      const created = await createCompany(newCompany);
      if (created?.id) setSelectedCompany(created.id);
      setShowAddCompany(false);
      setNewCompany({ name: "", currency: "USD" });
    } finally {
      setAddingCompany(false);
    }
  };

  //  Delete company
  const handleDeleteCompany = async () => {
    const company = companies.find((c) => c.id === selectedCompany);
    if (!company) return;
    if (!window.confirm(`Delete ${company.name} and all its rate cards?`)) return;
    try {
      await deleteCompany(company.id);
      toast.success(`Deleted ${company.name}`);
      setSelectedCompany("");
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete company");
    }
  };

  //  Skeleton Loader
  const SkeletonRow = () => (
    <tr className="animate-pulse">
      {[...Array(4)].map((_, i) => (
        <td key={i} className="px-4 py-3 border">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto"></div>
        </td>
      ))}
    </tr>
  );

  return (
    <div className="space-y-6 relative">
      <h1 className="text-2xl font-bold text-primary"> Rate Card Preview</h1>

      {/* Company Selector */}
      <div className="flex flex-wrap gap-3 items-center">
        <label className="text-sm text-gray-600 dark:text-gray-300">
          Select Company:
        </label>
        <select
          value={selectedCompany || ""}
          onChange={(e) => setSelectedCompany(e.target.value)}
          className="border rounded-md px-3 py-2 text-sm dark:bg-gray-900 dark:border-gray-700"
        >
          <option value="">-- Choose Company --</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.currency})
            </option>
          ))}
        </select>

        <button
          onClick={() => setShowAddCompany(true)}
          className="px-2.5 py-1 bg-emerald-600 text-white rounded flex items-center gap-2 hover:bg-emerald-700"
        >
          <Building2 className="w-4 h-4" /> Add Company
        </button>

        {selectedCompany && (
          <button
            onClick={handleDeleteCompany}
            className="px-2.5 py-1 bg-red-600 text-white rounded flex items-center gap-2 hover:bg-red-700"
          >
            <Trash2 className="w-4 h-4" /> Delete Company
          </button>
        )}

      </div>

      {/* Table Section */}
      {selectedCompany ? (
        <div className="border rounded-lg shadow-sm bg-white dark:bg-gray-900 max-h-[600px] overflow-y-auto">
          <table className="w-full border-collapse text-sm relative"> 
            <thead className="bg-emerald-50 dark:bg-gray-800 sticky top-0 z-10">
              <tr>
                <th className="px-3 py-[4px] text-left border">No.</th>
                <th className="px-3 py-[4px] text-left border">Role Name</th>
                <th className="px-3 py-[4px] text-left border">Monthly Rate</th>
                <th className="px-3 py-[4px] text-center border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <>
                  {[...Array(4)].map((_, i) => (
                    <SkeletonRow key={i} />
                  ))}
                </>
              ) : rateCards.length > 0 ? (
                rateCards.map((rc, i) => (
                  <tr key={rc.id || i} className="hover:bg-emerald-50 dark:hover:bg-gray-800 border-b">
                    <td className="px-3 py-[2px] border">{i + 1}</td>
                    <td className="px-3 py-[2px] border">
                      <input
                        type="text"
                        value={rc.role_name}
                        onChange={(e) => {
                          const newArr = [...rateCards];
                          newArr[i].role_name = e.target.value;
                          newArr[i]._updated = true;
                          setRateCards(newArr);
                        }}
                        className="w-full border-none bg-transparent focus:ring-0"
                        placeholder="Enter role name"
                      />
                    </td>
                    <td className="px-3 py-[2px] text-left border">
                      <input
                        type="number"
                        value={rc.monthly_rate}
                        onChange={(e) => {
                          const newArr = [...rateCards];
                          newArr[i].monthly_rate = e.target.value;
                          newArr[i]._updated = true;
                          setRateCards(newArr);
                        }}
                        className="w-full border-none bg-transparent focus:ring-0 text-left"
                        placeholder="Enter rate"
                      />
                    </td>
                    <td className="px-4 py-1 text-center border">
                      <button
                        onClick={() => deleteRateCard(rc.id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4 inline" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-4 py-4 text-center text-gray-500 italic">
                    No rate cards found for this company
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">Select a company to view rate cards.</p>
      )}

      {/* Action Buttons */}
      {selectedCompany && (
        <div className="flex gap-3">
          <button
            onClick={addRow}
            className="px-2.5 py-1 bg-emerald-600 text-white rounded flex items-center gap-2 hover:bg-emerald-700"
          >
            <Plus className="w-4 h-4" /> Add Role
          </button>
          <button
            onClick={saveChanges}
            disabled={saving}
            className="px-2.5 py-1 bg-blue-600 text-white rounded flex items-center gap-2 hover:bg-blue-700 disabled:opacity-60"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" /> Save Changes
              </>
            )}
          </button>
        </div>
      )}

      {/* Add Company Modal */}
      {showAddCompany && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg w-[400px] p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                Add Company
              </h2>
              <button onClick={() => setShowAddCompany(false)}>
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Company Name</label>
                <input
                  type="text"
                  value={newCompany.name}
                  onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
                  className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700"
                  placeholder="e.g. Sigmoid Analytics"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Currency</label>
                <select
                  value={newCompany.currency}
                  onChange={(e) =>
                    setNewCompany({ ...newCompany, currency: e.target.value })
                  }
                  className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700"
                >
                  <option value="USD">USD</option>
                  <option value="CAD">CAD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                  <option value="INR">INR</option>
                  <option value="SGD">SGD</option>

                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => setShowAddCompany(false)}
                className="px-4 py-2 text-sm rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCompany}
                disabled={addingCompany}
                className="px-2.5 py-1 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-2"
              >
                {addingCompany ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Adding...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" /> Add
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
