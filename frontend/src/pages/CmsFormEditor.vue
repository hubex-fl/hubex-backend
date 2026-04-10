<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const route = useRoute();
const router = useRouter();
const toast = useToastStore();

type FieldType =
  | "text"
  | "email"
  | "tel"
  | "url"
  | "number"
  | "textarea"
  | "select"
  | "radio"
  | "checkbox"
  | "date"
  | "time"
  | "file";

type FormField = {
  id: string;
  type: FieldType;
  label: string;
  required: boolean;
  placeholder?: string;
  validation?: Record<string, any>;
  options?: string[];
};

type CmsForm = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  fields: FormField[];
  submit_button_text: string;
  success_message: string;
  action: "store" | "email" | "webhook" | "both";
  email_to: string | null;
  webhook_url: string | null;
  enabled: boolean;
};

const FIELD_TYPES: { value: FieldType; label: string; icon: string }[] = [
  { value: "text",     label: "Text",         icon: "Aa" },
  { value: "email",    label: "Email",        icon: "@"  },
  { value: "tel",      label: "Phone",        icon: "#"  },
  { value: "url",      label: "URL",          icon: "/"  },
  { value: "number",   label: "Number",       icon: "12" },
  { value: "textarea", label: "Long Text",    icon: "T" },
  { value: "select",   label: "Select",       icon: "v" },
  { value: "radio",    label: "Radio",        icon: "o" },
  { value: "checkbox", label: "Checkbox",     icon: "x" },
  { value: "date",     label: "Date",         icon: "D" },
  { value: "time",     label: "Time",         icon: "t" },
  { value: "file",     label: "File Upload",  icon: "F" },
];

const formId = computed(() => Number(route.params.id));
const loading = ref(true);
const saving = ref(false);
const form = ref<CmsForm | null>(null);
const activeTab = ref<"build" | "settings" | "preview">("build");
const addFieldOpen = ref(false);
const selectedFieldIdx = ref<number | null>(null);

// Preview data (for live form)
const previewValues = ref<Record<string, any>>({});

async function loadForm() {
  loading.value = true;
  try {
    form.value = await apiFetch<CmsForm>(`/api/v1/cms/forms/${formId.value}`);
  } catch (e: any) {
    toast.show(e.message || "Failed to load", "error");
    router.push("/cms/forms");
  } finally {
    loading.value = false;
  }
}

function generateFieldId(): string {
  return "field_" + Math.random().toString(36).slice(2, 9);
}

function addField(type: FieldType) {
  if (!form.value) return;
  const newField: FormField = {
    id: generateFieldId(),
    type,
    label: `${type.charAt(0).toUpperCase() + type.slice(1)} field`,
    required: false,
    placeholder: "",
  };
  if (type === "select" || type === "radio") {
    newField.options = ["Option 1", "Option 2", "Option 3"];
  }
  form.value.fields.push(newField);
  selectedFieldIdx.value = form.value.fields.length - 1;
  addFieldOpen.value = false;
}

function removeField(idx: number) {
  if (!form.value) return;
  form.value.fields.splice(idx, 1);
  if (selectedFieldIdx.value === idx) selectedFieldIdx.value = null;
}

function moveField(idx: number, delta: number) {
  if (!form.value) return;
  const newIdx = idx + delta;
  if (newIdx < 0 || newIdx >= form.value.fields.length) return;
  const [item] = form.value.fields.splice(idx, 1);
  form.value.fields.splice(newIdx, 0, item);
  if (selectedFieldIdx.value === idx) selectedFieldIdx.value = newIdx;
}

function addOption(field: FormField) {
  if (!field.options) field.options = [];
  field.options.push(`Option ${field.options.length + 1}`);
}

function removeOption(field: FormField, idx: number) {
  if (field.options) field.options.splice(idx, 1);
}

async function saveForm() {
  if (!form.value) return;
  saving.value = true;
  try {
    await apiFetch(`/api/v1/cms/forms/${formId.value}`, {
      method: "PUT",
      body: JSON.stringify({
        name: form.value.name,
        slug: form.value.slug,
        description: form.value.description,
        fields: form.value.fields,
        submit_button_text: form.value.submit_button_text,
        success_message: form.value.success_message,
        action: form.value.action,
        email_to: form.value.email_to,
        webhook_url: form.value.webhook_url,
        enabled: form.value.enabled,
      }),
    });
    toast.show("Form saved", "success");
  } catch (e: any) {
    toast.show(e.message || "Failed to save", "error");
  } finally {
    saving.value = false;
  }
}

