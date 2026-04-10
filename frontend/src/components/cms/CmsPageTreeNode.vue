<script setup lang="ts">
import { computed } from "vue";

type Node = {
  id: number;
  slug: string;
  title: string;
  layout: string;
  visibility: string;
  published: boolean;
  parent_id: number | null;
  menu_order: number;
  show_in_menu: boolean;
  children: Node[];
};

const props = defineProps<{
  node: Node;
  expandedIds: Set<number>;
  dropTargetId: number | null;
  dropAsChild: boolean;
  depth?: number;
}>();

const emit = defineEmits<{
  (e: "toggle", id: number): void;
  (e: "edit", id: number): void;
  (e: "add-child", parentId: number): void;
  (e: "drag-start", ev: DragEvent, node: Node): void;
  (e: "drag-over", ev: DragEvent, node: Node, asChild: boolean): void;
  (e: "drag-leave"): void;
  (e: "drop", ev: DragEvent, node: Node): void;
}>();

const depth = computed(() => props.depth ?? 0);
const isExpanded = computed(() => props.expandedIds.has(props.node.id));
const hasChildren = computed(() => (props.node.children?.length || 0) > 0);
const isDropTarget = computed(() => props.dropTargetId === props.node.id);
</script>

<template>
  <li class="tree-node">
    <div
      class="node-row"
      :class="{
        'drop-above': isDropTarget && !dropAsChild,
        'drop-as-child': isDropTarget && dropAsChild,
        unpublished: !node.published,
      }"
      :style="{ paddingLeft: `${depth * 20}px` }"
      draggable="true"
      @dragstart="emit('drag-start', $event, node)"
      @dragover.prevent="emit('drag-over', $event, node, false)"
      @dragleave="emit('drag-leave')"
      @drop="emit('drop', $event, node)"
    >
      <button
        v-if="hasChildren"
        class="expand-btn"
        type="button"
        @click.stop="emit('toggle', node.id)"
      >
        {{ isExpanded ? '▾' : '▸' }}
      </button>
      <span v-else class="expand-spacer" aria-hidden="true"></span>

      <span class="node-title" @click="emit('edit', node.id)">
        {{ node.title }}
      </span>
      <span class="node-slug">/{{ node.slug }}</span>

      <span v-if="node.published" class="node-badge pub">live</span>
      <span v-else class="node-badge draft">draft</span>

      <div class="node-actions">
        <button
          class="a-btn"
          type="button"
          @click.stop="emit('add-child', node.id)"
          title="Add child page"
        >
          + Child
        </button>
        <button
          class="a-btn"
          type="button"
          @click.stop="emit('edit', node.id)"
        >
          Edit
        </button>
      </div>

      <!-- Drop-as-child hotspot on the right edge -->
      <div
        class="drop-child-zone"
        @dragover.prevent="emit('drag-over', $event, node, true)"
        @drop.stop="emit('drop', $event, node)"
        title="Drop here to nest"
      ></div>
    </div>

    <ul v-if="hasChildren && isExpanded" class="tree-children">
      <CmsPageTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :expanded-ids="expandedIds"
        :drop-target-id="dropTargetId"
        :drop-as-child="dropAsChild"
        :depth="depth + 1"
        @toggle="(id) => emit('toggle', id)"
        @edit="(id) => emit('edit', id)"
        @add-child="(id) => emit('add-child', id)"
        @drag-start="(ev, n) => emit('drag-start', ev, n)"
        @drag-over="(ev, n, asChild) => emit('drag-over', ev, n, asChild)"
        @drag-leave="() => emit('drag-leave')"
        @drop="(ev, n) => emit('drop', ev, n)"
      />
    </ul>
  </li>
</template>

<style scoped>
.tree-node { list-style: none; }
.tree-children {
  list-style: none;
  padding: 0;
  margin: 0;
}
.node-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px 10px 8px;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  margin: 4px 0;
  cursor: grab;
  position: relative;
  transition: border-color 0.15s, background 0.15s;
}
.node-row:hover {
  border-color: rgba(245,166,35,0.3);
}
.node-row.unpublished { opacity: 0.7; }
.node-row.drop-above { border-top: 2px solid #F5A623; }
.node-row.drop-as-child { background: rgba(245,166,35,0.12); border-color: #F5A623; }
.expand-btn {
  background: transparent;
  border: none;
  color: #A1A1AA;
  font-size: 12px;
  cursor: pointer;
  width: 20px;
  text-align: center;
}
.expand-spacer { width: 20px; display: inline-block; }
.node-title {
  color: #F5F5F5;
  font-weight: 600;
  cursor: pointer;
}
.node-title:hover { color: #F5A623; }
.node-slug {
  color: #71717A;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.node-badge {
  font-size: 10px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.node-badge.pub { background: rgba(45,212,191,0.15); color: #2DD4BF; }
.node-badge.draft { background: rgba(255,255,255,0.08); color: #A1A1AA; }
.node-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}
.a-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
}
.a-btn:hover { background: rgba(255,255,255,0.05); color: #F5F5F5; }
.drop-child-zone {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 40px;
  opacity: 0;
}
</style>
