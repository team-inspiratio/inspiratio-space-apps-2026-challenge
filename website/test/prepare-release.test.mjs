import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { prepareAssets } from "../scripts/prepare-release.mjs";

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "inspiratio-assets-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const source = path.join(root, "inspiratio-site/public/data/global-v1");
  fs.mkdirSync(source, { recursive: true });
  fs.mkdirSync(path.join(root, "results/expected"), { recursive: true });
  const files = {
    "index.json": JSON.stringify({ version: "global-v1", units: [{ file: "california.json.gz" }] }),
    "california.json.gz": "fixture data",
  };
  for (const [name, content] of Object.entries(files)) fs.writeFileSync(path.join(source, name), content);
  const manifest = Object.entries(files).map(([name, content]) =>
    `${createHash("sha256").update(content).digest("hex")}  ${name}`).join("\n");
  fs.writeFileSync(path.join(root, "results/expected/dataset-global-v1.sha256"), manifest);
  return { root, source, out: path.join(root, "website/public/data/global-v1") };
}

test("packages the public catalog and assets without credentials or unused metadata", t => {
  const { root, source, out } = fixture(t);
  prepareAssets(root);
  for (const name of ["index.json", "california.json.gz"])
    assert.deepEqual(fs.readFileSync(path.join(out, name)), fs.readFileSync(path.join(source, name)));
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(out, "ready.json"))).files,
    ["index.json", "california.json.gz"]);
});

test("a corrupt or missing asset invalidates an earlier readiness marker", t => {
  const { root, source, out } = fixture(t);
  prepareAssets(root);
  fs.writeFileSync(path.join(source, "california.json.gz"), "corrupted");
  assert.throws(() => prepareAssets(root), /SHA256 mismatch/);
  assert.equal(fs.existsSync(path.join(out, "ready.json")), false);
  fs.rmSync(path.join(source, "california.json.gz"));
  assert.throws(() => prepareAssets(root), /ENOENT/);
  assert.equal(fs.existsSync(path.join(out, "ready.json")), false);
});
