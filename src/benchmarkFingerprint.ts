import { fileSha256, hashObject, sha256 } from "./cache.js";
import { loadBenchmarkManifest, resolveInsideProject } from "./manifest.js";

export type BenchmarkArtifactFingerprint = {
  caseId: string;
  pdfHash: string;
  goldHash: string;
  specHash: string;
  factsHash: string;
};

export type BenchmarkFingerprint = {
  benchmarkFingerprint: string;
  manifestHash: string;
  inputProtocol: string;
  promptHash: string;
  scoringContractFingerprint: string;
  artifacts: BenchmarkArtifactFingerprint[];
};

export async function buildBenchmarkFingerprint(options: {
  manifestPath: string;
  promptHash: string;
  scoringContractFingerprint: string;
}): Promise<BenchmarkFingerprint> {
  const { manifest, manifestText } = await loadBenchmarkManifest(options.manifestPath);

  const artifacts = await Promise.all(
    manifest.cases.map(async (testCase) => {
      for (const field of ["pdf", "gold", "spec", "facts"] as const) {
        if (!testCase[field]) {
          throw new Error(`Benchmark case ${testCase.id} is missing ${field} in ${options.manifestPath}`);
        }
      }
      const [pdfPath, goldPath, specPath, factsPath] = [
        resolveInsideProject(testCase.pdf),
        resolveInsideProject(testCase.gold),
        resolveInsideProject(testCase.spec),
        resolveInsideProject(testCase.facts),
      ];
      const [pdfHash, goldHash, specHash, factsHash] = await Promise.all([
        fileSha256(pdfPath),
        fileSha256(goldPath),
        fileSha256(specPath),
        fileSha256(factsPath),
      ]);
      return { caseId: testCase.id, pdfHash, goldHash, specHash, factsHash };
    }),
  );

  const manifestHash = sha256(manifestText);
  const inputProtocol = manifest.inputProtocol;
  const benchmarkFingerprint = hashObject({
    schemaVersion: 2,
    manifestHash,
    inputProtocol,
    promptHash: options.promptHash,
    scoringContractFingerprint: options.scoringContractFingerprint,
    artifacts,
  });
  return {
    benchmarkFingerprint,
    manifestHash,
    inputProtocol,
    promptHash: options.promptHash,
    scoringContractFingerprint: options.scoringContractFingerprint,
    artifacts,
  };
}
