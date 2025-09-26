import { useParams, Link, useLocation } from "react-router-dom";
import { useState, useEffect, useMemo, useRef } from "react";
import { useProjects } from "../contexts/ProjectContext";
import { useExport } from "../contexts/ExportContext";
import exportApi from "../api/exportApi";
import projectApi from "../api/projectApi";
import {
  ArrowLeft,
  FileSpreadsheet,
  FileText,
  FileJson,
  Save,
  Loader2,
  CheckCircle2,
  Download,
} from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

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
  const { finalizeScope } = useProjects();
  const { previewPdf, getPdfBlob } = useExport();

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
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);

  const [excelSection, setExcelSection] = useState("");
  const [excelPreview, setExcelPreview] = useState({ headers: [], rows: [] });
  const [previewPdfUrl, setPreviewPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);

  const cachedPdfBlobRef = useRef(null);
  const lastPdfKeyRef = useRef("");

  // Load project
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const res = await projectApi.getProject(id);
        setProject(res.data);

        try {
          const finalizedData = await exportApi.exportToJson(id);
          setJsonText(JSON.stringify(finalizedData, null, 2));
          setIsFinalized(true);
        } catch {
          if (incomingDraft) setJsonText(JSON.stringify(incomingDraft, null, 2));
          setIsFinalized(false);
        }
      } catch (e) {
        console.error(" Failed to load project:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, incomingDraft]);

  // 🧹 Clear cached PDF on JSON change
  useEffect(() => {
    cachedPdfBlobRef.current = null;
    lastPdfKeyRef.current = "";
    setPreviewPdfUrl(null);
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
            if (idx === headers.length - 2) return totalEfforts;
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

  const handleFinalize = async () => {
    if (!parsedDraft) return;
    try {
      setLoading(true);
      await finalizeScope(id, parsedDraft);
      toast.success(" Scope finalized successfully!");
      setIsFinalized(true);
      setShowSuccessBanner(true);

      const finalizedData = await exportApi.exportToJson(id);
      setJsonText(JSON.stringify(finalizedData, null, 2));
      setPreviewPdfUrl(null);
    } catch (err) {
      console.error(" Finalize failed:", err);
      toast.error(" Failed to finalize scope.");
    } finally {
      setLoading(false);
      setTimeout(() => setShowSuccessBanner(false), 5000);
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async () => {
    try {
      const blob = await exportApi.exportToPdf(id);
      downloadBlob(blob, `project_${id}.pdf`);
    } catch {
      toast.error(" Failed to download final PDF.");
    }
  };

  const handleDownloadExcel = async () => {
    try {
      const blob = await exportApi.exportToExcel(id);
      downloadBlob(blob, `project_${id}.xlsx`);
    } catch {
      toast.error(" Failed to download final Excel.");
    }
  };

  const handleDownloadJson = async () => {
    try {
      const data = await exportApi.exportToJson(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      downloadBlob(blob, `project_${id}.json`);
    } catch {
      toast.error(" Failed to download final JSON.");
    }
  };

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
          <div className="mt-4 flex gap-3 flex-wrap">
            <button
              onClick={handleFinalize}
              disabled={!parsedDraft || loading}
              className={`px-4 py-2 rounded-lg text-white flex items-center gap-2 ${
                loading
                  ? "bg-emerald-400 cursor-not-allowed"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {loading ? (
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
              <button
                onClick={handleDownloadJson}
                className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
              >
                <Download className="w-5 h-5" /> Download Final JSON
              </button>
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
                            else if (
                              val.includes("progress") ||
                              val.includes("ongoing")
                            )
                              statusColor = "bg-yellow-100 text-yellow-800";
                            else statusColor = "bg-gray-100 text-gray-600";
                          }

                          return (
                            <td
                              key={j}
                              className={`px-3 py-2 border whitespace-nowrap max-w-[200px] truncate ${
                                isTotal
                                  ? "font-bold"
                                  : statusColor
                                  ? "font-medium text-center"
                                  : ""
                              }`}
                              title={cell}
                            >
                              {statusColor && !isTotal ? (
                                <span
                                  className={`px-2 py-1 rounded-md text-xs ${statusColor}`}
                                >
                                  {cell || "—"}
                                </span>
                              ) : (
                                cell
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No table data available.</p>
          )}

          {isFinalized && (
            <button
              onClick={handleDownloadExcel}
              className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
            >
              <Download className="w-5 h-5" /> Download Final Excel
            </button>
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
            <button
              onClick={handleDownloadPdf}
              className="px-4 py-2 rounded-lg bg-primary text-white inline-flex items-center gap-2"
            >
              <Download className="w-5 h-5" /> Download Final PDF
            </button>
          )}
        </div>
      )}
    </div>
  );
}
