/**
 * Sprint 8 R1-F0x — shared i18n helpers for backend-seeded shield
 * profile metadata.
 *
 * The backend (`app/api/v1/hardware.py` seed logic) ships English
 * `name` and `description` strings on every built-in ShieldProfile row
 * (HubEx Arduino Bridge Shield, HubEx RS485 Gateway Module,
 * Sensor Shield DHT22/BMP280/Light). The ShieldProfile model has no
 * stable slug column, only `name`, so we derive a stable slug
 * client-side from the English `name` via `shieldSlug()` and use it as
 * the lookup key:
 *
 *    hardware.shieldNames.<slug>       → translated shield name
 *    hardware.shieldDescs.<slug>       → translated shield description
 *
 * Each lookup falls back to the raw English string the backend sent
 * (so custom user-added shields continue to render their own name),
 * and finally to "Unknown" / "" so the helpers never return undefined.
 *
 * Mirrors the pattern of `useBoardLabels.ts` / `useFeatureLabels.ts`.
 */
import { useI18n } from "vue-i18n";

interface ShieldLike {
  name?: string | null;
  description?: string | null;
}

/**
 * Derive a stable, lowercase, snake_case slug from a shield name.
 * Strips parentheses, replaces non-alphanumerics with underscores,
 * collapses repeats, trims leading/trailing underscores.
 *
 * Examples:
 *   "HubEx Arduino Bridge Shield"          → "hubex_arduino_bridge_shield"
 *   "HubEx RS485 Gateway Module"           → "hubex_rs485_gateway_module"
 *   "Sensor Shield (DHT22 + BMP280 + Light)" → "sensor_shield_dht22_bmp280_light"
 */
export function shieldSlug(name: string | null | undefined): string {
  if (!name) return "";
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function useShieldLabels() {
  const { t } = useI18n();

  function shieldName(shield: ShieldLike): string {
    const slug = shieldSlug(shield.name);
    if (slug) {
      const i18nKey = `hardware.shieldNames.${slug}`;
      const translated = t(i18nKey);
      if (translated && translated !== i18nKey) return translated;
    }
    if (shield.name) return shield.name;
    return "Unknown";
  }

  function shieldDescription(shield: ShieldLike): string {
    const slug = shieldSlug(shield.name);
    if (slug) {
      const i18nKey = `hardware.shieldDescs.${slug}`;
      const translated = t(i18nKey);
      if (translated && translated !== i18nKey) return translated;
    }
    return shield.description || "";
  }

  return { shieldName, shieldDescription };
}
