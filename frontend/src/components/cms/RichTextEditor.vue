<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import TextAlign from "@tiptap/extension-text-align";
import MediaLibrary from "./MediaLibrary.vue";
import type { MediaAsset } from "../../lib/media";

const props = defineProps<{
  modelValue: string;
  minHeight?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const showMediaPicker = ref(false);
const showSource = ref(false);
const sourceText = ref(props.modelValue || "");

const editor = useEditor({
  content: props.modelValue || "",
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
    }),
    Link.configure({
      openOnClick: false,
      HTMLAttributes: { rel: "noopener noreferrer", target: "_blank" },
    }),
    Image.configure({
      HTMLAttributes: {
        style: "max-width:100%;border-radius:8px;",
      },
    }),
    TextAlign.configure({
      types: ["heading", "paragraph"],
    }),
  ],
  onUpdate: ({ editor }) => {
    const html = editor.getHTML();
    sourceText.value = html;
    emit("update:modelValue", html);
  },
});

watch(
  () => props.modelValue,
  (val) => {
    if (!editor.value) return;
    if (val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val || "", false);
    }
  },
);

onBeforeUnmount(() => {
  editor.value?.destroy();
});

function toggleBold() {
  editor.value?.chain().focus().toggleBold().run();
}
function toggleItalic() {
  editor.value?.chain().focus().toggleItalic().run();
}
function toggleStrike() {
  editor.value?.chain().focus().toggleStrike().run();
}
function toggleCode() {
  editor.value?.chain().focus().toggleCode().run();
}
function setHeading(level: 1 | 2 | 3) {
  editor.value?.chain().focus().toggleHeading({ level }).run();
}
function setParagraph() {
  editor.value?.chain().focus().setParagraph().run();
}
function toggleBulletList() {
  editor.value?.chain().focus().toggleBulletList().run();
}
function toggleOrderedList() {
  editor.value?.chain().focus().toggleOrderedList().run();
}
function setAlign(align: "left" | "center" | "right") {
  editor.value?.chain().focus().setTextAlign(align).run();
}
function clearFormat() {
  editor.value?.chain().focus().clearNodes().unsetAllMarks().run();
}
function undo() {
  editor.value?.chain().focus().undo().run();
}
function redo() {
  editor.value?.chain().focus().redo().run();
}

function promptLink() {
  const prev = editor.value?.getAttributes("link").href || "";
  const url = prompt("Link URL", prev || "https://");
  if (url === null) return;
  if (!url) {
    editor.value?.chain().focus().extendMarkRange("link").unsetLink().run();
    return;
  }
  editor.value
    ?.chain()
    .focus()
    .extendMarkRange("link")
    .setLink({ href: url })
    .run();
}

function pickImage() {
  showMediaPicker.value = true;
}

function onPickMedia(asset: MediaAsset) {
  if (asset.mime_type.startsWith("image/")) {
    editor.value
      ?.chain()
      .focus()
      .setImage({
        src: asset.public_url,
        alt: asset.alt_text || asset.filename,
      })
      .run();
  } else {
    // Non-image: insert as link
    editor.value
      ?.chain()
      .focus()
      .insertContent(
        `<a href="${asset.public_url}" target="_blank" rel="noopener">${asset.filename}</a>`,
      )
      .run();
  }
  showMediaPicker.value = false;
}

function toggleSource() {
  if (showSource.value) {
    // Leaving source mode: push source HTML into the editor
    editor.value?.commands.setContent(sourceText.value, false);
    emit("update:modelValue", sourceText.value);
  } else {
    // Entering source mode: populate textarea with current HTML
    sourceText.value = editor.value?.getHTML() || "";
  }
  showSource.value = !showSource.value;
}

function onSourceInput(e: Event) {
  const target = e.target as HTMLTextAreaElement;
  sourceText.value = target.value;
  emit("update:modelValue", target.value);
}

const isActive = computed(() => ({
  bold: !!editor.value?.isActive("bold"),
  italic: !!editor.value?.isActive("italic"),
  strike: !!editor.value?.isActive("strike"),
  code: !!editor.value?.isActive("code"),
  h1: !!editor.value?.isActive("heading", { level: 1 }),
  h2: !!editor.value?.isActive("heading", { level: 2 }),
  h3: !!editor.value?.isActive("heading", { level: 3 }),
  bulletList: !!editor.value?.isActive("bulletList"),
  orderedList: !!editor.value?.isActive("orderedList"),
  link: !!editor.value?.isActive("link"),
  alignLeft: !!editor.value?.isActive({ textAlign: "left" }),
  alignCenter: !!editor.value?.isActive({ textAlign: "center" }),
  alignRight: !!editor.value?.isActive({ textAlign: "right" }),
}));
</script>

