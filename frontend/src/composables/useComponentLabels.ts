/**
 * Sprint 8 R1-F0x — shared i18n helpers for backend-seeded hardware
 * component (sensor / actuator / display / module) metadata.
 *
 * The backend (`app/api/v1/components.py` seed logic) ships English
 * `name` and `description` strings on every built-in HardwareComponent
 * row (DHT22, BME280, DS18B20, HC-SR04, PIR, BH1750, Relay, Servo,
 * LED PWM, Neopixel, Buzzer, SSD1306, GPS NEO-6M, Analog Input, Push
 * Button). Until backend i18n lands, we translate them client-side
 * via the locale files, keyed on the stable `key` identifier:
 *
 *    hardware.componentNames.<key>     → translated component name
 *    hardware.componentDescs.<key>     → translated component description
 *
 * Each lookup falls back to the raw English string the backend sent
 * (so custom user-added components continue to render their own name),
 * and finally to "Unknown" / "" so the helpers never return undefined.
 *
 * Mirrors the pattern of `useBoardLabels.ts` / `useFeatureLabels.ts`
 * so /hardware/wizard Step 3 shares a single translation surface
 * instead of rendering raw English `c.name` / `c.description`.
 */
import { useI18n } from "vue-i18n";

interface ComponentLike {
  key: string;
  name?: string | null;
  description?: string | null;
}

export function useComponentLabels() {
  const { t } = useI18n();

  function componentName(component: ComponentLike): string {
    const i18nKey = `hardware.componentNames.${component.key}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    if (component.name) return component.name;
    return "Unknown";
  }

  function componentDescription(component: ComponentLike): string {
    const i18nKey = `hardware.componentDescs.${component.key}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    return component.description || "";
  }

  return { componentName, componentDescription };
}
