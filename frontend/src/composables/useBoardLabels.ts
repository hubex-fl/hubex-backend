/**
 * Sprint 8 R1-F06 — shared i18n helpers for backend-seeded hardware
 * board-profile metadata.
 *
 * The backend (`app/api/v1/hardware.py` seed logic) ships English
 * `name` and `description` strings on every built-in BoardProfile row
 * (ESP32 DevKit V1, ESP32-C3 Mini, ESP32-S3 DevKit, Raspberry Pi Pico W).
 * Until backend i18n lands, we translate them client-side via the
 * locale files, keyed on the stable `chip` identifier:
 *
 *    hardware.boardNames.<chip>       → translated board name
 *    hardware.boardDescs.<chip>       → translated board description
 *
 * Each lookup falls back to the raw English string the backend sent
 * (so custom user-added boards continue to render their own name),
 * and finally to "Unknown" / "" so the helpers never return undefined.
 *
 * Mirrors the pattern established in `useFeatureLabels.ts` (Sprint 5.a)
 * so /hardware and /hardware/wizard share a single translation surface
 * instead of duplicating inline lookups.
 */
import { useI18n } from "vue-i18n";

interface BoardLike {
  chip: string;
  name?: string | null;
  description?: string | null;
}

export function useBoardLabels() {
  const { t } = useI18n();

  function boardName(board: BoardLike): string {
    const i18nKey = `hardware.boardNames.${board.chip}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    if (board.name) return board.name;
    return "Unknown";
  }

  function boardDescription(board: BoardLike): string {
    const i18nKey = `hardware.boardDescs.${board.chip}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    return board.description || "";
  }

  return { boardName, boardDescription };
}
