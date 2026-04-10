/**
 * CMS Editor store — manages the current block list, selection,
 * undo/redo history, and dirty state for the block-based page editor.
 */
import { defineStore } from "pinia";

export type CmsBlock = {
  id: string;
  type: string;
  props: Record<string, any>;
};

const MAX_HISTORY = 50;

function genId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `blk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function cloneBlocks(blocks: CmsBlock[]): CmsBlock[] {
  return JSON.parse(JSON.stringify(blocks));
}

type State = {
  blocks: CmsBlock[];
  selectedIndex: number;
  history: CmsBlock[][];
  historyIndex: number;
  dirty: boolean;
};

export const useCmsEditorStore = defineStore("cmsEditor", {
  state: (): State => ({
    blocks: [],
    selectedIndex: -1,
    history: [[]],
    historyIndex: 0,
    dirty: false,
  }),
  getters: {
    selectedBlock(state): CmsBlock | null {
      if (state.selectedIndex < 0 || state.selectedIndex >= state.blocks.length) {
        return null;
      }
      return state.blocks[state.selectedIndex];
    },
    canUndo(state): boolean {
      return state.historyIndex > 0;
    },
    canRedo(state): boolean {
      return state.historyIndex < state.history.length - 1;
    },
  },
  actions: {
    setBlocks(blocks: CmsBlock[], resetHistory = true) {
      this.blocks = Array.isArray(blocks) ? cloneBlocks(blocks) : [];
      if (resetHistory) {
        this.history = [cloneBlocks(this.blocks)];
        this.historyIndex = 0;
      }
      this.selectedIndex = -1;
      this.dirty = false;
    },
    _pushHistory() {
      // Drop any "future" entries ahead of current index
      const base = this.history.slice(0, this.historyIndex + 1);
      base.push(cloneBlocks(this.blocks));
      // Cap history size
      const trimmed = base.length > MAX_HISTORY ? base.slice(base.length - MAX_HISTORY) : base;
      this.history = trimmed;
      this.historyIndex = trimmed.length - 1;
      this.dirty = true;
    },
    addBlock(type: string, props: Record<string, any> = {}, atIndex?: number) {
      const block: CmsBlock = { id: genId(), type, props };
      const idx =
        typeof atIndex === "number" && atIndex >= 0 && atIndex <= this.blocks.length
          ? atIndex
          : this.blocks.length;
      this.blocks.splice(idx, 0, block);
      this.selectedIndex = idx;
      this._pushHistory();
    },
    updateBlock(index: number, props: Record<string, any>) {
      if (index < 0 || index >= this.blocks.length) return;
      this.blocks[index] = {
        ...this.blocks[index],
        props: { ...this.blocks[index].props, ...props },
      };
      this._pushHistory();
    },
    setBlockProp(index: number, key: string, value: any) {
      if (index < 0 || index >= this.blocks.length) return;
      this.blocks[index] = {
        ...this.blocks[index],
        props: { ...this.blocks[index].props, [key]: value },
      };
      this._pushHistory();
    },
    deleteBlock(index: number) {
      if (index < 0 || index >= this.blocks.length) return;
      this.blocks.splice(index, 1);
      if (this.selectedIndex === index) this.selectedIndex = -1;
      else if (this.selectedIndex > index) this.selectedIndex--;
      this._pushHistory();
    },
    duplicateBlock(index: number) {
      if (index < 0 || index >= this.blocks.length) return;
      const src = this.blocks[index];
      const copy: CmsBlock = {
        id: genId(),
        type: src.type,
        props: JSON.parse(JSON.stringify(src.props || {})),
      };
      this.blocks.splice(index + 1, 0, copy);
      this.selectedIndex = index + 1;
      this._pushHistory();
    },
    moveBlock(from: number, to: number) {
      if (from < 0 || from >= this.blocks.length) return;
      if (to < 0 || to >= this.blocks.length) return;
      if (from === to) return;
      const [moved] = this.blocks.splice(from, 1);
      this.blocks.splice(to, 0, moved);
      this.selectedIndex = to;
      this._pushHistory();
    },
    selectBlock(index: number) {
      if (index < -1 || index >= this.blocks.length) return;
      this.selectedIndex = index;
    },
    undo() {
      if (!this.canUndo) return;
      this.historyIndex--;
      this.blocks = cloneBlocks(this.history[this.historyIndex]);
      this.dirty = true;
    },
    redo() {
      if (!this.canRedo) return;
      this.historyIndex++;
      this.blocks = cloneBlocks(this.history[this.historyIndex]);
      this.dirty = true;
    },
    markClean() {
      this.dirty = false;
    },
  },
});
