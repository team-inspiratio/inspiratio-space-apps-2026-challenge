// Number formatting shared by the atlas and the method page. Pure; unit-tested.
const intFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** Whole number with thousands separators; "—" for missing. */
export const int = (n) =>
  n == null || !Number.isFinite(n) ? "—" : intFmt.format(Math.round(n));

/**
 * Model estimates and area-weighted sums are not exact counts, so they are shown
 * without decimals: below 100 to the nearest whole number, otherwise to three
 * significant figures (11,623.85 → 11,600).
 */
export function roundEstimate(n) {
  if (n == null || !Number.isFinite(n)) return null;
  const a = Math.abs(n);
  if (a < 100) return Math.round(n);
  const step = 10 ** (Math.floor(Math.log10(a)) - 2);
  return Math.round(n / step) * step;
}

/** "≈ 11,600" for estimates; "< 1" for tiny positive values; "0" stays "0". */
export function approx(n) {
  if (n == null || !Number.isFinite(n)) return "—";
  if (n === 0) return "0";
  if (Math.abs(n) < 0.5) return "< 1";
  return "≈ " + intFmt.format(roundEstimate(n));
}

/** Exact integers stay exact; anything else is shown as an approximation. */
export const count = (n, estimated) =>
  n == null || !Number.isFinite(n)
    ? "—"
    : estimated || !Number.isInteger(n)
      ? approx(n)
      : int(n);

/** 96 → "96th", 1 → "1st", 12 → "12th"; percentiles are rounded first. */
export function ordinal(p) {
  const n = Math.round(p),
    mod100 = n % 100;
  const suffix =
    mod100 >= 11 && mod100 <= 13
      ? "th"
      : { 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th";
  return n + suffix;
}
