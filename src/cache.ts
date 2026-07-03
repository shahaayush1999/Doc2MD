import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

export async function fileSha256(filePath: string) {
  return createHash("sha256").update(await readFile(filePath)).digest("hex");
}

export function stableJson(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => stableJson(item)).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
  return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(",")}}`;
}

export function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

export function hashObject(value: unknown) {
  return sha256(stableJson(value));
}

