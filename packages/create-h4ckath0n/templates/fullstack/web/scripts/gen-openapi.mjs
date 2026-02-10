#!/usr/bin/env node
/**
 * gen-openapi.mjs
 *
 * 1. Runs the backend OpenAPI dump script (via uv) to produce openapi.json.
 * 2. Runs openapi-typescript to generate TypeScript types from the schema.
 *
 * Usage:  node scripts/gen-openapi.mjs
 *   or:  npm run gen
 */

import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, mkdirSync } from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(__dirname, "..");
const apiDir = resolve(webDir, "../api");

const openapiJson = resolve(apiDir, "openapi.json");
const outputTs = resolve(webDir, "src/gen/openapi.ts");

function findMonorepoRoot(startDir) {
  let dir = startDir;
  while (true) {
    const parent = dirname(dir);
    const isRoot = parent === dir;

    const hasPyproject = existsSync(resolve(dir, "pyproject.toml"));
    const hasUvLock = existsSync(resolve(dir, "uv.lock"));
    const hasLib = existsSync(resolve(dir, "src/h4ckath0n/__init__.py"));
    const hasScaffolder = existsSync(resolve(dir, "packages/create-h4ckath0n/package.json"));

    if (hasPyproject && hasUvLock && hasLib && hasScaffolder) return dir;
    if (isRoot) return null;
    dir = parent;
  }
}

const overrideProject = process.env.H4CKATH0N_UV_PROJECT || process.env.UV_PROJECT;
const monorepoRoot = findMonorepoRoot(webDir);
const uvProject = overrideProject || monorepoRoot || apiDir;

console.log(`→ Using uv project: ${uvProject}`);
console.log("→ Dumping OpenAPI schema from backend…");

try {
  execFileSync(
    "uv",
    [
      "--project",
      uvProject,
      "run",
      "--locked",
      "python",
      "-m",
      "scripts.dump_openapi",
      "--out",
      openapiJson,
    ],
    {
      cwd: webDir,
      stdio: "inherit",
      env: { ...process.env, PYTHONPATH: apiDir },
    },
  );
} catch {
  console.error("✗ Failed to dump OpenAPI schema from backend.");
  process.exit(1);
}

if (!existsSync(openapiJson)) {
  console.error(`✗ Expected OpenAPI file not found: ${openapiJson}`);
  process.exit(1);
}

console.log("→ Generating TypeScript types from OpenAPI schema…");
const outDir = dirname(outputTs);
if (!existsSync(outDir)) {
  mkdirSync(outDir, { recursive: true });
}

try {
  execFileSync(
    "npm",
    ["exec", "--no", "--", "openapi-typescript", openapiJson, "-o", outputTs],
    { cwd: webDir, stdio: "inherit" },
  );
} catch {
  console.error("✗ openapi-typescript generation failed.");
  process.exit(1);
}

console.log(`✓ Generated ${outputTs}`);
