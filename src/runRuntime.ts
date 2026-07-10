import { randomUUID } from "node:crypto";
import { mkdir, open, readFile, rename, rm, stat } from "node:fs/promises";
import { hostname } from "node:os";
import path from "node:path";

export type TokenPricing = {
  inputPerMillion: number;
  cachedInputPerMillion: number;
  outputPerMillion: number;
};

export type TokenUsageLike = {
  inputTokens?: number | null;
  outputTokens?: number | null;
  inputTokenDetails?: {
    cacheReadTokens?: number | null;
  } | null;
} | null;

function nonnegativeFinite(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, value) : 0;
}

export function calculateTokenCostUsd(pricing: TokenPricing, usage: TokenUsageLike): number {
  const inputTokens = nonnegativeFinite(usage?.inputTokens);
  const cachedInputTokens = Math.min(inputTokens, nonnegativeFinite(usage?.inputTokenDetails?.cacheReadTokens));
  const uncachedInputTokens = inputTokens - cachedInputTokens;
  const outputTokens = nonnegativeFinite(usage?.outputTokens);
  return (
    (uncachedInputTokens / 1_000_000) * nonnegativeFinite(pricing.inputPerMillion) +
    (cachedInputTokens / 1_000_000) * nonnegativeFinite(pricing.cachedInputPerMillion) +
    (outputTokens / 1_000_000) * nonnegativeFinite(pricing.outputPerMillion)
  );
}

async function atomicWrite(filePath: string, content: string | Uint8Array): Promise<void> {
  const directory = path.dirname(filePath);
  await mkdir(directory, { recursive: true });
  const temporaryPath = path.join(directory, `.${path.basename(filePath)}.${process.pid}.${randomUUID()}.tmp`);
  let handle;
  try {
    handle = await open(temporaryPath, "wx", 0o644);
    await handle.writeFile(content);
    await handle.sync();
    await handle.close();
    handle = undefined;
    await rename(temporaryPath, filePath);
  } catch (error) {
    if (handle) await handle.close().catch(() => undefined);
    await rm(temporaryPath, { force: true }).catch(() => undefined);
    throw error;
  }
}

export async function atomicWriteText(filePath: string, content: string): Promise<void> {
  await atomicWrite(filePath, content);
}

export async function atomicWriteJson(filePath: string, value: unknown): Promise<void> {
  await atomicWrite(filePath, JSON.stringify(value, null, 2) + "\n");
}

export const defaultRunModelId = "vertex-gemini-3.1-flash-lite";

export type RunCliArgs = {
  modelId: string;
  caseId?: string;
  manifestPath?: string;
  force: boolean;
  help: boolean;
};

export const runUsage = `Usage: npm run run -- [model-id] [--case CASE_ID] [--manifest PATH] [--force]

The model id is optional and must be the first positional argument. --model MODEL_ID is also accepted as an alternative.
Options:
  --model MODEL_ID  Select a model without using the positional form.
  --case CASE_ID     Run only one manifest case.
  --manifest PATH    Use a non-default benchmark manifest.
  --force            Invalidate and rerun otherwise current samples.
  --help              Show this message.`;

