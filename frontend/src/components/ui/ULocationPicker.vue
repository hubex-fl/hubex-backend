<template>
  <div class="location-picker">
    <div ref="mapRef" class="picker-map" />
    <p class="picker-hint">{{ t('common.clickMapToSetLocation') }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * ULocationPicker — Leaflet map that lets the user click to set lat/lng.
 * Sprint 10: GPS picker for the Entities create/edit dialog.
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const props = withDefaults(defineProps<{
  lat: number;
  lng: number;
}>(), { lat: 48.137, lng: 11.576 });

const emit = defineEmits<{
  (e: "update:lat", val: number): void;
  (e: "update:lng", val: number): void;
}>();

const mapRef = ref<HTMLElement | null>(null);
let map: any = null;
let marker: any = null;

async function initMap() {
  if (!mapRef.value) return;
  try {
    const L = await import("leaflet");
    await import("leaflet/dist/leaflet.css");

    map = L.map(mapRef.value, {
      center: [props.lat || 48.137, props.lng || 11.576],
      zoom: 13,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    // Place initial marker
    if (props.lat && props.lng) {
      marker = L.marker([props.lat, props.lng]).addTo(map);
    }

    // Click to set location
    map.on("click", (e: any) => {
      const { lat, lng } = e.latlng;
      emit("update:lat", Math.round(lat * 1000000) / 1000000);
      emit("update:lng", Math.round(lng * 1000000) / 1000000);
      if (marker) {
        marker.setLatLng([lat, lng]);
      } else {
        marker = L.marker([lat, lng]).addTo(map);
      }
    });

    // Fix Leaflet rendering in modal (needs invalidateSize after mount)
    setTimeout(() => map?.invalidateSize(), 200);
  } catch (err) {
    console.error("[LocationPicker] Failed to load Leaflet:", err);
  }
}

watch(() => [props.lat, props.lng], ([lat, lng]) => {
  if (map && lat && lng) {
    map.setView([lat, lng], map.getZoom());
    if (marker) marker.setLatLng([lat, lng]);
  }
});

onMounted(() => nextTick(initMap));
onUnmounted(() => { map?.remove(); map = null; marker = null; });
</script>

<style scoped>
.location-picker { width: 100%; }
.picker-map {
  width: 100%;
  height: 200px;
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}
.picker-hint {
  font-size: 9px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
