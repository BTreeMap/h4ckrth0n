import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Validate that a project name contains only alphanumeric chars, hyphens,
 * and underscores, starts with a letter or underscore, and is 1-214 chars.
 * @param {string} name
 * @returns {{ valid: boolean, reason?: string }}
 */
export function validateProjectName(name) {
  if (!name) {
    return { valid: false, reason: "Project name is required." };
  }
  if (name.length > 214) {
    return { valid: false, reason: "Project name must be 214 characters or fewer." };
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(name)) {
    return {
      valid: false,
      reason:
        "Project name must start with a letter or underscore and contain only alphanumeric characters, hyphens, and underscores.",
    };
  }
  return { valid: true };
}

/**
 * Generate a cryptographically random hex secret.
 * @param {number} [bytes=32]
 * @returns {string}
 */
export function generateSecret(bytes = 32) {
  return randomBytes(bytes).toString("hex");
}

// Binary file extensions that should be copied without placeholder replacement.
const BINARY_EXTENSIONS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
  ".woff", ".woff2", ".ttf", ".eot",
  ".zip", ".gz", ".tar", ".bz2",
  ".pdf", ".mp3", ".mp4", ".webm",
  ".wasm", ".bin",
]);

/**
 * Recursively copy a directory, replacing placeholder strings in text files.
 * @param {string} src  - source directory
 * @param {string} dest - destination directory
 * @param {Record<string, string>} replacements - map of placeholder -> value
 */
export function copyDir(src, dest, replacements) {
  mkdirSync(dest, { recursive: true });

  for (const entry of readdirSync(src)) {
    const srcPath = join(src, entry);
    const destPath = join(dest, entry);
    const stat = statSync(srcPath);

    if (stat.isDirectory()) {
      copyDir(srcPath, destPath, replacements);
    } else {
      const dotIdx = entry.lastIndexOf(".");
      const ext = dotIdx > 0 ? entry.slice(dotIdx).toLowerCase() : "";
      if (BINARY_EXTENSIONS.has(ext)) {
        writeFileSync(destPath, readFileSync(srcPath));
      } else {
        let content = readFileSync(srcPath, "utf8");
        for (const [placeholder, value] of Object.entries(replacements)) {
          content = content.replaceAll(placeholder, value);
        }
        writeFileSync(destPath, content, "utf8");
      }
    }
  }
}

/**
 * Build the contents of a .env file.
 * @param {"postgres" | "sqlite"} dbType
 * @param {string} projectName
 * @returns {string}
 */
function buildEnvContent(dbType, projectName) {
  const signingKey = generateSecret();
  const dbUrl =
    dbType === "sqlite"
      ? `sqlite+aiosqlite:///./data/${projectName}.db`
      : `postgresql+psycopg://postgres:postgres@localhost:5432/${projectName}`;

  return [
    "# h4ckath0n environment",
    "H4CKATH0N_ENV=development",
    `H4CKATH0N_DATABASE_URL=${dbUrl}`,
    `H4CKATH0N_AUTH_SIGNING_KEY=${signingKey}`,
    "H4CKATH0N_RP_ID=localhost",
    "H4CKATH0N_ORIGIN=http://localhost:5173",
    "VITE_API_BASE_URL=/api",
    "",
  ].join("\n");
}

/**
 * Build the contents of a .env.example file.
 * @param {"postgres" | "sqlite"} dbType
 * @returns {string}
 */
function buildEnvExampleContent(dbType) {
  const dbPlaceholder =
    dbType === "sqlite"
      ? "sqlite+aiosqlite:///./data/myproject.db"
      : "postgresql+psycopg://postgres:postgres@localhost:5432/myproject";

  return [
    "# h4ckath0n environment",
    "H4CKATH0N_ENV=development",
    `H4CKATH0N_DATABASE_URL=${dbPlaceholder}`,
    "H4CKATH0N_AUTH_SIGNING_KEY=<random-hex-secret>",
    "H4CKATH0N_RP_ID=localhost",
    "H4CKATH0N_ORIGIN=http://localhost:5173",
    "VITE_API_BASE_URL=/api",
    "",
  ].join("\n");
}

/**
 * Write .env and .env.example into the destination directory.
 * @param {string} dest - project root directory
 * @param {"postgres" | "sqlite"} dbType
 * @param {string} projectName
 */
export function writeEnvFiles(dest, dbType, projectName) {
  writeFileSync(join(dest, ".env"), buildEnvContent(dbType, projectName), "utf8");
  writeFileSync(join(dest, ".env.example"), buildEnvExampleContent(dbType), "utf8");
}

/**
 * Check whether a directory already exists and is non-empty.
 * @param {string} dir
 * @returns {boolean}
 */
export function dirExists(dir) {
  return existsSync(dir) && statSync(dir).isDirectory();
}
