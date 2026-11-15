// Published harmonized outputs only; no raw satellite records.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
const root = path.resolve(import.meta.dirname, "../..");
const out = path.join(root, "frontend-v2/public/data/global-v1");
const manifest = fs.readFileSync(
  path.join(root, "results/expected/dataset-global-v1.sha256"),
  "utf8",
);
const hashes = new Map(
  manifest
    .trim()
    .split("\n")
    .map((l) => {
      const [hash, name] = l.trim().split(/\s+/);
      return [name, hash];
    }),
);
const assets = [...hashes.keys()].filter(
  (n) => n.endsWith(".json.gz") || ["index.json", "meta.json"].includes(n),
);
const hash = (p) =>
  crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
fs.mkdirSync(out, { recursive: true });
execFileSync(
  path.join(root, ".venv/bin/python"),
  [
    "-c",
    'import datetime as d; from tools.guardrails import assert_download_allowed; assert_download_allowed("published harmonized global-v1 frontend",d.date(2000,11,1),d.date(2026,10,31))',
  ],
  { cwd: root, stdio: "inherit" },
);
for (const name of assets) {
  const dest = path.join(out, name);
  if (fs.existsSync(dest) && hash(dest) === hashes.get(name)) continue;
  const temp = path.join(out, ".download");
  fs.mkdirSync(temp, { recursive: true });
  execFileSync(
    "gh",
    [
      "release",
      "download",
      "global-v1",
      "--repo",
      "team-inspiratio/inspiratio-space-apps-2026",
      "--pattern",
      name,
      "--dir",
      temp,
      "--clobber",
    ],
    { stdio: "inherit" },
  );
  const file = path.join(temp, name);
  if (hash(file) !== hashes.get(name)) throw Error("SHA256 mismatch: " + name);
  fs.renameSync(file, dest);
  console.log("Verified", name);
}
// Sentinel is written only after every file verifies. The app will not mix partial releases.
fs.writeFileSync(
  path.join(out, "ready.json"),
  JSON.stringify({
    version: "global-v1",
    files: assets,
    manifest: crypto.createHash("sha256").update(manifest).digest("hex"),
  }),
);
console.log("Global frontend assets verified. Rebuild to include them.");
