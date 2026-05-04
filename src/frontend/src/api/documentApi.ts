import { authHeaders } from "./authApi";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface DocumentRecord {
  id: string;
  source_id: string;
  doc_type: string;
  title: string;
  language: string;
  source_url?: string;
  ocr_status: string;
  graphrag_status: string;
  page_count?: number;
  publication_date?: string;
  created_at: string;
}

export async function addFromUrl(
  url: string,
  overrides?: { doc_type?: string; source_key?: string; title?: string }
): Promise<DocumentRecord> {
  const resp = await fetch(`${BASE}/api/documents/from-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ url, ...overrides }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to add document");
  }
  return resp.json();
}

export async function uploadFile(
  file: File,
  doc_type: string = "policy_paper"
): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(
    `${BASE}/api/documents/upload?doc_type=${doc_type}`,
    { method: "POST", headers: authHeaders(), body: form }
  );
  if (!resp.ok) throw new Error("Upload failed");
  return resp.json();
}

export async function listDocuments(params?: {
  source_key?: string;
  doc_type?: string;
  ocr_status?: string;
  limit?: number;
  offset?: number;
}): Promise<DocumentRecord[]> {
  const qs = new URLSearchParams();
  if (params?.source_key) qs.set("source_key", params.source_key);
  if (params?.doc_type) qs.set("doc_type", params.doc_type);
  if (params?.ocr_status) qs.set("ocr_status", params.ocr_status);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const resp = await fetch(`${BASE}/api/documents?${qs}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Failed to list documents");
  return resp.json();
}

export async function getDocument(id: string): Promise<DocumentRecord> {
  const resp = await fetch(`${BASE}/api/documents/${id}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Document not found");
  return resp.json();
}
