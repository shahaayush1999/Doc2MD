import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const safeIdentifier = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const repositoryReference = z
  .string()
  .min(1)
  .refine((value) => !path.isAbsolute(value), "must be repository-relative")
  .refine((value) => !value.split(/[\\/]+/).includes(".."), "must not contain a parent traversal");

export const manifestCaseSchema = z.strictObject({
  id: z.string().regex(safeIdentifier),
  title: z.string().min(1),
  family: z.string().min(1),
  tags: z.array(z.string().min(1)).min(1),
  pages: z.number().int().positive(),
  pdf: repositoryReference,
  gold: repositoryReference,
  spec: repositoryReference,
  facts: repositoryReference,
});

export const manifestSchema = z.strictObject({
  schemaVersion: z.literal(2),
  name: z.string().min(1),
  suite: z.string().regex(safeIdentifier),
  scoreName: z.string().min(1),
  inputProtocol: z.literal("native_pdf"),
  providerFileModePolicy: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  description: z.string().min(1),
  caseCount: z.number().int().positive(),
  pageCount: z.number().int().positive(),
  cases: z.array(manifestCaseSchema).min(1),
});

export type BenchmarkManifestCase = z.infer<typeof manifestCaseSchema>;
export type BenchmarkManifest = z.infer<typeof manifestSchema>;
export type LoadedBenchmarkManifest = {
  manifest: BenchmarkManifest;
  manifestPath: string;
  manifestText: string;
};

function formatZodError(error: z.ZodError): string {
  return error.issues.map((issue) => `${issue.path.join(".") || "root"}: ${issue.message}`).join("; ");
}

export function resolveInsideProject(reference: string, label = "path"): string {
  const resolved = path.resolve(projectRoot, reference);
  const relative = path.relative(projectRoot, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} escapes the project root: ${reference}`);
  }
  return resolved;
}

/** Stable repository-relative spelling for any path inside the project. */
export function canonicalProjectReference(reference: string): string {
  const resolved = path.resolve(projectRoot, reference);
  const relative = path.relative(projectRoot, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) return resolved;
  return relative.split(path.sep).join("/");
}

async function requireFile(reference: string, label: string): Promise<string> {
  const resolved = resolveInsideProject(reference, label);
  const details = await stat(resolved).catch(() => null);
  if (!details?.isFile()) throw new Error(`${label} is missing or is not a file: ${reference}`);
  return resolved;
}

export async function loadBenchmarkManifest(manifestReference = "benchmark/manifest.json"): Promise<LoadedBenchmarkManifest> {
  const manifestPath = await requireFile(manifestReference, "benchmark manifest");
  const manifestText = await readFile(manifestPath, "utf8");
  let raw: unknown;
  try {
    raw = JSON.parse(manifestText);
  } catch (error) {
    throw new Error(`Benchmark manifest is not valid JSON: ${manifestReference}`, { cause: error });
  }
  const parsed = manifestSchema.safeParse(raw);
  if (!parsed.success) throw new Error(`Invalid benchmark manifest: ${formatZodError(parsed.error)}`);
  const manifest = parsed.data;
  const caseIds = manifest.cases.map((testCase) => testCase.id);
  if (new Set(caseIds).size !== caseIds.length) throw new Error("Benchmark manifest contains duplicate case ids.");
  if (manifest.caseCount !== manifest.cases.length) {
    throw new Error(`Manifest caseCount ${manifest.caseCount} does not equal ${manifest.cases.length}.`);
  }
  const pageCount = manifest.cases.reduce((sum, testCase) => sum + testCase.pages, 0);
  if (manifest.pageCount !== pageCount) throw new Error(`Manifest pageCount ${manifest.pageCount} does not equal ${pageCount}.`);

  const artifactReferences: Array<{ reference: string; label: string }> = [];
  for (const testCase of manifest.cases) {
    for (const field of ["pdf", "gold", "spec", "facts"] as const) {
      artifactReferences.push({ reference: testCase[field], label: `${testCase.id} ${field}` });
    }
  }
  const resolvedArtifacts = await Promise.all(
    artifactReferences.map(({ reference, label }) => requireFile(reference, label).then((resolved) => ({ reference, resolved }))),
  );
  if (new Set(resolvedArtifacts.map(({ resolved }) => resolved)).size !== resolvedArtifacts.length) {
    throw new Error("Two manifest artifact references resolve to the same file.");
  }

  const artifactNames = { pdf: "source.pdf", gold: "gold.md", spec: "spec.md", facts: "facts.json" } as const;
  for (const testCase of manifest.cases) {
    for (const field of ["pdf", "gold", "spec", "facts"] as const) {
      const actual = resolveInsideProject(testCase[field], `${testCase.id} ${field}`);
      const expected = path.join(path.dirname(manifestPath), "cases", testCase.id, artifactNames[field]);
      if (actual !== expected) {
        throw new Error(`${testCase.id} ${field} must resolve to ${canonicalProjectReference(expected)}.`);
      }
    }
  }

  await Promise.all(
    manifest.cases.map(async (testCase) => {
      const pdfPath = resolveInsideProject(testCase.pdf, `${testCase.id} pdf`);
      const signature = (await readFile(pdfPath)).subarray(0, 5).toString("ascii");
      if (signature !== "%PDF-") throw new Error(`${testCase.id} source is not a PDF file.`);
    }),
  );

  return { manifest, manifestPath, manifestText };
}
