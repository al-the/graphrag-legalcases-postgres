import React from "react";
import { MY_ENTITY_COLORS } from "./constants";

interface Props {
  selectedTypes: Set<string>;
  onTypeToggle: (type: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function GraphFilters({
  selectedTypes,
  onTypeToggle,
  searchQuery,
  onSearchChange,
}: Props) {
  const types = Object.keys(MY_ENTITY_COLORS).filter((k) => k !== "DEFAULT");

  return (
    <div className="graph-filters" style={styles.container}>
      <h3 style={styles.heading}>Filter</h3>

      <input
        type="search"
        placeholder="Search entities…"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        style={styles.search}
      />

      <div style={styles.typeList}>
        {types.map((type) => (
          <label key={type} style={styles.typeLabel}>
            <input
              type="checkbox"
              checked={selectedTypes.has(type)}
              onChange={() => onTypeToggle(type)}
              style={{ marginRight: 6 }}
            />
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: MY_ENTITY_COLORS[type],
                marginRight: 6,
              }}
            />
            {type}
          </label>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: 220,
    background: "#1e293b",
    color: "#e2e8f0",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 12,
    overflowY: "auto",
  },
  heading: { margin: 0, fontSize: 14, fontWeight: 600, color: "#94a3b8" },
  search: {
    width: "100%",
    padding: "6px 8px",
    borderRadius: 6,
    border: "1px solid #334155",
    background: "#0f172a",
    color: "#e2e8f0",
    fontSize: 13,
  },
  typeList: { display: "flex", flexDirection: "column", gap: 8 },
  typeLabel: { display: "flex", alignItems: "center", fontSize: 12, cursor: "pointer" },
};
