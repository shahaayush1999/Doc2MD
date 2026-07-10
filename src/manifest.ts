import { readFile } from "node:fs/promises";

export type BenchmarkCase = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  pages: number;
  pdf: string;
  gold: string;
  spec: string;
  facts: string;
};

export type BenchmarkManifest = {
  name: string;
  pageCount: number;
  cases: BenchmarkCase[];
};

export async function loadBenchmarkManifest(manifestPath = "benchmark/manifest.json") {
  const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as BenchmarkManifest;
  if (!Array.isArray(manifest.cases) || manifest.cases.length === 0) throw new Error("Benchmark manifest has no cases.");
  if (new Set(manifest.cases.map((testCase) => testCase.id)).size !== manifest.cases.length) {
    throw new Error("Benchmark manifest has duplicate case ids.");
  }
  await Promise.all(
    manifest.cases.flatMap((testCase) =>
      [testCase.pdf, testCase.gold, testCase.spec, testCase.facts].map(async (filePath) => {
        await readFile(filePath);
      }),
    ),
  );
  return { manifest, manifestPath };
}
