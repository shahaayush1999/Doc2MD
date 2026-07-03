import { runModel } from "./run.js";
import { scoreModel } from "./score.js";
import { summarizeModel } from "./summary.js";

function parseArgs() {
  const args = new Map<string, string>();
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = process.argv[i + 1];
      args.set(key, next && !next.startsWith("--") ? process.argv[++i] : "true");
    }
  }
  return args;
}

const args = parseArgs();

if (args.has("help")) {
  console.log(`Usage: npm run bench -- --model <model-id> [--concurrency <n>]

Runs the full Doc2MD benchmark for one model:
1. model inference for every case
2. evaluator scoring with structured Zod output
3. deterministic summary aggregation

Default model: vertex-gemini-3.1-flash-lite
Default concurrency: 3`);
  process.exit(0);
}

const modelId = args.get("model") ?? "vertex-gemini-3.1-flash-lite";
const concurrency = Number(args.get("concurrency") ?? "3");

await runModel(modelId, { concurrency });
await scoreModel(modelId);
const summary = await summarizeModel(modelId);

console.log("Final summary:");
console.log(JSON.stringify(summary, null, 2));
