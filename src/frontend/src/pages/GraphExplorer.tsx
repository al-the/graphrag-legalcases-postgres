import React, { useCallback, useEffect, useState } from "react";
import { GraphCanvas } from "../components/GraphViewer/GraphCanvas";
import { GraphFilters } from "../components/GraphViewer/GraphFilters";
import { EntityDetail } from "../components/GraphViewer/EntityDetail";
import { toSigmaGraph } from "../components/GraphViewer/graph-adapter";
import { MY_ENTITY_COLORS } from "../components/GraphViewer/constants";
import { listEntities, getSubgraph, searchEntities } from "../api/graphApi";
import type { EntityNode, RelationshipEdge } from "../api/graphApi";

export function GraphExplorer() {
  const [nodes, setNodes] = useState<EntityNode[]>([]);
  const [edges, setEdges] = useState<RelationshipEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(Object.keys(MY_ENTITY_COLORS).filter((k) => k !== "DEFAULT"))
  );
  const [searchQuery, setSearchQuery] = useState("");

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const allNodes = await listEntities({ limit: 200 });
      const filtered = selectedTypes.size
        ? allNodes.filter((n) => selectedTypes.has(n.entity_type?.toUpperCase() ?? ""))
        : allNodes;
      setNodes(filtered);
      setEdges([]);  // edges loaded on demand via subgraph
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedTypes]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  const handleNodeClick = useCallback(async (nodeId: string) => {
    setSelectedEntity(nodeId);
    try {
      const sg = await getSubgraph(nodeId, 1);
      setEdges(sg.edges);
    } catch (_) {}
  }, []);

  const handleTypeToggle = (type: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  };

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2) { loadGraph(); return; }
    try {
      const results = await searchEntities(q);
      setNodes(results);
    } catch (_) {}
  };

  const { nodes: sNodes, edges: sEdges } = toSigmaGraph(nodes, edges);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 64px)", background: "#0f172a" }}>
      <GraphFilters
        selectedTypes={selectedTypes}
        onTypeToggle={handleTypeToggle}
        searchQuery={searchQuery}
        onSearchChange={handleSearch}
      />

      <div style={{ flex: 1, position: "relative" }}>
        {loading && (
          <div style={overlayStyle}>
            <span style={{ color: "#94a3b8" }}>Loading knowledge graph…</span>
          </div>
        )}
        {error && (
          <div style={{ ...overlayStyle, color: "#f87171" }}>{error}</div>
        )}
        {!loading && !error && (
          <GraphCanvas
            nodes={sNodes}
            edges={sEdges}
            onNodeClick={handleNodeClick}
            highlightedId={selectedEntity ?? undefined}
          />
        )}
      </div>

      <EntityDetail
        entityId={selectedEntity}
        onClose={() => setSelectedEntity(null)}
        onNavigate={handleNodeClick}
      />
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
