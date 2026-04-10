<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import {
  listMedia,
  uploadFile,
  deleteMedia,
  formatBytes,
  assetKind,
  type MediaAsset,
  type MediaKind,
  type MediaKindCategory,
} from "../../lib/media";

const props = defineProps<{
  // When set, shows a modal-style picker. Click on an asset emits `select`.
  pickerMode?: boolean;
  // Filter by a single kind when picking (e.g. images only)
  restrictKind?: MediaKind;
}>();

const emit = defineEmits<{
  (e: "select", asset: MediaAsset): void;
  (e: "close"): void;
}>();

const assets = ref<MediaAsset[]>([]);
const loading = ref(false);
const uploading = ref(false);
const uploadError = ref<string | null>(null);
const search = ref("");
const kindFilter = ref<MediaKind>(props.restrictKind);
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const total = ref(0);
const page = ref(1);
const pageSize = 40;

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
);

async function loadAssets() {
  loading.value = true;
  try {
    const res = await listMedia({
      kind: kindFilter.value,
      search: search.value || undefined,
      page: page.value,
      pageSize,
    });
    assets.value = res.items;
    total.value = res.total;
  } catch (e) {
    console.error("MediaLibrary load failed", e);
  } finally {
    loading.value = false;
  }
}

watch([kindFilter, search], () => {
  page.value = 1;
  loadAssets();
});

async function handleFiles(files: FileList | File[] | null) {
  if (!files || files.length === 0) return;
  uploading.value = true;
  uploadError.value = null;
  try {
    for (const f of Array.from(files)) {
      await uploadFile(f);
    }
    await loadAssets();
  } catch (e: any) {
    uploadError.value = e?.message || "Upload failed";
  } finally {
    uploading.value = false;
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  dragOver.value = false;
  handleFiles(e.dataTransfer?.files || null);
}

function onFileInput(e: Event) {
  const target = e.target as HTMLInputElement;
  handleFiles(target.files);
  target.value = "";
}

async function remove(asset: MediaAsset) {
  if (!confirm(`Delete "${asset.filename}"?`)) return;
  try {
    await deleteMedia(asset.id);
    await loadAssets();
  } catch (e: any) {
    alert(e?.message || "Delete failed");
  }
}

function select(asset: MediaAsset) {
  if (props.pickerMode) {
    emit("select", asset);
  }
}

function isImage(a: MediaAsset): boolean {
  return a.mime_type.startsWith("image/");
}

function isVideo(a: MediaAsset): boolean {
  return a.mime_type.startsWith("video/");
}

function kindOf(a: MediaAsset): MediaKindCategory {
  return assetKind(a);
}

function thumbSrc(a: MediaAsset): string {
  if (a.thumbnail_url) return a.thumbnail_url;
  if (isImage(a)) return a.public_url;
  return "";
}

/** Short label shown on fallback thumbnails for non-image assets. */
function kindLabel(a: MediaAsset): string {
  switch (kindOf(a)) {
    case "videos": return "VIDEO";
    case "audio": return "AUDIO";
    case "documents":
      if (a.mime_type === "application/pdf") return "PDF";
      if (a.mime_type.includes("word")) return "DOC";
      if (a.mime_type.includes("sheet") || a.mime_type.includes("excel")) return "XLS";
      if (a.mime_type.includes("presentation") || a.mime_type.includes("powerpoint")) return "PPT";
      return "DOC";
    case "archives": return "ZIP";
    default: return "FILE";
  }
}

onMounted(loadAssets);
</script>

<template>
  <div class="media-library" :class="{ picker: pickerMode }">
    <header class="ml-header">
      <div class="ml-title">
        <h3>Media Library</h3>
        <span class="ml-count">{{ total }} items</span>
      </div>
      <div class="ml-actions">
        <button
          v-if="pickerMode"
          class="btn-ghost"
          type="button"
          @click="emit('close')"
        >
          Close
        </button>
      </div>
    </header>

    <div class="ml-toolbar">
      <input
        v-model="search"
        type="search"
        placeholder="Search filename…"
        class="ml-search"
      />
      <div class="ml-filters" v-if="!props.restrictKind">
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: !kindFilter }"
          @click="kindFilter = undefined"
        >
          All
        </button>
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: kindFilter === 'images' }"
          @click="kindFilter = 'images'"
        >
          Images
        </button>
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: kindFilter === 'videos' }"
          @click="kindFilter = 'videos'"
        >
          Videos
        </button>
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: kindFilter === 'audio' }"
          @click="kindFilter = 'audio'"
        >
          Audio
        </button>
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: kindFilter === 'documents' }"
          @click="kindFilter = 'documents'"
        >
          Documents
        </button>
        <button
          type="button"
          class="ml-filter-btn"
          :class="{ active: kindFilter === 'archives' }"
          @click="kindFilter = 'archives'"
        >
          Archives
        </button>
      </div>
      <button
        type="button"
        class="btn-primary"
        :disabled="uploading"
        @click="fileInput?.click()"
      >
        {{ uploading ? "Uploading…" : "Upload" }}
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="image/*,video/*,audio/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/zip,application/x-zip-compressed"
        style="display:none"
        @change="onFileInput"
      />
    </div>

    <div
      class="ml-dropzone"
      :class="{ over: dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop="onDrop"
    >
      <div v-if="uploadError" class="ml-error">{{ uploadError }}</div>
      <div class="ml-dz-text">
        Drop files here or click Upload to add to your library
      </div>
    </div>

    <div class="ml-grid" v-if="!loading">
      <div
        v-for="a in assets"
        :key="a.id"
        class="ml-item"
        :class="{ clickable: pickerMode }"
        @click="select(a)"
      >
        <div class="ml-thumb">
          <img
            v-if="thumbSrc(a)"
            :src="thumbSrc(a)"
            :alt="a.alt_text || a.filename"
            loading="lazy"
          />
          <div v-else-if="kindOf(a) === 'videos'" class="ml-thumb-fallback video">
            <!-- Play icon -->
            <svg class="ml-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z"/>
            </svg>
            <span>{{ kindLabel(a) }}</span>
          </div>
          <div v-else-if="kindOf(a) === 'audio'" class="ml-thumb-fallback audio">
            <svg class="ml-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"/>
            </svg>
            <span>{{ kindLabel(a) }}</span>
          </div>
          <div v-else-if="kindOf(a) === 'documents'" class="ml-thumb-fallback doc">
            <svg class="ml-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zM9 12h6m-6 3h6m-6 3h6"/>
            </svg>
            <span>{{ kindLabel(a) }}</span>
          </div>
          <div v-else-if="kindOf(a) === 'archives'" class="ml-thumb-fallback archive">
            <svg class="ml-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"/>
            </svg>
            <span>{{ kindLabel(a) }}</span>
          </div>
          <div v-else class="ml-thumb-fallback doc">
            <span>{{ kindLabel(a) }}</span>
          </div>
        </div>
        <div class="ml-info">
          <div class="ml-name" :title="a.filename">{{ a.filename }}</div>
          <div class="ml-meta">
            <span>{{ formatBytes(a.size_bytes) }}</span>
            <span v-if="a.width && a.height"
              >{{ a.width }}×{{ a.height }}</span
            >
          </div>
        </div>
        <button
          v-if="!pickerMode"
          type="button"
          class="ml-delete"
          @click.stop="remove(a)"
          title="Delete"
        >
          ×
        </button>
      </div>
      <div v-if="assets.length === 0" class="ml-empty">
        No media yet. Upload your first file!
      </div>
    </div>
    <div v-else class="ml-empty">Loading…</div>

    <div class="ml-pager" v-if="totalPages > 1">
      <button
        type="button"
        class="btn-ghost"
        :disabled="page <= 1"
        @click="page--; loadAssets()"
      >
        Prev
      </button>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <button
        type="button"
        class="btn-ghost"
        :disabled="page >= totalPages"
        @click="page++; loadAssets()"
      >
        Next
      </button>
    </div>
  </div>
