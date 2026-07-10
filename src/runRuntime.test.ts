import assert from "node:assert/strict";
import { mkdtemp, readFile, readdir, rm, utimes, writeFile } from "node:fs/promises";
import { hostname, tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import {
  SampleLockError,
  acquireSampleLock,
  atomicWriteJson,
  atomicWriteText,
  calculateTokenCostUsd,
  parseRunCliArgs,
  writeImmutableJson,
} from "./runRuntime.js";

test("cached-token pricing separates cached and uncached input", () => {
  const cost = calculateTokenCostUsd(
    { inputPerMillion: 2, cachedInputPerMillion: 0.2, outputPerMillion: 12 },
    {
      inputTokens: 1_500_000,
      outputTokens: 200_000,
      inputTokenDetails: { cacheReadTokens: 500_000 },
    },
  );
  assert.equal(cost, 4.5);
});

test("cached-token pricing clamps malformed token counts", () => {
  const pricing = { inputPerMillion: 2, cachedInputPerMillion: 0.2, outputPerMillion: 12 };
  assert.equal(
    calculateTokenCostUsd(pricing, {
      inputTokens: 1_000_000,
      outputTokens: -5,
      inputTokenDetails: { cacheReadTokens: 2_000_000 },
    }),
    0.2,
  );
  assert.equal(calculateTokenCostUsd(pricing, null), 0);
});

test("run CLI accepts one optional positional model and strict flags", () => {
  assert.deepEqual(parseRunCliArgs([]), {
    modelId: "vertex-gemini-3.1-flash-lite",
    help: false,
  });
  assert.deepEqual(parseRunCliArgs(["openai-gpt-5-nano", "--case", "P07", "--manifest", "suite.json"]), {
    modelId: "openai-gpt-5-nano",
    caseId: "P07",
    manifestPath: "suite.json",
    help: false,
  });
  assert.deepEqual(
    parseRunCliArgs([
      "--model",
      "openai-gpt-5.4-nano",
      "--final-validation-authorization",
      "final-validation:checkpoint-1",
    ]),
    {
      modelId: "openai-gpt-5.4-nano",
      finalValidationAuthorization: "final-validation:checkpoint-1",
      help: false,
    },
  );
});

test("run CLI rejects unknown, duplicate, missing, conflicting, and extra arguments", () => {
  assert.throws(() => parseRunCliArgs(["--wat"]), /Unknown option --wat/);
  assert.throws(() => parseRunCliArgs(["--case"]), /--case requires a value/);
  assert.throws(() => parseRunCliArgs(["--case", "a", "--case", "b"]), /Duplicate option --case/);
  assert.throws(() => parseRunCliArgs(["model-a", "model-b"]), /Unexpected positional argument model-b/);
  assert.throws(() => parseRunCliArgs(["model-a", "--model", "model-b"]), /both positionally and with --model/);
  assert.throws(() => parseRunCliArgs(["--force"]), /--force is disabled/);
  assert.throws(
    () => parseRunCliArgs(["--final-validation-authorization"]),
    /--final-validation-authorization requires a value/,
  );
});

test("atomic writers replace complete text and JSON without leaving temp files", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-atomic-"));
  try {
    const textPath = path.join(root, "prediction.md");
    const jsonPath = path.join(root, "result.json");
    await writeFile(textPath, "old", "utf8");
    await atomicWriteText(textPath, "new prediction");
    await atomicWriteJson(jsonPath, { ok: true });
    assert.equal(await readFile(textPath, "utf8"), "new prediction");
    assert.equal(await readFile(jsonPath, "utf8"), '{\n  "ok": true\n}\n');
    assert.deepEqual((await readdir(root)).sort(), ["prediction.md", "result.json"]);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("immutable JSON markers are create-once and preserve their first value", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-immutable-"));
  try {
    const markerPath = path.join(root, "attempts", "run-key.json");
    await writeImmutableJson(markerPath, { attempt: 1 });
    await assert.rejects(writeImmutableJson(markerPath, { attempt: 2 }), (error: unknown) => {
      return (error as NodeJS.ErrnoException).code === "EEXIST";
    });
    assert.equal(await readFile(markerPath, "utf8"), '{\n  "attempt": 1\n}\n');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("sample locks are exclusive, owner-checked, and reusable after release", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-lock-"));
  const lockPath = path.join(root, ".sample.lock");
  try {
    const first = await acquireSampleLock(lockPath);
    await assert.rejects(acquireSampleLock(lockPath), (error: unknown) => error instanceof SampleLockError && /active lock/.test(error.message));
    await utimes(lockPath, new Date(0), new Date(0));
    await assert.rejects(
      acquireSampleLock(lockPath, { staleAfterMs: 1 }),
      (error: unknown) => error instanceof SampleLockError && !error.stale && /active lock/.test(error.message),
    );
    await first.release();
    const second = await acquireSampleLock(lockPath);
    await second.release();
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("stale sample locks abort clearly instead of being deleted unsafely", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-stale-lock-"));
  const lockPath = path.join(root, ".sample.lock");
  try {
    await writeFile(
      lockPath,
      JSON.stringify({ schemaVersion: 1, token: "abandoned", pid: 999_999_999, hostname: hostname(), createdAt: "2000-01-01T00:00:00.000Z" }),
      "utf8",
    );
    await assert.rejects(
      acquireSampleLock(lockPath),
      (error: unknown) => error instanceof SampleLockError && /stale lock detected/i.test(error.message) && /remove it only after verifying/i.test(error.message),
    );
    assert.equal(await readFile(lockPath, "utf8").then(() => true), true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
