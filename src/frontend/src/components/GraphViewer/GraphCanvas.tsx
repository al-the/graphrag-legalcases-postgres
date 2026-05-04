import React, { useEffect, useRef } from "react";
import Sigma from "sigma";
import Graph from "graphology";
import { circular } from "graphology-layout";
import forceAtlas2 from "graphology-layout-forceatlas2";
import type { SigmaNode, SigmaEdge } from "./graph-adapter";

interface Props {
  nodes: SigmaNode[];
  edges: SigmaEdge[];
  onNodeClick?: (nodeId: string) => void;
  highlightedId?: string;
}

export function GraphCanvas({ nodes, edges, onNodeClick, highlightedId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new Graph();
    graphRef.current = graph;

    nodes.forEach((n) => {
      if (!graph.hasNode(n.key)) {
        graph.addNode(n.key, {
          label: n.label,
          x: n.x,
          y: n.y,
          size: n.size,
          color: n.color,
          entity_type: n.entity_type,
          description: n.description,
        });
      }
    });

    edges.forEach((e) => {
      if (!graph.hasEdge(e.key) && graph.hasNode(e.source) && graph.hasNode(e.target)) {
        graph.addEdgeWithKey(e.key, e.source, e.target, {
          label: e.label,
          color: e.color,
          size: Math.max(1, e.weight),
        });
      }
    });

    // Layout
    circular.assign(graph);
    if (graph.order > 0) {
      const settings = forceAtlas2.inferSettings(graph);
      forceAtlas2.assign(graph, { settings, iterations: 150 });
    }

    const renderer = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      defaultEdgeColor: "#cbd5e1",
      defaultNodeColor: "#94a3b8",
      nodeReducer: (node, data) => ({
        ...data,
        highlighted: node === highlightedId,
        size: node === highlightedId ? data.size * 1.5 : data.size,
      }),
    });

    renderer.on("clickNode", ({ node }) => onNodeClick?.(node));
    sigmaRef.current = renderer;

    return () => {
      renderer.kill();
      sigmaRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  // Update highlight without full re-render
  useEffect(() => {
    sigmaRef.current?.refresh();
  }, [highlightedId]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", background: "#0f172a" }}
    />
  );
}
