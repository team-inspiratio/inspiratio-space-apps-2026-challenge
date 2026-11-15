// Frontend packaging only: reads published v1 assets; never downloads FIRMS or fits a model.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { gzipSync, gunzipSync } from "node:zlib";
import {
  asyncBufferFromFile,
  parquetMetadataAsync,
  parquetRead,
} from "hyparquet";
import { compressors } from "hyparquet-compressors";

const root = path.resolve(import.meta.dirname, ".."),
  out = path.join(root, "public/data/v1");
const raw = path.join(root, ".source-data");
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync(raw, { recursive: true });
const repo = "team-inspiratio/inspiratio-space-apps-2026-challenge";
const regions = [
  "california",
  "cordoba",
  "southern_africa",
  "north_australia",
  "central_siberia",
  "indo_gangetic",
];
const small = [
  ...regions.map((r) => r + ".json.gz"),
  "meta.json",
  "SHA256SUMS.txt",
  "anomaly-cases.json",
  "data-card.md",
  "data-interface.md",
  "region_totals_v1.csv",
];
const sha = (p) =>
  crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
async function ensureAsset(dir, name, hash) {
  const p = path.join(dir, name);
  if (fs.existsSync(p) && sha(p) === hash) return;
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      execFileSync(
        "gh",
        [
          "release",
          "download",
          "v1",
          "--repo",
          repo,
          "-D",
          dir,
          "-p",
          name,
          "--clobber",
        ],
        { stdio: "inherit" },
      );
      if (sha(p) !== hash) throw Error("Checksum mismatch: " + name);
      return;
    } catch (error) {
      if (attempt === 3) throw error;
      console.log(`Retrying published asset ${name} (${attempt + 1}/3)`);
      await new Promise((resolve) => setTimeout(resolve, 750 * 2 ** attempt));
    }
  }
}
const sums = path.join(out, "SHA256SUMS.txt");
await ensureAsset(
  out,
  "SHA256SUMS.txt",
  "35e505942288739bb4dc059aefdfa9eb2c1f205553ac9d096b5368641bc5c76e",
);
if (
  sha(sums) !==
  "35e505942288739bb4dc059aefdfa9eb2c1f205553ac9d096b5368641bc5c76e"
)
  throw Error("v1 checksum manifest differs from the reviewed release");
const expected = Object.fromEntries(
  fs
    .readFileSync(sums, "utf8")
    .trim()
    .split(/\r?\n/)
    .map((l) => {
      const [hash, ...name] = l.trim().split(/\s+/);
      return [name.join(" ").replace(/^\*/, ""), hash];
    }),
);
for (const name of [
  ...small.filter((n) => n !== "SHA256SUMS.txt"),
  "dataset_v1.parquet",
  "resamples20_v1.parquet",
]) {
  const p = path.join(name.endsWith(".parquet") ? raw : out, name);
  if (!expected[name])
    throw Error("Asset absent from reviewed manifest: " + name);
  await ensureAsset(path.dirname(p), name, expected[name]);
}
console.log("Published v1 checksums verified.");
const data = regions.map((r) =>
  JSON.parse(gunzipSync(fs.readFileSync(path.join(out, r + ".json.gz")))),
);
const T = data[0].months.length,
  N = 20;
const time = new Map(data[0].months.map((m, t) => [m, t]));
const cells = new Map();
const draws = data.map((d) => new Float32Array(d.cells.lat_idx.length * T * N));
const fields = ["est_m0", "aqua_count", "terra_count", "snpp_count"];
const originals = data.map((d) =>
  new Float32Array(d.cells.lat_idx.length * T * fields.length).fill(NaN),
);
data.forEach((d, r) =>
  d.cells.lat_idx.forEach((i, k) =>
    cells.set(i * 1440 + d.cells.lon_idx[k], [r, k]),
  ),
);

async function columns(name, types) {
  const file = await asyncBufferFromFile(path.join(raw, name));
  const count = Number((await parquetMetadataAsync(file)).num_rows);
  const result = Object.fromEntries(
    Object.entries(types).map(([k, C]) => [k, new C(count)]),
  );
  await parquetRead({
    file,
    columns: Object.keys(types),
    compressors,
    onChunk({ columnName, columnData, rowStart }) {
      const dest = result[columnName];
      for (let i = 0; i < columnData.length; i++)
        dest[rowStart + i] =
          columnName === "month"
            ? time.get(columnData[i])
            : (columnData[i] ?? NaN);
    },
  });
  return result;
}
let c = await columns("resamples20_v1.parquet", {
  lat_idx: Int16Array,
  lon_idx: Int16Array,
  month: Uint16Array,
  resample: Uint8Array,
  value: Float32Array,
});
for (let n = 0; n < c.value.length; n++) {
  const loc = cells.get(c.lat_idx[n] * 1440 + c.lon_idx[n]);
  if (!loc) throw Error("Unknown resampling cell");
  const [r, k] = loc,
    b = c.resample[n];
  if (b >= N) throw Error("Unexpected resampling index " + b);
  draws[r][(k * T + c.month[n]) * N + b] = c.value[n];
}
c = null;
console.log("20 published resamples reshaped for browser use.");
c = await columns("dataset_v1.parquet", {
  lat_idx: Int16Array,
  lon_idx: Int16Array,
  month: Uint16Array,
  ...Object.fromEntries(fields.map((f) => [f, Float32Array])),
});
for (let n = 0; n < c.lat_idx.length; n++) {
  const [r, k] = cells.get(c.lat_idx[n] * 1440 + c.lon_idx[n]);
  fields.forEach((f, j) => {
    originals[r][(k * T + c.month[n]) * fields.length + j] = c[f][n];
  });
}
const generated = [];
for (let r = 0; r < data.length; r++)
  for (const [suffix, values] of [
    ["draws", draws[r]],
    ["raw", originals[r]],
  ]) {
    const name = regions[r] + "." + suffix + ".f32.gz",
      p = path.join(out, name);
    fs.writeFileSync(
      p,
      gzipSync(Buffer.from(values.buffer), { level: 9, mtime: 0 }),
    );
    generated.push({ name, sha256: sha(p), bytes: fs.statSync(p).size });
    console.log(name, fs.statSync(p).size);
  }
const manifest = {
  version: "v1",
  release: `https://github.com/${repo}/releases/tag/v1`,
  release_manifest_sha256: sha(sums),
  regions,
  months: T,
  draws: N,
  layout: "little-endian float32, [cell][month][draw or raw field]",
  raw_fields: fields,
  generated,
};
fs.writeFileSync(
  path.join(out, "browser-assets.json"),
  JSON.stringify(manifest, null, 2) + "\n",
);
console.log("Frontend assets prepared; no scientific estimates changed.");
