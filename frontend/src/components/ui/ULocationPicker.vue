<template>
  <div class="location-picker">
    <!-- Address search bar -->
    <div class="search-bar">
      <input
        v-model="addressQuery"
        class="search-input"
        :placeholder="t('common.searchAddress')"
        @keydown.enter.prevent="searchAddress"
      />
      <button class="search-btn" @click="searchAddress" :disabled="searching" :title="t('common.search')">
        <svg v-if="!searching" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <svg v-else class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
      </button>
    </div>
    <!-- Search results dropdown -->
    <div v-if="searchResults.length > 0" class="search-results">
      <button
        v-for="(result, i) in searchResults"
        :key="i"
        class="search-result-item"
        @click="selectResult(result)"
      >
        <span class="result-name">{{ result.display_name }}</span>
      </button>
    </div>
    <div v-if="searchError" class="search-error">{{ searchError }}</div>
    <div ref="mapRef" class="picker-map" />
    <p class="picker-hint">{{ t('common.clickMapToSetLocation') }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * ULocationPicker — Leaflet map with address search (Nominatim geocoding).
 * Click the map or search an address to set lat/lng coordinates.
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
const addressQuery = ref("");
const searching = ref(false);
const searchError = ref("");
const searchResults = ref<Array<{ display_name: string; lat: string; lon: string }>>([]);
let map: any = null;
let marker: any = null;

// ── Address search via Nominatim (free, no API key) ─────────────────────
async function searchAddress() {
  const q = addressQuery.value.trim();
  if (!q || q.length < 3) return;

  searching.value = true;
  searchError.value = "";
  searchResults.value = [];

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=5&addressdetails=0`,
      { headers: { "Accept-Language": "de,en" } }
    );
    const data = await response.json();

    if (!data.length) {
      searchError.value = t('common.noAddressFound');
      return;
    }

    if (data.length === 1) {
      // Single result: apply immediately
      selectResult(data[0]);
    } else {
      searchResults.value = data;
    }
  } catch {
    searchError.value = t('common.addressSearchError');
  } finally {
    searching.value = false;
  }
}

function selectResult(result: { lat: string; lon: string; display_name: string }) {
  const lat = parseFloat(result.lat);
  const lng = parseFloat(result.lon);
  searchResults.value = [];
  addressQuery.value = result.display_name;

  emit("update:lat", Math.round(lat * 1000000) / 1000000);
  emit("update:lng", Math.round(lng * 1000000) / 1000000);

  if (map) {
    map.setView([lat, lng], 15);
    if (marker) {
      marker.setLatLng([lat, lng]);
    } else {
      const L = (window as any).L;
      if (L) marker = L.marker([lat, lng]).addTo(map);
    }
  }
}

// ── Map initialization ──────────────────────────────────────────────────
async function initMap() {
  if (!mapRef.value) return;
  try {
    const L = await import("leaflet");
    await import("leaflet/dist/leaflet.css");
    // Store L globally for selectResult to access
    (window as any).L = L;

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
.search-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}
.search-input {
  flex: 1;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-input, var(--bg-surface));
  color: var(--text-primary);
  font-size: 12px;
}
.search-input:focus {
  outline: none;
  border-color: var(--primary);
}
.search-input::placeholder {
  color: var(--text-muted);
}
.search-btn {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
}
.search-btn:hover {
  background: var(--bg-raised);
}
.search-results {
  max-height: 120px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  margin-bottom: 6px;
}
.search-result-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-primary);
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
}
.search-result-item:last-child {
  border-bottom: none;
}
.search-result-item:hover {
  background: var(--bg-raised);
}
.result-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
.search-error {
  font-size: 10px;
  color: var(--text-error, #ef4444);
  margin-bottom: 4px;
}
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
