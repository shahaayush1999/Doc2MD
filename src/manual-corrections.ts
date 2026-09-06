import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { z } from "zod";
import { scoreFinalAtomicRegions, type FactFile, type JudgeResult, type UnsupportedClaim } from "./evaluator.js";

const memberDecision = z.object({ regionId: z.string().min(1), key: z.string().min(1), reason: z.string().min(1) });
const correctionsSchema = z.object({
  predictionHash: z.string().regex(/^[a-f0-9]{64}$/),
  leaves: z.array(z.object({
    id: z.string().min(1),
    status: z.enum(["correct", "missing", "incorrect"]),
    candidateLineRefs: z.array(z.number().int().positive()),
    reason: z.string().min(1),
  })).default([]),
  rejectedUnsupported: z.array(memberDecision).default([]),
  approvedUnsupported: z.array(memberDecision).default([]),
});

export type ManualCorrections = z.infer<typeof correctionsSchema>;

export async function readManualCorrections(filePath: string): Promise<ManualCorrections | null> {
  try {
    return correctionsSchema.parse(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

const memberKey = (claim: { regionId: string; key: string }) => `${claim.regionId}\u0000${claim.key.normalize("NFKC").toLowerCase().replace(/\s+/g, " ").trim()}`;

/** Apply human decisions last, preserving every other saved final leaf judgment. */
export function applyManualCorrections(facts: FactFile, prediction: string, evaluation: any, value: ManualCorrections) {
  const corrections = correctionsSchema.parse(value);
  if (createHash("sha256").update(prediction).digest("hex") !== corrections.predictionHash) {
    throw new Error("Manual corrections belong to a different prediction; review corrections.json before applying them.");
  }
  if (!evaluation.valid || !evaluation.atomicScore?.regions) {
    throw new Error("Manual corrections require a completed saved evaluation.");
  }
  const lines = prediction.replace(/\r\n/g, "\n").split("\n");
  const leaves = new Map<string, JudgeResult["leafResults"][number]>(
    evaluation.atomicScore.regions.flatMap((region: any) => region.leaves.map((leaf: any) => [leaf.id, {
      id: leaf.id, status: leaf.status, candidateLineRefs: [...leaf.candidateLineRefs],
      ...(leaf.note ? { note: leaf.note } : {}),
    }])),
  );
  const changed = new Set<string>();
  for (const correction of corrections.leaves) {
    if (!leaves.has(correction.id)) throw new Error(`Unknown corrected obligation ${correction.id}.`);
    if (changed.has(correction.id)) throw new Error(`Duplicate correction for ${correction.id}.`);
    changed.add(correction.id);
    const refs = [...new Set(correction.candidateLineRefs)];
    if (refs.some((ref) => !lines[ref - 1]?.trim()) || (correction.status !== "missing" && refs.length === 0)) {
      throw new Error(`Correction ${correction.id} needs nonblank candidate evidence.`);
    }
    leaves.set(correction.id, {
      id: correction.id, status: correction.status,
      candidateLineRefs: correction.status === "missing" ? [] : refs,
      note: `Manual review: ${correction.reason}`,
    });
  }

  const proposals = new Map<string, UnsupportedClaim>();
  for (const claim of [
    ...(evaluation.judgeResult?.unsupportedClaims ?? []),
    ...(evaluation.atomicScore.unsupported?.claims ?? []),
    ...(evaluation.atomicScore.unsupported?.reviewClaims ?? []),
  ] as UnsupportedClaim[]) proposals.set(memberKey(claim), claim);
  const rejected = new Set(corrections.rejectedUnsupported.map(memberKey));
  const approved = new Set(corrections.approvedUnsupported.map(memberKey));
  for (const key of approved) {
    if (rejected.has(key)) throw new Error("The same unsupported claim cannot be approved and rejected.");
    if (!proposals.has(key)) throw new Error("An approved unsupported claim must identify a saved review proposal.");
  }
  const judge: JudgeResult = {
    leafResults: [...leaves.values()],
    unsupportedClaims: [...proposals].filter(([key]) => approved.has(key)).map(([, claim]) => claim),
    rationale: evaluation.judgeResult?.rationale ?? "Saved final judgments with manual corrections.",
  };
  const reviewClaims = [...proposals].filter(([key]) => !approved.has(key) && !rejected.has(key)).map(([, claim]) => claim);
  const atomicScore = scoreFinalAtomicRegions(facts, judge, reviewClaims);
  return {
    ...evaluation,
    score: atomicScore.score,
    atomicScore,
    judgeResult: judge,
    manualCorrections: {
      ...evaluation.manualCorrections,
      predictionHash: corrections.predictionHash,
      leaves: corrections.leaves,
      rejectedUnsupported: corrections.rejectedUnsupported,
      approvedUnsupported: corrections.approvedUnsupported,
    },
  };
}
