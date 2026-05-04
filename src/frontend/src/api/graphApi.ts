import { authHeaders } from "./authApi";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface EntityNode {
  id: string;
  title: string;
  entity_type: string;
  description?: string;
  degree?: number;
  frequency?: number;
  community_ids?: string[];
}

export interface RelationshipEdge {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  description?: string;
  weight?: number;
}

export interface SubgraphData {
  nodes: (EntityNode & { depth: number })[];
  edges: RelationshipEdge[];
}

export async function listEntities(params?: {
  entity_type?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<EntityNode[]> {
  const qs = new URLSearchParams();
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.q) qs.set("q", params.q);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const resp = await fetch(`${BASE}/api/graph/entities?${qs}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Failed to fetch entities");
  return resp.json();
}

export async function getEntity(id: string): Promise<EntityNode & { relationships: RelationshipEdge[] }> {
  const resp = await fetch(`${BASE}/api/graph/entities/${id}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Entity not found");
  return resp.json();
}

export async function getSubgraph(
  entityId: string,
  hops: number = 2
): Promise<SubgraphData> {
  const resp = await fetch(
    `${BASE}/api/graph/subgraph?entity_id=${entityId}&hops=${hops}`,
    { headers: authHeaders() }
  );
  if (!resp.ok) throw new Error("Failed to fetch subgraph");
  return resp.json();
}

export async function searchEntities(
  q: string,
  entity_types?: string
): Promise<EntityNode[]> {
  const qs = new URLSearchParams({ q });
  if (entity_types) qs.set("entity_types", entity_types);
  const resp = await fetch(`${BASE}/api/graph/search?${qs}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Search failed");
  return resp.json();
}

export async function listCommunities(level?: number): Promise<any[]> {
  const qs = new URLSearchParams();
  if (level !== undefined) qs.set("level", String(level));
  const resp = await fetch(`${BASE}/api/graph/communities?${qs}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Failed to fetch communities");
  return resp.json();
}
