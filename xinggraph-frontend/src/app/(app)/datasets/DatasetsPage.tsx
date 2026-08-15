"use client";

import { captureException, recordUploadSuccess, recordUploadFailure } from "@/utils/monitoring";
import { useState, useEffect, useRef, useCallback } from "react";
import { useCogniInstance, useTenant } from "@/modules/tenant/TenantProvider";
import PageLoading from "@/ui/elements/PageLoading";
import { useFilter } from "@/ui/layout/FilterContext";
import getDatasets from "@/modules/datasets/getDatasets";
import getDatasetData from "@/modules/datasets/getDatasetData";
import createDataset from "@/modules/datasets/createDataset";
import deleteDataset from "@/modules/datasets/deleteDataset";
import pollDatasetStatus, { type DatasetProcessingStatus } from "@/modules/datasets/pollDatasetStatus";
import { TrackPageView, trackEvent } from "@/modules/analytics";
import { loadGraphModelsConfig, findPromptForDataset, findChunkerForDataset, assignPromptToDataset, assignChunkerToDataset, saveCustomPrompt, findAnswerPromptForDataset, assignAnswerPromptToDataset, saveAnswerCustomPrompt, type CustomPromptsMap, type AnswerCustomPromptsMap } from "@/modules/configuration/userConfiguration";
import getPrompts, { type PromptsContent } from "@/modules/configuration/getPrompts";
import rememberData from "@/modules/ingestion/rememberData";
import deleteDatasetData from "@/modules/datasets/deleteDatasetData";
import ShareDatasetModal from "@/ui/elements/ShareDatasetModal";
import SkeletonBar from "@/ui/elements/SkeletonBar";

interface DatasetRaw {
  id: string;
  name: string;
  createdAt?: string;
  ownerId?: string;
}

interface FileEntry {
  id: string;
  name: string;
  extension?: string;
  mimeType?: string;
  createdAt?: string;
  size?: number;
}

type DisplayStatus = "pending" | "running" | "completed" | "failed" | "empty" | "loading";

interface Dataset extends DatasetRaw {
  documents: number;
  status: DisplayStatus;
}

function mapProcessingStatus(raw: DatasetProcessingStatus | undefined, docCount: number): DisplayStatus {
  if (!raw) return docCount > 0 ? "completed" : "empty";
  if (raw === "DATASET_PROCESSING_COMPLETED") return "completed";
  if (raw === "DATASET_PROCESSING_ERRORED") return "failed";
  if (raw === "DATASET_PROCESSING_STARTED") return "running";
  if (raw === "DATASET_PROCESSING_INITIATED") return "pending";
  return docCount > 0 ? "completed" : "empty";
}

const STATUS_DOT: Record<DisplayStatus, string> = {
  pending:   "#F59E0B",
  running:   "#F59E0B",
  completed: "#22C55E",
  failed:    "#EF4444",
  empty:     "#D4D4D8",
  loading:   "#D4D4D8",
};

const EXT_META: Record<string, { fill: string; stroke: string; text: string; label: string }> = {
  pdf:  { fill: "#FEE2E2", stroke: "#EF4444", text: "#DC2626", label: "PDF" },
  docx: { fill: "#DBEAFE", stroke: "#3B82F6", text: "#2563EB", label: "DOC" },
  doc:  { fill: "#DBEAFE", stroke: "#3B82F6", text: "#2563EB", label: "DOC" },
  md:   { fill: "#F3F4F6", stroke: "#6B7280", text: "#374151", label: "MD"  },
  txt:  { fill: "#F3F4F6", stroke: "#9CA3AF", text: "#6B7280", label: "TXT" },
  csv:  { fill: "#DCFCE7", stroke: "#22C55E", text: "#16A34A", label: "CSV" },
  json: { fill: "#FEF3C7", stroke: "#D97706", text: "#B45309", label: "JSON"},
};

function decodeFilename(name: string): string {
  try {
    let decoded = name;
    let prev: string;
    do { prev = decoded; decoded = decodeURIComponent(decoded); } while (decoded !== prev);
    return decoded;
  } catch {
    return name;
  }
}

function getExtMeta(name: string, ext?: string) {
  const e = (ext || name.split(".").pop() || "").toLowerCase();
  return EXT_META[e] || { fill: "#F3F4F6", stroke: "#9CA3AF", text: "#6B7280", label: e.toUpperCase().slice(0, 4) || "FILE" };
}

