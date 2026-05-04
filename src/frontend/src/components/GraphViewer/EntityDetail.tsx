import React, { useEffect, useState } from "react";
import { getEntity } from "../../api/graphApi";
import { entityColor } from "./constants";

interface Props {
  entityId: string | null;
  onClose: () => void;
  onNavigate: (id: string) => void;
}

export function EntityDetail({ entityId, onClose, onNavigate }: Props) {
  const [entity, setEntity] = useState<any>(null);

  useEffect(() => {
    if (!entityId) return;
    setEntity(null);
    getEntity(entityId).then(setEntity).catch(console.error);
  }, [entityId]);

  if (!entityId) return null;

  return (
    <div style={styles.panel}>
      <button onClick={onClose} style={styles.close}>✕</button>
      {!entity ? (
        <p style={{ color: "#94a3b8" }}>Loading…</p>
      ) : (
        <>
          <span
            style={{
              display: "inline-block",
              background: entityColor(entity.entity_type),
              color: "#fff",
              fontSize: 11,
              borderRadius: 4,
              padding: "2px 8px",
              marginBottom: 8,
            }}
          >
            {entity.entity_type}
          </span>
          <h2 style={styles.title}>{entity.title}</h2>
          {entity.description && (
            <p style={styles.description}>{entity.description}</p>
          )}
          <p style={styles.meta}>Degree: {entity.degree ?? 0}</p>

          {entity.relationships?.length > 0 && (
            <>
              <h4 style={styles.sectionTitle}>Related Entities</h4>
              <ul style={styles.relList}>
                {entity.relationships.slice(0, 15).map((r: any) => (
                  <li key={r.id} style={styles.relItem}>
                    <button
                      onClick={() =>
                        onNavigate(
                          r.source_entity_id === entityId
                            ? r.target_entity_id
                            : r.source_entity_id
                        )
                      }
                      style={styles.relButton}
                    >
                      {r.related_title}
                      <span style={{ color: "#64748b", fontSize: 11, marginLeft: 4 }}>
                        ({r.related_type})
                      </span>
                    </button>
                    {r.description && (
                      <p style={styles.relDesc}>{r.description.slice(0, 80)}</p>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 320,
    background: "#1e293b",
    color: "#e2e8f0",
    padding: 20,
    overflowY: "auto",
    position: "relative",
  },
  close: {
    position: "absolute",
    top: 12,
    right: 12,
    background: "none",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 16,
  },
  title: { margin: "0 0 8px", fontSize: 18, fontWeight: 700 },
  description: { fontSize: 13, color: "#94a3b8", lineHeight: 1.5 },
  meta: { fontSize: 12, color: "#64748b" },
  sectionTitle: { fontSize: 13, fontWeight: 600, color: "#94a3b8", margin: "16px 0 8px" },
  relList: { listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 },
  relItem: { borderLeft: "2px solid #334155", paddingLeft: 10 },
  relButton: {
    background: "none",
    border: "none",
    color: "#e2e8f0",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    padding: 0,
    textAlign: "left",
  },
  relDesc: { margin: "2px 0 0", fontSize: 11, color: "#64748b" },
};
