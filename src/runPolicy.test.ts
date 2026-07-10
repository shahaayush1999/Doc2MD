import assert from "node:assert/strict";
import test from "node:test";
import { parseBenchCliArgs } from "./bench.js";
import {
  authorizePaidInference,
  benchmarkModelIds,
  finalValidationAuthorizationEnvironment,
} from "./run.js";

test("benchmark CLI defaults to exactly the two development anchors", () => {
  assert.deepEqual(parseBenchCliArgs([]), { modelIds: [...benchmarkModelIds] });
  assert.deepEqual(parseBenchCliArgs(["--model", "openai-gpt-5-nano"]), {
    modelIds: ["openai-gpt-5-nano"],
  });
});

test("force overwrite is rejected by the benchmark CLI", () => {
  assert.throws(() => parseBenchCliArgs(["--force"]), /--force is disabled/);
});

test("development anchors need no final-validation authorization", () => {
  for (const modelId of benchmarkModelIds) {
    assert.deepEqual(authorizePaidInference(modelId, undefined, {}), {
      runMode: "development_anchor",
      authorizationHash: null,
    });
  }
});

test("non-anchor inference requires a matching, explicitly prefixed checkpoint authorization", () => {
  const modelId = "openai-gpt-5.4-nano";
  const authorization = "final-validation:checkpoint-2026-07-10";
  assert.throws(() => authorizePaidInference(modelId, undefined, {}), /not a development anchor/);
  assert.throws(
    () => authorizePaidInference(modelId, authorization, { [finalValidationAuthorizationEnvironment]: "different" }),
    /requires a checkpoint id/,
  );
  assert.throws(
    () => authorizePaidInference(modelId, "approved", { [finalValidationAuthorizationEnvironment]: "approved" }),
    /requires a checkpoint id/,
  );
  const approved = authorizePaidInference(modelId, authorization, {
    [finalValidationAuthorizationEnvironment]: authorization,
  });
  assert.equal(approved.runMode, "final_validation");
  assert.match(approved.authorizationHash!, /^[a-f0-9]{64}$/);
});

test("benchmark CLI preserves but does not itself manufacture final-validation authorization", () => {
  assert.deepEqual(
    parseBenchCliArgs([
      "--model",
      "openai-gpt-5.4-nano",
      "--final-validation-authorization",
      "final-validation:checkpoint-2026-07-10",
    ]),
    {
      modelIds: ["openai-gpt-5.4-nano"],
      finalValidationAuthorization: "final-validation:checkpoint-2026-07-10",
    },
  );
});
