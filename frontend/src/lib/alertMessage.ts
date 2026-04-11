/**
 * Sprint 8 R3-F03 fix: legacy AlertEvent message format translation.
 *
 * Background
 * ----------
 * Sprint 3.6 changed the alert-worker output format from the old
 * English-coded form
 *
 *     variable 'temperature' value 20.3 gt 20
 *
 * to the new locale-agnostic symbol form
 *
 *     temperature = 20.3 > 20
 *
 * New alerts fired after Sprint 3.6 use the new format. Pre-existing
 * DB rows from before Sprint 3.6 still have the old format. The
 * Sprint 5.c backfill script `scripts/backfill_alert_format.py`
 * handles this at the DB level but requires an admin to run it
 * manually on the production DB.
 *
 * This helper provides a client-side safety net: every alert
 * message rendered in the UI is run through `formatAlertMessage()`
 * which detects the legacy format and converts it on display. That
 * way:
 *
 *   1. Pre-existing legacy rows still render the modern format even
 *      without the admin running the backfill
 *   2. Any other code path that accidentally emits the legacy format
 *      (backend regression, third-party integration) is also caught
 *   3. Messages in the new format pass through unchanged
 *
 * Symbols match the server-side alert_worker:
 *   gt  → >
 *   gte → ≥
 *   lt  → <
 *   lte → ≤
 *   eq  → =
 *   ne  → ≠
 */

/**
 * Same regex as scripts/backfill_alert_format.py _LEGACY_RE.
 * Captures: key / numeric / op / threshold
 */
const LEGACY_RE =
  /^variable\s+'([^']+)'\s+value\s+(-?\d+(?:\.\d+)?)\s+(gt|gte|lt|lte|eq|ne)\s+(-?\d+(?:\.\d+)?)\s*$/;

const SYMBOLS: Record<string, string> = {
  gt: ">",
  gte: "\u2265",
  lt: "<",
  lte: "\u2264",
  eq: "=",
  ne: "\u2260",
};

/**
 * Normalise an alert message for display. Returns the new symbol
 * format if the input matches the legacy regex; otherwise returns
 * the input unchanged.
 */
export function formatAlertMessage(message: string | null | undefined): string {
  if (!message) return "";
  const match = LEGACY_RE.exec(message);
  if (!match) return message;
  const [, key, numeric, op, threshold] = match;
  const sym = SYMBOLS[op] ?? op;
  return `${key} = ${numeric} ${sym} ${threshold}`;
}
