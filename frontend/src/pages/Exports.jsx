import { useParams, Link, useLocation } from "react-router-dom";
import { useState, useEffect, useMemo, useRef } from "react";
import { useProjects } from "../contexts/ProjectContext";
import { useExport } from "../contexts/ExportContext";
import { usePrompts } from "../contexts/PromptsContext";
import projectApi from "../api/projectApi";
import exportApi, { safeFileName } from "../api/exportApi";
import {
  FileSpreadsheet,
  FileText,
  FileJson,
  Save,
  Loader2,
  CheckCircle2,
  Download,
  Package,
  XCircle,
  Trash2,
} from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import JSZip from "jszip";
import { saveAs } from "file-saver";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

const TABS = [
  { key: "json", label: "JSON", icon: FileJson },
  { key: "excel", label: "Excel", icon: FileSpreadsheet },
  { key: "pdf", label: "PDF", icon: FileText },
];

const formatCurrency = (v, currency = "USD") => {
  if (v == null || v === "") return "";
  const n = Number(v);
  if (isNaN(n)) return v;
  return n.toLocaleString("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  });
};

export default function Exports() {
  const { id } = useParams();
  const location = useLocation();
  const { finalizeScope, getFinalizedScope, regenerateScope } = useProjects();
  const chatEndRef = useRef(null);
  const { previewPdf, getPdfBlob } = useExport();
  const [finalizing, setFinalizing] = useState(false);
  const incomingDraft = location.state?.draftScope || null;
  const [jsonText, setJsonText] = useState("");
  const [parseError, setParseError] = useState(null);
  const parsedDraft = useMemo(() => {
    if (!jsonText?.trim()) return null;
    try {
      const obj = JSON.parse(jsonText);
      setParseError(null);
      return obj;
    } catch (e) {
      setParseError(e.message);
      return null;
    }
  }, [jsonText]);

  const [project, setProject] = useState(null);
  const [activeTab, setActiveTab] = useState("json");
  const activeCurrency = useMemo(() => {
    return (
      project?.company?.currency ||
      parsedDraft?.overview?.Currency ||
      parsedDraft?.overview?.currency ||
      "USD"
    );
  }, [project, parsedDraft]);

  const [loading, setLoading] = useState(false);
  const [isFinalized, setIsFinalized] = useState(false);

  const [showSuccessBanner, setShowSuccessBanner] = useState(false);

  const [excelSection, setExcelSection] = useState("");
  const [excelPreview, setExcelPreview] = useState({ headers: [], rows: [] });
  const [previewPdfUrl, setPreviewPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);

  const cachedPdfBlobRef = useRef(null);
  const lastPdfKeyRef = useRef("");

  // --- Download states (progress + cancel) ---
  const [downloadState, setDownloadState] = useState({
    json: { loading: false, progress: 0, controller: null },
    excel: { loading: false, progress: 0, controller: null },
    pdf: { loading: false, progress: 0, controller: null },
    all: { loading: false, progress: 0, controller: null },
  });
  const [regenPrompt, setRegenPrompt] = useState("");
  const [regenLoading, setRegenLoading] = useState(false);
  const { prompts, loadPrompts, addPrompt, clearPrompts } = usePrompts();
  const textareaRef = useRef(null);
  useEffect(() => {
    if (chatEndRef.current && Array.isArray(prompts) && prompts.length > 0) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [prompts]);

  const handleInputChange = (e) => {
    setRegenPrompt(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto"; 
      el.style.height = `${el.scrollHeight}px`; 
    }
  };
  const updateParsedDraft = (section, newRows) => {
    if (!parsedDraft) return;

    if (section === "overview") {
      const newOverview = {};
      newRows.forEach(([k, v]) => {
        if (k) newOverview[k] = v;
      });
      const newDraft = { ...parsedDraft, overview: newOverview };
      setJsonText(JSON.stringify(newDraft, null, 2));
    } else {
      const headers = excelPreview.headers;
      const arr = newRows.map((row) =>
        headers.reduce((obj, h, idx) => {
          obj[h] = row[idx];
          return obj;
        }, {})
      );
      const newDraft = { ...parsedDraft, [section]: arr };
      setJsonText(JSON.stringify(newDraft, null, 2));
    }
  };
  const handleRegenerate = async () => {
    if (!parsedDraft || !regenPrompt.trim()) {
      toast.info("Please enter regeneration instructions first.");
      return;
    }

    const userMsg = regenPrompt.trim();

    // Add user message to chat history
    await addPrompt(id, userMsg, "user");

    // Reset input field + height
    setRegenPrompt("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      setRegenLoading(true);
      toast.info("Regenerating scope… this may take a few seconds");

      const result = await regenerateScope(id, parsedDraft, userMsg);

      if (result?.scope) {
        // Update JSON editor with regenerated scope
        setJsonText(JSON.stringify(result.scope, null, 2));
        setIsFinalized(false);
        toast.success("Scope regenerated successfully!");

        // Add assistant summary message to chat
        const summary =
          result.scope.overview?.["Project Summary"] ||
          "Scope updated successfully with your latest instructions.";
        await addPrompt(id, summary, "assistant");
      } else {
        toast.warn("No changes were made to the scope.");
      }
    } catch (err) {
      console.error("Regeneration failed:", err);
      toast.error("Failed to regenerate scope. Please try again.");
    } finally {
      setRegenLoading(false);
    }
  };






  const startDownload = (key, controller) =>
    setDownloadState((s) => ({
      ...s,
      [key]: { ...s[key], loading: true, progress: 0, controller },
    }));

  const updateProgress = (key, percent) =>
    setDownloadState((s) => ({
      ...s,
      [key]: { ...s[key], progress: percent },
    }));

  const finishDownload = (key) =>
    setDownloadState((s) => ({
      ...s,
      [key]: { ...s[key], loading: false, progress: 100, controller: null },
    }));

  const resetDownload = (key) =>
    setDownloadState((s) => ({
      ...s,
      [key]: { loading: false, progress: 0, controller: null },
    }));

  useEffect(() => {
    let isActive = true;

    (async () => {
      try {
        setLoading(true);

        // Fetch project metadata
        const res = await projectApi.getProject(id);
        if (!isActive) return;
        setProject(res.data);

        //  Try to load finalized_scope.json first
        const latest = await getFinalizedScope(id);
        if (!isActive) return;

        if (latest && Object.keys(latest).length > 0) {
          setJsonText(JSON.stringify(latest, null, 2));
          setIsFinalized(true);
          console.log(" Loaded finalized_scope.json from blob");
        } else if (incomingDraft) {
          // fallback to draft only if finalized file truly doesn’t exist
          setJsonText(JSON.stringify(incomingDraft, null, 2));
          setIsFinalized(false);
          console.log("ℹ Showing draft_scope.json since no finalized version found");
        } else {
          console.warn(" No scope found for project, showing empty editor");
          setJsonText("");
          setIsFinalized(false);
        }
      } catch (err) {
        console.error(" Failed to load project or scope:", err);
        toast.error("Failed to load finalized scope");
      } finally {
        if (isActive) setLoading(false);
      }
    })();

    //  Auto-refresh when tab regains focus
    const refreshOnFocus = async () => {
      try {
        const latest = await getFinalizedScope(id);
        if (latest && isActive && Object.keys(latest).length > 0) {
          setJsonText(JSON.stringify(latest, null, 2));
          setIsFinalized(true);
          console.log(" Refreshed finalized_scope.json on focus");
        }
      } catch (err) {
        console.error(" Failed to refresh finalized scope on focus:", err);
      }
    };

    window.addEventListener("focus", refreshOnFocus);
    return () => {
      isActive = false;
      window.removeEventListener("focus", refreshOnFocus);
    };
  }, [id, incomingDraft, getFinalizedScope]);

  useEffect(() => {
    if (id) loadPrompts(id);
  }, [id, loadPrompts]);

  //  Clear cached PDF & reset finalized state when JSON changes
  useEffect(() => {
    cachedPdfBlobRef.current = null;
    lastPdfKeyRef.current = "";
    setPreviewPdfUrl(null);

    //  Only reset if this was a user edit (not internal finalize refresh)
    if (!skipResetRef.current && isFinalized) {
      setIsFinalized(false);
      setShowSuccessBanner(false);
    }

    //  Always clear skip flag after handling one JSON update
    skipResetRef.current = false;
  }, [jsonText, isFinalized]);

  // Keep finalized state stable and remove unnecessary reset logic
  const prevJsonRef = useRef("");
  useEffect(() => {
    // Simply track JSON changes; don't auto-reset isFinalized
    prevJsonRef.current = jsonText;
  }, [jsonText]);

  useEffect(() => {
    return () => {
      if (previewPdfUrl) URL.revokeObjectURL(previewPdfUrl);
    };
  }, [previewPdfUrl]);

  //  Auto-refresh PDF preview
  useEffect(() => {
    if (activeTab !== "pdf" || !parsedDraft) return;

    const currentKey = JSON.stringify(parsedDraft);
    if (lastPdfKeyRef.current === currentKey && cachedPdfBlobRef.current) {
      const cachedBlob = cachedPdfBlobRef.current;
      if (cachedBlob && cachedBlob.size > 0 && cachedBlob.type === "application/pdf") {
        setPreviewPdfUrl(URL.createObjectURL(cachedBlob));
      }
      return;
    }

    (async () => {
      try {
        console.log("🔄 Starting PDF preview generation...");
        console.log("  - isFinalized:", isFinalized);
        console.log("  - parsedDraft keys:", Object.keys(parsedDraft));

        const blob = isFinalized
          ? await getPdfBlob(id)
          : await previewPdf(id, parsedDraft);

        console.log("📦 PDF blob received:");
        console.log("  - Blob size:", blob?.size);
        console.log("  - Blob type:", blob?.type);

        if (!blob || blob.size === 0 || blob.type !== "application/pdf") {
          console.error("❌ Invalid PDF blob:", { blob, size: blob?.size, type: blob?.type });
          toast.error("Invalid PDF generated. Please check the console for details.");
          return;
        }

        cachedPdfBlobRef.current = blob;
        lastPdfKeyRef.current = currentKey;

        if (previewPdfUrl) URL.revokeObjectURL(previewPdfUrl);
        const newUrl = URL.createObjectURL(blob);
        console.log("✅ PDF preview URL created:", newUrl);
        setPreviewPdfUrl(newUrl);
      } catch (err) {
        console.error("❌ Failed to load PDF preview:", err);
        console.error("  - Error message:", err.message);
        console.error("  - Error stack:", err.stack);
        toast.error(`Failed to load PDF preview: ${err.message || 'Unknown error'}`);
      }
    })();
  }, [activeTab, parsedDraft, isFinalized, id, getPdfBlob, previewPdf]);  // REMOVED previewPdfUrl from deps!

  // Auto-refresh Excel preview
  useEffect(() => {
    if (!parsedDraft || activeTab !== "excel") return;

    const keys = Object.keys(parsedDraft).filter(
      (k) => Array.isArray(parsedDraft[k]) || k === "overview"
    );
    if (!excelSection && keys.length > 0) setExcelSection(keys[0]);
    if (!excelSection) return;

    if (excelSection === "overview") {
      const ov = parsedDraft.overview || {};
      setExcelPreview({
        headers: ["Field", "Value"],
        rows: Object.entries(ov).map(([k, v]) => [k, v]),
      });
    } else if (Array.isArray(parsedDraft[excelSection])) {
      const arr = parsedDraft[excelSection];
      if (arr.length && typeof arr[0] === "object") {
        const headers = Object.keys(arr[0]);
        const rows = arr.map((r) =>
          headers.map((h) => {
            if (h.toLowerCase().includes("rate") || h.toLowerCase().includes("cost")) {
              return formatCurrency(r[h], activeCurrency);
            }
            return r[h];
          })
        );

        // Totals row for resourcing_plan
        if (excelSection === "resourcing_plan") {
          const monthCols = headers.filter((h) => h.split(" ").length === 2);
          let totalEfforts = 0;
          let totalCost = 0;

          arr.forEach((r) => {
            const sumMonths = monthCols.reduce(
              (acc, m) => acc + (parseFloat(r[m] || 0) || 0),
              0
            );
            totalEfforts += sumMonths;

            // Use the actual Cost field (which includes discount) instead of recalculating
            const actualCost = parseFloat(r["Cost"] || 0);
            totalCost += actualCost;
          });

          const totalRow = headers.map((h, idx) => {
            if (idx === headers.length - 2) return Number(totalEfforts.toFixed(2));
            if (idx === headers.length - 1) return formatCurrency(totalCost, activeCurrency);

            return idx === 0 ? "Total" : "";
          });

          rows.push(totalRow);
        }

        setExcelPreview({ headers, rows });
      } else {
        setExcelPreview({ headers: [], rows: [] });
      }
    }
  }, [parsedDraft, excelSection, activeTab, activeCurrency]);

  // Auto-refresh finalized scope when navigating back to Exports tab
  useEffect(() => {
    const refreshScope = async () => {
      try {
        const latest = await getFinalizedScope(id);
        if (latest && Object.keys(latest).length > 0) {
          setJsonText(JSON.stringify(latest, null, 2));
          setIsFinalized(true);
          console.log(" Reloaded finalized_scope.json after navigation");
        }
      } catch (err) {
        console.error(" Failed to refresh finalized scope after navigation:", err);
      }
    };

    // Run immediately whenever this component mounts or URL changes
    refreshScope();
  }, [id, location.key, getFinalizedScope]);
    
  // ---------- Handle Finalize Scope ----------
  const handleFinalize = async () => {
    if (!parsedDraft) return;
    try {
      setFinalizing(true);
      await finalizeScope(id, parsedDraft);
      toast.success("Scope finalized successfully!");

      //  No need for justFinalized
      setIsFinalized(true);
      setShowSuccessBanner(true);

      //  Fetch latest finalized data immediately
      const finalizedData = await getFinalizedScope(id);
      if (finalizedData) {
        skipResetRef.current = true; 
        setJsonText(JSON.stringify(finalizedData, null, 2));
      }
      setPreviewPdfUrl(null);
    } catch (err) {
      console.error("Finalize failed:", err);
      toast.error("Failed to finalize scope.");
    } finally {
      setFinalizing(false);
      setTimeout(() => setShowSuccessBanner(false), 5000);
    }
  };

  // Track if the JSON update came from finalize process
  const skipResetRef = useRef(false);




  // ---------- Unified Download Handler ----------
  const downloadFile = async (key, fetchFn, defaultName, ext) => {
    const controller = new AbortController();
    startDownload(key, controller);

    try {
      const blob = await fetchFn({
        signal: controller.signal,
        onDownloadProgress: (e) => {
          if (e.total) updateProgress(key, Math.round((e.loaded * 100) / e.total));
        },
      });

      if (!blob || blob.size === 0) throw new Error("Empty file");

      const filename = safeFileName(defaultName, ext);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      finishDownload(key);
      toast.success(`${filename} downloaded`);
    } catch (err) {
      if (controller.signal.aborted) {
        toast.info(`${defaultName} download cancelled`);
      } else {
        console.error(err);
        toast.error(`Failed to download ${defaultName}`);
      }
      resetDownload(key);
    }
  };

  // ---------- Individual Downloads ----------
  const handleDownloadJson = () =>
    downloadFile(
      "json",
      async (opts) => {
        const data = await exportApi.exportToJson(id, opts);
        return new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      },
      parsedDraft?.overview?.["Project Name"] || `project_${id}`,
      "json"
    );

  const handleDownloadExcel = () =>
    downloadFile(
      "excel",
      (opts) => exportApi.exportToExcel(id, opts),
      parsedDraft?.overview?.["Project Name"] || `project_${id}`,
      "xlsx"
    );

  const handleDownloadPdf = () =>
    downloadFile(
      "pdf",
      (opts) => exportApi.exportToPdf(id, opts),
      parsedDraft?.overview?.["Project Name"] || `project_${id}`,
      "pdf"
    );

  // ---------- Download All as ZIP ----------
  const handleDownloadAll = async () => {
    const controller = new AbortController();
    startDownload("all", controller);

    try {
      const zip = new JSZip();
      const projectName = parsedDraft?.overview?.["Project Name"] || `project_${id}`;

      // JSON
      const jsonData = await exportApi.exportToJson(id, { signal: controller.signal });
      zip.file(safeFileName(projectName, "json"), JSON.stringify(jsonData, null, 2));

      // Excel
      const excelBlob = await exportApi.exportToExcel(id, {
        signal: controller.signal,
        onDownloadProgress: (e) => {
          if (e.total) updateProgress("all", Math.round((e.loaded * 100) / e.total));
        },
      });
      zip.file(safeFileName(projectName, "xlsx"), excelBlob);

      // PDF
      const pdfBlob = await exportApi.exportToPdf(id, { signal: controller.signal });
      zip.file(safeFileName(projectName, "pdf"), pdfBlob);

      const content = await zip.generateAsync({ type: "blob" });
      saveAs(content, safeFileName(projectName, "zip"));

      finishDownload("all");
      toast.success("All files downloaded");
    } catch (err) {
      if (controller.signal.aborted) toast.info("Download all cancelled");
      else {
        console.error("Download all failed:", err);
        toast.error("Failed to download all files");
      }
      resetDownload("all");
    }
  };

  // ProgressBar Component
  const ProgressBar = ({ percent }) => (
    <div className="w-40 h-5 bg-gray-200 rounded">
      <div
        className="h-2 bg-emerald-500 rounded transition-all"
        style={{ width: `${percent}%` }}
      ></div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4 text-gray-600 dark:text-gray-300">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p className="text-lg font-medium">Loading project scope…</p>
        <p className="text-sm text-gray-400">Please wait while we fetch the data from blob storage</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      <h1 className="text-2xl font-bold text-primary">
        {project ? project.name : "…"}
      </h1>

      {showSuccessBanner && (
        <div className="flex items-center gap-2 p-3 bg-green-100 text-green-800 rounded-md">
          <CheckCircle2 className="w-5 h-5" />
          <span>Scope finalized successfully! You can now download files.</span>
        </div>
      )}
      <div className="relative rounded-xl border bg-white dark:bg-gray-900 shadow-inner h-[400px] flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin scrollbar-thumb-emerald-400 scrollbar-track-gray-100">
          {loading ? (
            <p className="text-gray-400 text-sm italic">Loading chat history…</p>
          ) : Array.isArray(prompts) && prompts.length === 0 ? (
            <p className="text-gray-400 text-sm italic">No messages yet.</p>
          ) : (
            prompts.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`rounded-2xl px-4 py-2 text-sm max-w-[75%] leading-relaxed shadow-sm ${
                    msg.role === "user"
                      ? "bg-emerald-600 text-white rounded-br-none"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-none"
                  }`}
                >
                  {msg.message}
                  <div className="text-[10px] text-gray-400 mt-1 text-right">
                    {new Date(msg.created_at || Date.now()).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>
        {/* Chat input bar (padded inner container) */}
        <div className="px-3 pb-3 pt-2">
          <div className="px-3 py-1.5 bg-gray-90 dark:bg-gray-800 rounded-full flex items-center gap-2 border border-gray-300 dark:border-gray-700 shadow-sm transition-all focus-within:ring-2 focus-within:ring-emerald-400">
            <textarea
              ref={textareaRef}
              value={regenPrompt}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleRegenerate();
                  requestAnimationFrame(() => {
                    setTimeout(() => {
                      chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
                    }, 120);
                  });
                }
              }}
              placeholder="Send an instruction to regenerate scope…"
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 border-none focus:ring-0 outline-none px-2 py-1 rounded-full leading-relaxed max-h-24"
            />

            <button
              type="button"
              onClick={handleRegenerate}
              disabled={regenLoading || !parsedDraft}
              className={`p-3.5 rounded-full transition-all ${
                regenLoading
                  ? "bg-emerald-300 cursor-not-allowed"
                  : "bg-emerald-600 hover:bg-emerald-700 active:scale-95"
              } text-white shadow-md`}
            >
              {regenLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4"
                  fill="none"
                  viewBox="1 1 24 24"
                  stroke="currentColor"
                  strokeWidth={3}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4l16 8-16 8 4-8-4-8z" />
                </svg>
              )}
            </button>
          </div>
        </div>



      </div>
      <div className="flex justify-end border-t border-gray-200 px-3 py-0.5">
          <button
            type="button"
            onClick={async () => {
              if (!window.confirm("Clear entire chat history?")) return;
              await clearPrompts(id);
            }}
            className="text-xs text-red-500 hover:text-red-700"
          >
            Clear Chat
          </button>
        </div>


      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition ${
              activeTab === t.key
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-gray-500 hover:text-primary"
            }`}
          >
            <t.icon className="w-5 h-5" /> {t.label}
          </button>
        ))}
      </div>
      
      {/* JSON */}
      {activeTab === "json" && (
        <div>
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            className="w-full h-96 font-mono text-sm p-3 rounded-md border"
            spellCheck={false}
          />
          {parseError ? (
            <p className="text-red-600 text-sm mt-2">JSON error: {parseError}</p>
          ) : (
            <p className="text-emerald-600 text-sm mt-2">JSON looks valid.</p>
          )}
          <div className="mt-4 flex gap-3 flex-wrap items-center">


            {isFinalized && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownloadJson}
                  disabled={downloadState.json.loading}
                  className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
                >
                  {downloadState.json.loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> JSON
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" /> Download JSON
                    </>
                  )}
                </button>
                {downloadState.json.loading && (
                  <>
                    <ProgressBar percent={downloadState.json.progress} />
                    <button
                      onClick={() => downloadState.json.controller?.abort()}
                      className="px-3 py-2 bg-red-500 text-white rounded-lg flex items-center gap-1"
                    >
                      <XCircle className="w-4 h-4" /> Cancel
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

            {/* Excel */}
      {activeTab === "excel" && (
        <div className="space-y-4">
          {parsedDraft && (
            <div>
              <label className="block text-sm mb-1 text-gray-600">
                Select Section:
              </label>
              <select
                value={excelSection}
                onChange={(e) => setExcelSection(e.target.value)}
                className="border rounded-md px-3 py-2 text-sm"
              >
                {/* Only show valid scope sections with user-friendly labels */}
                {Object.keys(parsedDraft)
                  .filter((k) => k === "overview" || k === "activities" || k === "resourcing_plan")
                  .map((k) => (
                    <option key={k} value={k}>
                      {k === "resourcing_plan" ? "Resources Plan" : k === "activities" ? "Activities" : "Overview"}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {/* Notice about saving edits */}
          {excelSection && excelPreview.headers.length > 0 && (
            <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
              <span className="text-amber-600 text-lg">ℹ️</span>
              <div className="text-sm text-amber-800">
                <strong>Editing Note:</strong> Changes made to this table are temporary and will be lost when you refresh.
                To make permanent changes, use the chat box below to request modifications (e.g., "change Data Engineer rate to $3000", "increase Backend Developer effort by 2 months").
              </div>
            </div>
          )}

          {excelPreview.headers.length ? (
            <div className="overflow-x-auto max-h-[500px] border border-gray-200 rounded-lg shadow">
              <table className="min-w-full text-sm border-collapse">
                <thead className="bg-emerald-50 sticky top-0 z-10">
                  <tr>
                    {excelPreview.headers.map((h) => (
                      <th
                        key={h}
                        className="px-3 py-2 border text-left text-xs font-semibold text-gray-700 whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {excelPreview.rows.map((row, i) => {
                    const isTotal = row[0] === "Total";
                    return (
                      <tr
                        key={i}
                        className={`border-t ${
                          isTotal
                            ? "bg-green-100 font-bold text-green-800"
                            : i % 2 === 0
                            ? "bg-white"
                            : "bg-gray-50"
                        } hover:bg-emerald-50 transition`}
                      >

                        {row.map((cell, j) => {
                          const header = excelPreview.headers[j]?.toLowerCase();
                          let statusColor = "";
                          if (!isTotal && header === "status") {
                            const val = String(cell || "").toLowerCase();
                            if (val.includes("complete"))
                              statusColor = "bg-green-100 text-green-800";
                            else if (val.includes("progress") || val.includes("ongoing"))
                              statusColor = "bg-yellow-100 text-yellow-800";
                            else statusColor = "bg-gray-100 text-gray-600";
                          }

                          return (
                            <td key={j} className={`px-3 py-2 border ${statusColor}`}>
                              {isTotal ? (
                                cell
                              ) : (
                                <input
                                  type="text"
                                  value={cell}
                                  onChange={(e) => {
                                    const newRows = [...excelPreview.rows];
                                    newRows[i][j] = e.target.value;
                                    setExcelPreview({ ...excelPreview, rows: newRows });
                                    updateParsedDraft(excelSection, newRows);
                                  }}
                                  className="w-full bg-transparent border-none focus:ring-0 text-sm px-1 py-0.5 h-4"

                                />
                              )}
                            </td>

                          );
                        })}
                        <td className="px-2 py-1 border">
                        {!isTotal && (
                          <button
                            onClick={() => {
                              const newRows = excelPreview.rows.filter((_, idx) => idx !== i);
                              setExcelPreview({ ...excelPreview, rows: newRows });
                              updateParsedDraft(excelSection, newRows);
                            }}
                            className="text-red-500 text-sm"
                          >
                            <Trash2 className="w-4 h-4 inline" />
                          </button>
                        )}
                      </td>

                      </tr>
                      
                      
                    );
                  })}
                </tbody>
              </table>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => {
                    const emptyRow = excelPreview.headers.map(() => "");
                    const newRows = [...excelPreview.rows, emptyRow];
                    setExcelPreview({ ...excelPreview, rows: newRows });
                    updateParsedDraft(excelSection, newRows);
                  }}
                  className="px-3 py-1 bg-emerald-600 text-white rounded"
                >
                  Add New
                </button>
              </div>

            </div>
          ) : (
            <p className="text-gray-500 text-sm">No table data available.</p>
          )}

          {isFinalized && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadExcel}
                disabled={downloadState.excel.loading}
                className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
              >
                {downloadState.excel.loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Excel
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Download Excel
                  </>
                )}
              </button>
              {downloadState.excel.loading && (
                <>
                  <ProgressBar percent={downloadState.excel.progress} />
                  <button
                    onClick={() => downloadState.excel.controller?.abort()}
                    className="px-3 py-2 bg-red-500 text-white rounded-lg flex items-center gap-1"
                  >
                    <XCircle className="w-4 h-4" /> Cancel
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* PDF */}
      {activeTab === "pdf" && (
        <div className="space-y-4">
          {previewPdfUrl ? (
            <div className="flex justify-center w-full">
              <div className="w-full max-w-6xl border rounded-lg overflow-hidden shadow max-h-[600px] overflow-y-auto bg-white dark:bg-dark-surface">
                <Document
                  file={previewPdfUrl}
                  onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                  loading={
                    <div className="flex flex-col items-center justify-center h-[400px] text-gray-600 dark:text-gray-300">
                      <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mb-3" />
                      <p className="text-sm font-medium">Loading PDF preview…</p>
                    </div>
                  }
                  error={
                    <div className="text-center text-red-500 p-4">
                      <p>Failed to load PDF preview. Please try again.</p>
                    </div>
                  }
                  className="flex flex-col items-center"
                >
                  {Array.from({ length: numPages || 0 }, (_, i) => (
                    <Page
                      key={i}
                      pageNumber={i + 1}
                      renderTextLayer={false}
                      renderAnnotationLayer={false}
                      width={1000} 
                      className="mx-auto my-2"
                    />
                  ))}
                </Document>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[400px] text-gray-600 dark:text-gray-300">
              <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
              <p className="text-sm font-medium">
                {isFinalized
                  ? "Loading final PDF from blob storage…"
                  : "Generating draft PDF preview…"}
              </p>
            </div>
          )}



          {isFinalized && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadPdf}
                disabled={downloadState.pdf.loading}
                className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
              >
                {downloadState.pdf.loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> PDF
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" /> Download PDF
                  </>
                )}
              </button>
              {downloadState.pdf.loading && (
                <>
                  <ProgressBar percent={downloadState.pdf.progress} />
                  <button
                    onClick={() => downloadState.pdf.controller?.abort()}
                    className="px-3 py-2 bg-red-500 text-white rounded-lg flex items-center gap-1"
                  >
                    <XCircle className="w-4 h-4" /> Cancel
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/*  Finalize + Download All Section (Always visible at bottom) */}
      <div className="pt-6 flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={handleFinalize}
          disabled={!parsedDraft || finalizing}
          className={`px-4 py-2 rounded-lg text-white flex items-center gap-2 ${
            finalizing
              ? "bg-emerald-400 cursor-not-allowed"
              : "bg-emerald-600 hover:bg-emerald-700"
          }`}
        >
          {finalizing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Finalizing…
            </>
          ) : (
            <>
              <Save className="w-4 h-4" /> Finalize Scope
            </>
          )}
        </button>

        {isFinalized && (
          <>
            <button
              onClick={handleDownloadAll}
              disabled={downloadState.all.loading}
              className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white font-semibold inline-flex items-center gap-2"
            >
              {downloadState.all.loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> ZIP
                </>
              ) : (
                <>
                  <Package className="w-4 h-4" /> Download All (ZIP)
                </>
              )}
            </button>

            {downloadState.all.loading && (
              <>
                <ProgressBar percent={downloadState.all.progress} />
                <button
                  onClick={() => downloadState.all.controller?.abort()}
                  className="px-3 py-2 bg-red-500 text-white rounded-lg flex items-center gap-1"
                >
                  <XCircle className="w-4 h-4" /> Cancel
                </button>
              </>
            )}
          </>
        )}
      </div>

    </div>
  );
}
