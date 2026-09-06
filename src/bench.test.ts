import assert from "node:assert/strict";
import test from "node:test";
import { parseOptions, selectCases } from "./bench.js";

test("paid work requires explicit candidate selection", () => {
  assert.throws(() => parseOptions([]), /Select a --candidate/);
  assert.throws(() => parseOptions(["--runs", "3"]), /Select a --candidate/);
});

test("offline report cannot accidentally accept paid run selections", () => {
  assert.equal(parseOptions(["--report-only"]).reportOnly, true);
  for (const args of [["--candidate", "pdftotext"], ["--case", "task-1"], ["--runs", "1"], ["--dry-run"]]) {
    assert.throws(() => parseOptions(["--report-only", ...args]), /cannot be combined/);
  }
});

test("case selection limits work while preserving manifest order", () => {
  const cases = [{ id: "task-1" }, { id: "task-2" }, { id: "task-3" }];
  const parsed = parseOptions(["--candidate", "pdftotext", "--case", "task-3", "--case", "task-1", "--case", "task-1", "--dry-run"]);
  assert.equal(parsed.dryRun, true);
  assert.deepEqual(selectCases(cases, parsed.caseIds), [cases[0], cases[2]]);
  assert.deepEqual(selectCases(cases, []), cases);
  assert.throws(() => selectCases(cases, ["task-typo"]), /Unknown case/);
});

test("unknown flags and malformed runs fail before any work", () => {
  for (const args of [["--runs", "0"], ["--runs", "1.5"], ["--case"], ["--report-onyl"]]) {
    assert.throws(() => parseOptions(["--candidate", "pdftotext", ...args]));
  }
});
