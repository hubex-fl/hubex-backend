/**
 * Sprint 8 Round 2 — shared relative-time formatter.
 *
 * Before this module existed, 9 Vue files had their own copy of the
 * `fmtAge(seconds)` / `fmtRelative(dateStr)` helper, each hardcoding
 * the English strings "Xs ago", "Xm ago", "Xh ago", "Xd ago" directly
 * inside template literals. These leaked into the DE locale and
 * created a systemic i18n bug.
 *
 * This module centralises the formatting through the existing
 * `dashboardsList.relative.*` i18n namespace (set up in Batch 6):
 *
 *     secondsAgo / minutesAgo / hoursAgo / daysAgo (with {n} param)
 *     justNow
 *
 * Usage:
 *
 *     import { fmtAgeSeconds, fmtRelativeIso } from "@/lib/relativeTime";
 *
 *     fmtAgeSeconds(12)    // → "vor 12 Sek" on DE, "12s ago" on EN
 *     fmtAgeSeconds(null)  // → "" (empty string — caller decides on — or similar)
 *     fmtRelativeIso("2026-04-11T10:00:00Z")
 *                         // → "vor 3 Min" on DE, "3m ago" on EN
 *
 * Implementation uses `i18n.global.t()` so it works from both Vue
 * component setup and plain TS modules.
 */
import { i18n } from "../i18n";

/**
 * Format an age in seconds as a relative time string.
 *
 * Returns "" for null / undefined / NaN input.
 * Returns "just now" (locale-translated) for ageSeconds < 1.
 */
export function fmtAgeSeconds(ageSeconds: number | null | undefined): string {
  if (ageSeconds === null || ageSeconds === undefined || Number.isNaN(ageSeconds)) {
    return "";
  }
  const t = i18n.global.t;
  if (ageSeconds < 1) return t("dashboardsList.relative.justNow");
  if (ageSeconds < 60) {
    return t("dashboardsList.relative.secondsAgo", { n: Math.floor(ageSeconds) });
  }
  if (ageSeconds < 3600) {
    return t("dashboardsList.relative.minutesAgo", { n: Math.floor(ageSeconds / 60) });
  }
  if (ageSeconds < 86400) {
    return t("dashboardsList.relative.hoursAgo", { n: Math.floor(ageSeconds / 3600) });
  }
  return t("dashboardsList.relative.daysAgo", { n: Math.floor(ageSeconds / 86400) });
}

/**
 * Format an ISO 8601 date string (or anything `new Date()` understands)
 * as a relative time string from now.
 *
 * Returns "" for empty / invalid input.
 */
export function fmtRelativeIso(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const parsed = new Date(dateStr).getTime();
  if (Number.isNaN(parsed)) return "";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  return fmtAgeSeconds(diffSeconds);
}
