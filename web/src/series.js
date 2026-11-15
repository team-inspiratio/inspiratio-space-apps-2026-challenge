// Yearly totals and the "why is this blank?" rules. Pure; unit-tested.

/**
 * Sum each year's months. A year only gets a total when every month the
 * dataset has for that year passes `usable(t)`; otherwise the total is null,
 * so a year with one month of data never plots as a tiny value.
 * `partial` marks years the dataset itself only partly covers (2000, 2026).
 */
export function annualTotals(months, values, usable = (t) => values[t] != null) {
  const byYear = new Map();
  months.forEach((m, t) => {
    const y = +m.slice(0, 4);
    if (!byYear.has(y)) byYear.set(y, []);
    byYear.get(y).push(t);
  });
  const out = new Map();
  for (const [y, idx] of byYear) {
    const complete = idx.every(usable);
    out.set(y, {
      total: complete ? idx.reduce((s, t) => s + values[t], 0) : null,
      complete,
      months: idx.length,
      partial: idx.length < 12,
    });
  }
  return out;
}

/** Which sensor a direct-splice month comes from (dataset v1 definition of M0). */
export const spliceSource = (month) =>
  month < "2002-07"
    ? "Terra MODIS as recorded"
    : month < "2012-02"
      ? "Aqua MODIS as recorded"
      : "S-NPP VIIRS as recorded";

/**
 * Why a direct-splice value is missing. The splice is MODIS as recorded until
 * 2012-01 and S-NPP VIIRS after; the gaps have different causes.
 */
export function spliceGapReason(data, splice, t) {
  const month = data.months[t];
  if (splice[t] != null) return null;
  if (data.role === "holdout")
    return "No VIIRS here: this region's VIIRS data were held out to test the model, so the splice stops in 2012-01.";
  if (month >= "2012-02" && month <= "2013-12")
    return "S-NPP VIIRS for 2012–13 is withheld for the one-time blind test; only the external grader has it.";
  if (data.month_source[t] === "noaa20_scaled")
    return "S-NPP VIIRS has an outage this month; the harmonized view fills it with scaled NOAA-20.";
  return "No source data for this month.";
}
