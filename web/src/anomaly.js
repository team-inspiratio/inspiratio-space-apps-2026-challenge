// Port of harmonization/anomaly.py. The repository's 25 standard cases are the contract.
export function anomaly(series, target, as_of, baseline = "all") {
  const t = series.find((s) => s.month === target);
  const out = {
    status: "",
    value: null,
    n_ref: 0,
    ref_years: [],
    median: null,
    ratio: null,
    percentile: null,
    level: null,
    preliminary: false,
    notes: [],
  };
  if (!t || t.value == null) {
    out.status = "no_data";
    return out;
  }
  const h = Number(t.value);
  out.value = h;
  out.preliminary = Boolean(t.nrt ?? false);
  if (out.preliminary) out.notes.push("preliminary");
  const [y, m] = target.split("-").map(Number);
  const next = `${y + (m === 12 ? 1 : 0)}-${String((m % 12) + 1).padStart(2, "0")}-01`;
  if (as_of < next) {
    out.status = "month_in_progress";
    return out;
  }
  if (t.input_complete === false) {
    out.status = "incomplete_coverage";
    out.notes.push("incomplete_coverage");
    return out;
  }
  const refs = series
    .filter((s) => {
      const year = Number(s.month.slice(0, 4));
      return (
        s.month.slice(5) === target.slice(5) &&
        year >= 2001 &&
        year < y &&
        s.value != null &&
        s.input_complete !== false &&
        (baseline !== "snpp" || s.source === "snpp")
      );
    })
    .map((s) => [Number(s.month.slice(0, 4)), Number(s.value)])
    .sort((a, b) => a[0] - b[0]);
  out.n_ref = refs.length;
  out.ref_years = refs.map((r) => r[0]);
  if (!refs.length) {
    out.status = "no_history";
    return out;
  }
  const values = refs.map((r) => r[1]).sort((a, b) => a - b);
  out.percentile =
    (100 *
      (values.filter((x) => x < h - 0.005).length +
        0.5 * values.filter((x) => Math.abs(x - h) <= 0.005).length)) /
    values.length;
  out.median = quantile(values, 0.5);
  if (out.median >= 5) out.ratio = h / out.median;
  else out.notes.push("small_median");
  if (refs.length < 10) {
    out.status = "insufficient_history";
    out.notes.push("insufficient_history");
    return out;
  }
  out.level =
    out.percentile >= 90 ? "high" : out.percentile <= 10 ? "low" : "normal";
  out.status = "ok";
  return out;
}

export function quantile(sorted, p) {
  if (!sorted.length) return null;
  const k = (sorted.length - 1) * p,
    i = Math.floor(k),
    f = k - i;
  return sorted[i] + f * ((sorted[i + 1] ?? sorted[i]) - sorted[i]);
}