</template>

<style scoped>
.media-library {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #0f0f0e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  color: #e5e5e5;
  max-height: 100%;
  overflow: auto;
}
.media-library.picker {
  max-height: 80vh;
}
.ml-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ml-title { display: flex; gap: 12px; align-items: baseline; }
.ml-title h3 { margin: 0; color: #f5f5f5; font-size: 16px; }
.ml-count { color: #71717a; font-size: 12px; }
.ml-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ml-search {
  flex: 1;
  min-width: 180px;
  background: #0c0c0b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e5e5e5;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
}
.ml-filters { display: flex; gap: 4px; }
.ml-filter-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #a1a1aa;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.ml-filter-btn.active {
  background: rgba(245, 166, 35, 0.15);
  color: #f5a623;
  border-color: rgba(245, 166, 35, 0.3);
}
.btn-primary {
  background: #f5a623;
  color: #111110;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-ghost {
  background: transparent;
  color: #a1a1aa;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.ml-dropzone {
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}
.ml-dropzone.over {
  border-color: #f5a623;
  background: rgba(245, 166, 35, 0.06);
}
.ml-dz-text { color: #71717a; font-size: 12px; }
.ml-error { color: #ef4444; font-size: 12px; margin-bottom: 8px; }
.ml-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.ml-item {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.ml-item.clickable { cursor: pointer; }
.ml-item.clickable:hover { border-color: rgba(245, 166, 35, 0.4); }
.ml-thumb {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0c0c0b;
  overflow: hidden;
}
.ml-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ml-thumb-fallback {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #71717a;
  font-weight: 600;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.ml-thumb-fallback .ml-icon {
  width: 36px;
  height: 36px;
}
.ml-thumb-fallback.video { color: #2dd4bf; }
.ml-thumb-fallback.audio { color: #a78bfa; }
.ml-thumb-fallback.doc { color: #f5a623; }
.ml-thumb-fallback.archive { color: #fb923c; }
.ml-info {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ml-name {
  font-size: 12px;
  color: #e5e5e5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ml-meta {
  display: flex;
  gap: 8px;
  font-size: 10px;
  color: #71717a;
}
.ml-delete {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #f5f5f5;
  border: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  display: none;
}
.ml-item:hover .ml-delete { display: block; }
.ml-empty {
  grid-column: 1/-1;
  padding: 40px;
  text-align: center;
  color: #71717a;
}
.ml-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px;
  color: #71717a;
  font-size: 12px;
}
</style>
