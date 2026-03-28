<template>
  <!-- Leaflet map — lazy-loaded only when this component mounts -->
  <div class="viz-map" ref="mapRef" :style="{ height: `${height}px` }">
    <div v-if="!loaded" class="map-loading">
      <span class="map-icon">🗺</span>
      <span>Loading map…</span>
    </div>
    <div v-if="loadError" class="map-error">{{ loadError }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from "vue";

const props = withDefaults(defineProps<{
  currentValue?: unknown;   // expected: { lat: number; lng: number; label?: string }
  height?: number;
}>(), {
  currentValue: null,
  height: 220,
});

const mapRef   = ref<HTMLElement | null>(null);
const loaded   = ref(false);
const loadError = ref<string | null>(null);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mapInstance: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let marker: any = null;

function parseCoords(): { lat: number; lng: number; label?: string } | null {
  const v = props.currentValue;
  if (!v || typeof v !== "object") return null;
  const obj = v as Record<string, unknown>;
  const lat = Number(obj.lat ?? obj.latitude);
  const lng = Number(obj.lng ?? obj.longitude ?? obj.lon);
  if (isNaN(lat) || isNaN(lng)) return null;
  return { lat, lng, label: String(obj.label ?? "") };
}

async function initMap() {
  if (!mapRef.value) return;
  try {
    // Dynamic import — Leaflet only loads when map widget is actually used
    const L = (await import("leaflet")).default;
    await import("leaflet/dist/leaflet.css");

    const coords = parseCoords();
    const center: [number, number] = coords ? [coords.lat, coords.lng] : [51.505, -0.09];

    mapInstance = L.map(mapRef.value, { zoomControl: true }).setView(center, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      className: "map-tiles",
    }).addTo(mapInstance);

    if (coords) {
      marker = L.marker([coords.lat, coords.lng]).addTo(mapInstance);
      if (coords.label) marker.bindPopup(coords.label).openPopup();
    }

    loaded.value = true;
  } catch (e) {
    loadError.value = "Map could not be loaded";
  }
}

function updateMarker() {
  if (!mapInstance) return;
  const coords = parseCoords();
  if (!coords) return;

  if (marker) {
    marker.setLatLng([coords.lat, coords.lng]);
  } else {
    // Dynamic import was already done, L should be available
    import("leaflet").then(({ default: L }) => {
      marker = L.marker([coords.lat, coords.lng]).addTo(mapInstance);
      if (coords.label) marker.bindPopup(coords.label);
    });
  }
  mapInstance.setView([coords.lat, coords.lng], mapInstance.getZoom());
}

watch(() => props.currentValue, updateMarker);

onMounted(initMap);
onUnmounted(() => {
  if (mapInstance) { mapInstance.remove(); mapInstance = null; }
});
</script>

<style scoped>
.viz-map { position: relative; width: 100%; border-radius: 4px; overflow: hidden; background: #161b22; }
.map-loading, .map-error {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  color: #8b949e; font-size: 13px;
}
.map-icon { font-size: 24px; }
.map-error { color: #f85149; }
</style>

<style>
/* Override Leaflet tiles for dark look */
.map-tiles { filter: brightness(0.75) saturate(0.7); }
</style>
