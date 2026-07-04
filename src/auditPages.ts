import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { generateObject } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { z } from "zod";

const pageAuditSchema = z.object({
  severity: z.enum(["ok", "minor", "major", "broken"]),
  realisticScore: z.number().min(0).max(100),
  densityScore: z.number().min(0).max(100),
  issues: z.array(z.string()).max(12),
  fixes: z.array(z.string()).max(12),
  shouldFixBeforeBenchmarking: z.boolean(),
});

type PageAudit = z.infer<typeof pageAuditSchema> & {
  caseId: string;
  page: number;
  image: string;
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
  const response = await generateObject({
    model: googleVertex("gemini-3.1-flash-lite"),
    schema: pageAuditSchema,
    reasoning: "minimal",
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text:
              "Audit this benchmark PDF page visually. Be blunt. We are trying to find pages that look like synthetic nonsense, broken layouts, clipped or overlapping text, unreadable tiny text, too much empty space, unrealistic spacing, toy-looking charts/tables, impossible document design, or anything that would make the benchmark data low quality. Do not judge the benchmark task difficulty; judge visual/layout realism and defects. Return only the structured audit.",
          },
          { type: "file", data: image, mediaType: "image/png", filename: `${page.caseId}-p${page.page}.png` },
        ],
      },
    ],
  });
  return { caseId: page.caseId, page: page.page, image: page.image, ...response.object };
}

const root = process.argv[2] ?? "tmp/page-audit/pages";
const out = process.argv[3] ?? "tmp/page-audit/audit.json";
const pages = await listPages(root);
const audits: PageAudit[] = [];

for (const page of pages) {
  const audit = await auditPage(page);
  audits.push(audit);
  console.log(
    `${audit.caseId} p${audit.page}: ${audit.severity} realism=${audit.realisticScore} density=${audit.densityScore}` +
      (audit.issues.length ? ` - ${audit.issues[0]}` : ""),
  );
}

await writeFile(out, JSON.stringify({ model: "gemini-3.1-flash-lite", reasoning: "minimal", pages: audits }, null, 2) + "\n", "utf-8");
console.log(`Wrote ${audits.length} page audits to ${out}`);
