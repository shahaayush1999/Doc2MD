import { createHash } from "node:crypto";
import { execFile as execFileCallback } from "node:child_process";
import { mkdir, mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { processPdf } from "@firecrawl/pdf-inspector";
import LlamaCloud from "@llamaindex/llama-cloud";
import { generateText, type ModelMessage } from "ai";
import type { ManifestCase } from "./evaluator.js";
import type { ParserSpec } from "./candidates.js";
import { createModel, models } from "./models.js";

const execFile = promisify(execFileCallback);
const parserEnvRoot = path.resolve(process.env.DOC2MD_PARSER_ENV_ROOT ?? ".parser-envs");
const parserCacheRoot = path.resolve(".parser-cache");
const commandOptions = {
  cwd: process.cwd(),
  encoding: "utf8" as const,
  maxBuffer: 64 * 1024 * 1024,
};

// Bump only the adapter whose behavior changed. Hashing this entire source file
// made an unrelated parser addition invalidate every cached parser result.
const adapterProtocols: Record<ParserSpec["parser"], number> = {
  pdftotext: 1,
  "pdf-inspector": 1,
  "markitdown-base": 1,
  "markitdown-ocr-luna": 1,
  "llm-page-parallelism-5.6-luna": 1,
  "llm-page-parallelism-3.1-flash-lite": 1,
  pymupdf4llm: 1,
  docling: 1,
  marker: 1,
  reducto: 2,
  "mistral-ocr": 1,
  "llamaparse-agentic": 2,
  "firecrawl-hosted-auto": 1,
  "landingai-dpt2": 1,
  "upstage-auto": 1,
  "nanonets-docstrange": 1,
  "unstructured-vlm-gpt4o": 1,
};

export type ParserRunResult = {
  text: string;
  resolvedModel: string;
  costUsd?: number;
  usage: {
    inputTokens: number;
    outputTokens: number;
    inputTokenDetails: { cacheReadTokens: number };
  };
  metadata: Record<string, unknown>;
};

function sha256(value: string | Uint8Array) {
  return createHash("sha256").update(value).digest("hex");
}

function executable(environment: string, name: string) {
  return path.join(parserEnvRoot, environment, "bin", name);
}

function parserEnvironment() {
  return {
    ...process.env,
    HF_HOME: path.join(parserCacheRoot, "huggingface"),
  };
}

async function command(
  spec: ParserSpec,
  executablePath: string,
  args: string[],
  options: { env?: NodeJS.ProcessEnv } = {},
) {
  try {
    return await execFile(executablePath, args, { ...commandOptions, ...options });
  } catch (error: any) {
    const detail = String(error?.stderr || error?.stdout || error?.message || error).trim();
    const setup = spec.parser === "pdftotext" || spec.parser.startsWith("llm-page-parallelism-")
      ? "Install Poppler so pdftotext is available on PATH."
      : "Run `npm run parsers:setup` and follow any reported system-dependency instructions.";
    throw new Error(`${spec.id} failed. ${setup}${detail ? `\n${detail}` : ""}`);
  }
}

async function temporaryDirectory(prefix: string) {
  const root = path.resolve("tmp/pdfs/parser-runs");
  await mkdir(root, { recursive: true });
  return mkdtemp(path.join(root, `${prefix}-`));
}

export async function parserCacheIdentity(spec: ParserSpec) {
  const identity: Record<string, unknown> = {
    id: spec.id,
    parser: spec.parser,
    version: spec.version,
    ingestionMode: spec.ingestionMode,
    adapterProtocol: adapterProtocols[spec.parser],
  };

  if (spec.parser === "pdftotext") {
    const version = await command(spec, "pdftotext", ["-v"]);
    identity.runtimeVersion = `${version.stdout}${version.stderr}`.trim().split("\n")[0] ?? "unknown";
  }
  if (spec.parser === "markitdown-ocr-luna") {
    identity.prompt = sha256(await readFile("benchmark/parser-prompts/markitdown-vision.md"));
    identity.script = sha256(await readFile("scripts/parser_adapters/run_markitdown_ocr.py"));
  }
  if (spec.parser.startsWith("llm-page-parallelism-")) {
    identity.prompt = sha256(await readFile("benchmark/parser-prompts/llm-page-parallelism-5.6-luna.md"));
    const version = await command(spec, "pdfseparate", ["-v"]);
    identity.runtimeVersion = `${version.stdout}${version.stderr}`.trim().split("\n")[0] ?? "unknown";
  }
  if (spec.parser === "pymupdf4llm") {
    identity.script = sha256(await readFile("scripts/parser_adapters/run_pymupdf4llm.py"));
  }
  return identity;
}

export async function runParser(
  spec: ParserSpec,
  testCase: ManifestCase,
  workingDirectory: string,
): Promise<ParserRunResult> {
  const pdf = path.resolve(testCase.pdf);
  let text = "";
  let usage = {
    inputTokens: 0,
    outputTokens: 0,
    inputTokenDetails: { cacheReadTokens: 0 },
  };
  let metadata: Record<string, unknown> = {};
  let costUsd: number | undefined;

  if (spec.parser === "pdftotext") {
    ({ stdout: text } = await command(spec, "pdftotext", ["-layout", pdf, "-"]));
  } else if (spec.parser === "pdf-inspector") {
    const parsed = processPdf(await readFile(pdf));
    text = parsed.markdown ?? "";
    metadata = {
      pdfType: parsed.pdfType,
      pagesNeedingOcr: parsed.pagesNeedingOcr,
      pagesWithTables: parsed.pagesWithTables,
      pagesWithColumns: parsed.pagesWithColumns,
      hasEncodingIssues: parsed.hasEncodingIssues,
    };
  } else if (spec.parser === "markitdown-base") {
    ({ stdout: text } = await command(
      spec,
      executable("markitdown", "markitdown"),
      [pdf],
    ));
  } else if (spec.parser === "markitdown-ocr-luna") {
    const metadataPath = path.join(workingDirectory, ".markitdown-ocr-usage.json");
    try {
      ({ stdout: text } = await command(
        spec,
        executable("markitdown", "python"),
        [
          path.resolve("scripts/parser_adapters/run_markitdown_ocr.py"),
          pdf,
          path.resolve("benchmark/parser-prompts/markitdown-vision.md"),
          metadataPath,
        ],
      ));
      metadata = JSON.parse(await readFile(metadataPath, "utf8"));
      usage = (metadata.usage ?? usage) as typeof usage;
      if (!Number.isSafeInteger(metadata.successfulVisionCalls) || Number(metadata.successfulVisionCalls) < 1) {
        throw new Error(`MarkItDown OCR completed without a successful vision call; refusing to cache its silent base-converter fallback. ${JSON.stringify(metadata)}`);
      }
    } finally {
      await rm(metadataPath, { force: true });
    }
  } else if (spec.parser.startsWith("llm-page-parallelism-")) {
    const splitDirectory = await temporaryDirectory(spec.parser);
    try {
      await command(spec, "pdfseparate", [pdf, path.join(splitDirectory, "page-%d.pdf")]);
      const pageFiles = (await readdir(splitDirectory))
        .filter((file) => /^page-\d+\.pdf$/.test(file))
        .sort((a, b) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]));
      if (pageFiles.length === 0) throw new Error(`${spec.id} produced no single-page PDFs.`);

      const prompt = (await readFile("benchmark/parser-prompts/llm-page-parallelism-5.6-luna.md", "utf8")).trim();
      const pageModel = spec.parser === "llm-page-parallelism-5.6-luna"
        ? models["openai-gpt-5.6-luna"]!
        : models["google-gemini-3.1-flash-lite"]!;
      const pageResults = await Promise.all(pageFiles.map(async (pageFile, index) => {
        const messages: ModelMessage[] = [{
          role: "user",
          content: [
            { type: "text", text: `${prompt}\n\nThis is physical page ${index + 1} of ${pageFiles.length}.` },
            {
              type: "file",
              data: await readFile(path.join(splitDirectory, pageFile)),
              mediaType: "application/pdf",
              filename: pageFile,
            },
          ],
        }];
        const response = await generateText({
          model: createModel(pageModel),
          messages,
          maxOutputTokens: 20_000,
          maxRetries: 2,
          reasoning: "none",
        });
        if (!response.text.trim()) throw new Error(`${spec.id} returned empty Markdown for page ${index + 1}.`);
        return response;
      }));

      const resolvedModels = [...new Set(pageResults.map((result) => result.response.modelId))];
      if (resolvedModels.length !== 1) throw new Error(`${spec.id} resolved to multiple models: ${resolvedModels.join(", ")}`);
      text = pageResults
        .map((result, index) => `<!-- Page ${index + 1} -->\n\n${result.text.trim()}`)
        .join("\n\n");
      usage = {
        inputTokens: pageResults.reduce((sum, result) => sum + (result.usage.inputTokens ?? 0), 0),
        outputTokens: pageResults.reduce((sum, result) => sum + (result.usage.outputTokens ?? 0), 0),
        inputTokenDetails: {
          cacheReadTokens: pageResults.reduce(
            (sum, result) => sum + (result.usage.inputTokenDetails?.cacheReadTokens ?? 0),
            0,
          ),
        },
      };
      metadata = { pipeline: spec.id, version: spec.version };
      return {
        text,
        resolvedModel: `${spec.id}-v${spec.version}`,
        usage,
        metadata,
      };
    } finally {
      await rm(splitDirectory, { recursive: true, force: true });
    }
  } else if (spec.parser === "pymupdf4llm") {
    ({ stdout: text } = await command(
      spec,
      executable("pymupdf4llm", "python"),
      [path.resolve("scripts/parser_adapters/run_pymupdf4llm.py"), pdf],
    ));
  } else if (spec.parser === "docling") {
    const outputDirectory = await temporaryDirectory("docling");
    try {
      await command(
        spec,
        executable("docling", "docling"),
        [
          "convert",
          pdf,
          "--from", "pdf",
          "--to", "md",
          "--pipeline", "standard",
          "--device", "cpu",
          "--image-export-mode", "placeholder",
          "--output", outputDirectory,
          "--quiet",
        ],
        { env: parserEnvironment() },
      );
      text = await readFile(path.join(outputDirectory, `${path.basename(pdf, path.extname(pdf))}.md`), "utf8");
    } finally {
      await rm(outputDirectory, { recursive: true, force: true });
    }
  } else if (spec.parser === "marker") {
    const outputDirectory = await temporaryDirectory("marker");
    try {
      await command(
        spec,
        executable("marker", "marker_single"),
        [
          pdf,
          "--mode", "fast",
          "--output_format", "markdown",
          "--disable_image_extraction",
          "--output_dir", outputDirectory,
          "--disable_tqdm",
        ],
        { env: parserEnvironment() },
      );
      const stem = path.basename(pdf, path.extname(pdf));
      text = await readFile(path.join(outputDirectory, stem, `${stem}.md`), "utf8");
    } finally {
      await rm(outputDirectory, { recursive: true, force: true });
    }
  } else if (spec.parser === "reducto") {
    const apiKey = process.env.REDUCTO_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires REDUCTO_API_KEY in .env.local.`);
    const agentic = spec.id === "reducto-agentic";
    const fidelityPrompt = [
      "Reconstruct the document faithfully for Markdown reuse.",
      "Preserve every visible value and its binding to its row, column, label, image, and state.",
      "Retain strikeouts, checkboxes, superseded/current distinctions, reading order, spatial relationships, directed edges, captions, and image identifiers.",
      "Do not infer or invent absent content.",
    ].join(" ");

    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    const uploadResponse = await fetch("https://platform.reducto.ai/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    });
    const upload = await uploadResponse.json() as any;
    if (!uploadResponse.ok) {
      throw new Error(`Reducto upload failed (${uploadResponse.status}): ${JSON.stringify(upload)}`);
    }
    const input = upload.file_id ?? upload.fileId;
    if (typeof input !== "string") throw new Error("Reducto upload response did not contain a file ID.");

    const parseResponse = await fetch("https://platform.reducto.ai/parse", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input,
        enhance: {
          agentic: agentic ? [
            { scope: "text", prompt: fidelityPrompt },
            { scope: "table", prompt: fidelityPrompt },
            { scope: "figure", prompt: fidelityPrompt },
          ] : [],
          summarize_figures: true,
          intelligent_ordering: agentic,
        },
        retrieval: { chunking: { chunk_mode: "disabled" } },
        formatting: { table_output_format: "dynamic", add_page_markers: true },
        settings: { ocr_system: "standard", extraction_mode: "hybrid", persist_results: false },
      }),
    });
    const parsed = await parseResponse.json() as any;
    if (!parseResponse.ok) {
      throw new Error(`Reducto parse failed (${parseResponse.status}): ${JSON.stringify(parsed)}`);
    }

    let chunks = parsed.result?.chunks;
    if (parsed.result?.type === "url" && typeof parsed.result.url === "string") {
      const resultResponse = await fetch(parsed.result.url);
      const result = await resultResponse.json() as any;
      if (!resultResponse.ok) throw new Error(`Reducto result download failed (${resultResponse.status}).`);
      chunks = Array.isArray(result) ? result : result.chunks;
    }
    if (!Array.isArray(chunks)) throw new Error("Reducto parse response did not contain chunks.");
    text = chunks.map((chunk: any) => chunk?.content).filter((content: unknown) => typeof content === "string").join("\n\n");
    const credits = Number(parsed.usage?.credits ?? 0);
    metadata = {
      jobId: parsed.job_id ?? null,
      studioLink: parsed.studio_link ?? null,
      pages: parsed.usage?.num_pages ?? null,
      credits,
      creditPriceUsd: 0.015,
      configuration: agentic
        ? "agentic-text-table-figure-intelligent-ordering-dynamic-tables-generic-fidelity-prompt"
        : "standard-hybrid-dynamic-tables-figures-page-markers",
    };
    costUsd = credits * 0.015;
  } else if (spec.parser === "mistral-ocr") {
    const apiKey = process.env.MISTRAL_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires MISTRAL_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const response = await fetch("https://api.mistral.ai/v1/ocr", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: spec.version,
        document: {
          type: "document_url",
          document_url: `data:application/pdf;base64,${pdfBytes.toString("base64")}`,
        },
      }),
    });
    const parsed = await response.json() as any;
    if (!response.ok) {
      throw new Error(`Mistral OCR failed (${response.status}): ${JSON.stringify(parsed)}`);
    }
    if (!Array.isArray(parsed.pages)) throw new Error("Mistral OCR response did not contain pages.");
    text = parsed.pages
      .map((page: any) => page?.markdown)
      .filter((markdown: unknown) => typeof markdown === "string")
      .join("\n\n");
    const pages = parsed.pages.length;
    metadata = {
      pages,
      resolvedModel: parsed.model ?? spec.version,
      usageInfo: parsed.usage_info ?? null,
      configuration: "standard-ocr-default-markdown",
    };
    costUsd = pages * 0.004;
  } else if (spec.parser === "llamaparse-agentic") {
    const apiKey = process.env.LLAMA_CLOUD_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires LLAMA_CLOUD_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const client = new LlamaCloud({ apiKey });
    const parsed = await client.parsing.parse({
      tier: "agentic",
      version: spec.version,
      upload_file: new File([new Uint8Array(pdfBytes)], path.basename(pdf), { type: "application/pdf" }),
      expand: ["markdown", "job_metadata"],
      client_name: "doc2md-benchmark",
    }, {
      pollingInterval: 1,
      timeout: 15 * 60,
    });
    const pages = parsed.markdown?.pages ?? [];
    const successfulPages = pages.filter((page) => page.success);
    if (successfulPages.length !== pages.length) {
      const failures = pages.filter((page) => !page.success);
      throw new Error(`LlamaParse returned failed pages: ${JSON.stringify(failures)}`);
    }
    text = successfulPages.map((page) => page.markdown).join("\n\n");
    metadata = {
      jobId: parsed.job.id,
      pages: successfulPages.length,
      tier: parsed.job.tier ?? "agentic",
      jobMetadata: parsed.job_metadata ?? null,
      configuration: "agentic-default-markdown",
    };
    costUsd = successfulPages.length * 0.012;
  } else if (spec.parser === "firecrawl-hosted-auto") {
    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    form.append("options", JSON.stringify({
      formats: ["markdown"],
      onlyMainContent: false,
      timeout: 300_000,
      parsers: [{ type: "pdf", mode: "auto" }],
    }));
    const apiKey = process.env.FIRECRAWL_API_KEY;
    const response = await fetch("https://api.firecrawl.dev/v2/parse", {
      method: "POST",
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : undefined,
      body: form,
    });
    const parsed = await response.json() as any;
    if (!response.ok || parsed.success !== true) {
      throw new Error(`Firecrawl hosted parse failed (${response.status}): ${JSON.stringify(parsed)}`);
    }
    text = parsed.data?.markdown ?? "";
    const pages = Number(parsed.data?.metadata?.numPages ?? parsed.data?.metadata?.totalPages ?? 0);
    metadata = {
      pages: Number.isFinite(pages) ? pages : null,
      totalPages: parsed.data?.metadata?.totalPages ?? null,
      configuration: "v2-parse-auto-markdown-only-main-content-false",
    };
    costUsd = Number.isFinite(pages) ? pages * (16 / 5_000) : undefined;
  } else if (spec.parser === "landingai-dpt2") {
    const apiKey = process.env.LANDINGAI_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires LANDINGAI_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("document", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    form.append("model", spec.version);
    const response = await fetch("https://api.va.landing.ai/v1/ade/parse", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    });
    const parsed = await response.json() as any;
    if (!response.ok) {
      throw new Error(`LandingAI ADE Parse failed (${response.status}): ${JSON.stringify(parsed)}`);
    }
    text = parsed.markdown ?? "";
    const pages = testCase.pages;
    metadata = {
      pages: pages ?? null,
      chunks: Array.isArray(parsed.chunks) ? parsed.chunks.length : null,
      splits: Array.isArray(parsed.splits) ? parsed.splits.length : null,
      configuration: "ade-parse-dpt-2-latest-whole-document-markdown",
    };
    costUsd = pages === undefined ? undefined : pages * 0.03;
  } else if (spec.parser === "upstage-auto") {
    const apiKey = process.env.UPSTAGE_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires UPSTAGE_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("document", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    form.append("model", spec.version);
    form.append("mode", "auto");
    form.append("output_format", "markdown");
    form.append("ocr", "auto");
    const response = await fetch("https://api.upstage.ai/v1/document-digitization", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    });
    const parsed = await response.json() as any;
    if (!response.ok) {
      throw new Error(`Upstage Document Parse failed (${response.status}): ${JSON.stringify(parsed)}`);
    }
    text = parsed.content?.markdown ?? "";
    const standardPages = Array.isArray(parsed.usage?.standard) ? parsed.usage.standard.length : 0;
    const enhancedPages = Array.isArray(parsed.usage?.enhanced) ? parsed.usage.enhanced.length : 0;
    const pages = Number(parsed.usage?.pages ?? standardPages + enhancedPages);
    metadata = {
      pages: Number.isFinite(pages) ? pages : null,
      standardPages,
      enhancedPages,
      configuration: "document-parse-nightly-auto-routing-auto-ocr-markdown",
    };
    costUsd = standardPages * 0.01 + enhancedPages * 0.03;
  } else if (spec.parser === "nanonets-docstrange") {
    const apiKey = process.env.NANONETS_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires NANONETS_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    form.append("output_format", "markdown");
    const submitResponse = await fetch("https://extraction-api.nanonets.com/api/v1/extract/async", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: form,
    });
    const submitted = await submitResponse.json() as any;
    if (!submitResponse.ok) {
      throw new Error(`Nanonets DocStrange submission failed (${submitResponse.status}): ${JSON.stringify(submitted)}`);
    }
    const recordId = submitted.record_id;
    if (typeof recordId !== "string" && typeof recordId !== "number") {
      throw new Error("Nanonets DocStrange response did not contain a record ID.");
    }

    let parsed = submitted;
    const deadline = Date.now() + 15 * 60_000;
    while (parsed.status === "processing" || parsed.status === "queued") {
      if (Date.now() >= deadline) throw new Error(`Nanonets DocStrange job ${recordId} timed out.`);
      await new Promise((resolve) => setTimeout(resolve, 10_000));
      const resultResponse = await fetch(`https://extraction-api.nanonets.com/api/v1/extract/results/${recordId}`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      parsed = await resultResponse.json() as any;
      if (!resultResponse.ok) {
        throw new Error(`Nanonets DocStrange result failed (${resultResponse.status}): ${JSON.stringify(parsed)}`);
      }
    }
    if (parsed.status !== "completed" || parsed.success !== true) {
      throw new Error(`Nanonets DocStrange extraction failed: ${JSON.stringify(parsed)}`);
    }
    text = parsed.result?.markdown?.content ?? "";
    const pages = Number(parsed.pages_processed ?? testCase.pages);
    metadata = {
      recordId: String(recordId),
      pages: Number.isFinite(pages) ? pages : null,
      providerProcessingSeconds: parsed.processing_time ?? null,
      configuration: "api-v1-async-default-markdown",
    };
    costUsd = Number.isFinite(pages) ? pages * 0.01 : undefined;
  } else if (spec.parser === "unstructured-vlm-gpt4o") {
    const apiKey = process.env.UNSTRUCTURED_API_KEY;
    if (!apiKey) throw new Error(`${spec.id} requires UNSTRUCTURED_API_KEY in .env.local.`);
    const pdfBytes = await readFile(pdf);
    const form = new FormData();
    form.append("files", new Blob([new Uint8Array(pdfBytes)], { type: "application/pdf" }), path.basename(pdf));
    form.append("strategy", "vlm");
    form.append("vlm_model_provider", "openai");
    form.append("vlm_model", "gpt-4o");
    form.append("output_format", "application/json");
    const response = await fetch("https://api.unstructuredapp.io/general/v0/general", {
      method: "POST",
      headers: { "unstructured-api-key": apiKey },
      body: form,
    });
    const parsed = await response.json() as any;
    if (!response.ok) {
      throw new Error(`Unstructured Partition failed (${response.status}): ${JSON.stringify(parsed)}`);
    }
    if (!Array.isArray(parsed)) throw new Error("Unstructured Partition response did not contain document elements.");

    let currentPage: number | null = null;
    const parts: string[] = [];
    const typeCounts: Record<string, number> = {};
    for (const element of parsed) {
      const page = Number(element?.metadata?.page_number);
      if (Number.isFinite(page) && page !== currentPage) {
        currentPage = page;
        parts.push(`PAGE: ${page}`);
      }
      const type = typeof element?.type === "string" ? element.type : "Unknown";
      typeCounts[type] = (typeCounts[type] ?? 0) + 1;
      const content = element?.metadata?.text_as_html ?? element?.text;
      if (typeof content === "string" && content.trim()) parts.push(content.trim());
    }
    text = parts.join("\n\n");
    const pages = new Set(parsed
      .map((element: any) => Number(element?.metadata?.page_number))
      .filter((page: number) => Number.isFinite(page))).size;
    metadata = {
      pages,
      elements: parsed.length,
      typeCounts,
      configuration: "legacy-partition-vlm-openai-gpt-4o-json-elements-html-serialization",
    };
    costUsd = pages * 0.03;
  }

  if (!text.trim()) throw new Error(`${spec.id} returned empty Markdown for ${testCase.id}.`);
  return {
    text,
    resolvedModel: `${spec.modelName}@${spec.version}`,
    costUsd,
    usage,
    metadata,
  };
}
