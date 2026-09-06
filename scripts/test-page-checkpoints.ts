import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { promisify } from "node:util";
import { convertPagesWithCheckpoints, loadSplitPages, type PageRequest } from "../src/page-checkpoints.js";

test("real pdfseparate output stays byte-identical across retries by reusing saved split pages", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "doc2md-split-"));
  const source = path.resolve("benchmark/cases/task-5/source.pdf");
  const pdf = await readFile(source);
  let splits = 0;
  const split = async (destination: string) => {
    splits++;
    await promisify(execFile)("pdfseparate", ["-f", "1", "-l", "2", source, path.join(destination, "page-%d.pdf")]);
  };
  try {
    const first = await loadSplitPages(directory, pdf, split);
    const retry = await loadSplitPages(directory, pdf, split);
    assert.equal(splits, 1);
    assert.equal(first.length, 2);
    assert.deepEqual(retry, first);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("failed pages preserve successful siblings; retries and changed inputs reuse only matching pages", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "doc2md-pages-"));
  const pages: PageRequest[] = [0, 1, 2].map((index) => ({
    pdf: Buffer.from(`PDF ${index}`), prompt: `Page ${index}`, filename: `page-${index}.pdf`,
  }));
  const calls: number[] = [];
  let fail = true;
  const convert = async (_page: PageRequest, index: number) => {
    calls.push(index);
    if (index === 1 && fail) throw new Error("Simulated conversion failure");
    // This page finishes after its sibling rejects and still must reach disk.
    if (index === 2) await new Promise((resolve) => setTimeout(resolve, 15));
    return {
      text: `Reconstructed page ${index}`, resolvedModel: "fake-model",
      usage: { inputTokens: 10, outputTokens: 5, inputTokenDetails: { cacheReadTokens: 0 } },
    };
  };
  try {
    await assert.rejects(convertPagesWithCheckpoints(directory, pages, { model: "one" }, convert), /checkpointed for retry/);
    assert.equal((await readdir(directory)).length, 2);
    calls.length = 0;
    fail = false;
    const retried = await convertPagesWithCheckpoints(directory, pages, { model: "one" }, convert);
    assert.deepEqual(calls, [1]);
    assert.deepEqual(retried.map((page) => page.reused), [true, false, true]);
    assert.deepEqual(retried.map((page) => page.text), pages.map((_, index) => `Reconstructed page ${index}`));
    assert.equal(retried.reduce((sum, page) => sum + page.usage.inputTokens, 0), 30);
    assert.ok(retried.every((page) => page.elapsedMs >= 0));

    calls.length = 0;
    pages[0] = { ...pages[0]!, pdf: Buffer.from("changed PDF") };
    await convertPagesWithCheckpoints(directory, pages, { model: "one" }, convert);
    assert.deepEqual(calls, [0]);

    calls.length = 0;
    pages[2] = { ...pages[2]!, prompt: "changed prompt" };
    await convertPagesWithCheckpoints(directory, pages, { model: "one" }, convert);
    assert.deepEqual(calls, [2]);

    calls.length = 0;
    await convertPagesWithCheckpoints(directory, pages, { model: "two" }, convert);
    assert.deepEqual(calls, [0, 1, 2]);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
