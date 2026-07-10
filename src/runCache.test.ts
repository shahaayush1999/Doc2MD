import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { hashObject, sha256 } from "./cache.js";
import { buildRunContext, models, readCurrentCachedRun, runCacheKey, vertexProviderRoute, type ManifestCase } from "./run.js";

test("explicit Vertex locations use a project-scoped endpoint with API-key authentication", () => {
  const globalModel = models["vertex-gemini-2.5-flash-lite"]!;
  assert.throws(
    () => vertexProviderRoute(globalModel, { GOOGLE_VERTEX_API_KEY: "test-key" }),
    /requires GOOGLE_VERTEX_PROJECT/,
  );
  assert.deepEqual(
    vertexProviderRoute(globalModel, {
      GOOGLE_VERTEX_API_KEY: "test-key",
      GOOGLE_VERTEX_PROJECT: "123456789012",
      GOOGLE_VERTEX_LOCATION: "asia-southeast1",
    }),
    {
      authMode: "express_api_key",
      project: "123456789012",
      location: "global",
      baseURL:
        "https://aiplatform.googleapis.com/v1/projects/123456789012/locations/global/publishers/google",
    },
  );

  const regionalExpressModel = models["vertex-gemini-3.1-flash-lite"]!;
  assert.deepEqual(vertexProviderRoute(regionalExpressModel, { GOOGLE_VERTEX_API_KEY: "test-key" }), {
    authMode: "express_api_key",
    project: null,
    location: null,
    baseURL: null,
  });
});

