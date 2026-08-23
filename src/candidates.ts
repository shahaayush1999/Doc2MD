import { models, type ModelSpec } from "./models.js";

export type ParserKind =
  | "pdftotext"
  | "pdf-inspector"
  | "markitdown-base"
  | "markitdown-ocr-luna"
  | "llm-page-parallelism-5.6-luna"
  | "pymupdf4llm"
  | "docling"
  | "marker"
  | "reducto"
  | "mistral-ocr"
  | "llamaparse-agentic"
  | "firecrawl-hosted-auto"
  | "landingai-dpt2"
  | "upstage-auto"
  | "nanonets-docstrange"
  | "unstructured-vlm-gpt4o";

export type ParserSpec = {
  id: string;
  kind: "parser";
  parser: ParserKind;
  modelName: string;
  provider: "local" | "hybrid" | "hosted";
  version: string;
  ingestionMode: string;
  pricingVersion: string;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  cacheWritePerMillion?: number;
  outputPerMillion: number;
};

const luna = models["openai-gpt-5.6-luna"]!;

export const parsers: Record<string, ParserSpec> = {
  pdftotext: {
    id: "pdftotext",
    kind: "parser",
    parser: "pdftotext",
    modelName: "Poppler pdftotext",
    provider: "local",
    version: "system",
    ingestionMode: "native PDF parsed locally with pdftotext -layout",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "firecrawl-pdf-inspector": {
    id: "firecrawl-pdf-inspector",
    kind: "parser",
    parser: "pdf-inspector",
    modelName: "Firecrawl PDF Inspector",
    provider: "local",
    version: "1.11.2",
    ingestionMode: "native PDF parsed locally by the released Rust/NAPI package",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "markitdown-base": {
    id: "markitdown-base",
    kind: "parser",
    parser: "markitdown-base",
    modelName: "Microsoft MarkItDown",
    provider: "local",
    version: "0.1.6",
    ingestionMode: "native PDF parsed locally by MarkItDown's released PDF converter",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "markitdown-ocr-gpt-5.6-luna": {
    id: "markitdown-ocr-gpt-5.6-luna",
    kind: "parser",
    parser: "markitdown-ocr-luna",
    modelName: "MarkItDown OCR + GPT-5.6 Luna",
    provider: "hybrid",
    version: "markitdown-0.1.6+markitdown-ocr-0.1.0+gpt-5.6-luna",
    ingestionMode: "native PDF parsed by MarkItDown; embedded images and scanned pages sent through its official OpenAI-compatible OCR plugin",
    pricingVersion: luna.pricingVersion,
    inputPerMillion: luna.inputPerMillion,
    cachedInputPerMillion: luna.cachedInputPerMillion,
    cacheWritePerMillion: luna.cacheWritePerMillion,
    outputPerMillion: luna.outputPerMillion,
  },
  "llm-page-parallelism-5.6-luna": {
    id: "llm-page-parallelism-5.6-luna",
    kind: "parser",
    parser: "llm-page-parallelism-5.6-luna",
    modelName: "llm-page-parallelism-5.6-luna",
    provider: "hybrid",
    version: "0.1",
    ingestionMode: "whole PDF split into pages and reconstructed in parallel with GPT-5.6 Luna",
    pricingVersion: luna.pricingVersion,
    inputPerMillion: luna.inputPerMillion,
    cachedInputPerMillion: luna.cachedInputPerMillion,
    cacheWritePerMillion: luna.cacheWritePerMillion,
    outputPerMillion: luna.outputPerMillion,
  },
  "pymupdf4llm-default": {
    id: "pymupdf4llm-default",
    kind: "parser",
    parser: "pymupdf4llm",
    modelName: "PyMuPDF4LLM",
    provider: "local",
    version: "0.2.9",
    ingestionMode: "native PDF parsed locally with PyMuPDF4LLM default automatic OCR",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "docling-standard-cpu": {
    id: "docling-standard-cpu",
    kind: "parser",
    parser: "docling",
    modelName: "Docling standard CPU",
    provider: "local",
    version: "2.117.0",
    ingestionMode: "native PDF processed locally by Docling's standard pipeline with CPU acceleration and placeholder image export",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "marker-fast-cpu": {
    id: "marker-fast-cpu",
    kind: "parser",
    parser: "marker",
    modelName: "Marker fast CPU",
    provider: "local",
    version: "2.0.0",
    ingestionMode: "native PDF processed locally by Marker's released fast CPU mode with OCR enabled",
    pricingVersion: "local-zero-api-cost",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "reducto-standard": {
    id: "reducto-standard",
    kind: "parser",
    parser: "reducto",
    modelName: "Reducto Parse standard",
    provider: "hosted",
    version: "v3",
    ingestionMode: "native PDF uploaded to Reducto Parse with standard hybrid OCR, dynamic table formatting, figure summaries, and page markers enabled",
    pricingVersion: "2026-08-03-usd-0.015-per-credit",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "reducto-agentic": {
    id: "reducto-agentic",
    kind: "parser",
    parser: "reducto",
    modelName: "Reducto Parse agentic",
    provider: "hosted",
    version: "v3",
    ingestionMode: "native PDF uploaded to Reducto Parse with agentic text, table, and figure review, intelligent ordering, dynamic tables, a generic fidelity prompt, and page markers",
    pricingVersion: "2026-08-03-usd-0.015-per-credit",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "mistral-ocr-4": {
    id: "mistral-ocr-4",
    kind: "parser",
    parser: "mistral-ocr",
    modelName: "Mistral OCR 4",
    provider: "hosted",
    version: "mistral-ocr-4-0",
    ingestionMode: "native PDF sent as base64 to Mistral's standard OCR endpoint; page Markdown concatenated without annotations or Q&A",
    pricingVersion: "2026-08-04-usd-0.004-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "llamaparse-agentic": {
    id: "llamaparse-agentic",
    kind: "parser",
    parser: "llamaparse-agentic",
    modelName: "LlamaParse Agentic",
    provider: "hosted",
    version: "2026-07-15",
    ingestionMode: "native PDF uploaded through LlamaParse's official SDK and parsed with the released Agentic tier at default settings",
    pricingVersion: "2026-08-04-usd-0.012-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "firecrawl-hosted-auto": {
    id: "firecrawl-hosted-auto",
    kind: "parser",
    parser: "firecrawl-hosted-auto",
    modelName: "Firecrawl hosted PDF auto",
    provider: "hosted",
    version: "v2-auto",
    ingestionMode: "native PDF uploaded to Firecrawl /v2/parse with its documented auto text-first/OCR-fallback mode and Markdown output",
    pricingVersion: "2026-08-04-hobby-usd-16-per-5000-credits",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "landingai-dpt2": {
    id: "landingai-dpt2",
    kind: "parser",
    parser: "landingai-dpt2",
    modelName: "LandingAI ADE DPT-2",
    provider: "hosted",
    version: "dpt-2-latest",
    ingestionMode: "native PDF uploaded to LandingAI ADE Parse with DPT-2 and returned as whole-document Markdown",
    pricingVersion: "2026-08-04-usd-0.03-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "upstage-auto": {
    id: "upstage-auto",
    kind: "parser",
    parser: "upstage-auto",
    modelName: "Upstage Document Parse Auto",
    provider: "hosted",
    version: "document-parse-nightly",
    ingestionMode: "native PDF uploaded to Upstage Document Digitization with automatic per-page Standard/Enhanced routing, automatic OCR, and Markdown output",
    pricingVersion: "2026-08-04-usd-0.01-standard-0.03-enhanced-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "nanonets-docstrange": {
    id: "nanonets-docstrange",
    kind: "parser",
    parser: "nanonets-docstrange",
    modelName: "Nanonets DocStrange",
    provider: "hosted",
    version: "api-v1",
    ingestionMode: "native PDF uploaded to Nanonets DocStrange asynchronous extraction API with its default processing and Markdown output",
    pricingVersion: "2026-08-04-usd-0.01-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
  "unstructured-vlm-gpt4o": {
    id: "unstructured-vlm-gpt4o",
    kind: "parser",
    parser: "unstructured-vlm-gpt4o",
    modelName: "Unstructured VLM (GPT-4o)",
    provider: "hosted",
    version: "legacy-partition-vlm-gpt-4o",
    ingestionMode: "native PDF uploaded to Unstructured's documented Partition API with VLM strategy and GPT-4o; ordered HTML document elements returned as Markdown-compatible HTML",
    pricingVersion: "2026-08-04-usd-0.03-per-page",
    inputPerMillion: 0,
    cachedInputPerMillion: 0,
    outputPerMillion: 0,
  },
};

export type CandidateSpec = ModelSpec | ParserSpec;

export const candidates: Record<string, CandidateSpec> = { ...models, ...parsers };

export function isParserSpec(spec: CandidateSpec): spec is ParserSpec {
  return "kind" in spec && spec.kind === "parser";
}
