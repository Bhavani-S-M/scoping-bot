import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useProjects } from "../contexts/ProjectContext";
import { File, Trash2, Upload } from "lucide-react";
import { toast } from "react-toastify";

export default function ProjectForm({ onSubmit }) {
  const navigate = useNavigate();
  const { createProject } = useProjects();

  // Domain Options
  const DOMAIN_OPTIONS = [
    "Consumer Packaged Goods (CPG)","Banking and Financial Services (BFSI)","Life Sciences and MedTech","Media and AdTech","Industrial and Manufacturing","GovTech","E-Commerce","InsurTech","EdTech",
    "Smart Mobility","B2B SaaS","AgriTech","Logistics","Energy/Utilities",
    "CivicTech","RegTech","Other",
  ];

  // Compliance options
  const COMPLIANCE_OPTIONS_IN = [
    { value: "DPDP-2023", label: "DPDP Act 2023 (India)" },
    { value: "CERT-In-2022", label: "CERT-In Directions 2022" },
    { value: "IT-Rules-2021", label: "MeitY IT Rules 2021" },
    { value: "RBI-KYC-AML", label: "RBI KYC/AML & Master Directions" },
    { value: "NPCI-UPI", label: "NPCI (UPI/IMPS/AEPS) Conformance" },
    { value: "UIDAI-Aadhaar", label: "UIDAI (Aadhaar eKYC/eSign)" },
    { value: "ABDM-NDHM", label: "ABDM / NDHM (Health)" },
    { value: "IRDAI-IT", label: "IRDAI IT & Outsourcing (Insurance)" },
    { value: "ONDC", label: "ONDC Protocol Conformance" },
    { value: "NCMC", label: "MoHUA NCMC (Mobility)" },
    { value: "FSSAI", label: "FSSAI (Food/Agri)" },
    { value: "CEA-CERC", label: "CEA / CERC (Power sector)" },
    { value: "NABH", label: "NABH (Hospitals/Labs)" },
  ];

  const COMPLIANCE_OPTIONS_GLOBAL = [
    { value: "ISO-27001", label: "ISO 27001" },
    { value: "SOC-2", label: "SOC 2" },
    { value: "PCI-DSS", label: "PCI-DSS" },
    { value: "HIPAA", label: "HIPAA" },
    { value: "GDPR", label: "GDPR" },
    { value: "WCAG", label: "WCAG 2.2 / ADA" },
  ];

  // handy lists for group actions
  const INDIA_VALUES  = COMPLIANCE_OPTIONS_IN.map(o => o.value);
  const GLOBAL_VALUES = COMPLIANCE_OPTIONS_GLOBAL.map(o => o.value);
  const ALL_VALUES    = [...INDIA_VALUES, ...GLOBAL_VALUES];

  // Domain → Recommended compliance
  const DOMAIN_COMPLIANCE_MAP = {
    fintech: ["RBI-KYC-AML","NPCI-UPI","UIDAI-Aadhaar","DPDP-2023","CERT-In-2022","IT-Rules-2021","PCI-DSS","ISO-27001","SOC-2"],
    healthtech: ["ABDM-NDHM","NABH","DPDP-2023","CERT-In-2022","IT-Rules-2021","ISO-27001"],
    govtech: ["UIDAI-Aadhaar","IT-Rules-2021","CERT-In-2022","DPDP-2023","WCAG"],
    ecommerce: ["ONDC","DPDP-2023","IT-Rules-2021","CERT-In-2022","PCI-DSS","ISO-27001"],
    insurtech: ["IRDAI-IT","DPDP-2023","CERT-In-2022","ISO-27001","SOC-2"],
    edtech: ["DPDP-2023","IT-Rules-2021","CERT-In-2022","WCAG"],
    "smart mobility": ["NCMC","RBI-KYC-AML","NPCI-UPI","DPDP-2023"],
    "b2b saas": ["ISO-27001","SOC-2","DPDP-2023"],
    agritech: ["FSSAI","DPDP-2023"],
    logistics: ["ISO-27001","SOC-2","DPDP-2023"],
    "energy/utilities": ["CEA-CERC","DPDP-2023","CERT-In-2022"],
    civictech: ["IT-Rules-2021","CERT-In-2022","DPDP-2023","WCAG"],
    regtech: ["RBI-KYC-AML","UIDAI-Aadhaar","DPDP-2023","ISO-27001"],
    other: ["DPDP-2023","CERT-In-2022","IT-Rules-2021"],
  };

  const normalize = (s) => (s || "").toLowerCase().trim();
  const recommendForDomain = (domain) => {
    const d = normalize(domain);
    if (DOMAIN_COMPLIANCE_MAP[d]) return DOMAIN_COMPLIANCE_MAP[d];
    if (/(bank|nbfc|upi|lending|fin)/.test(d)) return DOMAIN_COMPLIANCE_MAP["fintech"];
    if (/(health|hospital|lims|telemed)/.test(d)) return DOMAIN_COMPLIANCE_MAP["healthtech"];
    if (/(gov|e-gov|municipal|smart city)/.test(d)) return DOMAIN_COMPLIANCE_MAP["civictech"];
    if (/(commerce|retail|ondc)/.test(d)) return DOMAIN_COMPLIANCE_MAP["ecommerce"];
    if (/(insurance)/.test(d)) return DOMAIN_COMPLIANCE_MAP["insurtech"];
    if (/(education|edtech|learning)/.test(d)) return DOMAIN_COMPLIANCE_MAP["edtech"];
    if (/(mobility|transport|ncmc|metro)/.test(d)) return DOMAIN_COMPLIANCE_MAP["smart mobility"];
    if (/(hr|payroll|b2b|saas)/.test(d)) return DOMAIN_COMPLIANCE_MAP["b2b saas"];
    if (/(agri|fpo|farm)/.test(d)) return DOMAIN_COMPLIANCE_MAP["agritech"];
    if (/(logistics|supply)/.test(d)) return DOMAIN_COMPLIANCE_MAP["logistics"];
    if (/(energy|discom|utility|power)/.test(d)) return DOMAIN_COMPLIANCE_MAP["energy/utilities"];
    if (/(regtech|kyc|aml)/.test(d)) return DOMAIN_COMPLIANCE_MAP["regtech"];
    return DOMAIN_COMPLIANCE_MAP["other"];
  };

  const ALL_COMPLIANCE = [...COMPLIANCE_OPTIONS_IN, ...COMPLIANCE_OPTIONS_GLOBAL];
  const labelFor = (v) => ALL_COMPLIANCE.find((o) => o.value === v)?.label || v;

  // State
  const [form, setForm] = useState({
    name: "",
    domain: "",
    complexity: "",
    tech_stack: "",
    use_cases: "",
    compliance: [],
    duration: "",
    files: [],
  });

  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});
  const [recommended, setRecommended] = useState([]);

  useEffect(() => {
    setRecommended(recommendForDomain(form.domain));
  }, [form.domain]);

  // Validation
  const validateField = (name, value) => {
    const isArray = Array.isArray(value);
    const isEmpty = isArray ? value.length === 0 : !value || !String(value).trim();
    if (isEmpty) {
      switch (name) {
        default: return "";
      }
    }
    return "";
  };

  // Handlers
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setValidationErrors((prev) => ({ ...prev, [name]: validateField(name, value) }));
  };

  const handleComplianceMultiChange = (e) => {
    const selected = Array.from(e.target.selectedOptions, (opt) => opt.value);
    setForm((prev) => ({ ...prev, compliance: selected }));
    setValidationErrors((prev) => ({
      ...prev,
      compliance: validateField("compliance", selected),
    }));
  };

  // Group actions (India / Global / All)
  const uniqMerge = (arrA, arrB) => Array.from(new Set([...arrA, ...arrB]));
  const selectIndia   = () => {
    const next = uniqMerge(form.compliance, INDIA_VALUES);
    setForm((p) => ({ ...p, compliance: next }));
    setValidationErrors((v) => ({ ...v, compliance: "" }));
  };
  const selectGlobal  = () => {
    const next = uniqMerge(form.compliance, GLOBAL_VALUES);
    setForm((p) => ({ ...p, compliance: next }));
    setValidationErrors((v) => ({ ...v, compliance: "" }));
  };
  const selectAll     = () => {
    setForm((p) => ({ ...p, compliance: ALL_VALUES }));
    setValidationErrors((v) => ({ ...v, compliance: "" }));
  };
  const clearIndia    = () => {
    const next = form.compliance.filter((v) => !INDIA_VALUES.includes(v));
    setForm((p) => ({ ...p, compliance: next }));
    setValidationErrors((v) => ({ ...v, compliance: validateField("compliance", next) }));
  };
  const clearGlobal   = () => {
    const next = form.compliance.filter((v) => !GLOBAL_VALUES.includes(v));
    setForm((p) => ({ ...p, compliance: next }));
    setValidationErrors((v) => ({ ...v, compliance: validateField("compliance", next) }));
  };
  const clearAll      = () => {
    setForm((p) => ({ ...p, compliance: [] }));
    setValidationErrors((v) => ({ ...v, compliance: "Select at least one compliance need." }));
  };

  // Domain recommendations
  const applyRecommended = () => {
    const next = uniqMerge(form.compliance, recommended);
    setForm((p) => ({ ...p, compliance: next }));
    setValidationErrors((v) => ({ ...v, compliance: "" }));
  };
  const replaceWithRecommended = () => {
    setForm((p) => ({ ...p, compliance: [...recommended] }));
    setValidationErrors((v) => ({ ...v, compliance: "" }));
  };

  // Files
  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files || []).map((file) => ({ file, type: "" }));
    setForm((prev) => ({ ...prev, files: [...prev.files, ...newFiles] }));
  };
  const handleFileTypeChange = (index, type) => {
    setForm((prev) => {
      const updated = [...prev.files];
      updated[index].type = type;
      return { ...prev, files: updated };
    });
  };
  const handleDrop = (e) => {
    e.preventDefault();
    const newFiles = Array.from(e.dataTransfer.files || []).map((file) => ({ file, type: "" }));
    setForm((prev) => ({ ...prev, files: [...prev.files, ...newFiles] }));
  };
  const handleDragOver = (e) => e.preventDefault();
  const handleRemoveFile = (index) =>
    setForm((prev) => ({ ...prev, files: prev.files.filter((_, i) => i !== index) }));

  // Submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    const newErrors = {};
    Object.keys(form).forEach((field) => {
      if (field !== "files") {
        const msg = validateField(field, form[field]);
        if (msg) newErrors[field] = msg;
      }
    });

    const hasAtLeastOne =
      Object.entries(form).some(([key, value]) => {
        if (key === "files") return value.length > 0;
        if (Array.isArray(value)) return value.length > 0;
        return value && String(value).trim() !== "";
      });

    if (!hasAtLeastOne) {
      toast.error("Please fill at least one field or upload a file.");
      return;
    }

    setValidationErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      toast.error("Please fix the highlighted errors.");
      return;
    }

    setLoading(true);
    try {
      const payload = { ...form };
      const { projectId, scope, redirectUrl } = await createProject(payload);

      toast.success(` Project "${form.name || "Untitled"}" created successfully!`);
      if (onSubmit) onSubmit({ project_id: projectId, scope, redirect_url: redirectUrl });

      if (scope) {
        navigate(`/exports/${projectId}`, { state: { draftScope: scope } });
      } else {
        navigate(`/exports/${projectId}`);
      }

      setForm({
        name: "",
        domain: "",
        complexity: "",
        tech_stack: "",
        use_cases: "",
        compliance: [],
        duration: "",
        files: [],
      });
      setValidationErrors({});
    } catch (err) {
      console.error("Failed to create project:", err);
      toast.error("Failed to create and scope project.");
    } finally {
      setLoading(false);
    }
  };


  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-7xl mx-auto space-y-6 bg-white dark:bg-dark-card p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted"
    >

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Project Name */}
        <div>
          <input
            name="name"
            placeholder="Project Name "
            value={form.name}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({ ...prev, name: validateField("name", e.target.value) }))
            }
            className={`border rounded-lg px-3 py-2 w-full ${
              validationErrors.name ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          />
          {validationErrors.name && <p className="text-red-500 text-sm mt-1">{validationErrors.name}</p>}
        </div>

        {/* Domain */}
        <div>
          <select
            name="domain"
            value={form.domain}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({ ...prev, domain: validateField("domain", e.target.value) }))
            }
            className={`border rounded-lg px-3 py-2 w-full bg-white dark:bg-dark-card ${
              validationErrors.domain ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          >
            <option value="" >Select Domain </option>
            {DOMAIN_OPTIONS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          {validationErrors.domain && <p className="text-red-500 text-sm mt-1">{validationErrors.domain}</p>}
        </div>

        {/* Tech Stack */}
        <div>
          <input
            name="tech_stack"
            placeholder="Tech Stack"
            value={form.tech_stack}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({ ...prev, tech_stack: validateField("tech_stack", e.target.value) }))
            }
            className={`border rounded-lg px-3 py-2 w-full ${
              validationErrors.tech_stack ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          />
          {validationErrors.tech_stack && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.tech_stack}</p>
          )}
        </div>
        {/* Duration */}
        <div>
          <input
            name="duration"
            placeholder="Duration (e.g. 6 months) "
            value={form.duration}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({ ...prev, duration: validateField("duration", e.target.value) }))
            }
            className={`border rounded-lg px-3 py-2 w-full ${
              validationErrors.duration ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          />
          {validationErrors.duration && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.duration}</p>
          )}
        </div>

        {/* Use Cases */}
        <div className="md:col-span-2">
          <textarea
            name="use_cases"
            placeholder="Use Cases"
            value={form.use_cases}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({ ...prev, use_cases: validateField("use_cases", e.target.value) }))
            }
            className={`border rounded-lg px-3 py-2 w-full ${
              validationErrors.use_cases ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
            rows="3"
          />
          {validationErrors.use_cases && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.use_cases}</p>
          )}
        </div>

        {/* Compliance — native multi-select with group actions */}
        <div className="md:col-span-2">
          <div className="flex items-center justify-between mb-1">
            <label className="font-medium text-gray-700 dark:text-gray-200">
              Compliance Needs
            </label>
            {validationErrors.compliance && (
              <p className="text-red-500 text-sm">{validationErrors.compliance}</p>
            )}
          </div>

          {/* Group selectors */}
          <div className="flex flex-wrap gap-2 mb-2 text-xs">
            <button type="button" onClick={selectIndia}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              India ({INDIA_VALUES.length})
            </button>
            <button type="button" onClick={selectGlobal}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              Global ({GLOBAL_VALUES.length})
            </button>
            <button type="button" onClick={selectAll}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              All ({ALL_VALUES.length})
            </button>
            <span className="mx-2 h-4 w-px bg-gray-300 inline-block" />
            <button
              type="button"
              onClick={applyRecommended}
              disabled={!recommended.length}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 disabled:opacity-50 dark:border-dark-muted"
            >
              Apply Recomendations
            </button>
            <button
              type="button"
              onClick={replaceWithRecommended}
              disabled={!recommended.length}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 disabled:opacity-50 dark:border-dark-muted"
            >
              Replace with Recomendations
            </button>
            <span className="mx-2 h-4 w-px bg-gray-300 inline-block" />
            <button type="button" onClick={clearIndia}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              Clear India
            </button>
            <button type="button" onClick={clearGlobal}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              Clear Global
            </button>
            <button type="button" onClick={clearAll}
              className="px-2 py-0.5 rounded border hover:bg-gray-100 dark:border-dark-muted">
              Clear All
            </button>
          </div>

          <select
            name="compliance"
            multiple
            value={form.compliance}
            onChange={handleComplianceMultiChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({
                ...prev,
                compliance: validateField(
                  "compliance",
                  Array.from(e.target.selectedOptions, (o) => o.value)
                ),
              }))
            }
            className={`border rounded-lg px-3 py-1 w-full h-30 bg-white dark:bg-dark-card ${
              validationErrors.compliance ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          >   
            <option disabled className="bg-primary text-white font-semibold">  Indian Regulations </option>
              {COMPLIANCE_OPTIONS_IN.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
  
            <option disabled className="bg-primary text-white font-semibold">  Global Standards </option>
              {COMPLIANCE_OPTIONS_GLOBAL.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Hold <b>Ctrl</b> to select multiple options.
          </p>

          {/* Selected preview */}
          {form.compliance.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {form.compliance.map((v) => (
                <span
                  key={v}
                  className="inline-flex items-center gap-2 text-xs bg-gray-100 dark:bg-dark-surface px-2 py-1 rounded-full"
                  title={labelFor(v)}
                >
                  {labelFor(v)}
                  <button
                    type="button"
                    onClick={() =>
                      setForm((prev) => ({
                        ...prev,
                        compliance: prev.compliance.filter((x) => x !== v),
                      }))
                    }
                    className="text-gray-500 hover:text-gray-700"
                    aria-label={`Remove ${labelFor(v)}`}
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Complexity */}
        <div>
          <select
            name="complexity"
            value={form.complexity}
            onChange={handleChange}
            onBlur={(e) =>
              setValidationErrors((prev) => ({
                ...prev,
                complexity: validateField("complexity", e.target.value),
              }))
            }
            className={`border rounded-lg px-3 py-2 w-full bg-white dark:bg-dark-card ${
              validationErrors.complexity ? "border-red-500 focus:ring-red-500" : "focus:ring-primary"
            }`}
          >
            <option value="">Select Complexity</option>
            <option value="Simple">Simple</option>
            <option value="Medium">Medium</option>
            <option value="Large">Large</option>
          </select>
          {validationErrors.complexity && (
            <p className="text-red-500 text-sm mt-1">{validationErrors.complexity}</p>
          )}
        </div>
      </div>
      

      {/* File Upload */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="md:col-span-2 flex flex-col items-center justify-center w-full p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary hover:bg-gray-50 dark:hover:bg-dark-surface/40 transition"
      >
        <input type="file" multiple onChange={handleFileChange} className="hidden" id="fileUpload" />
        <label htmlFor="fileUpload" className="flex flex-col items-center gap-2 cursor-pointer">
          <Upload className="w-6 h-6 text-gray-500" />
          <span className="text-gray-500">Drag & Drop files here</span>
        </label>
      </div>

      {/* File List */}
      {form.files.length > 0 && (
        <ul className="mt-3 space-y-2">
          {form.files.map((f, index) => (
            <li
              key={f.file.name + index}
              className="flex items-center justify-between border p-2 rounded bg-gray-50 dark:bg-dark-surface"
            >
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-gray-500" />
                <span className="truncate max-w-[950px]">{f.file.name}</span>
              </div>
              <button
                type="button"
                onClick={() => handleRemoveFile(index)}
                className="flex items-center gap-1 text-red-500 hover:text-red-700 text-sm"
              >
                <Trash2 className="w-4 h-4" /> 
              </button>
            </li>
          ))}
        </ul>
      )}

      
      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center bg-primary hover:bg-secondary text-white px-4 py-2 rounded-lg shadow font-semibold transition disabled:opacity-50"
      >
        {loading ? (
          <>
            <svg
              className="animate-spin h-5 w-5 mr-2 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            Generating...
          </>
        ) : (
          "Generate Project Scope"
        )}
      </button>

    </form>
  );
}
