/**
 * Run bounded async work without starting additional paid jobs after the first
 * failure. Already-started jobs are allowed to settle before the error escapes.
 */
export async function runBoundedJobs<T>(jobs: Array<() => Promise<T>>, concurrency: number): Promise<T[]> {
  if (!Number.isSafeInteger(concurrency) || concurrency < 1) throw new Error("Concurrency must be a positive integer.");
  if (jobs.length === 0) return [];
  const results = new Array<T>(jobs.length);
  let cursor = 0;
  let firstError: unknown;

  async function worker() {
    while (firstError === undefined) {
      const index = cursor++;
      if (index >= jobs.length) return;
      try {
        results[index] = await jobs[index]!();
      } catch (error) {
        if (firstError === undefined) firstError = error;
        return;
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, jobs.length) }, () => worker()));
  if (firstError !== undefined) throw firstError;
  return results;
}

/**
 * Start every job immediately, preserve input ordering, and wait for all jobs
 * to settle before surfacing the first failure. This prevents locks from being
 * released while already-started paid work is still running.
 */
export async function runJobsInParallel<T>(jobs: Array<() => Promise<T>>): Promise<T[]> {
  const outcomes = await Promise.all(
    jobs.map(async (job) => {
      try {
        return { ok: true as const, value: await job() };
      } catch (error) {
        return { ok: false as const, error };
      }
    }),
  );
  const failure = outcomes.find((outcome) => !outcome.ok);
  if (failure && !failure.ok) throw failure.error;
  return outcomes.map((outcome) => {
    if (!outcome.ok) throw outcome.error;
    return outcome.value;
  });
}
