import React, { useEffect, useRef, useState } from "react";
import { listDocuments, addFromUrl, uploadFile } from "../api/documentApi";
import type { DocumentRecord } from "../api/documentApi";

const STATUS_COLORS: Record<string, string> = {
  done: "#22c55e",
  queued: "#f59e0b",
  processing: "#3b82f6",
  failed: "#ef4444",
  pending: "#64748b",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      style={{
        background: STATUS_COLORS[status] ?? "#64748b",
        color: "#fff",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {status}
    </span>
  );
}

export function DocumentBrowser() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [urlInput, setUrlInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = () => {
    setLoading(true);
    listDocuments({ limit: 100 })
      .then(setDocs)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const handleAddUrl = async () => {
    if (!urlInput.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      const doc = await addFromUrl(urlInput.trim());
      setDocs((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
      setUrlInput("");
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAdding(true);
    setAddError(null);
    try {
      const doc = await uploadFile(file);
      setDocs((prev) => [doc, ...prev]);
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setAdding(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div style={styles.page}>
      <h1 style={styles.heading}>Documents</h1>

      {/* Add document */}
      <div style={styles.addBox}>
        <h3 style={styles.subheading}>Add a PDF</h3>
        <div style={styles.urlRow}>
          <input
            type="url"
            placeholder="Paste a PDF URL (Hansard, Bursa, DOSM, OECD, FATF…)"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
            style={styles.urlInput}
          />
          <button onClick={handleAddUrl} disabled={adding} style={styles.addBtn}>
            {adding ? "Adding…" : "Add URL"}
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
          <span style={{ color: "#64748b", fontSize: 13 }}>or</span>
          <input ref={fileRef} type="file" accept=".pdf" onChange={handleUpload} style={{ display: "none" }} />
          <button onClick={() => fileRef.current?.click()} style={styles.uploadBtn}>
            Upload PDF
          </button>
        </div>
        {addError && <p style={{ color: "#ef4444", fontSize: 13, margin: "8px 0 0" }}>{addError}</p>}
      </div>

      {/* Document list */}
      {loading ? (
        <p style={{ color: "#64748b" }}>Loading…</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              {["Title", "Type", "Language", "OCR", "GraphRAG", "Pages", "Added"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id} style={styles.row}>
                <td style={styles.td}>
                  <a href={doc.source_url ?? "#"} target="_blank" rel="noreferrer" style={styles.link}>
                    {doc.title.slice(0, 60)}{doc.title.length > 60 ? "…" : ""}
                  </a>
                </td>
                <td style={styles.td}><code style={styles.code}>{doc.doc_type}</code></td>
                <td style={styles.td}>{doc.language}</td>
                <td style={styles.td}><StatusBadge status={doc.ocr_status} /></td>
                <td style={styles.td}><StatusBadge status={doc.graphrag_status} /></td>
                <td style={styles.td}>{doc.page_count ?? "—"}</td>
                <td style={styles.td}>{new Date(doc.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <button onClick={refresh} style={styles.refreshBtn}>Refresh</button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32, maxWidth: 1100, margin: "0 auto", color: "#e2e8f0" },
  heading: { fontSize: 28, fontWeight: 700, marginBottom: 24 },
  subheading: { margin: "0 0 12px", fontSize: 15, fontWeight: 600, color: "#94a3b8" },
  addBox: {
    background: "#1e293b",
    borderRadius: 12,
    padding: 24,
    marginBottom: 32,
  },
  urlRow: { display: "flex", gap: 12 },
  urlInput: {
    flex: 1,
    padding: "10px 14px",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "#0f172a",
    color: "#e2e8f0",
    fontSize: 14,
  },
  addBtn: {
    padding: "10px 20px",
    borderRadius: 8,
    border: "none",
    background: "#6366f1",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 14,
  },
  uploadBtn: {
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "transparent",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 13,
  },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: { textAlign: "left", padding: "10px 12px", color: "#64748b", borderBottom: "1px solid #1e293b", fontWeight: 600 },
  row: { borderBottom: "1px solid #1e293b" },
  td: { padding: "12px 12px", verticalAlign: "top" },
  link: { color: "#818cf8", textDecoration: "none" },
  code: { background: "#0f172a", padding: "2px 6px", borderRadius: 4, fontSize: 11 },
  refreshBtn: {
    marginTop: 16,
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "transparent",
    color: "#94a3b8",
    cursor: "pointer",
  },
};
