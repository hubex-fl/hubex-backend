<template>
  <!-- Leaflet map — lazy-loaded only when this component mounts -->
  <div class="viz-map" ref="mapRef" :style="{ height: computedHeight }">
    <div v-if="!loaded && !noData && !loadError" class="map-overlay">
      <span class="map-icon">&#x1f5fa;</span>
      <span>Loading map...</span>
    </div>
    <div v-if="noData && !loadError" class="map-overlay map-no-data">
      <span class="map-icon">&#x1f4cd;</span>
      <span>No GPS data available</span>
      <span class="map-hint">Send coordinates as <code>{ lat, lng }</code> or <code>{ latitude, longitude }</code> to display a marker.</span>
    </div>
    <div v-if="loadError" class="map-overlay map-error">{{ loadError }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";

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
const noData   = ref(false);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mapInstance: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let marker: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let resizeObserver: ResizeObserver | null = null;

// Default center: Europe (approx center of EU)
const DEFAULT_CENTER: [number, number] = [48.5, 10.0];
const DEFAULT_ZOOM = 4;

const computedHeight = computed(() => {
  return props.height ? `${props.height}px` : '100%';
});

function parseCoords(): { lat: number; lng: number; label?: string } | null {
  const v = props.currentValue;
  if (!v || typeof v !== "object") return null;
  const obj = v as Record<string, unknown>;
  const lat = Number(obj.lat ?? obj.latitude);
  const lng = Number(obj.lng ?? obj.longitude ?? obj.lon);
  if (isNaN(lat) || isNaN(lng)) return null;
  // Reject obviously invalid coordinates
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  return { lat, lng, label: String(obj.label ?? "") };
}

async function initMap() {
  if (!mapRef.value) return;

  const coords = parseCoords();
  noData.value = !coords;

  try {
    // Dynamic import — Leaflet only loads when map widget is actually used
    const L = (await import("leaflet")).default;
    // Import Leaflet CSS — required for proper rendering
    await import("leaflet/dist/leaflet.css");

    // Fix default marker icon paths broken by bundlers (Vite/Webpack)
    // Leaflet tries to auto-detect icon paths from CSS which fails with bundlers
    /* eslint-disable @typescript-eslint/no-require-imports */
    const markerIcon = await import("leaflet/dist/images/marker-icon.png");
    const markerIcon2x = await import("leaflet/dist/images/marker-icon-2x.png");
    const markerShadow = await import("leaflet/dist/images/marker-shadow.png");

    delete (L.Icon.Default.prototype as Record<string, unknown>)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconUrl: markerIcon.default ?? markerIcon,
      iconRetinaUrl: markerIcon2x.default ?? markerIcon2x,
      shadowUrl: markerShadow.default ?? markerShadow,
    });

    const center: [number, number] = coords
      ? [coords.lat, coords.lng]
      : DEFAULT_CENTER;
    const zoom = coords ? 13 : DEFAULT_ZOOM;

    mapInstance = L.map(mapRef.value, {
      zoomControl: true,
      attributionControl: true,
    }).setView(center, zoom);

    // Dark tile layer matching the app's dark theme
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(mapInstance);

    if (coords) {
      marker = L.marker([coords.lat, coords.lng]).addTo(mapInstance);
      if (coords.label) marker.bindPopup(coords.label).openPopup();
    }

    loaded.value = true;

    // Invalidate size after the map container becomes visible / resizes
    await nextTick();
    mapInstance.invalidateSize();

    // Use ResizeObserver to handle container resize (e.g., dashboard grid changes)
    if (mapRef.value && typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        if (mapInstance) mapInstance.invalidateSize();
      });
      resizeObserver.observe(mapRef.value);
    }
  } catch (e) {
    loadError.value = "Map could not be loaded";
    console.warn("[VizMapView] Failed to load Leaflet:", e);
  }
}

function updateMarker() {
  const coords = parseCoords();

  if (!coords) {
    // Data became null — remove marker, show no-data overlay but keep map
    if (marker && mapInstance) {
      marker.remove();
      marker = null;
    }
    noData.value = true;
    // If map exists, pan back to default view
    if (mapInstance) {
      mapInstance.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }
    return;
  }

  noData.value = false;

  // Data appeared but map not yet initialized — init now
  if (!mapInstance) {
    initMap();
    return;
  }

  if (marker) {
    marker.setLatLng([coords.lat, coords.lng]);
    if (coords.label) marker.bindPopup(coords.label);
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
  if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null; }
  if (mapInstance) { mapInstance.remove(); mapInstance = null; }
});
</script>

<style scoped>
.viz-map {
  position: relative;
  width: 100%;
  min-height: 120px;
  border-radius: 4px;
  overflow: hidden;
  background: #161b22;
}
.map-overlay {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  color: #8b949e; font-size: 13px;
  z-index: 800; /* above Leaflet tiles (z-index ~400) but below controls */
  pointer-events: none;
}
.map-no-data {
  background: rgba(17, 17, 16, 0.55);
  color: #8b949e;
}
.map-icon { font-size: 24px; }
.map-error { color: #f85149; background: rgba(17, 17, 16, 0.7); }
.map-hint { font-size: 11px; color: #6e7681; margin-top: 2px; }
.map-hint code {
  background: rgba(255,255,255,0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
}
</style>

<style>
/* Ensure Leaflet controls are visible on dark background */
.leaflet-control-zoom a { background: #1c2128 !important; color: #c9d1d9 !important; border-color: #30363d !important; }
.leaflet-control-attribution { background: rgba(22, 27, 34, 0.8) !important; color: #8b949e !important; font-size: 10px !important; }
.leaflet-control-attribution a { color: #58a6ff !important; }
/* Fix Leaflet popup styling for dark theme */
.leaflet-popup-content-wrapper { background: #1c2128 !important; color: #c9d1d9 !important; border-radius: 6px !important; }
.leaflet-popup-tip { background: #1c2128 !important; }
</style>
