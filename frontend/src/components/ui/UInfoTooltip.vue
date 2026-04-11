<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { useTourStore } from "../../stores/tour";

const { t } = useI18n();

const props = defineProps<{
  title: string;
  items: string[];
  /** Optional tour ID. When provided a "Take a guided tour" link appears. */
  tourId?: string;
}>();

const tourStore = useTourStore();

function startTour() {
  if (props.tourId) {
    hide();
    tourStore.start(props.tourId);
  }
}

const visible = ref(false);
const tooltipRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLElement | null>(null);

function show() {
  visible.value = true;
  nextTick(adjustPosition);
}

function hide() {
  visible.value = false;
}

function toggle(e: MouseEvent) {
  e.stopPropagation();
  if (visible.value) {
    hide();
  } else {
    show();
  }
}

function adjustPosition() {
  const el = tooltipRef.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  // If overflowing right, shift left
  if (rect.right > window.innerWidth - 8) {
    el.style.left = "auto";
    el.style.right = "0";
  }
  // If overflowing bottom, show above
  if (rect.bottom > window.innerHeight - 8) {
    el.style.top = "auto";
    el.style.bottom = "calc(100% + 6px)";
  }
}

function onClickOutside(e: MouseEvent) {
  if (
    triggerRef.value &&
    !triggerRef.value.contains(e.target as Node) &&
    tooltipRef.value &&
    !tooltipRef.value.contains(e.target as Node)
  ) {
    hide();
  }
}

onMounted(() => {
  document.addEventListener("click", onClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", onClickOutside);
});
</script>

<template>
  <span
    ref="triggerRef"
    class="info-trigger"
    @mouseenter="show"
    @mouseleave="hide"
    @click="toggle"
    tabindex="0"
    @focus="show"
    @blur="hide"
  >
    <!-- Info icon (circle with "i") -->
    <svg
      class="info-icon"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fill-rule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
        clip-rule="evenodd"
      />
    </svg>

    <!-- Tooltip popover -->
    <Transition name="info-pop">
      <div
        v-if="visible"
        ref="tooltipRef"
        class="info-popover"
        @click.stop
      >
        <p class="info-popover-title">{{ title }}</p>
        <ul v-if="items.length" class="info-popover-list">
          <li v-for="(item, i) in items" :key="i">{{ item }}</li>
        </ul>
        <button
          v-if="tourId"
          class="info-tour-link"
          @click.stop="startTour"
        >
          <svg class="info-tour-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.62 48.62 0 0112 20.904a48.62 48.62 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
          </svg>
          {{ t('infoTooltip.takeGuidedTour') }}
        </button>
      </div>
    </Transition>
  </span>
</template>

<style scoped>
.info-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: help;
  margin-left: 6px;
  vertical-align: middle;
}

.info-icon {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  opacity: 0.6;
  transition: opacity 0.15s ease, color 0.15s ease;
}

.info-trigger:hover .info-icon,
.info-trigger:focus .info-icon {
  opacity: 1;
  color: var(--primary, #F5A623);
}

.info-popover {
  position: absolute;
  top: calc(100% + 6px);
  left: -4px;
  z-index: 100;
  min-width: 260px;
  max-width: 340px;
  padding: 10px 14px;
  background: var(--bg-raised, #1c1c1b);
  border: 1px solid var(--primary, #F5A623);
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  pointer-events: auto;
}

.info-popover-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary, #e6edf3);
  line-height: 1.5;
  margin: 0 0 6px 0;
}

.info-popover-list {
  margin: 0;
  padding: 0 0 0 16px;
  list-style: disc;
}

.info-popover-list li {
  font-size: 11px;
  color: var(--text-muted, #8b949e);
  line-height: 1.6;
}

.info-popover-list li + li {
  margin-top: 2px;
}

/* Tour link */
.info-tour-link {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  background: none;
  border-left: none;
  border-right: none;
  border-bottom: none;
  font-size: 11px;
  font-weight: 500;
  color: var(--primary, #F5A623);
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.info-tour-link:hover {
  opacity: 0.8;
}

.info-tour-icon {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
}

/* Transition */
.info-pop-enter-active,
.info-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.info-pop-enter-from,
.info-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