<template>
  <div class="rte-wrap">
    <div class="rte-toolbar" v-if="!showSource">
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.bold }"
        @click="toggleBold"
        title="Bold"
      >
        B
      </button>
      <button
        type="button"
        class="rte-btn italic"
        :class="{ active: isActive.italic }"
        @click="toggleItalic"
        title="Italic"
      >
        I
      </button>
      <button
        type="button"
        class="rte-btn strike"
        :class="{ active: isActive.strike }"
        @click="toggleStrike"
        title="Strikethrough"
      >
        S
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.code }"
        @click="toggleCode"
        title="Inline code"
      >
        &lt;/&gt;
      </button>
      <span class="rte-sep"></span>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.h1 }"
        @click="setHeading(1)"
        title="Heading 1"
      >
        H1
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.h2 }"
        @click="setHeading(2)"
        title="Heading 2"
      >
        H2
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.h3 }"
        @click="setHeading(3)"
        title="Heading 3"
      >
        H3
      </button>
      <button type="button" class="rte-btn" @click="setParagraph" title="Paragraph">
        P
      </button>
      <span class="rte-sep"></span>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.bulletList }"
        @click="toggleBulletList"
        title="Bullet list"
      >
        •≡
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.orderedList }"
        @click="toggleOrderedList"
        title="Ordered list"
      >
        1≡
      </button>
      <span class="rte-sep"></span>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.link }"
        @click="promptLink"
        title="Link"
      >
        🔗
      </button>
      <button type="button" class="rte-btn" @click="pickImage" title="Insert image">
        🖼
      </button>
      <span class="rte-sep"></span>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.alignLeft }"
        @click="setAlign('left')"
        title="Align left"
      >
        ⇤
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.alignCenter }"
        @click="setAlign('center')"
        title="Align center"
      >
        ⇔
      </button>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: isActive.alignRight }"
        @click="setAlign('right')"
        title="Align right"
      >
        ⇥
      </button>
      <span class="rte-sep"></span>
      <button type="button" class="rte-btn" @click="clearFormat" title="Clear formatting">
        ⨯
      </button>
      <button type="button" class="rte-btn" @click="undo" title="Undo">↶</button>
      <button type="button" class="rte-btn" @click="redo" title="Redo">↷</button>
      <span class="rte-sep"></span>
      <button
        type="button"
        class="rte-btn"
        :class="{ active: showSource }"
        @click="toggleSource"
        title="Source view"
      >
        &lt;/&gt; HTML
      </button>
    </div>
    <div class="rte-toolbar" v-else>
      <button type="button" class="rte-btn active" @click="toggleSource">
        Back to editor
      </button>
    </div>

    <div class="rte-body" :style="{ minHeight: props.minHeight || '180px' }">
      <textarea
        v-if="showSource"
        class="rte-source"
        :value="sourceText"
        @input="onSourceInput"
        spellcheck="false"
      ></textarea>
      <EditorContent v-else :editor="editor" class="rte-editor" />
    </div>

    <!-- Media picker modal -->
    <div v-if="showMediaPicker" class="rte-modal" @click.self="showMediaPicker = false">
      <div class="rte-modal-body">
        <MediaLibrary
          picker-mode
          restrict-kind="images"
          @select="onPickMedia"
          @close="showMediaPicker = false"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.rte-wrap {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
  background: #0c0c0b;
}
.rte-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  background: #111110;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 6px;
}
.rte-btn {
  background: transparent;
  border: 1px solid transparent;
  color: #a1a1aa;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.rte-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f5;
}
.rte-btn.active {
  background: rgba(245, 166, 35, 0.15);
  color: #f5a623;
  border-color: rgba(245, 166, 35, 0.3);
}
.rte-btn.italic { font-style: italic; }
.rte-btn.strike { text-decoration: line-through; }
.rte-sep {
  width: 1px;
  height: 18px;
  background: rgba(255, 255, 255, 0.1);
  margin: 0 4px;
}
.rte-body {
  padding: 12px 14px;
  color: #e5e5e5;
  font-family: "Inter", sans-serif;
  font-size: 14px;
  line-height: 1.6;
}
.rte-editor :deep(.ProseMirror) {
  min-height: 120px;
  outline: none;
}
.rte-editor :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  color: #52525b;
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
.rte-editor :deep(h1) { color: #f5f5f5; font-size: 28px; margin: 16px 0 8px; }
.rte-editor :deep(h2) { color: #f5f5f5; font-size: 22px; margin: 14px 0 8px; }
.rte-editor :deep(h3) { color: #f5f5f5; font-size: 18px; margin: 12px 0 6px; }
.rte-editor :deep(a) { color: #2dd4bf; text-decoration: underline; }
.rte-editor :deep(code) {
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.9em;
}
.rte-editor :deep(img) { max-width: 100%; border-radius: 8px; margin: 8px 0; }
.rte-source {
  width: 100%;
  min-height: 200px;
  background: #0c0c0b;
  border: none;
  color: #e5e5e5;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
}
.rte-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.rte-modal-body {
  max-width: 900px;
  width: 100%;
  max-height: 85vh;
  overflow: auto;
  background: #0f0f0e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}
</style>
