// Package only checksum-verified assets committed in this public repository.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

export function prepareAssets(root = path.resolve(import.meta.dirname, "../../..")) {
  const source = path.join(root, "inspiratio-site/public/data/global-v1");
  const out = path.join(root, "frontend-v2/website/public/data/global-v1");
  fs.mkdirSync(out, { recursive: true });
  // A failed refresh must never leave the app advertising a complete catalog.
  fs.rmSync(path.join(out, "ready.json"), { force: true });
  const manifest = fs.readFileSync(
    path.join(root, "results/expected/dataset-global-v1.sha256"), "utf8",
  );
  const hashes = new Map(manifest.trim().split(/\r?\n/).map(line => {
    const [digest, name] = line.trim().split(/\s+/);
    return [name, digest];
  }));
  const index = JSON.parse(fs.readFileSync(path.join(source, "index.json"), "utf8"));
  if (index.version !== "global-v1" || !Array.isArray(index.units) || !index.units.length)
    throw Error("Invalid bundled global-v1 catalog");
  const assets = ["index.json", ...index.units.map(unit => unit.file)];
  for (const name of assets) {
    if (typeof name !== "string" || !/^[A-Za-z0-9_-]+\.json(?:\.gz)?$/.test(name))
      throw Error("Invalid bundled asset filename");
    const digest = crypto.createHash("sha256")
      .update(fs.readFileSync(path.join(source, name))).digest("hex");
    if (!hashes.has(name) || digest !== hashes.get(name))
      throw Error("SHA256 mismatch: " + name);
  }
  for (const name of assets) fs.copyFileSync(path.join(source, name), path.join(out, name));
  fs.writeFileSync(path.join(out, "ready.json"), JSON.stringify({
    version: "global-v1",
    files: assets,
    manifest: crypto.createHash("sha256").update(manifest).digest("hex"),
  }));
  console.log(`Verified and packaged ${assets.length} public repository assets.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href)
  prepareAssets();
