# Doc2MD Working Instructions

## Primary guiding principle

**FOCUS ON ACCURACY, NOT PRECISION.**

The purpose of this repository is to produce a useful, accurate, informal comparison. It is not a methodology-engineering project, and methodological perfection is not a goal.

- Prefer the most useful, evidence-grounded answer over procedural or methodological purity.
- Keep the benchmark and its implementation as simple as possible. Do not introduce infrastructure, abstraction, measurement, or process unless it materially improves the answer.
- Manual intervention is allowed and encouraged when it improves accuracy or avoids waste. This includes manually reviewing and correcting evaluator mistakes, migrating or reusing valid caches and checkpoints, and correcting individual result artifacts by hand.
- Do not rerun otherwise valid work solely for cache purity, evaluator-version uniformity, provenance purity, or methodological consistency.
- Do not incur unnecessary API cost, rate-limit usage, or execution time merely to make the process formally uniform.
- When an automated judgment looks suspicious, inspect the source facts and candidate output and use grounded human judgment. The evaluator is a convenience, not an authority.
- Make manual corrections transparently with a short note describing what changed and why. Do not build an elaborate audit system for them.
- Preserve existing useful results whenever reasonable. A global regrade or cache invalidation requires a concrete accuracy benefit and should not happen merely because an implementation detail changed.
- If accuracy and consistency conflict, choose accuracy. If a simple manual correction and a large automated rerun reach the same useful result, choose the manual correction.
