import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { buildCohortArtifactFingerprint } from "./cohortFingerprint.js";

test("cohort fingerprint changes when any committed run, prediction, or score artifact changes", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-cohort-"));
  try {
    const sampleDir = path.join(root, "model-a", "case-a", "samples", "001");
    await mkdir(sampleDir, { recursive: true });
    await Promise.all([
      writeFile(path.join(sampleDir, "prediction.md"), "prediction one", "utf8"),
      writeFile(path.join(sampleDir, "result.json"), "{\"run\":1}\n", "utf8"),
      writeFile(path.join(sampleDir, "score.json"), "{\"score\":1}\n", "utf8"),
    ]);
    const before = await buildCohortArtifactFingerprint("model-a", "official", [{ id: "case-a" }], 1, root);
    await writeFile(path.join(sampleDir, "score.json"), "{\"score\":2}\n", "utf8");
    const after = await buildCohortArtifactFingerprint("model-a", "official", [{ id: "case-a" }], 1, root);
    assert.notEqual(after, before);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
