const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface UserRead {
  id: string;
  email: string;
  display_name?: string;
  is_admin: boolean;
  is_active: boolean;
}

function getToken(): string | null {
  return localStorage.getItem("kg_token");
}

export function setToken(token: string): void {
  localStorage.setItem("kg_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("kg_token");
}

export function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username: email, password });
  const resp = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!resp.ok) throw new Error("Invalid credentials");
  const data = await resp.json();
  return data.access_token;
}

export async function register(
  email: string,
  password: string,
  displayName?: string
): Promise<UserRead> {
  const resp = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail ?? "Registration failed");
  }
  return resp.json();
}

export async function getMe(): Promise<UserRead> {
  const resp = await fetch(`${BASE}/auth/users/me`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error("Not authenticated");
  return resp.json();
}
