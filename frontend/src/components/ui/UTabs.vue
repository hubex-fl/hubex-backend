<script setup lang="ts">
import { provide, ref, computed } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue?: string | number;
    variant?: "underline" | "pills";
  }>(),
  { variant: "underline" }
);

const emit = defineEmits<{ (e: "update:modelValue", v: string | number): void }>();

const active = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v!),
});

provide("tabs-active", active);
provide("tabs-set-active", (v: string | number) => { active.value = v; });
provide("tabs-variant", computed(() => props.variant));
</script>

<template>
  <div class="flex flex-col">
    <div
      :class="[
        'flex',
        variant === 'underline'
          ? 'border-b border-[var(--border)] gap-0'
          : 'gap-1 p-1 bg-[var(--bg-raised)] rounded-lg w-fit',
      ]"
      role="tablist"
    >
      <slot name="tabs" />
    </div>
    <div class="flex-1 pt-4">
      <slot />
    </div>
  </div>
</template>
