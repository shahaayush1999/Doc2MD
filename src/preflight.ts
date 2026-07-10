import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { z } from "zod";
import { loadBenchmarkManifest, projectRoot, resolveInsideProject } from "./manifest.js";
import { parseFactFile } from "./score.js";

const execFileAsync = promisify(execFile);

const providerCapabilitiesSchema = z.strictObject({
  schemaVersion: z.literal(1),
  lastReviewed: z.string().min(1),
  notes: z.array(z.string()),
  providers: z.record(
    z.string(),
    z.object({
      documents: z.record(
        z.string(),
        z.object({
          supported: z.boolean(),
          ingestionMode: z.string().min(1),
        }).passthrough(),
      ),
    }).passthrough(),
  ),
});

type PythonValidation = {
  ok?: boolean;
  errors?: unknown;
  warnings?: unknown;
  cases?: unknown;
};

export async function preflightBenchmark(manifestReference = "benchmark/manifest.json") {
  const loaded = await loadBenchmarkManifest(manifestReference);
  if (path.basename(loaded.manifestPath) !== "manifest.json") {
    throw new Error("The benchmark manifest must be named manifest.json so the Python artifact validator can inspect its directory.");
  }

  await Promise.all(
    loaded.manifest.cases.map(async (testCase) => {
      const rawFacts = JSON.parse(await readFile(resolveInsideProject(testCase.facts), "utf8"));
      parseFactFile(rawFacts, { caseId: testCase.id, pages: testCase.pages });
    }),
  );

  const capabilitiesReference = path
    .relative(projectRoot, path.join(path.dirname(loaded.manifestPath), "provider-capabilities.json"))
    .split(path.sep)
    .join("/");
  const capabilities = providerCapabilitiesSchema.parse(
    JSON.parse(await readFile(resolveInsideProject(capabilitiesReference, "provider capabilities"), "utf8")),
  );
  for (const provider of ["openai", "google-vertex"] as const) {
    const pdf = capabilities.providers[provider]?.documents?.pdf;
    if (!pdf?.supported || !pdf.ingestionMode) throw new Error(`Provider capabilities do not declare supported PDF handling for ${provider}.`);
  }

  const benchmarkRoot = path.dirname(loaded.manifestPath);
  let stdout: string;
  let stderr: string;
  try {
    ({ stdout, stderr } = await execFileAsync(
      "uv",
      ["run", "python", "scripts/validate_benchmark.py", "--benchmark", benchmarkRoot, "--json"],
      { cwd: projectRoot, maxBuffer: 16 * 1024 * 1024 },
    ));
  } catch (error) {
    const details = error as Error & { stdout?: string; stderr?: string };
    throw new Error(
      `Benchmark artifact validation failed before inference.${details.stdout ? `\n${details.stdout.trim()}` : ""}${
        details.stderr ? `\n${details.stderr.trim()}` : ""
      }`,
      { cause: error },
    );
  }
  let validation: PythonValidation;
  try {
    validation = JSON.parse(stdout) as PythonValidation;
  } catch (error) {
    throw new Error(`Benchmark validator did not return JSON.${stderr ? `\n${stderr.trim()}` : ""}`, { cause: error });
  }
  if (validation.ok !== true) throw new Error(`Benchmark validator rejected the suite: ${JSON.stringify(validation.errors)}`);
  const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];
  if (warnings.length > 0) {
    throw new Error(`Benchmark validator returned release-blocking warning(s): ${warnings.map(String).join(" | ")}`);
  }

  return {
    manifest: loaded.manifest,
    manifestPath: loaded.manifestPath,
    caseCount: loaded.manifest.caseCount,
    pageCount: loaded.manifest.pageCount,
    warnings,
    cases: Array.isArray(validation.cases) ? validation.cases : [],
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const argv = process.argv.slice(2);
  let manifestPath = "benchmark/manifest.json";
  if (argv.length > 0) {
    if (argv.length !== 2 || argv[0] !== "--manifest" || !argv[1] || argv[1].startsWith("--")) {
      throw new Error("Usage: npm run preflight -- [--manifest PATH]");
    }
    manifestPath = argv[1];
  }
  const result = await preflightBenchmark(manifestPath);
  console.log(`Preflight passed: ${result.caseCount} cases / ${result.pageCount} pages, zero warnings.`);
}