const embedUrl = computed(() => {
  if (!form.value) return "";
  return `${window.location.origin}/api/v1/cms/forms/public/${form.value.slug}/submit`;
});

onMounted(loadForm);
</script>

<template>
  <div class="editor-wrap" v-if="!loading && form">
    <header class="editor-head">
      <button class="back-btn" @click="router.push('/cms/forms')">← Back</button>
      <div class="head-title">
        <input v-model="form.name" class="title-input" />
        <div class="head-slug">/{{ form.slug }}</div>
      </div>
      <div class="head-tabs">
        <button
          v-for="t in ['build','settings','preview'] as const"
          :key="t"
          class="tab-btn"
          :class="{ active: activeTab === t }"
          @click="activeTab = t"
        >{{ t }}</button>
      </div>
      <button class="btn-primary" :disabled="saving" @click="saveForm">
        {{ saving ? "Saving…" : "Save" }}
      </button>
    </header>

    <!-- BUILD TAB -->
    <div v-if="activeTab === 'build'" class="editor-body">
      <div class="fields-col">
        <h3 class="col-title">Form Fields</h3>

        <div v-if="form.fields.length === 0" class="empty-state">
          No fields yet. Click “Add Field” below.
        </div>

        <div
          v-for="(field, idx) in form.fields"
          :key="field.id"
          class="field-row"
          :class="{ selected: selectedFieldIdx === idx }"
          @click="selectedFieldIdx = idx"
        >
          <div class="field-handle">{{ idx + 1 }}</div>
          <div class="field-info">
            <div class="field-label">{{ field.label }}</div>
            <div class="field-meta">
              <span class="type-badge">{{ field.type }}</span>
              <span v-if="field.required" class="required-badge">Required</span>
            </div>
          </div>
          <div class="field-ops">
            <button class="ops-btn" @click.stop="moveField(idx, -1)" title="Move up">↑</button>
            <button class="ops-btn" @click.stop="moveField(idx, 1)" title="Move down">↓</button>
            <button class="ops-btn danger" @click.stop="removeField(idx)" title="Delete">×</button>
          </div>
        </div>

        <div class="add-field-wrap">
          <button class="add-btn" @click="addFieldOpen = !addFieldOpen">+ Add Field</button>
          <div v-if="addFieldOpen" class="field-type-grid">
            <button
              v-for="t in FIELD_TYPES"
              :key="t.value"
              class="type-btn"
              @click="addField(t.value)"
            >
              <span class="type-icon">{{ t.icon }}</span>
              <span>{{ t.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="prop-col">
        <h3 class="col-title">Field Properties</h3>
        <div v-if="selectedFieldIdx === null" class="empty-state">
          Select a field to edit its properties.
        </div>
        <div v-else-if="form.fields[selectedFieldIdx]">
          <label class="field-input">
            <span>Label</span>
            <input v-model="form.fields[selectedFieldIdx].label" type="text" />
          </label>
          <label class="field-input">
            <span>Field ID (key in submission)</span>
            <input v-model="form.fields[selectedFieldIdx].id" type="text" />
          </label>
          <label class="field-input">
            <span>Placeholder</span>
            <input v-model="form.fields[selectedFieldIdx].placeholder" type="text" />
          </label>
          <label class="checkbox-row">
            <input type="checkbox" v-model="form.fields[selectedFieldIdx].required" />
            <span>Required field</span>
          </label>

          <div
            v-if="
              form.fields[selectedFieldIdx].type === 'select' ||
              form.fields[selectedFieldIdx].type === 'radio'
            "
            class="options-section"
          >
            <div class="opt-header">
              <span>Options</span>
              <button class="mini-btn" @click="addOption(form.fields[selectedFieldIdx])">
                + Add
              </button>
            </div>
            <div
              v-for="(opt, i) in form.fields[selectedFieldIdx].options || []"
              :key="i"
              class="opt-row"
            >
              <input v-model="form.fields[selectedFieldIdx].options![i]" type="text" />
              <button class="mini-btn danger" @click="removeOption(form.fields[selectedFieldIdx], i)">
                ×
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SETTINGS TAB -->
    <div v-if="activeTab === 'settings'" class="editor-body single-col">
      <div class="settings-section">
        <h3>General</h3>
        <label class="field-input">
          <span>Form Name</span>
          <input v-model="form.name" type="text" />
        </label>
        <label class="field-input">
          <span>Slug</span>
          <input v-model="form.slug" type="text" />
        </label>
        <label class="field-input">
          <span>Description</span>
          <textarea v-model="form.description" rows="2"></textarea>
        </label>
        <label class="field-input">
          <span>Submit Button Text</span>
          <input v-model="form.submit_button_text" type="text" />
        </label>
        <label class="field-input">
          <span>Success Message</span>
          <textarea v-model="form.success_message" rows="2"></textarea>
        </label>
        <label class="checkbox-row">
          <input type="checkbox" v-model="form.enabled" />
          <span>Form is enabled (accepts submissions)</span>
        </label>
      </div>

      <div class="settings-section">
        <h3>On Submission</h3>
        <label class="field-input">
          <span>Action</span>
          <select v-model="form.action">
            <option value="store">Store in database only</option>
            <option value="email">Store + send email notification</option>
            <option value="webhook">Store + call webhook</option>
            <option value="both">Store + email + webhook</option>
          </select>
        </label>
        <label
          v-if="form.action === 'email' || form.action === 'both'"
          class="field-input"
        >
          <span>Email to</span>
          <input v-model="form.email_to" type="email" placeholder="you@example.com" />
        </label>
        <label
          v-if="form.action === 'webhook' || form.action === 'both'"
          class="field-input"
        >
          <span>Webhook URL</span>
          <input v-model="form.webhook_url" type="url" placeholder="https://example.com/webhook" />
        </label>
      </div>

      <div class="settings-section">
        <h3>Integration</h3>
        <p class="settings-hint">Submit this form by POSTing JSON to:</p>
        <code class="embed-code">{{ embedUrl }}</code>
      </div>
    </div>

    <!-- PREVIEW TAB -->
    <div v-if="activeTab === 'preview'" class="editor-body single-col">
      <div class="preview-wrap">
        <div class="preview-form">
          <h2>{{ form.name }}</h2>
          <p v-if="form.description" class="preview-desc">{{ form.description }}</p>
          <div v-for="field in form.fields" :key="field.id" class="preview-field">
            <label>
              {{ field.label }}
              <span v-if="field.required" class="req">*</span>
            </label>
            <input
              v-if="['text','email','tel','url','number','date','time'].includes(field.type)"
              :type="field.type"
              :placeholder="field.placeholder"
              v-model="previewValues[field.id]"
            />
            <textarea
              v-else-if="field.type === 'textarea'"
              :placeholder="field.placeholder"
              v-model="previewValues[field.id]"
              rows="4"
            ></textarea>
            <select v-else-if="field.type === 'select'" v-model="previewValues[field.id]">
              <option value="" disabled>Choose…</option>
              <option v-for="opt in field.options || []" :key="opt" :value="opt">{{ opt }}</option>
            </select>
            <div v-else-if="field.type === 'radio'" class="radio-group">
              <label v-for="opt in field.options || []" :key="opt" class="radio-opt">
                <input type="radio" :name="field.id" :value="opt" v-model="previewValues[field.id]" />
                <span>{{ opt }}</span>
              </label>
            </div>
            <label v-else-if="field.type === 'checkbox'" class="checkbox-opt">
              <input type="checkbox" v-model="previewValues[field.id]" />
              <span>{{ field.placeholder || "Yes" }}</span>
            </label>
            <input v-else-if="field.type === 'file'" type="file" />
          </div>
          <button class="preview-submit">{{ form.submit_button_text }}</button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="state-msg">Loading…</div>
</template>

<style scoped>
.editor-wrap {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #111110;
  color: #E5E5E5;
}
.state-msg {
  padding: 80px 24px;
  text-align: center;
  color: #71717A;
}
.editor-head {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: #0c0c0b;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.back-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
}
.back-btn:hover { color: #F5F5F5; }
.head-title { flex: 1; }
.title-input {
  background: transparent;
  border: none;
  color: #F5F5F5;
  font-size: 18px;
  font-weight: 600;
  width: 100%;
  padding: 2px 4px;
}
.title-input:focus { outline: 1px solid #F5A623; border-radius: 4px; }
.head-slug {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #71717A;
  margin-top: 2px;
}
.head-tabs {
  display: flex;
  gap: 4px;
  background: rgba(255,255,255,0.04);
  padding: 4px;
  border-radius: 8px;
}
.tab-btn {
  background: transparent;
  color: #A1A1AA;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  text-transform: capitalize;
  font-size: 13px;
}
.tab-btn.active {
  background: #F5A623;
  color: #111110;
  font-weight: 600;
}
.btn-primary {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 9px 18px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.editor-body {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 1px;
  background: rgba(255,255,255,0.04);
}
.editor-body.single-col {
  grid-template-columns: 1fr;
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
  background: transparent;
}
.fields-col,
.prop-col {
  background: #111110;
  padding: 20px 24px;
  overflow-y: auto;
}
.col-title {
  font-size: 13px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 16px;
}
.empty-state {
  padding: 32px 16px;
  text-align: center;
  color: #71717A;
  font-size: 13px;
  background: rgba(255,255,255,0.02);
  border: 1px dashed rgba(255,255,255,0.08);
  border-radius: 8px;
}
.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.field-row:hover { border-color: rgba(245,166,35,0.3); }
.field-row.selected { border-color: #F5A623; background: rgba(245,166,35,0.05); }
.field-handle {
  width: 28px;
  height: 28px;
  background: rgba(255,255,255,0.08);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #71717A;
  flex-shrink: 0;
}
.field-info { flex: 1; min-width: 0; }
.field-label { color: #F5F5F5; font-weight: 500; font-size: 14px; margin-bottom: 2px; }
.field-meta { display: flex; gap: 8px; }
.type-badge {
  background: rgba(45,212,191,0.12);
  color: #2DD4BF;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}
.required-badge {
  background: rgba(239,68,68,0.12);
  color: #ef4444;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}
.field-ops { display: flex; gap: 4px; }
.ops-btn {
  background: transparent;
  color: #71717A;
  border: 1px solid rgba(255,255,255,0.08);
  width: 28px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.ops-btn:hover { color: #F5F5F5; background: rgba(255,255,255,0.05); }
.ops-btn.danger:hover { color: #ef4444; border-color: #ef4444; }

.add-field-wrap { margin-top: 16px; }
.add-btn {
  width: 100%;
  background: rgba(245,166,35,0.1);
  color: #F5A623;
  border: 1px dashed #F5A623;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}
.add-btn:hover { background: rgba(245,166,35,0.15); }
.field-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
}
.type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: rgba(255,255,255,0.04);
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 12px 6px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
}
.type-btn:hover { border-color: #F5A623; color: #F5A623; }
.type-icon {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 16px;
  font-weight: 600;
}

/* Field input (right column + settings) */
.field-input { display: block; margin-bottom: 16px; }
.field-input span {
  display: block;
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}
.field-input input,
.field-input textarea,
.field-input select {
  width: 100%;
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
}
.field-input input:focus,
.field-input textarea:focus,
.field-input select:focus { outline: none; border-color: #F5A623; }

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #E5E5E5;
  font-size: 13px;
  margin-bottom: 16px;
}
.checkbox-row input { width: 16px; height: 16px; accent-color: #F5A623; }

.options-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.opt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  color: #71717A;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.opt-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.opt-row input {
  flex: 1;
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
}
.mini-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}
.mini-btn:hover { color: #F5F5F5; }
.mini-btn.danger:hover { color: #ef4444; border-color: #ef4444; }

/* Settings */
.settings-section {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}
.settings-section h3 { margin: 0 0 16px; color: #F5F5F5; font-size: 16px; }
.settings-hint { color: #71717A; font-size: 13px; margin: 0 0 8px; }
.embed-code {
  display: block;
  background: #0c0c0b;
  color: #2DD4BF;
  padding: 12px 16px;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  overflow-x: auto;
  white-space: nowrap;
}

/* Preview */
.preview-wrap {
  display: flex;
  justify-content: center;
  padding: 32px 0;
}
.preview-form {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 32px;
  max-width: 520px;
  width: 100%;
}
.preview-form h2 { margin: 0 0 8px; color: #F5F5F5; }
.preview-desc { color: #A1A1AA; margin: 0 0 24px; }
.preview-field { margin-bottom: 16px; }
.preview-field > label {
  display: block;
  color: #E5E5E5;
  font-size: 13px;
  margin-bottom: 6px;
  font-weight: 500;
}
.preview-field .req { color: #ef4444; margin-left: 2px; }
.preview-field input,
.preview-field textarea,
.preview-field select {
  width: 100%;
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
}
.radio-group { display: flex; flex-direction: column; gap: 6px; }
.radio-opt, .checkbox-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #E5E5E5;
  font-size: 13px;
  cursor: pointer;
}
.preview-submit {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  margin-top: 8px;
}
</style>
