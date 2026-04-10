/**
 * Media Library API client — upload, list, delete media assets.
 */
import { apiFetch, getToken } from "./api";

export type MediaAsset = {
  id: number;
  filename: string;
  public_url: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  alt_text: string | null;
  thumbnail_url: string | null;
  kind?: MediaKindCategory;
  created_at: string;
};

export type MediaListResponse = {
  items: MediaAsset[];
  total: number;
  page: number;
  page_size: number;
};

export type MediaKindCategory =
  | "images"
  | "videos"
  | "audio"
  | "documents"
  | "archives"
  | "other";

export type MediaKind =
  | "images"
  | "videos"
  | "audio"
  | "documents"
  | "archives"
  | undefined;

/** Classify a MediaAsset by mime type client-side as a fallback when `kind` is absent. */
export function assetKind(a: MediaAsset): MediaKindCategory {
  if (a.kind) return a.kind;
  const m = a.mime_type || "";
  if (m.startsWith("image/")) return "images";
  if (m.startsWith("video/")) return "videos";
  if (m.startsWith("audio/")) return "audio";
  if (
    m === "application/pdf" ||
    m.startsWith("application/vnd.openxmlformats-") ||
    m === "application/msword" ||
    m === "application/vnd.ms-excel" ||
    m === "application/vnd.ms-powerpoint"
  )
    return "documents";
  if (
    m === "application/zip" ||
    m === "application/x-zip-compressed" ||
    m === "application/x-tar" ||
    m === "application/gzip" ||
    m === "application/x-7z-compressed"
  )
    return "archives";
  return "other";
}

export async function uploadFile(
  file: File,
  altText?: string,
): Promise<MediaAsset> {
  const form = new FormData();
  form.append("file", file);
  if (altText) form.append("alt_text", altText);
  const token = getToken();
  const res = await fetch("/api/v1/media/upload", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`Upload failed: ${res.status} ${msg || res.statusText}`);
  }
  return res.json();
}

export async function listMedia(params: {
  kind?: MediaKind;
  search?: string;
  page?: number;
  pageSize?: number;
} = {}): Promise<MediaListResponse> {
  const q = new URLSearchParams();
  if (params.kind) q.set("kind", params.kind);
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.pageSize) q.set("page_size", String(params.pageSize));
  const qs = q.toString();
  return apiFetch<MediaListResponse>(`/api/v1/media${qs ? `?${qs}` : ""}`);
}

export async function getMedia(id: number): Promise<MediaAsset> {
  return apiFetch<MediaAsset>(`/api/v1/media/${id}`);
}

export async function updateMedia(
  id: number,
  data: { alt_text?: string | null; filename?: string | null },
): Promise<MediaAsset> {
  return apiFetch<MediaAsset>(`/api/v1/media/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteMedia(id: number): Promise<void> {
  const token = getToken();
  const res = await fetch(`/api/v1/media/${id}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Delete failed: ${res.status}`);
  }
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
}
