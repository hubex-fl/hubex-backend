<script setup lang="ts">
export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
}

withDefaults(
  defineProps<{
    columns: TableColumn[];
    rows: Record<string, unknown>[];
    loading?: boolean;
    emptyText?: string;
    sortKey?: string;
    sortDir?: "asc" | "desc";
  }>(),
  { loading: false, emptyText: "No data" }
);

const emit = defineEmits<{
  (e: "sort", key: string): void;
  (e: "row-click", row: Record<string, unknown>): void;
}>();

const alignClass: Record<string, string> = {
  left:   "text-left",
  center: "text-center",
  right:  "text-right",
};
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-[var(--border)]">
    <table class="w-full text-sm border-collapse">
      <thead>
        <tr class="border-b border-[var(--border)] bg-[var(--bg-raised)]">
          <th
            v-for="col in columns"
            :key="col.key"
            :style="col.width ? { width: col.width } : {}"
            :class="[
              'px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]',
              alignClass[col.align || 'left'],
              col.sortable && 'cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors',
            ]"
            @click="col.sortable && emit('sort', col.key)"
          >
            <span class="inline-flex items-center gap-1">
              {{ col.label }}
              <svg
                v-if="col.sortable"
                class="h-3 w-3"
                :class="sortKey === col.key ? 'text-[var(--primary)]' : 'text-[var(--border)]'"
                fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
              >
                <path v-if="sortKey === col.key && sortDir === 'asc'"  d="M5 15l7-7 7 7" />
                <path v-else-if="sortKey === col.key && sortDir === 'desc'" d="M19 9l-7 7-7-7" />
                <path v-else d="M8 9l4-4 4 4M8 15l4 4 4-4" />
              </svg>
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <!-- Loading skeleton rows -->
        <template v-if="loading">
          <tr v-for="i in 5" :key="i" class="border-b border-[var(--border)]">
            <td v-for="col in columns" :key="col.key" class="px-4 py-3">
              <div class="h-4 rounded animate-pulse bg-[var(--bg-raised)]" :style="{ width: `${60 + Math.random() * 30}%` }" />
            </td>
          </tr>
        </template>
        <!-- Empty state -->
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length" class="px-4 py-10 text-center text-[var(--text-muted)]">
            {{ emptyText }}
          </td>
        </tr>
        <!-- Data rows -->
        <tr
          v-else
          v-for="(row, i) in rows"
          :key="i"
          class="border-b border-[var(--border)] last:border-0 transition-colors hover:bg-[var(--bg-raised)] cursor-pointer"
          @click="emit('row-click', row)"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :class="['px-4 py-3 text-[var(--text-primary)]', alignClass[col.align || 'left']]"
          >
            <slot :name="col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
