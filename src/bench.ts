import { models, runModel } from "./run.js";
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
  console.log(`Usage: npm run bench -- --model <model-id|all> [--concurrency <n>] [--force]
       npm run bench -- --models <model-a,model-b> [--concurrency <n>] [--force]

Runs the full Doc2MD benchmark:
1. model inference for every case
2. evaluator scoring with structured Zod output
3. deterministic summary aggregation

Unchanged model/case runs and scores are skipped automatically.
Default model: vertex-gemini-3.1-flash-lite
Default concurrency: 3`);
  process.exit(0);
}

function selectedModels() {
  const requested = args.get("models") ?? args.get("model") ?? "vertex-gemini-3.1-flash-lite";
  if (requested === "all") return Object.keys(models);
  const ids = requested
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean);
  for (const id of ids) {
    if (!models[id]) throw new Error(`Unknown model ${id}. Options: ${Object.keys(models).join(", ")}, all`);
  }
  return ids;
}

const concurrency = Number(args.get("concurrency") ?? "3");
const force = args.has("force");

const summaries = [];
for (const modelId of selectedModels()) {
  await runModel(modelId, { concurrency, force });
  await scoreModel(modelId, { force });
  summaries.push(await summarizeModel(modelId));
}

console.log("Final summaries:");
console.log(JSON.stringify(summaries, null, 2));