function FileIcon({ fill, stroke, text, label }: { fill: string; stroke: string; text: string; label: string }) {
  const fs = label.length > 3 ? 4.5 : label.length > 2 ? 5 : 5.5;
  return (
    <svg width="16" height="20" viewBox="0 0 16 20" fill="none" style={{ flexShrink: 0 }}>
      <path d="M10 1H3a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V6l-5-5z" fill={fill} stroke={stroke} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 1v5h5" stroke={stroke} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      <text x="8" y="14.5" textAnchor="middle" fontSize={fs} fontWeight="700" fill={text}>{label}</text>
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg width="15" height="13" viewBox="0 0 15 13" fill="none" style={{ flexShrink: 0 }}>
      <path d="M1 3a1 1 0 011-1h3.5L7 4h7a1 1 0 011 1v6a1 1 0 01-1 1H2a1 1 0 01-1-1V3z"
        fill="#D4D4D8" fillOpacity="0.5"
        stroke="#A1A1AA"
        strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

function formatSize(bytes?: number): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function PlusIcon() {
  return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}

function EmptyStateIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path d="M6 4a2 2 0 012-2h8l6 6v16a2 2 0 01-2 2H8a2 2 0 01-2-2V4z" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 16v-4M12 14h4" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function DatasetsPage() {
  const { cogniInstance, isInitializing } = useCogniInstance();
  const { tenant } = useTenant();
  const { datasets: contextDatasets, refreshDatasets: refreshFilterDatasets } = useFilter();

  const [datasets, setDatasets]           = useState<Dataset[]>([]);
  const [loading, setLoading]             = useState(true);
  const [refreshing, setRefreshing]       = useState(false);
  const [outdatedDatasets, setOutdated]   = useState<Set<string>>(new Set());

  // Per-dataset prompt / chunker selectors (mirrors the Memory Schema toolbar)
  const CHUNKER_OPTIONS = [
    { value: "automatic", label: "Automatic", hint: "Default" },
    { value: "text", label: "Text", hint: "Paragraph" },
    { value: "structured_doc", label: "Structured Doc", hint: "Doc blocks" },
    { value: "langchain", label: "Langchain", hint: "Recursive split" },
    { value: "csv", label: "CSV", hint: "Rows" },
  ];
  const [customPrompts, setCustomPrompts] = useState<CustomPromptsMap>({});
  const [selectedPromptName, setSelectedPromptName]   = useState<string | null>(null);
  const [selectedChunker, setSelectedChunker]          = useState<string | null>(null);
  const [promptDropdownOpen, setPromptDropdownOpen]    = useState(false);
  const [chunkerDropdownOpen, setChunkerDropdownOpen]  = useState(false);
  const [showCreatePromptModal, setShowCreatePromptModal] = useState(false);
  const [editingPromptName, setEditingPromptName] = useState("");
  const [editingPromptText, setEditingPromptText] = useState("");
  const [savingPrompt, setSavingPrompt] = useState(false);
  const promptDropdownRef = useRef<HTMLDivElement>(null);
  const chunkerDropdownRef = useRef<HTMLDivElement>(null);

  // Pipeline rules panel
  const [rulesOpen, setRulesOpen] = useState(false);
  const [promptsContent, setPromptsContent] = useState<PromptsContent | null>(null);
  const [answerCustomPrompts, setAnswerCustomPrompts] = useState<AnswerCustomPromptsMap>({});
  const [selectedAnswerPrompt, setSelectedAnswerPrompt] = useState<string | null>(null);
  const [answerDropdownOpen, setAnswerDropdownOpen] = useState(false);
  const [showCreateAnswerPromptModal, setShowCreateAnswerPromptModal] = useState(false);
  const [editingAnswerPromptName, setEditingAnswerPromptName] = useState("");
  const [editingAnswerPromptText, setEditingAnswerPromptText] = useState("");
  const [savingAnswerPrompt, setSavingAnswerPrompt] = useState(false);
  const [copiedPromptKey, setCopiedPromptKey] = useState<string | null>(null);
  const answerDropdownRef = useRef<HTMLDivElement>(null);

  // Finder selection
  const [selectedId, setSelectedId]       = useState<string | null>(null);
  const [selectedDocs, setSelectedDocs]   = useState<FileEntry[]>([]);
  const [docsLoading, setDocsLoading]     = useState(false);

  // Upload
  const [isDragOver, setIsDragOver]       = useState(false);
  const [isUploading, setIsUploading]     = useState(false);
  const [uploadError, setUploadError]     = useState<string | null>(null);
  const fileInputRef                      = useRef<HTMLInputElement>(null);
  const dragCounter                       = useRef(0);

  // Modals
  const [showCreateModal, setShowCreate]  = useState(false);
  const [newName, setNewName]             = useState("");
  const [creating, setCreating]           = useState(false);
  const [createError, setCreateError]     = useState("");
  const [deleteTarget, setDeleteTarget]   = useState<Dataset | null>(null);
  const [shareTarget, setShareTarget]     = useState<Dataset | null>(null);
  const [deletingId, setDeletingId]       = useState<string | null>(null);
  const [deleteDocTarget, setDeleteDocTarget] = useState<FileEntry | null>(null);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pasteText, setPasteText]           = useState("");
  const [pasting, setPasting]               = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatuses = useCallback(async (ids: string[]) => {
    if (!cogniInstance || !ids.length) return;
    try {
      const resp = await cogniInstance.fetch("/v1/datasets/status");
      if (!resp.ok) return;
      const data: Record<string, DatasetProcessingStatus> = await resp.json();
      let completedSelectedId: string | null = null;
      setDatasets((prev) => {
        return prev.map((d) => {
          const raw = data[d.id];
          if (!raw) return d;
          const newStatus = mapProcessingStatus(raw, d.documents);
          if (newStatus !== d.status) {
            // When the selected brain finishes, schedule a file list refresh
            if (d.id === selectedId && (d.status === "pending" || d.status === "running") && newStatus === "completed") {
              completedSelectedId = d.id;
            }
            return { ...d, status: newStatus };
          }
          return d;
        });
      });
      if (completedSelectedId) {
        getDatasetData(completedSelectedId, cogniInstance)
          .then((docs) => {
            setSelectedDocs(Array.isArray(docs) ? docs : []);
            setDatasets((prev) => prev.map((d) => d.id === completedSelectedId ? { ...d, documents: Array.isArray(docs) ? docs.length : d.documents } : d));
          })
          .catch((err) => {
            console.error("Failed to fetch dataset documents:", err);
            setSelectedDocs([]);
          });
      }
    } catch { /* graceful */ }
  }, [cogniInstance, selectedId]);

  useEffect(() => {
    if (!cogniInstance || isInitializing) return;
    loadDatasets();
    loadGraphModelsConfig(cogniInstance)
      .then((cfg) => {
        setOutdated(new Set(cfg.outdatedDatasets ?? []));
        setCustomPrompts(cfg.customPrompts ?? {});
        setAnswerCustomPrompts(cfg.answerCustomPrompts ?? {});
      })
      .catch((err) => { console.error("Failed to load graph models config:", err); });
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [cogniInstance, isInitializing]);

  // Apply the selected dataset's saved prompt/chunker assignments
  useEffect(() => {
    if (!selectedId) return;
    setSelectedPromptName(null);
    setSelectedChunker(null);
    setSelectedAnswerPrompt(null);
    setRulesOpen(false);
    loadGraphModelsConfig(cogniInstance!)
      .then((cfg) => {
        setCustomPrompts(cfg.customPrompts ?? {});
        setAnswerCustomPrompts(cfg.answerCustomPrompts ?? {});
        setSelectedPromptName(findPromptForDataset(cfg.promptAssignments ?? {}, selectedId));
        setSelectedChunker(findChunkerForDataset(cfg.chunkerAssignments ?? {}, selectedId));
        setSelectedAnswerPrompt(findAnswerPromptForDataset(cfg.answerPromptAssignments ?? {}, selectedId));
      })
      .catch(() => {});
    getPrompts(cogniInstance!)
      .then(setPromptsContent)
      .catch(() => setPromptsContent(null));
  }, [selectedId, cogniInstance]);

  // Close dropdowns on outside click
  useEffect(() => {
    function h(e: MouseEvent) { if (promptDropdownRef.current && !promptDropdownRef.current.contains(e.target as Node)) setPromptDropdownOpen(false); }
    if (promptDropdownOpen) { document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h); }
  }, [promptDropdownOpen]);
  useEffect(() => {
    function h(e: MouseEvent) { if (chunkerDropdownRef.current && !chunkerDropdownRef.current.contains(e.target as Node)) setChunkerDropdownOpen(false); }
    if (chunkerDropdownOpen) { document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h); }
  }, [chunkerDropdownOpen]);
  useEffect(() => {
    function h(e: MouseEvent) { if (answerDropdownRef.current && !answerDropdownRef.current.contains(e.target as Node)) setAnswerDropdownOpen(false); }
    if (answerDropdownOpen) { document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h); }
  }, [answerDropdownOpen]);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    const hasActive = datasets.some((d) => d.status === "pending" || d.status === "running");
    if (!hasActive || !cogniInstance) return;
    pollRef.current = setInterval(() => fetchStatuses(datasets.map((d) => d.id)), 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [datasets, cogniInstance, fetchStatuses]);

  async function loadDatasets() {
    if (!cogniInstance) return;
    try {
      let list: DatasetRaw[];
      try {
        const fetched = await getDatasets(cogniInstance);
        list = Array.isArray(fetched) ? fetched : [];
      } catch {
        list = contextDatasets as DatasetRaw[];
      }
      const initial = list.map((ds) => ({ ...ds, documents: -1, status: "loading" as DisplayStatus }));
      setDatasets(initial);
      setLoading(false);

      const statusResp = await cogniInstance.fetch("/v1/datasets/status").catch(() => null);
      const statusData: Record<string, DatasetProcessingStatus> = statusResp?.ok ? await statusResp.json() : {};

      for (const ds of list) {
        getDatasetData(ds.id, cogniInstance)
          .then((data) => {
            const count = Array.isArray(data) ? data.length : 0;
            setDatasets((prev) => prev.map((d) => d.id === ds.id ? { ...d, documents: count, status: mapProcessingStatus(statusData[ds.id], count) } : d));
          })
          .catch(() => {
            setDatasets((prev) => prev.map((d) => d.id === ds.id ? { ...d, documents: 0, status: mapProcessingStatus(statusData[ds.id], 0) } : d));
          });
      }
    } catch {
      setDatasets([]);
      setLoading(false);
    }
  }

  async function refreshSelectedDocs(id: string) {
    setDocsLoading(true);
    try {
      const data = await getDatasetData(id, cogniInstance!);
      setSelectedDocs(Array.isArray(data) ? data : []);
    } catch {
      setSelectedDocs([]);
    } finally {
      setDocsLoading(false);
    }
  }

  async function handleSelectDataset(id: string) {
    if (selectedId === id) return;
    setSelectedId(id);
    setSelectedDocs([]);
    await refreshSelectedDocs(id);
  }

  async function handleUploadFiles(files: File[]) {
    if (!cogniInstance || !selectedId || !files.length) return;
    const ds = datasets.find((d) => d.id === selectedId);
    if (!ds) return;

    const totalBytes = files.reduce((sum, f) => sum + f.size, 0);
    const fileTypes = files.map((f) => f.type || "unknown");
    const uploadStartedAt = Date.now();

    setIsUploading(true);
    setUploadError(null);

    trackEvent({
      pageName: "Brains",
      eventName: "dataset_upload_started",
      additionalProperties: {
        dataset_id: ds.id,
        file_count: String(files.length),
        total_bytes: String(totalBytes),
        file_types: fileTypes.join(","),
      },
    });

    try {
      // Kick off ingestion in the background so the upload POST returns immediately,
      // then poll the dataset status until the pipeline finishes. This avoids holding
      // one HTTP request open for the full (multi-minute) build, which the client
      // would abort at the rememberData timeout — and which is also exposed to
      // gateway/LB idle timeouts — while the backend kept processing.
      await rememberData({ id: ds.id, name: ds.name }, files, cogniInstance, {
        runInBackground: true,
        customPrompt: selectedPromptName && customPrompts[selectedPromptName] ? customPrompts[selectedPromptName] : undefined,
        chunker: selectedChunker && selectedChunker !== "automatic" ? selectedChunker : undefined,
      });
      await pollDatasetStatus(ds.id, cogniInstance, { intervalMs: 5000 });
      const data = await getDatasetData(ds.id, cogniInstance) as FileEntry[];
      setSelectedDocs(Array.isArray(data) ? data : []);
      setDatasets((prev) => prev.map((d) => d.id === ds.id ? { ...d, documents: Array.isArray(data) ? data.length : d.documents, status: "running" } : d));

      const durationMs = Date.now() - uploadStartedAt;
      recordUploadSuccess(durationMs, totalBytes, files.length);
      trackEvent({
        pageName: "Brains",
        eventName: "dataset_files_uploaded",
        additionalProperties: {
          dataset_id: ds.id,
          file_count: String(files.length),
          total_bytes: String(totalBytes),
          duration_ms: String(durationMs),
        },
      });
    } catch (err) {
      const durationMs = Date.now() - uploadStartedAt;
      const errorName = err instanceof Error ? err.name : "UnknownError";
      const errorMessage = err instanceof Error ? err.message : String(err);

      recordUploadFailure(errorName, durationMs);
      trackEvent({
        pageName: "Brains",
        eventName: "dataset_upload_failed",
        additionalProperties: {
          dataset_id: ds.id,
          file_count: String(files.length),
          total_bytes: String(totalBytes),
          file_types: fileTypes.join(","),
          duration_ms: String(durationMs),
          error_name: errorName,
          error_message: errorMessage,
        },
      });

      if (errorName === "UploadTimeoutError") {
        setUploadError("The file took too long to process. Please try again with a smaller file.");
      } else {
        captureException(err, { datasetId: ds.id, fileCount: files.length, totalBytes, durationMs });
        setUploadError(errorMessage || "Upload failed. Please try again.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteFile(docId: string) {
    if (!cogniInstance || !selectedId) return;
    try {
      await deleteDatasetData(selectedId, docId, cogniInstance);
      setSelectedDocs((prev) => prev.filter((d) => d.id !== docId));
      setDatasets((prev) => prev.map((d) => d.id === selectedId ? { ...d, documents: Math.max(0, d.documents - 1) } : d));
    } catch (err) {
      console.error("Failed to delete file:", err);
    }
  }

  const handleDelete = async (ds: Dataset) => {
    if (!cogniInstance) return;
    setDeletingId(ds.id);
    try {
      await deleteDataset(ds.id, cogniInstance);
      trackEvent({ pageName: "Brains", eventName: "dataset_deleted", additionalProperties: { dataset_id: ds.id, dataset_name: ds.name } });
      setDatasets((prev) => prev.filter((d) => d.id !== ds.id));
      if (selectedId === ds.id) { setSelectedId(null); setSelectedDocs([]); }
      setDeleteTarget(null);
      refreshFilterDatasets();
    } catch (err) {
      console.error("Failed to delete brain:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreate = async () => {
    const trimmed = newName.trim();
    if (!trimmed || !cogniInstance) return;
    setCreateError("");
    if (trimmed.includes(" ") || trimmed.includes(".")) {
      setCreateError("Dataset name cannot contain spaces or periods.");
      return;
    }
    setCreating(true);
    try {
      const ds = await createDataset({ name: trimmed.toLowerCase() }, cogniInstance, tenant?.tenant_id);
      trackEvent({ pageName: "Brains", eventName: "dataset_created", additionalProperties: { dataset_name: ds.name } });
      setDatasets((prev) => [...prev, { ...ds, documents: 0, status: "empty" as DisplayStatus }]);
      setNewName(""); setCreateError(""); setShowCreate(false);
      refreshFilterDatasets();
    } catch (err) {
      console.error("Failed to create dataset:", err);
      setCreateError("Failed to create brain. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  async function handlePasteText() {
    if (!pasteText.trim() || !selectedId) return;
    setPasting(true);
    try {
      const blob = new Blob([pasteText], { type: "text/plain" });
      const file = new File([blob], `pasted-text-${Date.now()}.txt`, { type: "text/plain" });
      setShowPasteModal(false);
      setPasteText("");
      await handleUploadFiles([file]);
    } finally {
      setPasting(false);
    }
  }

  async function handleSavePrompt() {
    if (!cogniInstance) return;
    const name = editingPromptName.trim();
    if (!name) return;
    setSavingPrompt(true);
    try {
      await saveCustomPrompt(cogniInstance, name, editingPromptText);
      setCustomPrompts((prev) => ({ ...prev, [name]: editingPromptText }));
      setSelectedPromptName(name);
      setShowCreatePromptModal(false);
      if (selectedId) assignPromptToDataset(cogniInstance, selectedId, name).catch(() => {});
    } catch {
      /* ignore */
    } finally {
      setSavingPrompt(false);
    }
  }

  async function handleSaveAnswerPrompt() {
    if (!cogniInstance) return;
    const name = editingAnswerPromptName.trim();
    if (!name) return;
    setSavingAnswerPrompt(true);
    try {
      await saveAnswerCustomPrompt(cogniInstance, name, editingAnswerPromptText);
      setAnswerCustomPrompts((prev) => ({ ...prev, [name]: editingAnswerPromptText }));
      setSelectedAnswerPrompt(name);
      setShowCreateAnswerPromptModal(false);
      if (selectedId) assignAnswerPromptToDataset(cogniInstance, selectedId, name).catch(() => {});
    } catch {
      /* ignore */
    } finally {
      setSavingAnswerPrompt(false);
    }
  }

  if (loading || isInitializing) {
    return (
      <><TrackPageView page="Brains" />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <span style={{ fontSize: 14, color: "rgba(237,236,234,0.55)" }}>Loading datasets…</span>
        </div>
      </>
    );
  }

  const selectedDataset = datasets.find((d) => d.id === selectedId) ?? null;

  const isStructuredDocSelected = selectedChunker === "structured_doc";

  const graphAutoFallbackPrompt = isStructuredDocSelected
    ? (promptsContent?.graph_structured_doc ?? "")
    : (promptsContent?.graph_default ?? "");
  const graphPromptContent = selectedPromptName && customPrompts[selectedPromptName]
    ? customPrompts[selectedPromptName]
    : graphAutoFallbackPrompt;
  const graphPromptLabel = selectedPromptName
    ? `自定义：${selectedPromptName}`
    : isStructuredDocSelected ? "自动-结构化版" : "自动-默认版";
  const graphPromptNote = selectedPromptName
    ? "使用你保存的自定义建图提示词（覆盖自动选择）。"
    : isStructuredDocSelected
      ? "选 Structured Doc 且未指定自定义 → 自动用结构化版（= 默认版 + #0 包装头解析规则 + 规格存为属性）。"
      : "未指定自定义 → 使用默认建图提示词（generate_graph_prompt.txt）。";

  const answerPromptContent = (() => {
    if (selectedAnswerPrompt === "default") return promptsContent?.answer_default ?? "";
    if (selectedAnswerPrompt === "structured_doc") return promptsContent?.answer_structured_doc ?? "";
    if (selectedAnswerPrompt && answerCustomPrompts[selectedAnswerPrompt]) return answerCustomPrompts[selectedAnswerPrompt];
    return isStructuredDocSelected
      ? (promptsContent?.answer_structured_doc ?? "")
      : (promptsContent?.answer_default ?? "");
  })();
  const answerPromptLabel = selectedAnswerPrompt === "default"
    ? "默认版"
    : selectedAnswerPrompt === "structured_doc"
      ? "结构化版"
      : selectedAnswerPrompt && answerCustomPrompts[selectedAnswerPrompt]
        ? `自定义：${selectedAnswerPrompt}`
        : "自动";
  const answerPromptNote = selectedAnswerPrompt === "default"
    ? "固定使用默认回答提示词（answer_simple_question.txt）。"
    : selectedAnswerPrompt === "structured_doc"
      ? "固定使用结构化版（标题归因，answer_simple_question_structured_doc.txt）。"
      : selectedAnswerPrompt && answerCustomPrompts[selectedAnswerPrompt]
        ? "使用你保存的自定义回答提示词（覆盖自动选择）。"
        : isStructuredDocSelected
          ? "自动 → 随切片策略：Structured Doc 数据集用标题归因版（不吐 wrapper 头）。"
          : "自动 → 随切片策略：非 Structured Doc 用默认回答提示词。";

  const chunkerDescription = (() => {
    switch (selectedChunker) {
      case "text": return "Text：按段落切分，适合普通文本/纯文本段落。";
      case "structured_doc": return "Structured Doc：按文档块切分，一块 = 一个 chunk，保留 titles 标题层级；专用于解析过的结构化 PDF（带 Doc N/M 包装头）。";
      case "langchain": return "Langchain：递归字符切分，适合代码/长文本。";
      case "csv": return "CSV：按表格行切分，适合结构化表格数据。";
      case "automatic":
      default: return "Automatic：自动选择默认切分方式（按段落/固定大小），适合普通文本。";
    }
  })();

  function copyPrompt(key: string, text: string) {
    navigator.clipboard.writeText(text || "")
      .then(() => {
        setCopiedPromptKey(key);
        setTimeout(() => setCopiedPromptKey(null), 1500);
      })
      .catch(() => {});
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <TrackPageView page="Brains" />

      {/* ── Create modal ── */}
      {showCreateModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => { setShowCreate(false); setCreateError(""); }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 420, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.12)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Create brain</h2>
            <p style={{ fontSize: 13, color: "rgba(237,236,234,0.55)", margin: 0 }}>Give your brain a name. You can upload documents after creation.</p>
            <input ref={inputRef} autoFocus type="text" value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
              placeholder="e.g. product-docs, sec-filings..."
              style={{ width: "100%", height: 40, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, paddingInline: 14, fontSize: 14, color: "#EDECEA", fontFamily: "inherit", outline: "none", boxSizing: "border-box" }}
              onFocus={(e) => { e.target.style.borderColor = "#6510F4"; e.target.style.boxShadow = "0 0 0 3px rgba(188,155,255,0.10)"; }}
              onBlur={(e)  => { e.target.style.borderColor = "rgba(255,255,255,0.12)"; e.target.style.boxShadow = "none"; }}
            />
            {createError && <p style={{ fontSize: 13, color: "#EF4444", margin: 0 }}>{createError}</p>}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => { setShowCreate(false); setNewName(""); setCreateError(""); }} className="cursor-pointer"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit" }}>Cancel</button>
              <button onClick={handleCreate} disabled={creating} className="cursor-pointer"
                style={{ background: newName.trim() ? "#6510F4" : "rgba(255,255,255,0.06)", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: newName.trim() ? "#fff" : "rgba(237,236,234,0.35)", fontFamily: "inherit" }}>
                {creating ? "Creating…" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete document modal ── */}
      {deleteDocTarget && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => setDeleteDocTarget(null)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 420, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.12)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Delete document</h2>
            <p style={{ fontSize: 13, color: "rgba(237,236,234,0.55)", margin: 0 }}>
              Are you sure you want to delete <strong>{decodeFilename(deleteDocTarget.name)}</strong>? This action cannot be undone.
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setDeleteDocTarget(null)} className="cursor-pointer"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit" }}>Cancel</button>
              <button onClick={() => { handleDeleteFile(deleteDocTarget.id); setDeleteDocTarget(null); }} className="cursor-pointer"
                style={{ background: "#EF4444", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "#fff", fontFamily: "inherit" }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Paste text modal ── */}
      {showPasteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => { setShowPasteModal(false); setPasteText(""); }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 420, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.12)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Paste text</h2>
            <p style={{ fontSize: 13, color: "rgba(237,236,234,0.55)", margin: 0 }}>Paste your text below. It will be added as a document to the selected brain.</p>
            <textarea
              autoFocus
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="Paste your text here…"
              rows={8}
              style={{ width: "100%", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", fontSize: 14, color: "#EDECEA", fontFamily: "inherit", outline: "none", resize: "vertical", boxSizing: "border-box" }}
              onFocus={(e) => { e.target.style.borderColor = "#6510F4"; e.target.style.boxShadow = "0 0 0 3px rgba(188,155,255,0.10)"; }}
              onBlur={(e)  => { e.target.style.borderColor = "rgba(255,255,255,0.12)"; e.target.style.boxShadow = "none"; }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => { setShowPasteModal(false); setPasteText(""); }} className="cursor-pointer"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit" }}>Cancel</button>
              <button onClick={handlePasteText} disabled={!pasteText.trim() || pasting} className="cursor-pointer"
                style={{ background: pasteText.trim() ? "#6510F4" : "rgba(255,255,255,0.06)", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: pasteText.trim() ? "#fff" : "rgba(237,236,234,0.35)", fontFamily: "inherit" }}>
                {pasting ? "Adding…" : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete brain modal ── */}
      {deleteTarget && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => setDeleteTarget(null)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 420, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.12)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Delete brain</h2>
            <p style={{ fontSize: 13, color: "rgba(237,236,234,0.55)", margin: 0 }}>
              Are you sure you want to delete <strong>{deleteTarget.name}</strong>? This will permanently remove the dataset and all its files.
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setDeleteTarget(null)} className="cursor-pointer"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit" }}>Cancel</button>
              <button onClick={() => handleDelete(deleteTarget)} disabled={deletingId === deleteTarget.id} className="cursor-pointer"
                style={{ background: "#EF4444", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "#fff", fontFamily: "inherit" }}>
                {deletingId === deleteTarget.id ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Share brain modal ── */}
      {shareTarget && (
        <ShareDatasetModal
          datasetId={shareTarget.id}
          datasetName={shareTarget.name}
          pageName="Brains"
          onClose={() => setShareTarget(null)}
        />
      )}

      {/* ── Header ── */}
      <div style={{ padding: "24px 32px 16px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexShrink: 0 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <h1 style={{ fontSize: 20, fontWeight: 300, color: "#EDECEA", margin: 0, fontFamily: '"TWKLausanne", sans-serif' }}>Brain</h1>
          <p style={{ fontSize: 14, color: "rgba(237,236,234,0.55)", margin: 0 }}>Upload documents to build searchable knowledge graphs.</p>
        </div>
        <button onClick={async () => { setRefreshing(true); await Promise.all([loadDatasets(), selectedId ? refreshSelectedDocs(selectedId) : Promise.resolve()]); setRefreshing(false); }} disabled={refreshing}
          className="hover:bg-white/10 cursor-pointer"
          style={{ background: "rgba(255,255,255,0.06)", color: "rgba(237,236,234,0.7)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 12px", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 4 }}
          title="Refresh">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(237,236,234,0.7)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={refreshing ? { animation: "spin 1s linear infinite" } : undefined}>
            <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0115.36-6.36L21 8" /><path d="M3 22v-6h6" /><path d="M21 12a9 9 0 01-15.36 6.36L3 16" />
          </svg>
        </button>
      </div>

      {/* ── Finder body ── */}
      {datasets.length > 0 ? (
        <div style={{ flex: 1, minHeight: 0, display: "flex", overflow: "hidden", marginInline: 32, marginBottom: 32, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12, background: "rgba(0,0,0,0.82)", backdropFilter: "blur(20px)" }}>

          {/* Column 1 — Datasets */}
          <div style={{ width: 312, flexShrink: 0, borderRight: "1px solid rgba(255,255,255,0.1)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{ height: 44, padding: "0 14px", borderBottom: "1px solid rgba(255,255,255,0.1)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(237,236,234,0.55)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Brain</span>
              <button onClick={() => { trackEvent({ pageName: "Brains", eventName: "dataset_create_modal_opened" }); setShowCreate(true); }}
                className="hover:bg-[#5A0ED6] cursor-pointer"
                style={{ background: "#6510F4", color: "#fff", border: "none", borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 500, display: "flex", alignItems: "center", gap: 4 }}>
                <PlusIcon /> New brain
              </button>
            </div>
            <div style={{ flex: 1, overflowY: "auto" }}>
              {datasets.map((ds, i) => {
                const active = ds.id === selectedId;
                const statusLoading = ds.status === "loading";
                const docsLoadingRow = ds.documents < 0;
                const dotColor = outdatedDatasets.has(ds.id) ? "#F59E0B" : STATUS_DOT[ds.status];
                return (
                  <div key={ds.id} onClick={() => handleSelectDataset(ds.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "8px 14px",
                      borderBottom: i < datasets.length - 1 ? "1px solid rgba(255,255,255,0.07)" : "none",
                      cursor: "pointer",
                      background: active ? "rgba(188,155,255,0.20)" : "transparent",
                      userSelect: "none",
                    }}
                    onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.06)"; }}
                    onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
                  >
                    {statusLoading ? (
                      <SkeletonBar width={7} height={7} />
                    ) : (
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: dotColor, flexShrink: 0 }} />
                    )}
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: "#EDECEA", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {ds.name}
                    </span>
                    <span style={{ fontSize: 11, color: "rgba(237,236,234,0.35)", flexShrink: 0, minWidth: 16, textAlign: "right" }}>
                      {docsLoadingRow ? <SkeletonBar width={14} height={8} /> : ds.documents}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); trackEvent({ pageName: "Brains", eventName: "dataset_share_modal_opened", additionalProperties: { dataset_id: ds.id } }); setShareTarget(ds); }}
                      className="hover:bg-white/10"
                      style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 9px", display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 500, color: "rgba(237,236,234,0.7)", cursor: "pointer", flexShrink: 0 }}
                      title="Share brain"
                    >
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="rgba(237,236,234,0.7)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" /></svg>
                      Share
                    </button>
                    {ds.name !== "default_dataset" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteTarget(ds); }}
                        style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 500, color: "rgba(237,236,234,0.7)", cursor: "pointer", flexShrink: 0 }}
                        title="Delete brain"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Column 2 — Documents */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: "none" }}
            onChange={(e) => { if (e.target.files?.length) { handleUploadFiles(Array.from(e.target.files)); e.target.value = ""; } }}
          />
          <div
            style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}
            onDragEnter={(e) => { e.preventDefault(); if (!selectedId) return; dragCounter.current++; setIsDragOver(true); }}
            onDragOver={(e) => { e.preventDefault(); }}
            onDragLeave={(e) => { e.preventDefault(); dragCounter.current--; if (dragCounter.current === 0) setIsDragOver(false); }}
            onDrop={(e) => { e.preventDefault(); dragCounter.current = 0; setIsDragOver(false); if (!selectedId) return; const files = Array.from(e.dataTransfer.files); if (files.length) handleUploadFiles(files); }}
          >
            {/* Drop overlay */}
            {isDragOver && selectedId && (
              <div style={{ position: "absolute", inset: 0, zIndex: 10, background: "rgba(101,16,244,0.06)", border: "2px dashed #6510F4", borderRadius: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, pointerEvents: "none" }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 15V3m0 0L8 7m4-4l4 4" stroke="#6510F4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /><path d="M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4" stroke="#6510F4" strokeWidth="1.5" strokeLinecap="round" /></svg>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#6510F4" }}>Drop to upload</span>
              </div>
            )}

            {/* Header */}
            <div style={{ height: 44, padding: "0 16px", borderBottom: "1px solid rgba(255,255,255,0.1)", flexShrink: 0, display: "flex", alignItems: "center", gap: 6 }}>
              {selectedDataset ? (
                <>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(237,236,234,0.55)", letterSpacing: "0.08em", textTransform: "uppercase" }}>{selectedDataset.name}</span>
                  <span style={{ fontSize: 11, color: "rgba(255,255,255,0.2)" }}>·</span>
                  <span style={{ fontSize: 11, color: "rgba(237,236,234,0.35)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                    {docsLoading ? <SkeletonBar width={36} height={8} /> : <>{selectedDocs.length} doc{selectedDocs.length !== 1 ? "s" : ""}</>}
                  </span>
                  <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="hover:bg-[#5A0ED6] cursor-pointer"
                      style={{ background: "#6510F4", color: "#fff", border: "none", borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 500, cursor: "pointer" }}
                    >
                      Add files
                    </button>
                    <button
                      onClick={() => setShowPasteModal(true)}
                      className="hover:bg-[#5A0ED6] cursor-pointer"
                      style={{ background: "#6510F4", color: "#fff", border: "none", borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 500, cursor: "pointer" }}
                    >
                      Paste text
                    </button>
                  </div>
                </>
              ) : (
                <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(237,236,234,0.55)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Documents</span>
              )}
            </div>

            {/* Pipeline Rules panel */}
            {selectedDataset && (
              <div style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", flexShrink: 0, overflow: "hidden" }}>
                <button onClick={() => setRulesOpen((v) => !v)}
                  style={{ width: "100%", background: "none", border: "none", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontFamily: "inherit", textAlign: "left" }}>
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style={{ transform: rulesOpen ? "rotate(90deg)" : "none", transition: "transform 0.15s" }}><path d="M3 1L7 5L3 9" stroke="rgba(237,236,234,0.55)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(237,236,234,0.55)", letterSpacing: "0.08em", textTransform: "uppercase" }}>处理规则 Pipeline Rules</span>
                  <span style={{ fontSize: 11, color: "rgba(255,255,255,0.2)" }}>·</span>
                  <span style={{ fontSize: 11, color: "rgba(188,155,255,0.9)" }}>
                    切片: {selectedChunker && selectedChunker !== "automatic" ? (CHUNKER_OPTIONS.find((o) => o.value === selectedChunker)?.label ?? selectedChunker) : "Automatic"}
                    {" · "}建图: {graphPromptLabel}
                    {" · "}回答: {answerPromptLabel}
                  </span>
                </button>

                {rulesOpen && (
                  <div style={{ padding: "4px 16px 12px", display: "flex", flexDirection: "column", gap: 10, maxHeight: "min(56vh, 560px)", overflowY: "auto" }}>

                    {/* intro / clarifications */}
                    <div style={{ fontSize: 12, lineHeight: "18px", color: "rgba(237,236,234,0.55)", background: "rgba(188,155,255,0.08)", border: "1px solid rgba(188,155,255,0.15)", borderRadius: 8, padding: "8px 12px" }}>
                      选择 Chunker 会同时改变三件事：<strong style={{ color: "#EDECEA" }}>切片方式、建图提示词、回答提示词</strong>。
                      「Structured Doc」= 按文档块切分（带标题包装头），建图提示词在默认版基础上加了「#0 包装头解析规则」+「规格存为属性」。
                    </div>
                    <div style={{ fontSize: 12, lineHeight: "18px", color: "rgba(237,236,234,0.45)" }}>
                      提示：Chunker 是<b>建图阶段</b>的切片方式，与<b>WIKI 渐进式检索</b>（检索阶段的回答算法）不是一回事；Structured Doc 适用于解析过的结构化 PDF，与 WIKI 检索可叠加使用。
                    </div>

                    {/* ① Chunker */}
                    <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, background: "rgba(255,255,255,0.03)", overflow: "hidden" }}>
                      <div style={{ padding: "8px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#EDECEA" }}>① 切片策略 Chunker</span>
                        <div ref={chunkerDropdownRef} style={{ position: "relative", marginLeft: "auto" }}>
                          <button onClick={() => setChunkerDropdownOpen((v) => !v)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", fontSize: 12, fontWeight: 500, color: "rgba(237,236,234,0.85)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, fontFamily: "inherit" }}>
                            {selectedChunker && selectedChunker !== "automatic" ? (CHUNKER_OPTIONS.find((o) => o.value === selectedChunker)?.label ?? selectedChunker) : "Automatic"}
                            <svg width="9" height="9" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5L7.5 4" stroke="rgba(237,236,234,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          </button>
                          {chunkerDropdownOpen && (
                            <div style={{ position: "absolute", top: "calc(100% + 4px)", right: 0, background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(16px)", borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.5)", minWidth: 220, zIndex: 50, overflow: "hidden" }}>
                              {CHUNKER_OPTIONS.map((option) => (
                                <button key={option.value} onClick={() => { setSelectedChunker(option.value); setChunkerDropdownOpen(false); if (cogniInstance && selectedId) { assignChunkerToDataset(cogniInstance, selectedId, option.value === "automatic" ? null : option.value).catch(() => {}); } }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#EDECEA", display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                  <span style={{ width: 14, color: "#BC9BFF" }}>{selectedChunker && selectedChunker === option.value ? "✓" : !selectedChunker && option.value === "automatic" ? "✓" : ""}</span>
                                  <span style={{ flex: 1 }}>{option.label}</span>
                                  <span style={{ fontSize: 10, color: "rgba(237,236,234,0.35)" }}>{option.hint}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div style={{ padding: "0 12px 10px", display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ fontSize: 12, color: "rgba(237,236,234,0.6)" }}>{chunkerDescription}</div>
                        <div style={{ fontSize: 11, lineHeight: "16px", color: "rgba(237,236,234,0.4)", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: "8px 10px", fontFamily: "ui-monospace, monospace", whiteSpace: "pre-wrap" }}>
{`【示例】同一段内容，不同策略切成什么样

原始 PDF（解析后）:
Doc 1/90: len=402, titles=['dw-86唯一', '技术数据']
--- 内容开始 ---
海尔医用低温保存箱 DW-86L959W，温度范围 -20~-86℃……
--- 内容结束 ---

┌ Automatic / Text ────────────────────┐
│ 按段落/字数硬切 → 标题层级丢失，      │
│ 前后两段可能被打散到不同 chunk        │
└──────────────────────────────────────┘
┌ Structured Doc ─────────────────────┐
│ 一个文档块 = 一个 chunk，            │
│ titles 层级完整保留（可精确归因到章节）│
└──────────────────────────────────────┘`}
                        </div>
                      </div>
                    </div>

                    {/* ② Graph prompt */}
                    <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, background: "rgba(255,255,255,0.03)", overflow: "hidden" }}>
                      <div style={{ padding: "8px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#EDECEA" }}>② 建图提示词（实体/关系抽取）</span>
                        <div ref={promptDropdownRef} style={{ position: "relative", marginLeft: "auto" }}>
                          <button onClick={() => setPromptDropdownOpen((v) => !v)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", fontSize: 12, fontWeight: 500, color: "rgba(237,236,234,0.85)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, fontFamily: "inherit" }}>
                            {graphPromptLabel}
                            <svg width="9" height="9" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5L7.5 4" stroke="rgba(237,236,234,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          </button>
                          {promptDropdownOpen && (
                            <div style={{ position: "absolute", top: "calc(100% + 4px)", right: 0, background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(16px)", borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.5)", minWidth: 240, zIndex: 50, overflow: "hidden" }}>
                              <button onClick={() => { setSelectedPromptName(null); setPromptDropdownOpen(false); if (cogniInstance && selectedId) assignPromptToDataset(cogniInstance, selectedId, null).catch(() => {}); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#EDECEA", display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                <span style={{ width: 14, color: "#BC9BFF" }}>{selectedPromptName === null ? "✓" : ""}</span>
                                <span style={{ flex: 1 }}>自动（默认版 · 53 行）</span>
                                <span style={{ fontSize: 10, color: "rgba(237,236,234,0.35)" }}>{selectedPromptName === null && isStructuredDocSelected ? "已切结构化版" : ""}</span>
                              </button>
                              {Object.keys(customPrompts).length > 0 && <div style={{ height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />}
                              {Object.entries(customPrompts).map(([name, text]) => (
                                <button key={name} onClick={() => { setSelectedPromptName(name); setPromptDropdownOpen(false); if (cogniInstance && selectedId) assignPromptToDataset(cogniInstance, selectedId, name).catch(() => {}); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#EDECEA", display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                  <span style={{ width: 14, color: "#BC9BFF" }}>{selectedPromptName === name ? "✓" : ""}</span>
                                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>自定义：{name}</span>
                                  <span style={{ fontSize: 10, color: "rgba(237,236,234,0.35)" }}>{text.split("\n").length} 行</span>
                                </button>
                              ))}
                              <div style={{ height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
                              <button onClick={() => { setPromptDropdownOpen(false); setEditingPromptName(`${selectedDataset?.name ?? "Brain"} Prompt`); setEditingPromptText(graphAutoFallbackPrompt); setShowCreatePromptModal(true); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#BC9BFF", fontWeight: 500, display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                <span style={{ width: 14 }}>+</span><span>新建自定义</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      <div style={{ padding: "0 12px 10px", display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ fontSize: 11, color: "rgba(237,236,234,0.45)" }}>{graphPromptNote}</div>
                        <div style={{ position: "relative" }}>
                          <button onClick={() => copyPrompt("graph", graphPromptContent)} style={{ position: "absolute", top: 6, right: 6, background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "2px 8px", fontSize: 10, fontWeight: 500, color: "rgba(237,236,234,0.7)", cursor: "pointer", fontFamily: "inherit" }}>
                            {copiedPromptKey === "graph" ? "已复制 ✓" : "📋 复制"}
                          </button>
                          <pre style={{ margin: 0, maxHeight: 180, overflow: "auto", fontSize: 11, lineHeight: "16px", color: "rgba(237,236,234,0.8)", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: "8px 10px", whiteSpace: "pre-wrap", fontFamily: "ui-monospace, monospace" }}>{graphPromptContent}</pre>
                        </div>
                      </div>
                    </div>

                    {/* ③ Answer prompt */}
                    <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, background: "rgba(255,255,255,0.03)", overflow: "hidden" }}>
                      <div style={{ padding: "8px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#EDECEA" }}>③ 回答提示词（检索回答）</span>
                        <div ref={answerDropdownRef} style={{ position: "relative", marginLeft: "auto" }}>
                          <button onClick={() => setAnswerDropdownOpen((v) => !v)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", fontSize: 12, fontWeight: 500, color: "rgba(237,236,234,0.85)", cursor: "pointer", display: "flex", alignItems: "center", gap: 5, fontFamily: "inherit" }}>
                            {answerPromptLabel}
                            <svg width="9" height="9" viewBox="0 0 10 10" fill="none"><path d="M2.5 4L5 6.5L7.5 4" stroke="rgba(237,236,234,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          </button>
                          {answerDropdownOpen && (
                            <div style={{ position: "absolute", top: "calc(100% + 4px)", right: 0, background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(16px)", borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.5)", minWidth: 240, zIndex: 50, overflow: "hidden" }}>
                              {[
                                { value: null, label: "自动（随切片策略）", note: isStructuredDocSelected ? "→ 结构化版" : "→ 默认版" },
                                { value: "default", label: "默认版", note: "1 行" },
                                { value: "structured_doc", label: "结构化版", note: "22 行" },
                              ].map((opt) => (
                                <button key={opt.value ?? "auto"} onClick={() => { setSelectedAnswerPrompt(opt.value); setAnswerDropdownOpen(false); if (cogniInstance && selectedId) assignAnswerPromptToDataset(cogniInstance, selectedId, opt.value).catch(() => {}); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#EDECEA", display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                  <span style={{ width: 14, color: "#BC9BFF" }}>{selectedAnswerPrompt === opt.value ? "✓" : ""}</span>
                                  <span style={{ flex: 1 }}>{opt.label}</span>
                                  <span style={{ fontSize: 10, color: "rgba(237,236,234,0.35)" }}>{opt.note}</span>
                                </button>
                              ))}
                              {Object.keys(answerCustomPrompts).length > 0 && <div style={{ height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />}
                              {Object.entries(answerCustomPrompts).map(([name, text]) => (
                                <button key={name} onClick={() => { setSelectedAnswerPrompt(name); setAnswerDropdownOpen(false); if (cogniInstance && selectedId) assignAnswerPromptToDataset(cogniInstance, selectedId, name).catch(() => {}); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#EDECEA", display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                  <span style={{ width: 14, color: "#BC9BFF" }}>{selectedAnswerPrompt === name ? "✓" : ""}</span>
                                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>自定义：{name}</span>
                                  <span style={{ fontSize: 10, color: "rgba(237,236,234,0.35)" }}>{text.split("\n").length} 行</span>
                                </button>
                              ))}
                              <div style={{ height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
                              <button onClick={() => { setAnswerDropdownOpen(false); setEditingAnswerPromptName(`${selectedDataset?.name ?? "Brain"} Answer Prompt`); setEditingAnswerPromptText(isStructuredDocSelected ? (promptsContent?.answer_structured_doc ?? "") : (promptsContent?.answer_default ?? "")); setShowCreateAnswerPromptModal(true); }} style={{ width: "100%", background: "none", border: "none", padding: "8px 12px", fontSize: 12, color: "#BC9BFF", fontWeight: 500, display: "flex", alignItems: "center", gap: 8, textAlign: "left", fontFamily: "inherit", cursor: "pointer" }}>
                                <span style={{ width: 14 }}>+</span><span>新建自定义</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      <div style={{ padding: "0 12px 10px", display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ fontSize: 11, color: "rgba(237,236,234,0.45)" }}>{answerPromptNote}</div>
                        <div style={{ position: "relative" }}>
                          <button onClick={() => copyPrompt("answer", answerPromptContent)} style={{ position: "absolute", top: 6, right: 6, background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "2px 8px", fontSize: 10, fontWeight: 500, color: "rgba(237,236,234,0.7)", cursor: "pointer", fontFamily: "inherit" }}>
                            {copiedPromptKey === "answer" ? "已复制 ✓" : "📋 复制"}
                          </button>
                          <pre style={{ margin: 0, maxHeight: 180, overflow: "auto", fontSize: 11, lineHeight: "16px", color: "rgba(237,236,234,0.8)", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: "8px 10px", whiteSpace: "pre-wrap", fontFamily: "ui-monospace, monospace" }}>{answerPromptContent}</pre>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Upload progress */}
            {isUploading && (
              <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.04)", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6510F4" strokeWidth="2" strokeLinecap="round" style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}><path d="M21 12a9 9 0 11-6.219-8.56" /></svg>
                <span style={{ fontSize: 12, color: "#6510F4" }}>Uploading…</span>
              </div>
            )}
            {uploadError && (
              <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(239,68,68,0.3)", background: "rgba(239,68,68,0.1)", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <span style={{ fontSize: 12, color: "#EF4444" }}>{uploadError}</span>
                <button onClick={() => setUploadError(null)} style={{ marginLeft: "auto", background: "none", border: "none", color: "rgba(237,236,234,0.35)", fontSize: 12, cursor: "pointer" }}>✕</button>
              </div>
            )}

            {/* Content */}
            <div style={{ flex: 1, overflowY: "auto" }}>
              {!selectedId ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 8 }}>
                  <svg width="32" height="32" viewBox="0 0 32 32" fill="none"><path d="M4 8a2 2 0 012-2h6l2 3h12a2 2 0 012 2v13a2 2 0 01-2 2H6a2 2 0 01-2-2V8z" stroke="rgba(237,236,234,0.2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  <span style={{ fontSize: 13, color: "rgba(237,236,234,0.35)" }}>Select a brain</span>
                </div>
              ) : docsLoading ? (
                <PageLoading name="Files" />
              ) : selectedDocs.length === 0 ? (
                <div
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 10, cursor: "pointer" }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div style={{ width: 44, height: 44, background: "rgba(188,155,255,0.20)", border: "1px solid rgba(188,155,255,0.35)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <EmptyStateIcon />
                  </div>
                  <span style={{ fontSize: 13, color: "rgba(237,236,234,0.55)", fontWeight: 500 }}>No documents yet</span>
                  <span style={{ fontSize: 12, color: "rgba(237,236,234,0.35)", textAlign: "center", maxWidth: 220 }}>
                    Drag &amp; drop files here, or <span style={{ color: "#6510F4", textDecoration: "underline" }}>browse</span>
                  </span>
                </div>
              ) : (
                <>
                  {selectedDocs.map((doc, i) => {
                    const displayName = decodeFilename(doc.name);
                    const meta = getExtMeta(displayName, doc.extension);
                    return (
                      <div key={doc.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 16px", borderBottom: i < selectedDocs.length - 1 ? "1px solid rgba(255,255,255,0.07)" : "none" }}>
                        <FileIcon {...meta} />
                        <span style={{ flex: 1, fontSize: 13, color: "#EDECEA", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{displayName}</span>
                        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                          <span style={{ fontSize: 11, color: "rgba(237,236,234,0.55)", fontWeight: 500, minWidth: 32, textAlign: "right" }}>{meta.label}</span>
                          <span style={{ fontSize: 11, color: "rgba(237,236,234,0.35)", minWidth: 52, textAlign: "right" }}>{formatSize(doc.size)}</span>
                          <span style={{ fontSize: 11, color: "rgba(237,236,234,0.35)", minWidth: 80, textAlign: "right", whiteSpace: "nowrap" }}>{formatDate(doc.createdAt)}</span>
                          <button
                            onClick={() => setDeleteDocTarget(doc)}
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 500, color: "rgba(237,236,234,0.7)", cursor: "pointer", flexShrink: 0 }}
                            title="Delete file"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </>
              )}
            </div>
          </div>

        </div>
      ) : (
        /* ── Empty state ── */
        <div style={{ flex: 1, display: "flex", flexDirection: "column", paddingInline: 32, paddingBottom: 32 }}>
          <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: 48 }}>
            <div style={{ width: 56, height: 56, background: "rgba(188,155,255,0.20)", border: "1px solid rgba(188,155,255,0.35)", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <EmptyStateIcon />
            </div>
            <span style={{ fontSize: 16, fontWeight: 700, color: "#EDECEA" }}>No brains yet</span>
            <p style={{ fontSize: 14, color: "rgba(237,236,234,0.35)", margin: 0, maxWidth: 340, textAlign: "center" }}>
              Create your first brain to start uploading documents and building knowledge graphs.
            </p>
            <button onClick={() => { trackEvent({ pageName: "Brains", eventName: "dataset_create_modal_opened" }); setShowCreate(true); }}
              className="hover:bg-[#5A0ED6] cursor-pointer"
              style={{ background: "#6510F4", color: "#fff", border: "none", borderRadius: 8, padding: "8px 20px", fontSize: 14, fontWeight: 500, display: "flex", alignItems: "center", gap: 6, marginTop: 12 }}>
              <PlusIcon /> Create brain
            </button>
          </div>
        </div>
      )}

      {/* ── Create custom prompt modal ── */}
      {showCreatePromptModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowCreatePromptModal(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 440, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.5)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Create Custom Prompt</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "rgba(237,236,234,0.55)", textTransform: "uppercase", letterSpacing: 0.3 }}>Name</label>
              <input type="text" value={editingPromptName} onChange={(e) => setEditingPromptName(e.target.value)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "8px 12px", fontSize: 14, fontFamily: "inherit", color: "#EDECEA", outline: "none" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "rgba(237,236,234,0.55)", textTransform: "uppercase", letterSpacing: 0.3 }}>Prompt</label>
              <textarea value={editingPromptText} onChange={(e) => setEditingPromptText(e.target.value)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 12px", fontSize: 13, fontFamily: "inherit", color: "#EDECEA", outline: "none", resize: "vertical", minHeight: 220, lineHeight: "20px" }} />
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowCreatePromptModal(false)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleSavePrompt} disabled={savingPrompt || !editingPromptName.trim()} style={{ background: "#6510F4", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "#fff", fontFamily: "inherit", cursor: "pointer" }}>{savingPrompt ? "Saving…" : "Save prompt"}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Create answer custom prompt modal ── */}
      {showCreateAnswerPromptModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowCreateAnswerPromptModal(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "rgba(15,15,15,0.92)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: 24, width: 440, display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 16px 48px rgba(0,0,0,0.5)" }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EDECEA", margin: 0 }}>Create Answer Prompt</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "rgba(237,236,234,0.55)", textTransform: "uppercase", letterSpacing: 0.3 }}>Name</label>
              <input type="text" value={editingAnswerPromptName} onChange={(e) => setEditingAnswerPromptName(e.target.value)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "8px 12px", fontSize: 14, fontFamily: "inherit", color: "#EDECEA", outline: "none" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: "rgba(237,236,234,0.55)", textTransform: "uppercase", letterSpacing: 0.3 }}>Prompt</label>
              <textarea value={editingAnswerPromptText} onChange={(e) => setEditingAnswerPromptText(e.target.value)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 12px", fontSize: 13, fontFamily: "inherit", color: "#EDECEA", outline: "none", resize: "vertical", minHeight: 220, lineHeight: "20px" }} />
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setShowCreateAnswerPromptModal(false)} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "rgba(237,236,234,0.7)", fontFamily: "inherit", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleSaveAnswerPrompt} disabled={savingAnswerPrompt || !editingAnswerPromptName.trim()} style={{ background: "#6510F4", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 500, color: "#fff", fontFamily: "inherit", cursor: "pointer" }}>{savingAnswerPrompt ? "Saving…" : "Save prompt"}</button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
