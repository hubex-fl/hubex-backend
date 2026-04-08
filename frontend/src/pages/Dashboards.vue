<template>
  <div class="dashboards-page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('nav.dashboards') }}</h1>
        <p class="page-sub">Visualize and control your devices</p>
      </div>
      <UButton icon="M12 4.5v15m7.5-7.5h-15" @click="showCreateModal = true">
        New Dashboard
      </UButton>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <USkeleton v-for="i in 3" :key="i" class="h-32" />
    </div>

    <!-- Empty state -->
    <UEmpty
      v-else-if="!dashboards.length"
      title="No dashboards yet"
      description="Create your first dashboard to start visualizing your devices"
      icon="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z"
    >
      <UButton @click="showCreateModal = true">Create Dashboard</UButton>
    </UEmpty>

    <!-- Dashboard grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="db in dashboards"
        :key="db.id"
        class="db-card"
        @click="router.push(`/dashboards/${db.id}`)"
      >
        <div class="db-card-header">
          <div class="db-card-icon">📊</div>
          <div class="db-card-badges">
            <UBadge v-if="db.is_default" color="amber" size="xs">Default</UBadge>
            <UBadge :color="sharingColor(db.sharing_mode)" size="xs">{{ db.sharing_mode }}</UBadge>
          </div>
        </div>
        <h3 class="db-card-name">{{ db.name }}</h3>
        <p v-if="db.description" class="db-card-desc">{{ db.description }}</p>
        <div class="db-card-footer">
          <span class="db-widget-count">{{ db.widget_count }} widget{{ db.widget_count !== 1 ? 's' : '' }}</span>
          <span class="db-updated">{{ relativeTime(db.updated_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
          <div class="modal-box">
            <h2 class="modal-title">New Dashboard</h2>

            <!-- Step 1: Template selection -->
            <div v-if="createStep === 1">
              <p class="modal-label">Choose a template</p>
              <div class="template-grid">
                <div
                  v-for="tpl in DASHBOARD_TEMPLATES"
                  :key="tpl.id"
                  class="tpl-card"
                  :class="{ selected: selectedTemplate === tpl.id }"
                  @click="selectedTemplate = tpl.id"
                >
                  <span class="tpl-icon">{{ tpl.icon }}</span>
                  <span class="tpl-name">{{ tpl.name }}</span>
                  <span class="tpl-desc">{{ tpl.description }}</span>
                </div>
              </div>
              <div class="modal-actions">
                <UButton variant="ghost" @click="showCreateModal = false">{{ t('common.cancel') }}</UButton>
                <UButton @click="createStep = 2">{{ t('common.next') }} →</UButton>
              </div>
            </div>

            <!-- Step 2: Name + options -->
            <div v-else-if="createStep === 2" class="form-fields">
              <div class="field">
                <label class="field-label">Name *</label>
                <input
                  v-model="newName"
                  class="field-input"
                  placeholder="My Dashboard"
                  @keydown.enter="submitCreate"
                  autofocus
                />
              </div>
              <div class="field">
                <label class="field-label">Description</label>
                <input v-model="newDesc" class="field-input" placeholder="Optional description" />
              </div>
              <div class="field-row">
                <label class="check-label">
                  <input type="checkbox" v-model="newIsDefault" class="check-input" />
                  Set as default dashboard
                </label>
              </div>
              <p v-if="createError" class="field-error">{{ createError }}</p>
              <div class="modal-actions">
                <UButton variant="ghost" @click="createStep = 1">← {{ t('common.back') }}</UButton>
                <UButton :loading="creating" :disabled="!newName.trim()" @click="submitCreate">
                  {{ t('common.create') }}
                </UButton>
              </div>
            </div>

          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import {
  listDashboards,
  createDashboard,
  addWidget,
  DASHBOARD_TEMPLATES,
  type DashboardSummary,
} from "../lib/dashboards";

const router = useRouter();
const { t } = useI18n();

const dashboards = ref<DashboardSummary[]>([]);
const loading = ref(true);

const showCreateModal = ref(false);
const createStep = ref(1);
const selectedTemplate = ref("blank");
const newName = ref("");
const newDesc = ref("");
const newIsDefault = ref(false);
const creating = ref(false);
const createError = ref("");

onMounted(load);

async function load() {
  loading.value = true;
  try {
    dashboards.value = await listDashboards();
  } catch {
    dashboards.value = [];
  } finally {
    loading.value = false;
  }
}

async function submitCreate() {
  if (!newName.value.trim()) return;
  creating.value = true;
  createError.value = "";
  try {
    const db = await createDashboard({
      name: newName.value.trim(),
      description: newDesc.value || null,
      is_default: newIsDefault.value,
    });

    // Add template widgets (errors are non-fatal — dashboard is already created)
    const tpl = DASHBOARD_TEMPLATES.find((t) => t.id === selectedTemplate.value);
    if (tpl && tpl.widgets.length) {
      let col = 0;
      let row = 0;
      let rowMaxH = 0;
      for (const w of tpl.widgets) {
        const spanW = w.grid_span_w ?? 4;
        const spanH = w.grid_span_h ?? 3;
        // Wrap to next row if widget won't fit in remaining columns
        if (col + spanW > 12) {
          col = 0;
          row += rowMaxH || spanH;
          rowMaxH = 0;
        }
        rowMaxH = Math.max(rowMaxH, spanH);
        try {
          await addWidget(db.id, {
            widget_type: w.widget_type,
            label: w.label ?? null,
            variable_key: w.variable_key ?? null,
            device_uid: w.device_uid ?? null,
            unit: w.unit ?? null,
            min_value: w.min_value ?? null,
            max_value: w.max_value ?? null,
            display_config: w.display_config ?? null,
            grid_col: col,
            grid_row: row,
            grid_span_w: spanW,
            grid_span_h: spanH,
          });
        } catch {
          // Skip failed widget — dashboard still usable
          console.warn(`Failed to add template widget "${w.label}"`);
        }
        col += spanW;
      }
    }

    showCreateModal.value = false;
    createStep.value = 1;
    newName.value = "";
    newDesc.value = "";
    newIsDefault.value = false;

    router.push(`/dashboards/${db.id}`);
  } catch (e: unknown) {
    const info = parseApiError(e);
    createError.value = mapErrorToUserText(info, "Could not create dashboard. Please check your input.");
  } finally {
    creating.value = false;
  }
}

function sharingColor(mode: string) {
  if (mode === "public") return "green";
  if (mode === "org") return "blue";
  return "default";
}

function relativeTime(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
</script>

<style scoped>
.dashboards-page { padding: 24px; max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}
.page-title { font-size: 22px; font-weight: 700; color: var(--text-base); }
.page-sub { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

/* ── Dashboard cards ─────────────────────────────────── */
.db-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.db-card:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
}
.db-card-header { display: flex; align-items: center; justify-content: space-between; }
.db-card-icon { font-size: 22px; }
.db-card-badges { display: flex; gap: 4px; }
.db-card-name { font-size: 15px; font-weight: 600; color: var(--text-base); }
.db-card-desc { font-size: 12px; color: var(--text-muted); }
.db-card-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
}
.db-widget-count { font-weight: 500; }

/* ── Modal ───────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  width: min(520px, calc(100vw - 32px));
  max-height: 80vh;
  overflow-y: auto;
}
.modal-title { font-size: 18px; font-weight: 700; color: var(--text-base); margin-bottom: 16px; }
.modal-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

/* Templates */
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}
.tpl-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: border-color 0.15s, background 0.15s;
  text-align: center;
}
.tpl-card:hover { border-color: var(--primary); background: var(--bg-elevated); }
.tpl-card.selected { border-color: var(--primary); background: color-mix(in srgb, var(--primary) 10%, transparent); }
.tpl-icon { font-size: 22px; }
.tpl-name { font-size: 12px; font-weight: 600; color: var(--text-base); }
.tpl-desc { font-size: 10px; color: var(--text-muted); }

/* Form */
.form-fields { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 12px; color: var(--text-muted); }
.field-input {
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--text-base);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.field-input:focus { border-color: var(--primary); }
.field-row { display: flex; align-items: center; gap: 8px; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-base); cursor: pointer; }
.check-input { accent-color: var(--primary); }
.field-error { font-size: 12px; color: var(--status-bad); }

/* Transitions */
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.97); }
</style>
