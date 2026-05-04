import type { EntityNode, RelationshipEdge } from "../../api/graphApi";
import { entityColor, NODE_SIZE_BASE, NODE_SIZE_SCALE } from "./constants";

export interface SigmaNode {
  key: string;
  label: string;
  x: number;
  y: number;
  size: number;
  color: string;
  entity_type: string;
  description?: string;
  degree: number;
}

export interface SigmaEdge {
  key: string;
  source: string;
  target: string;
  label?: string;
  weight: number;
  color: string;
}

export function toSigmaGraph(
  nodes: EntityNode[],
  edges: RelationshipEdge[]
): { nodes: SigmaNode[]; edges: SigmaEdge[] } {
  const sigmaNodes: SigmaNode[] = nodes.map((n, i) => ({
    key: n.id,
    label: n.title,
    // Initial positions — ForceAtlas2 will reposition
    x: Math.cos((2 * Math.PI * i) / nodes.length),
    y: Math.sin((2 * Math.PI * i) / nodes.length),
    size: NODE_SIZE_BASE + (n.degree ?? 0) * NODE_SIZE_SCALE,
    color: entityColor(n.entity_type),
    entity_type: n.entity_type,
    description: n.description,
    degree: n.degree ?? 0,
  }));

  const nodeIds = new Set(nodes.map((n) => n.id));
  const sigmaEdges: SigmaEdge[] = edges
    .filter((e) => nodeIds.has(e.source_entity_id) && nodeIds.has(e.target_entity_id))
    .map((e) => ({
      key: e.id,
      source: e.source_entity_id,
      target: e.target_entity_id,
      label: e.description?.slice(0, 60),
      weight: e.weight ?? 1,
      color: "#cbd5e1",
    }));

  return { nodes: sigmaNodes, edges: sigmaEdges };
}
