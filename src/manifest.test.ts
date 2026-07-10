import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { canonicalProjectReference, loadBenchmarkManifest, projectRoot } from "./manifest.js";

test("manifest references are canonicalized and confined to their own case directory", async () => {
  await mkdir(path.join(projectRoot, "tmp"), { recursive: true });
  const root = await mkdtemp(path.join(projectRoot, "tmp", "manifest-test-"));
  const caseId = "fixture-case";
  const caseDir = path.join(root, "cases", caseId);
  const manifestPath = path.join(root, "manifest.json");
  try {
    await mkdir(caseDir, { recursive: true });
    await Promise.all([
      writeFile(path.join(caseDir, "source.pdf"), "%PDF-fixture", "utf8"),
      writeFile(path.join(caseDir, "gold.md"), "# Fixture\n", "utf8"),
      writeFile(path.join(caseDir, "spec.md"), "# Spec\n", "utf8"),
      writeFile(path.join(caseDir, "facts.json"), "{}\n", "utf8"),
    ]);
    const reference = (file: string) => canonicalProjectReference(path.join(caseDir, file));
    const manifest = {
      schemaVersion: 2,
      name: "Fixture",
      suite: "fixture",
      scoreName: "Fixture score",
      inputProtocol: "native_pdf",
      providerFileModePolicy: "Native PDF",
      version: "1.0.0",
      description: "Manifest containment fixture.",
      caseCount: 1,
      pageCount: 1,
      cases: [
        {
          id: caseId,
          title: "Fixture",
          family: "test",
          tags: ["test"],
          pages: 1,
          pdf: reference("source.pdf"),
          gold: reference("gold.md"),
          spec: reference("spec.md"),
          facts: reference("facts.json"),
        },
      ],
    };
    await writeFile(manifestPath, `${JSON.stringify(manifest)}\n`, "utf8");
    const loaded = await loadBenchmarkManifest(canonicalProjectReference(manifestPath));
    assert.equal(loaded.manifest.cases[0]!.pdf, reference("source.pdf"));
    assert.equal(canonicalProjectReference("./benchmark/manifest.json"), "benchmark/manifest.json");

    manifest.cases[0]!.pdf = "benchmark/cases/P12-pfas-method-validation/source.pdf";
    await writeFile(manifestPath, `${JSON.stringify(manifest)}\n`, "utf8");
    await assert.rejects(loadBenchmarkManifest(canonicalProjectReference(manifestPath)), /fixture-case pdf must resolve to/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
