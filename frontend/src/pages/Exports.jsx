import { useParams, Link, useLocation } from "react-router-dom";
import { useState, useEffect, useMemo, useRef } from "react";
import { useProjects } from "../contexts/ProjectContext";
import { useExport } from "../contexts/ExportContext";

import projectApi from "../api/projectApi";
import exportApi, { safeFileName } from "../api/exportApi";
import {
  ArrowLeft,
  FileSpreadsheet,
  FileText,
  FileJson,
  Save,
  Loader2,
  CheckCircle2,
  Download,
  Package,
  XCircle,
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

const formatCurrency = (v) => {
  if (v == null || v === "") return "";
  const n = Number(v);
  if (isNaN(n)) return v;
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
};

export default function Exports() {
  const { id } = useParams();
  const location = useLocation();
  const { finalizeScope, getFinalizedScope } = useProjects();
  const { previewPdf, getPdfBlob, regenerateScope } = useExport();
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
  const [loading, setLoading] = useState(false);
  const [isFinalized, setIsFinalized] = useState(false);
  const [justFinalized, setJustFinalized] = useState(false);

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
  const textareaRef = useRef(null);

  const handleInputChange = (e) => {
    setRegenPrompt(e.target.value);

    // Auto grow & shrink
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto"; // reset to shrink
      el.style.height = `${el.scrollHeight}px`; // expand to fit
    }
  };
  const updateParsedDraft = (section, newRows) => {
    if (!parsedDraft) return;

    if (section === "overview") {
      // turn rows [["Domain","Fintech"],...] back into object
      const newOverview = {};
      newRows.forEach(([k, v]) => {
        if (k) newOverview[k] = v;
      });
      const newDraft = { ...parsedDraft, overview: newOverview };
      setJsonText(JSON.stringify(newDraft, null, 2));
    } else {
      // normal array section
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
    if (!parsedDraft || !regenPrompt.trim()) return;
    try {
      setRegenLoading(true);

      // ✅Correct usage: pass id, draft, and instructions separately
      const updated = await regenerateScope(id, parsedDraft, regenPrompt);

      setJsonText(JSON.stringify(updated, null, 2));
      setIsFinalized(false);

      setRegenPrompt(""); // clear input
    } catch (err) {
      toast.error("Failed to regenerate scope");
      console.error(err);
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

  // Load project
  // ✅ Load project with guard to prevent auto-refresh right after finalization
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const res = await projectApi.getProject(id);
        setProject(res.data);

        // Prevent overwriting immediately after finalize
        if (isFinalized && justFinalized) return;

        const finalizedData = await getFinalizedScope(id);

        if (finalizedData) {
          setJsonText(JSON.stringify(finalizedData, null, 2));
          setIsFinalized(true);
        } else if (incomingDraft) {
          setJsonText(JSON.stringify(incomingDraft, null, 2));
          setIsFinalized(false);
        } else {
          setJsonText("");
          setIsFinalized(false);
        }
      } catch (e) {
        console.error("Failed to load project:", e);
      } finally {
        setLoading(false);
      }
    })();
    // 👇 Important dependency: this prevents overwrite immediately after finalize
  }, [id, incomingDraft, justFinalized]);

  // 🧹 Clear cached PDF on JSON change
  useEffect(() => {
    cachedPdfBlobRef.current = null;
    lastPdfKeyRef.current = "";
    setPreviewPdfUrl(null);
  }, [jsonText]);

  const prevJsonRef = useRef("");
  useEffect(() => {
    // Skip reset right after finalization to prevent false un-finalizing
    if (isFinalized && prevJsonRef.current && prevJsonRef.current !== jsonText && !justFinalized) {
      setIsFinalized(false);
    }

    prevJsonRef.current = jsonText;

    // clear the flag once effect runs after finalize
    if (justFinalized) setJustFinalized(false);
  }, [jsonText, isFinalized, justFinalized]);




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
        const blob = isFinalized
          ? await getPdfBlob(id)
          : await previewPdf(id, parsedDraft);

        if (!blob || blob.size === 0 || blob.type !== "application/pdf") {
          toast.error(" Invalid PDF generated.");
          return;
        }

        cachedPdfBlobRef.current = blob;
        lastPdfKeyRef.current = currentKey;

        if (previewPdfUrl) URL.revokeObjectURL(previewPdfUrl);
        setPreviewPdfUrl(URL.createObjectURL(blob));
      } catch (err) {
        console.error(" Failed to load PDF preview:", err);
        toast.error("Failed to load PDF preview.");
      }
    })();
  }, [activeTab, parsedDraft, isFinalized, id, getPdfBlob, previewPdf]);

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
              return formatCurrency(r[h]);
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
            const rate = parseFloat(r["Rate/month"] || 0);
            totalEfforts += sumMonths;
            totalCost += sumMonths * rate;
          });

          const totalRow = headers.map((h, idx) => {
            if (idx === headers.length - 2) return Number(totalEfforts.toFixed(2));
            if (idx === headers.length - 1) return formatCurrency(totalCost);
            return idx === 0 ? "Total" : "";
          });

          rows.push(totalRow);
        }

        setExcelPreview({ headers, rows });
      } else {
        setExcelPreview({ headers: [], rows: [] });
      }
    }
  }, [parsedDraft, excelSection, activeTab]);

  // ---------- Handle Finalize Scope ----------
  const handleFinalize = async () => {
    if (!parsedDraft) return;
    try {
      setFinalizing(true);
      await finalizeScope(id, parsedDraft);
      toast.success("Scope finalized successfully!");

      setJustFinalized(true);   // 👈 add this line
      setIsFinalized(true);
      setShowSuccessBanner(true);

      const finalizedData = await getFinalizedScope(id);
      if (finalizedData) setJsonText(JSON.stringify(finalizedData, null, 2));

      setPreviewPdfUrl(null);
    } catch (err) {
      console.error("Finalize failed:", err);
      toast.error("Failed to finalize scope.");
    } finally {
      setFinalizing(false);
      setTimeout(() => setShowSuccessBanner(false), 5000);
    }
  };


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

  return (
    <div className="space-y-6">
      <Link
        to={`/projects/${id}`}
        className="inline-flex items-center gap-2 text-primary hover:text-secondary transition font-medium"
      >
        <ArrowLeft className="w-5 h-5" /> Back to Project
      </Link>

      <h1 className="text-2xl font-bold text-primary">
        Export Project {project ? project.name : "…"}
      </h1>

      {showSuccessBanner && (
        <div className="flex items-center gap-2 p-3 bg-green-100 text-green-800 rounded-md">
          <CheckCircle2 className="w-5 h-5" />
          <span>Scope finalized successfully! You can now download files.</span>
        </div>
      )}

      <div className="flex flex-col gap-2 rounded-xl border px-4 py-2 bg-white dark:bg-gray-900 shadow-sm">
        <textarea
        ref={textareaRef}
        value={regenPrompt}
        onChange={handleInputChange}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleRegenerate();
          }
        }}
        placeholder="Type your message here..."
        rows={1}
        className="w-full min-h-[1.25rem] bg-transparent border-none outline-none focus:ring-0 focus:outline-none text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 resize-none overflow-hidden leading-tight"
      />

        <button
          type="button"
          onClick={handleRegenerate}
          disabled={regenLoading || !parsedDraft}
          className={`self-end p-2 rounded-full flex items-center justify-center transition ${
            regenLoading
              ? "bg-emerald-300 cursor-not-allowed"
              : "bg-emerald-600 hover:bg-emerald-700"
          }`}
        >
          {regenLoading ? (
            <Loader2 className="w-5 h-5 text-white animate-spin" />
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4l16 8-16 8 4-8-4-8z"
              />
            </svg>
          )}
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
                  <Loader2 className="w-5 h-5 animate-spin" /> Finalizing…
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" /> Finalize Scope
                </>
              )}
            </button>


            {isFinalized && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownloadJson}
                  disabled={downloadState.json.loading}
                  className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
                >
                  {downloadState.json.loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" /> JSON
                    </>
                  ) : (
                    <>
                      <Download className="w-5 h-5" /> Download JSON
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
                {Object.keys(parsedDraft)
                  .filter((k) => Array.isArray(parsedDraft[k]) || k === "overview")
                  .map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {excelPreview.headers.length ? (
            <div className="overflow-x-auto max-h-[500px] border border-gray-200 rounded-lg shadow">
              <table className="min-w-full text-sm border-collapse">
                <thead className="bg-gray-100 sticky top-0 z-10">
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
                            <td key={j} className="px-3 py-2 border">
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
                                    updateParsedDraft(excelSection, newRows); // keep JSON in sync
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
                            Delete
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
                    <Loader2 className="w-5 h-5 animate-spin" /> Excel
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5" /> Download Excel
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
            <div className="border rounded-lg overflow-hidden shadow max-h-[600px] overflow-y-auto">
              <Document
                file={previewPdfUrl}
                onLoadSuccess={({ numPages }) => setNumPages(numPages)}
              >
                {Array.from({ length: numPages || 0 }, (_, i) => (
                  <Page key={i} pageNumber={i + 1} />
                ))}
              </Document>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">
              {isFinalized
                ? "Loading final PDF preview…"
                : "Generating draft PDF preview…"}
            </p>
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
                    <Loader2 className="w-5 h-5 animate-spin" /> PDF
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5" /> Download PDF
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

      {/* Download All */}
      {isFinalized && (
        <div className="pt-6 flex items-center gap-2">
          <button
            onClick={handleDownloadAll}
            disabled={downloadState.all.loading}
            className="px-6 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold inline-flex items-center gap-2"
          >
            {downloadState.all.loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> ZIP
              </>
            ) : (
              <>
                <Package className="w-5 h-5" /> Download All (ZIP)
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
        </div>
      )}
    </div>
  );
}
