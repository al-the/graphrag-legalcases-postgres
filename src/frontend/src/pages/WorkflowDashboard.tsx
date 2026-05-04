import React, { useEffect, useState } from "react";
import { authHeaders } from "../api/authApi";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const SOURCES = ["hansard", "bursa", "dosm", "oecd", "fatf", "bnm", "sc_malaysia"];

export function WorkflowDashboard() {
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadRuns = () => {
    fetch(`${BASE}/api/workflows/runs?limit=20`, { headers: authHeaders() })
      .then((r) => r.json())
      .then(setRuns)
      .catch(console.error);
  };

  useEffect(() => { loadRuns(); }, []);

  const toggleSource = (key: string) => {
    setSelectedSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const triggerIngest = async () => {
    if (!selectedSources.size) return;
    setTriggering(true);
    setMessage(null);
    try {
      const resp = await fetch(`${BASE}/api/workflows/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ source_keys: [...selectedSources] }),
      });
      const data = await resp.json();
      setMessage(`Ingestion queued: task ${data.task_id}`);
      setTimeout(loadRuns, 2000);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setTriggering(false);
    }
  };

  const statusColor: Record<string, string> = {
    done: "#22c55e", running: "#3b82f6", failed: "#ef4444",
    pending: "#64748b", queued: "#f59e0b", partial: "#f97316",
  };

  return (
    <div style={styles.page}>
      <h1 style={styles.heading}>Ingestion Workflows</h1>

      <div style={styles.triggerBox}>
        <h3 style={styles.sub}>Trigger Bulk Ingestion</h3>
        <div style={styles.sourceGrid}>
          {SOURCES.map((key) => (
            <label key={key} style={styles.sourceLabel}>
              <input
                type="checkbox"
                checked={selectedSources.has(key)}
                onChange={() => toggleSource(key)}
                style={{ marginRight: 6 }}
              />
              {key}
            </label>
          ))}
        </div>
        <button
          onClick={triggerIngest}
          disabled={triggering || !selectedSources.size}
          style={styles.triggerBtn}
        >
          {triggering ? "Queueing…" : "Start Ingestion"}
        </button>
        {message && <p style={{ color: "#94a3b8", fontSize: 13, margin: "8px 0 0" }}>{message}</p>}
      </div>

      <h2 style={{ ...styles.sub, marginTop: 32 }}>Recent Runs</h2>
      <button onClick={loadRuns} style={styles.refreshBtn}>Refresh</button>
      <table style={styles.table}>
        <thead>
          <tr>
            {["Run ID", "Type", "Status", "Entities", "Relationships", "Communities", "Started", "Completed"].map((h) => (
              <th key={h} style={styles.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id} style={styles.tr}>
              <td style={styles.td}><code style={{ fontSize: 10 }}>{r.id.slice(0, 8)}…</code></td>
              <td style={styles.td}>{r.run_type}</td>
              <td style={styles.td}>
                <span style={{ background: statusColor[r.status] ?? "#64748b", color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>
                  {r.status}
                </span>
              </td>
              <td style={styles.td}>{r.entity_count ?? "—"}</td>
              <td style={styles.td}>{r.relationship_count ?? "—"}</td>
              <td style={styles.td}>{r.community_count ?? "—"}</td>
              <td style={styles.td}>{r.started_at ? new Date(r.started_at).toLocaleString() : "—"}</td>
              <td style={styles.td}>{r.completed_at ? new Date(r.completed_at).toLocaleString() : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32, maxWidth: 1200, margin: "0 auto", color: "#e2e8f0" },
  heading: { fontSize: 28, fontWeight: 700, marginBottom: 24 },
  sub: { fontSize: 16, fontWeight: 600, color: "#94a3b8", margin: "0 0 12px" },
  triggerBox: { background: "#1e293b", borderRadius: 12, padding: 24, marginBottom: 24 },
  sourceGrid: { display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16 },
  sourceLabel: { display: "flex", alignItems: "center", fontSize: 13, cursor: "pointer", color: "#e2e8f0" },
  triggerBtn: { padding: "10px 24px", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontWeight: 700, cursor: "pointer", fontSize: 14 },
  refreshBtn: { marginBottom: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#94a3b8", cursor: "pointer", fontSize: 13 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: { textAlign: "left", padding: "10px 12px", color: "#64748b", borderBottom: "1px solid #1e293b", fontWeight: 600 },
  tr: { borderBottom: "1px solid #1e293b" },
  td: { padding: "10px 12px" },
};
