import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { generateObject } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { z } from "zod";
import { runBoundedJobs } from "./concurrency.js";
import { atomicWriteJson, calculateTokenCostUsd } from "./runRuntime.js";

const require = createRequire(import.meta.url);
const auditModel = "gemini-3.1-flash-lite";
const auditProtocolVersion = `page-quality-v3-ai${(require("ai/package.json") as { version: string }).version}-vertex${(require("@ai-sdk/google-vertex/package.json") as { version: string }).version}`;
const auditPricing = { inputPerMillion: 0.25, cachedInputPerMillion: 0.025, outputPerMillion: 1.5 };

const pageAuditSchema = z.strictObject({
  severity: z.enum(["ok", "minor", "major", "broken"]),
  legibility: z.number().int().min(1).max(5),
  realism: z.number().int().min(1).max(5),
  density: z.enum(["too_sparse", "balanced", "too_dense"]),
  extractionFacingLanguage: z.array(z.string()).max(12),
  issues: z.array(
    z.strictObject({
      type: z.enum(["clipping", "overlap", "legibility", "density", "realism", "copy", "ambiguity", "meta_language", "other"]),
      detail: z.string(),
    }),
  ).max(12),
  fixes: z.array(z.string()).max(12),
  shouldFixBeforeBenchmarking: z.boolean(),
});

type PageAudit = z.infer<typeof pageAuditSchema> & {
  caseId: string;
  page: number;
  image: string;
  imageHash: string;
  model: string;
  protocolVersion: string;
  usage: { inputTokens: number; outputTokens: number; totalTokens: number };
  costUsd: number;
};

function pageNumber(fileName: string) {
  const match = fileName.match(/-(\d+)\.png$/);
  return match ? Number(match[1]) : 0;
}

async function listPages(root: string) {
  const cases = (await readdir(root, { withFileTypes: true })).filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();
  const pages: Array<{ caseId: string; page: number; image: string }> = [];
  for (const caseId of cases) {
    const dir = path.join(root, caseId);
    const files = (await readdir(dir)).filter((file) => file.endsWith(".png")).sort((a, b) => pageNumber(a) - pageNumber(b));
    for (const file of files) pages.push({ caseId, page: pageNumber(file), image: path.join(dir, file) });
  }
  return pages;
}

async function auditPage(page: { caseId: string; page: number; image: string }): Promise<PageAudit> {
  const image = await readFile(page.image);
  const imageHash = createHash("sha256").update(image).digest("hex");
  const response = await generateObject({
    model: googleVertex(auditModel),
    schema: pageAuditSchema,
    reasoning: "minimal",
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text:
              "Audit this PDF page as a document-quality reviewer. Be blunt and use the full 1-5 scales: 1 means unusable, 3 means plausible but visibly synthetic or flawed, and 5 means polished and realistic. Check clipping, overlap, tiny or unreadable text, weak hierarchy, implausible density, toy-looking tables/charts/diagrams, synthetic copy, ambiguity a careful human could not resolve, and wording that explicitly tells a document-conversion system what to extract, reproduce, preserve, or omit. extractionFacingLanguage must contain only such explicit meta-instructions, never ordinary headings or field labels; return [] when none appear. A naturally sparse cover or signature page is acceptable when appropriate to its genre. Do not judge model difficulty. Return only the structured audit.",
          },
          { type: "file", data: image, mediaType: "image/png", filename: `${page.caseId}-p${page.page}.png` },
        ],
      },
    ],
  });
  const usage = {
    inputTokens: response.usage.inputTokens ?? 0,
    outputTokens: response.usage.outputTokens ?? 0,
    totalTokens: response.usage.totalTokens ?? 0,
  };
  return {
    caseId: page.caseId,
    page: page.page,
    image: page.image,
    imageHash,
    model: auditModel,
    protocolVersion: auditProtocolVersion,
    usage,
    costUsd: calculateTokenCostUsd(auditPricing, response.usage),
    ...response.object,
  };
}

function checkpointPath(out: string, page: { caseId: string; page: number }) {
  return path.join(path.dirname(out), "page-results", page.caseId, `page-${page.page}.json`);
}

async function readCheckpoint(out: string, page: { caseId: string; page: number; image: string }): Promise<PageAudit | null> {
  try {
    const [raw, image] = await Promise.all([readFile(checkpointPath(out, page), "utf-8"), readFile(page.image)]);
    const value = JSON.parse(raw) as Partial<PageAudit>;
    const parsed = pageAuditSchema.safeParse(value);
    const imageHash = createHash("sha256").update(image).digest("hex");
    if (
      !parsed.success ||
      value.caseId !== page.caseId ||
      value.page !== page.page ||
      value.imageHash !== imageHash ||
      value.model !== auditModel ||
      value.protocolVersion !== auditProtocolVersion ||
      typeof value.costUsd !== "number" ||
      !value.usage
    ) return null;
    return { ...(value as PageAudit), image: page.image };
  } catch {
    return null;
  }
}

async function auditWithRetry(page: { caseId: string; page: number; image: string }, attempts = 2): Promise<PageAudit> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await auditPage(page);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

async function mapWithConcurrency<T, U>(values: T[], concurrency: number, operation: (value: T) => Promise<U>): Promise<U[]> {
  return runBoundedJobs(values.map((value) => () => operation(value)), concurrency);
}

const root = process.argv[2] ?? "tmp/page-audit/pages";
const out = process.argv[3] ?? "tmp/page-audit/audit.json";
const pages = await listPages(root);
const audits = await mapWithConcurrency(pages, 6, async (page) => {
  const cached = await readCheckpoint(out, page);
  if (cached) return cached;
  const audit = await auditWithRetry(page);
  await atomicWriteJson(checkpointPath(out, page), audit);
  return audit;
});
audits.sort((a, b) => a.caseId.localeCompare(b.caseId) || a.page - b.page);
for (const audit of audits) {
  console.log(
    `${audit.caseId} p${audit.page}: ${audit.severity} realism=${audit.realism}/5 legibility=${audit.legibility}/5 density=${audit.density}` +
      (audit.issues.length ? ` - ${audit.issues[0].detail}` : ""),
  );
}

const totalCostUsd = audits.reduce((sum, audit) => sum + audit.costUsd, 0);
await atomicWriteJson(out, {
  model: auditModel,
  protocolVersion: auditProtocolVersion,
  reasoning: "minimal",
  totalCostUsd,
  pages: audits,
});
console.log(`Wrote ${audits.length} page audits to ${out} (auditor cost $${totalCostUsd.toFixed(4)})`);
