import { hashObject, sha256 } from "./cache.js";

export type AggregationSample = {
  sample: string;
  score: number | null;
  valid: boolean;
  modelCallFailed?: boolean;
  evaluatorFailure?: boolean;
  evaluatorMissingInvalid?: boolean;
  evaluatorStatus?: "valid" | "failed" | "missing_invalid" | "not_required";
  reason?: string;
};

export type AggregationCase = {
  caseId: string;
  samples: AggregationSample[];
};

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function sampleStddev(values: number[]): number | null {
  if (values.length <= 1) return null;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / (values.length - 1));
}

export function aggregateSampleFirst(cases: AggregationCase[], expectedSampleIds: string[]) {
  const invalidSamples: Array<{ caseId: string; sample: string; reason: string }> = [];
  const caseAggregates = cases.map((testCase) => {
    const invalidCountBefore = invalidSamples.length;
    const bySample = new Map<string, AggregationSample[]>();
    for (const sample of testCase.samples) {
      const values = bySample.get(sample.sample) ?? [];
      values.push(sample);
      bySample.set(sample.sample, values);
    }

    for (const sampleId of expectedSampleIds) {
      const matches = bySample.get(sampleId) ?? [];
      if (matches.length === 0) invalidSamples.push({ caseId: testCase.caseId, sample: sampleId, reason: "missing sample" });
      else if (matches.length > 1) invalidSamples.push({ caseId: testCase.caseId, sample: sampleId, reason: "duplicate sample" });
      else if (
        !matches[0]!.valid ||
        matches[0]!.score === null ||
        !Number.isFinite(matches[0]!.score) ||
        matches[0]!.score! < 0 ||
        matches[0]!.score! > 100
      ) {
        invalidSamples.push({
          caseId: testCase.caseId,
          sample: sampleId,
          reason: matches[0]!.reason ?? (matches[0]!.evaluatorFailure ? "evaluator failure" : "invalid score"),
        });
      }
    }
    for (const sampleId of bySample.keys()) {
      if (!expectedSampleIds.includes(sampleId)) invalidSamples.push({ caseId: testCase.caseId, sample: sampleId, reason: "unexpected sample" });
    }

    const validScores = expectedSampleIds
      .map((sampleId) => bySample.get(sampleId)?.[0])
      .filter(
        (sample): sample is AggregationSample & { score: number } =>
          Boolean(sample?.valid && sample.score !== null && Number.isFinite(sample.score) && sample.score >= 0 && sample.score <= 100),
      )
      .map((sample) => sample.score);
    const complete =
      invalidSamples.length === invalidCountBefore &&
      testCase.samples.length === expectedSampleIds.length &&
      validScores.length === expectedSampleIds.length;
    const hasObservedVariability = complete && validScores.length > 1;
    return {
      caseId: testCase.caseId,
      complete,
      score: complete ? mean(validScores) : null,
      scoreMin: hasObservedVariability ? Math.min(...validScores) : null,
      scoreMax: hasObservedVariability ? Math.max(...validScores) : null,
      scoreStddev: hasObservedVariability ? sampleStddev(validScores) : null,
    };
  });

  const complete = cases.length > 0 && invalidSamples.length === 0 && caseAggregates.every((testCase) => testCase.complete);
  const suiteSampleScores = complete
    ? expectedSampleIds.map((sampleId) => ({
        sample: sampleId,
        score: mean(cases.map((testCase) => testCase.samples.find((item) => item.sample === sampleId)!.score!)),
      }))
    : [];
  const suiteScores = suiteSampleScores.map((item) => item.score);

  const hasObservedVariability = complete && suiteScores.length > 1;
  return {
    complete,
    invalidSamples,
    caseAggregates,
    suiteSampleScores,
    score: complete ? mean(suiteScores) : null,
    scoreStddev: hasObservedVariability ? sampleStddev(suiteScores) : null,
    scoreMin: hasObservedVariability ? Math.min(...suiteScores) : null,
    scoreMax: hasObservedVariability ? Math.max(...suiteScores) : null,
  };
}

export const aggregationContractVersion = "equal-case-sample-first-v3-single-draw-null-variability";
export const aggregationContractFingerprint = hashObject({
  version: aggregationContractVersion,
  aggregateSampleFirstHash: sha256(aggregateSampleFirst.toString()),
  sampleStddevHash: sha256(sampleStddev.toString()),
});
