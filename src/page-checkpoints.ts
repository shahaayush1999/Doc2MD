import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";

export type PageRequest = {
  pdf: Uint8Array;
  prompt: string;
  filename: string;
};

export type PageConversion = {
  text: string;
  resolvedModel: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
    inputTokenDetails: { cacheReadTokens: number };
  };
};

type PageCheckpoint = PageConversion & { cacheKey: string; elapsedMs: number };

/** Retain split PDFs because pdfseparate generates fresh random trailer IDs on every split. */
export async function loadSplitPages(
  directory: string,
  sourcePdf: Uint8Array,
  split: (destination: string) => Promise<unknown>,
): Promise<Array<{ pdf: Uint8Array; filename: string }>> {
  const destination = path.join(directory, createHash("sha256").update(sourcePdf).digest("hex"));
  await mkdir(destination, { recursive: true });
  const marker = path.join(destination, ".complete");
  const complete = await readFile(marker, "utf8").catch((error: any) => {
    if (error.code === "ENOENT") return "";
    throw error;
  });
  if (complete !== "complete") {
    await split(destination);
    await writeFile(marker, "complete", "utf8");
  }
  const files = (await readdir(destination))
    .filter((file) => /^page-\d+\.pdf$/.test(file))
    .sort((a, b) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]));
  if (!files.length) throw new Error("PDF split produced no pages.");
  return Promise.all(files.map(async (filename) => ({
    pdf: await readFile(path.join(destination, filename)), filename,
  })));
}

/** Save completed pages even when another page fails, so retries only pay for missing work. */
export async function convertPagesWithCheckpoints(
  directory: string,
  pages: PageRequest[],
  modelConfiguration: unknown,
  convert: (page: PageRequest, index: number) => Promise<PageConversion>,
): Promise<Array<PageCheckpoint & { reused: boolean }>> {
  await mkdir(directory, { recursive: true });
  const settled = await Promise.allSettled(pages.map(async (page, index) => {
    const cacheKey = createHash("sha256")
      .update(JSON.stringify({ version: 1, modelConfiguration, prompt: page.prompt, filename: page.filename }))
      .update(page.pdf)
      .digest("hex");
    const destination = path.join(directory, `${cacheKey}.json`);
    try {
      const cached = JSON.parse(await readFile(destination, "utf8")) as PageCheckpoint;
      if (cached.cacheKey === cacheKey && cached.text?.trim() && cached.resolvedModel
        && Number.isFinite(cached.elapsedMs) && Number.isFinite(cached.usage?.inputTokens)
        && Number.isFinite(cached.usage?.outputTokens)
        && Number.isFinite(cached.usage?.inputTokenDetails?.cacheReadTokens)) {
        return { ...cached, reused: true };
      }
    } catch (error: any) {
      if (error.code !== "ENOENT" && !(error instanceof SyntaxError)) throw error;
    }

    const started = performance.now();
    const result = await convert(page, index);
    if (!result.text.trim()) throw new Error(`Page ${index + 1} returned empty Markdown.`);
    const checkpoint: PageCheckpoint = { ...result, cacheKey, elapsedMs: performance.now() - started };
    const temporary = `${destination}.${randomUUID()}.tmp`;
    try {
      await writeFile(temporary, JSON.stringify(checkpoint) + "\n", "utf8");
      await rename(temporary, destination);
    } finally {
      await rm(temporary, { force: true });
    }
    return { ...checkpoint, reused: false };
  }));
  const failures = settled.filter((result) => result.status === "rejected");
  if (failures.length) {
    throw new AggregateError(failures.map((result) => result.reason),
      `${failures.length} page conversion(s) failed; completed pages are checkpointed for retry.`);
  }
  return settled.map((result) => {
    if (result.status === "rejected") throw result.reason;
    return result.value;
  });
}
