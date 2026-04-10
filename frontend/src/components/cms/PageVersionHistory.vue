<script setup lang="ts">
/**
 * PageVersionHistory — modal listing page version snapshots with
 * preview and restore actions.
 */
import { ref, onMounted } from "vue";
import { apiFetch } from "../../lib/api";

type VersionSummary = {
  id: number;
  version_num: number;
  title: string;
  created_by: number | null;
  created_at: string;
  note: string | null;
};

type VersionFull = VersionSummary & {
  page_id: number;
  content_html: string;
  blocks: any[] | null;
};

const props = defineProps<{ pageId: number }>();
const emit = defineEmits<{
  (e: "close"): void;
  (e: "restored"): void;
}>();

const versions = ref<VersionSummary[]>([]);
const loading = ref(true);
const selected = ref<VersionFull | null>(null);
const restoring = ref(false);

async function loadVersions() {
  loading.value = true;
  try {
    versions.value = await apiFetch<VersionSummary[]>(
      `/api/v1/cms/pages/${props.pageId}/versions`,
    );
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function viewVersion(v: VersionSummary) {
  try {
    selected.value = await apiFetch<VersionFull>(
      `/api/v1/cms/pages/${props.pageId}/versions/${v.version_num}`,
    );
  } catch (e) {
    console.error(e);
  }
}

async function restore() {
  if (!selected.value) return;
  if (
    !confirm(
      `Restore version ${selected.value.version_num}? Current state will be saved as a new version first.`,
    )
  ) {
    return;
  }
  restoring.value = true;
  try {
    await apiFetch(
      `/api/v1/cms/pages/${props.pageId}/versions/${selected.value.version_num}/restore`,
      { method: "POST" },
    );
    emit("restored");
    emit("close");
  } catch (e: any) {
    alert(e?.message || "Restore failed");
  } finally {
    restoring.value = false;
  }
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

onMounted(loadVersions);
</script>

<template>
  <div class="vh-modal" @click.self="emit('close')">
    <div class="vh-body">
      <header class="vh-head">
        <h3>Version history</h3>
        <button type="button" class="btn-ghost" @click="emit('close')">Close</button>
      </header>
      <div class="vh-content">
        <aside class="vh-list">
          <div v-if="loading" class="vh-empty">Loading…</div>
          <div v-else-if="versions.length === 0" class="vh-empty">No versions yet.</div>
          <button
            v-for="v in versions"
            :key="v.id"
            type="button"
            class="vh-row"
            :class="{ active: selected?.version_num === v.version_num }"
            @click="viewVersion(v)"
          >
            <div class="vh-row-title">v{{ v.version_num }} — {{ v.title }}</div>
            <div class="vh-row-meta">
              <span>{{ fmtDate(v.created_at) }}</span>
              <span v-if="v.note" class="vh-note">{{ v.note }}</span>
            </div>
          </button>
        </aside>
        <main class="vh-preview">
          <div v-if="!selected" class="vh-empty">
            Select a version to preview.
          </div>
          <div v-else>
            <div class="vh-meta-bar">
              <div>
                <strong>v{{ selected.version_num }}</strong> — {{ selected.title }}
              </div>
              <button
                type="button"
                class="btn-primary"
                :disabled="restoring"
                @click="restore"
              >
                {{ restoring ? "Restoring…" : "Restore this version" }}
              </button>
            </div>
            <div class="vh-frame" v-html="selected.content_html"></div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vh-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.vh-body {
  width: 100%;
  max-width: 1100px;
  max-height: 90vh;
  background: #0f0f0e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.vh-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.vh-head h3 {
  margin: 0;
  color: #f5f5f5;
  font-size: 16px;
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
.vh-content {
  display: grid;
  grid-template-columns: 260px 1fr;
  flex: 1;
  overflow: hidden;
}
.vh-list {
  overflow-y: auto;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding: 8px;
}
.vh-row {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  color: #e5e5e5;
  margin-bottom: 4px;
}
.vh-row:hover {
  background: rgba(255, 255, 255, 0.04);
}
.vh-row.active {
  background: rgba(245, 166, 35, 0.1);
  border-color: rgba(245, 166, 35, 0.3);
}
.vh-row-title {
  font-size: 13px;
  font-weight: 600;
}
.vh-row-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #71717a;
  margin-top: 4px;
}
.vh-note {
  color: #2dd4bf;
}
.vh-preview {
  overflow-y: auto;
  padding: 16px 20px;
  background: #0c0c0b;
}
.vh-meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  color: #e5e5e5;
  font-size: 13px;
}
.vh-frame {
  background: #111110;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  min-height: 200px;
  color: #e5e5e5;
}
.vh-empty {
  padding: 32px;
  text-align: center;
  color: #71717a;
  font-size: 13px;
}
</style>