export function parseRunCliArgs(argv: string[]): RunCliArgs {
  const values = new Map<string, string>();
  const switches = new Set<string>();
  const seen = new Set<string>();
  let positionalModel: string | undefined;
  let sawOption = false;

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) {
      if (sawOption || positionalModel !== undefined) throw new Error(`Unexpected positional argument ${argument}.\n${runUsage}`);
      positionalModel = argument;
      continue;
    }

    sawOption = true;
    const option = argument.slice(2);
    if (!new Set(["model", "case", "manifest", "force", "help"]).has(option)) {
      throw new Error(`Unknown option --${option}.\n${runUsage}`);
    }
    if (seen.has(option)) throw new Error(`Duplicate option --${option}.`);
    seen.add(option);

    if (option === "force" || option === "help") {
      switches.add(option);
      continue;
    }

    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${option} requires a value.\n${runUsage}`);
    values.set(option, value);
    index += 1;
  }

  if (positionalModel !== undefined && values.has("model")) {
    throw new Error("Do not specify the model both positionally and with --model.");
  }

  return {
    modelId: positionalModel ?? values.get("model") ?? defaultRunModelId,
    ...(values.has("case") ? { caseId: values.get("case")! } : {}),
    ...(values.has("manifest") ? { manifestPath: values.get("manifest")! } : {}),
    force: switches.has("force"),
    help: switches.has("help"),
  };
}

type LockRecord = {
  schemaVersion: 1;
  token: string;
  pid: number;
  hostname: string;
  createdAt: string;
};

export class SampleLockError extends Error {
  constructor(
    message: string,
    readonly lockPath: string,
    readonly stale: boolean,
  ) {
    super(message);
    this.name = "SampleLockError";
  }
}

function processIsAlive(pid: number): boolean | null {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ESRCH") return false;
    if (code === "EPERM") return true;
    return null;
  }
}

async function existingLockError(lockPath: string, staleAfterMs: number): Promise<SampleLockError> {
  let parsed: Partial<LockRecord> | null = null;
  let ageMs = 0;
  try {
    const [content, details] = await Promise.all([readFile(lockPath, "utf8"), stat(lockPath)]);
    ageMs = Math.max(0, Date.now() - details.mtimeMs);
    parsed = JSON.parse(content) as Partial<LockRecord>;
  } catch {
    // A missing lock is treated as a short race; the caller receives a clear abort
    // and can retry instead of risking removal of a lock it does not own.
  }

  const sameHost = parsed?.hostname === hostname();
  const live = sameHost && typeof parsed?.pid === "number" ? processIsAlive(parsed.pid) : null;
  const stale = live === false || (live !== true && ageMs >= staleAfterMs);
  const owner = parsed?.pid ? `pid ${parsed.pid}${parsed.hostname ? ` on ${parsed.hostname}` : ""}` : "an unknown owner";
  if (stale) {
    return new SampleLockError(
      `Stale lock detected at ${lockPath} (${owner}, age ${Math.round(ageMs / 1000)}s). ` +
        "The runner will not delete a lock it does not own; remove it only after verifying that no provider call is still active, then retry.",
      lockPath,
      true,
    );
  }
  return new SampleLockError(`Sample has an active lock at ${lockPath} owned by ${owner}. Wait for that runner to finish or retry later.`, lockPath, false);
}

export type SampleLock = {
  lockPath: string;
  release: () => Promise<void>;
};

export async function acquireSampleLock(lockPath: string, options: { staleAfterMs?: number } = {}): Promise<SampleLock> {
  const staleAfterMs = options.staleAfterMs ?? 6 * 60 * 60 * 1000;
  await mkdir(path.dirname(lockPath), { recursive: true });
  const record: LockRecord = {
    schemaVersion: 1,
    token: randomUUID(),
    pid: process.pid,
    hostname: hostname(),
    createdAt: new Date().toISOString(),
  };

  let handle;
  try {
    handle = await open(lockPath, "wx", 0o644);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") throw await existingLockError(lockPath, staleAfterMs);
    throw error;
  }

  try {
    await handle.writeFile(JSON.stringify(record, null, 2) + "\n", "utf8");
    await handle.sync();
    await handle.close();
  } catch (error) {
    await handle.close().catch(() => undefined);
    await rm(lockPath, { force: true }).catch(() => undefined);
    throw error;
  }

  let released = false;
  return {
    lockPath,
    release: async () => {
      if (released) return;
      let current: Partial<LockRecord>;
      try {
        current = JSON.parse(await readFile(lockPath, "utf8")) as Partial<LockRecord>;
      } catch (error) {
        const detail = error instanceof Error ? ` ${error.message}` : "";
        throw new SampleLockError(`Cannot release ${lockPath}: the owned lock disappeared or became unreadable.${detail}`, lockPath, false);
      }
      if (current.token !== record.token) {
        throw new SampleLockError(`Cannot release ${lockPath}: lock ownership changed.`, lockPath, false);
      }
      await rm(lockPath);
      released = true;
    },
  };
}
