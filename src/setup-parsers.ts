import { spawn } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const environmentRoot = path.resolve(".parser-envs");
const cacheRoot = path.resolve(".parser-cache/uv");

const environments = [
  {
    name: "markitdown",
    packages: ["markitdown[pdf]==0.1.6", "markitdown-ocr==0.1.0", "openai==2.52.0"],
  },
  {
    name: "pymupdf4llm",
    packages: ["pymupdf4llm==0.2.9"],
  },
  {
    name: "docling",
    packages: ["docling==2.117.0"],
  },
  {
    name: "marker",
    packages: ["marker-pdf==2.0.0"],
  },
];

async function run(executable: string, args: string[]) {
  await new Promise<void>((resolve, reject) => {
    const child = spawn(executable, args, { cwd: process.cwd(), stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(`${executable} ${args.join(" ")} exited with ${signal ?? code}`));
    });
  });
}

async function commandExists(command: string) {
  const pathEntries = (process.env.PATH ?? "").split(path.delimiter);
  for (const entry of pathEntries) {
    if (!entry) continue;
    try {
      await access(path.join(entry, command));
      return true;
    } catch {
      // Continue looking through PATH.
    }
  }
  return false;
}

export async function setupParsers() {
  if (!await commandExists("uv")) throw new Error("uv is required to install the isolated Python parser environments.");
  await Promise.all([mkdir(environmentRoot, { recursive: true }), mkdir(cacheRoot, { recursive: true })]);

  for (const environment of environments) {
    const destination = path.join(environmentRoot, environment.name);
    console.log(`\nSetting up ${environment.name} in ${path.relative(process.cwd(), destination)}`);
    await run("uv", ["venv", "--python", "3.12", "--allow-existing", "--cache-dir", cacheRoot, destination]);
    await run("uv", [
      "pip", "install",
      "--python", path.join(destination, "bin", "python"),
      "--cache-dir", cacheRoot,
      ...environment.packages,
    ]);
  }

  const missing: string[] = [];
  if (!await commandExists("pdftotext")) missing.push("Poppler pdftotext (macOS: `brew install poppler`)");
  if (!await commandExists("llama-server")) missing.push("llama.cpp for Marker fast CPU (macOS: `brew install llama.cpp`)");
  if (missing.length > 0) {
    console.warn(`\nPython environments are ready, but these system dependencies are missing:\n- ${missing.join("\n- ")}`);
  } else {
    console.log("\nAll parser environments and system dependencies are ready.");
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await setupParsers();