test("provider file mode is present in hashed execution protocol and cache provenance", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-context-"));
  try {
    const pdfPath = path.join(root, "fixture.pdf");
    await writeFile(pdfPath, "fixture bytes", "utf8");
    const testCase: ManifestCase = { id: "fixture", title: "Fixture", family: "test", pdf: pdfPath };
    const context = await buildRunContext(
      models["openai-gpt-5-nano"]!,
      { name: "Fixture", inputProtocol: "native_pdf", cases: [testCase] },
      path.join(root, "manifest.json"),
    );
    assert.equal(context.protocol.providerFileMode, context.providerFileMode);
    assert.ok(context.protocol.transportEpoch);
    assert.ok(context.protocol.sdkVersions.ai);
    assert.equal(context.protocol.sdkVersions.providerPackage, "@ai-sdk/openai");
    assert.equal(context.protocolHash, hashObject(context.protocol));
    const cache = await runCacheKey(testCase, models["openai-gpt-5-nano"]!, context, "001");
    assert.equal(cache.providerFileMode, context.providerFileMode);

    const changedProtocol = { ...context.protocol, providerFileMode: `${context.providerFileMode}-changed` };
    const changed = await runCacheKey(testCase, models["openai-gpt-5-nano"]!, {
      ...context,
      providerFileMode: changedProtocol.providerFileMode,
      protocol: changedProtocol,
      protocolHash: hashObject(changedProtocol),
    }, "001");
    assert.notEqual(changed.runKey, cache.runKey);
    const changedSample = await runCacheKey(testCase, models["openai-gpt-5-nano"]!, context, "002");
    assert.notEqual(changedSample.runKey, cache.runKey);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("cache reader accepts complete response artifacts and rejects legacy infrastructure errors", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "doc2md-run-cache-"));
  try {
    const predictionPath = path.join(root, "prediction.md");
    const resultPath = path.join(root, "result.json");
    const prediction = "complete prediction";
    const runKey = "a".repeat(64);
    const pdfHash = "b".repeat(64);
    const promptHash = "c".repeat(64);
    const modelConfigHash = "d".repeat(64);
    const protocolHash = "e".repeat(64);
    const inferenceBenchmarkFingerprint = "f".repeat(64);
    const base = {
      artifactStatus: "scoreable_model_response",
      responseReceived: true,
      caseId: "fixture",
      title: "Fixture",
      modelId: "openai-gpt-5-nano",
      modelName: "gpt-5-nano",
      provider: "openai",
      suite: "official",
      manifestPath: "benchmark/manifest.json",
      inputProtocol: "native_pdf",
      providerFileMode: "native file attachment",
      executionProvenance: {
        schemaVersion: 1,
        protocolVersion: "native-pdf-v2",
        inputMode: "native_pdf",
        inputProtocol: "native_pdf",
        mediaType: "application/pdf",
        providerFileMode: "native file attachment",
        maxOutputTokens: 24000,
        maxRetries: 2,
        transportEpoch: "fixture-transport",
        providerPayloadMode: "messages.user.content.file.buffer",
        samplingMode: "provider-default-sampling",
        sdkVersions: { ai: "7.0.11", providerPackage: "@ai-sdk/openai", providerPackageVersion: "4.0.5" },
        promptHash,
        protocolHash,
        pdfHash,
        modelConfigHash,
        inferenceFingerprint: runKey,
        inferenceBenchmarkFingerprint,
      },
      providerMetadata: {
        requested: { provider: "openai", modelId: "gpt-5-nano" },
        resolved: { provider: "openai.responses", modelId: "gpt-5-nano" },
      },
      elapsedMs: 100,
      finishReason: "stop",
      usage: { inputTokens: 10, outputTokens: 2, totalTokens: 12 },
      estimatedCostUsd: 0.0000013,
      pricing: {
        version: "2026-07-10",
        currency: "USD",
        inputPerMillion: 0.05,
        cachedInputPerMillion: 0.005,
        outputPerMillion: 0.4,
        estimatedCostUsd: 0.0000013,
      },
      outputLength: prediction.length,
      sample: "001",
      cache: {
        schemaVersion: 3,
        runKey,
        inferenceFingerprint: runKey,
        sample: "001",
        pdfHash,
        promptHash,
        modelConfigHash,
        protocolHash,
        inferenceBenchmarkFingerprint,
        providerFileMode: "native file attachment",
        predictionHash: sha256(prediction),
      },
      inputMode: "native_pdf",
    };
    const expected = {
      runKey,
      caseId: "fixture",
      modelId: "openai-gpt-5-nano",
      sample: "001",
      suite: "official",
      manifestPath: "benchmark/manifest.json",
      inputProtocol: "native_pdf",
      providerFileMode: "native file attachment",
      protocol: {
        version: "native-pdf-v2",
        inputMode: "native_pdf",
        inputProtocol: "native_pdf",
        mediaType: "application/pdf",
        providerFileMode: "native file attachment",
        maxOutputTokens: 24000,
        maxRetries: 2,
        samplesPerModelCase: 3,
        transportEpoch: "fixture-transport",
        providerPayloadMode: "messages.user.content.file.buffer",
        samplingMode: "provider-default-sampling",
        sdkVersions: { ai: "7.0.11", providerPackage: "@ai-sdk/openai", providerPackageVersion: "4.0.5" },
      },
      inferenceBenchmarkFingerprint,
      protocolHash,
      modelConfigHash,
      pdfHash,
    };
    await writeFile(predictionPath, prediction, "utf8");
    await writeFile(resultPath, JSON.stringify(base), "utf8");
    assert.ok(await readCurrentCachedRun(resultPath, predictionPath, expected));

    // The suite-level fingerprint is summary metadata, not part of this
    // case/sample run identity. Unchanged cases remain reusable when another
    // case in the suite changes.
    assert.ok(
      await readCurrentCachedRun(resultPath, predictionPath, {
        ...expected,
        inferenceBenchmarkFingerprint: "9".repeat(64),
      }),
    );

    await writeFile(resultPath, JSON.stringify({ ...base, manifestPath: "./benchmark/manifest.json" }), "utf8");
    assert.ok(await readCurrentCachedRun(resultPath, predictionPath, expected));
    await writeFile(resultPath, JSON.stringify(base), "utf8");

    assert.equal(await readCurrentCachedRun(resultPath, predictionPath, { ...expected, sample: "002" }), null);

    const { usage: _usage, ...withoutUsage } = base;
    await writeFile(resultPath, JSON.stringify(withoutUsage), "utf8");
    assert.equal(await readCurrentCachedRun(resultPath, predictionPath, expected), null);

    await writeFile(resultPath, JSON.stringify({ ...base, outputLength: prediction.length + 1 }), "utf8");
    assert.equal(await readCurrentCachedRun(resultPath, predictionPath, expected), null);

    await writeFile(resultPath, JSON.stringify({ ...base, error: "disk full" }), "utf8");
    assert.equal(await readCurrentCachedRun(resultPath, predictionPath, expected), null);

    await writeFile(resultPath, JSON.stringify({ ...base, artifactStatus: "infrastructure_error" }), "utf8");
    assert.equal(await readCurrentCachedRun(resultPath, predictionPath, expected), null);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
