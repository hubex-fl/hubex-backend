import { apiFetch } from "./api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CustomEndpoint {
  id: number;
  name: string;
  path: string;
  method: "GET" | "POST";
  description: string | null;
  source_config: Record<string, unknown>;
  auth_type: "api_key" | "bearer" | "none";
  api_key: string | null;
  rate_limit: number;
  write_enabled: boolean;
  enabled: boolean;
  request_count: number;
  last_called_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface EndpointCreate {
  name: string;
  path: string;
  method: "GET" | "POST";
  description?: string | null;
  source_config?: Record<string, unknown>;
  auth_type?: "api_key" | "bearer" | "none";
  rate_limit?: number;
  write_enabled?: boolean;
  enabled?: boolean;
}

export interface EndpointUpdate {
  name?: string;
  description?: string | null;
  source_config?: Record<string, unknown>;
  auth_type?: "api_key" | "bearer" | "none";
  rate_limit?: number;
  write_enabled?: boolean;
  enabled?: boolean;
}

// ── API ──────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/custom-endpoints";

export async function listEndpoints(): Promise<CustomEndpoint[]> {
  return apiFetch<CustomEndpoint[]>(BASE);
}

export async function getEndpoint(id: number): Promise<CustomEndpoint> {
  return apiFetch<CustomEndpoint>(`${BASE}/${id}`);
}

export async function createEndpoint(data: EndpointCreate): Promise<CustomEndpoint> {
  return apiFetch<CustomEndpoint>(BASE, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateEndpoint(id: number, data: EndpointUpdate): Promise<CustomEndpoint> {
  return apiFetch<CustomEndpoint>(`${BASE}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteEndpoint(id: number): Promise<void> {
  await apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" });
}

export async function previewEndpoint(id: number): Promise<unknown> {
  return apiFetch<unknown>(`${BASE}/${id}/preview`);
}

export async function testEndpoint(id: number): Promise<unknown> {
  return apiFetch<unknown>(`${BASE}/${id}/test`, { method: "POST" });
}

export async function regenerateKey(id: number): Promise<{ api_key: string }> {
  return apiFetch<{ api_key: string }>(`${BASE}/${id}/regenerate-key`, { method: "POST" });
}
