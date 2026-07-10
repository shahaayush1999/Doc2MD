import assert from "node:assert/strict";
import test from "node:test";
import { runBoundedJobs, runJobsInParallel } from "./concurrency.js";

test("bounded jobs stop pulling new work after failure and await in-flight work", async () => {
  const started: number[] = [];
  let inFlightSettled = false;
  const failure = new Error("stop");
  const jobs = [
    async () => {
      started.push(0);
      await new Promise((resolve) => setTimeout(resolve, 15));
      inFlightSettled = true;
      return 0;
    },
    async () => {
      started.push(1);
      throw failure;
    },
    async () => {
      started.push(2);
      return 2;
    },
  ];

  await assert.rejects(runBoundedJobs(jobs, 2), (error) => error === failure);
  assert.equal(inFlightSettled, true);
  assert.deepEqual(started, [0, 1]);
});

test("parallel jobs start the full cohort and await every job before surfacing a failure", async () => {
  const started: number[] = [];
  let slowJobSettled = false;
  const failure = new Error("stop");
  const jobs = [
    async () => {
      started.push(0);
      await new Promise((resolve) => setTimeout(resolve, 15));
      slowJobSettled = true;
      return 0;
    },
    async () => {
      started.push(1);
      throw failure;
    },
    async () => {
      started.push(2);
      return 2;
    },
  ];

  await assert.rejects(runJobsInParallel(jobs), (error) => error === failure);
  assert.equal(slowJobSettled, true);
  assert.deepEqual(started, [0, 1, 2]);
});
