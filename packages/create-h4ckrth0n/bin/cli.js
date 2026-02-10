#!/usr/bin/env node

import { execSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { copyDir, dirExists, generateSecret, validateProjectName, writeEnvFiles } from "../lib/scaffold.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function printUsage() {
  console.log(`
Usage: h4ckrth0n <project-name> [options]

Options:
  --no-install   Skip dependency installation (uv sync / npm install)
  --no-git       Skip git init
  --no-python    Skip Python backend scaffolding
  --no-node      Skip Node/React frontend scaffolding
  --db <type>    Database type: postgres (default) or sqlite
  -h, --help     Show this help message
`);
}

// ---------------------------------------------------------------------------
// Arg parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {
    name: null,
    install: true,
    git: true,
    python: true,
    node: true,
    db: "postgres",
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--no-install") {
      opts.install = false;
    } else if (arg === "--no-git") {
      opts.git = false;
    } else if (arg === "--no-python") {
      opts.python = false;
    } else if (arg === "--no-node") {
      opts.node = false;
    } else if (arg === "--db") {
      i++;
      const val = args[i];
      if (val !== "postgres" && val !== "sqlite") {
        console.error(`Error: --db must be "postgres" or "sqlite", got "${val}".`);
        process.exit(1);
      }
      opts.db = val;
    } else if (arg === "-h" || arg === "--help") {
      opts.help = true;
    } else if (arg.startsWith("-")) {
      console.error(`Error: Unknown flag "${arg}". Use --help for usage.`);
      process.exit(1);
    } else if (!opts.name) {
      opts.name = arg;
    } else {
      console.error(`Error: Unexpected argument "${arg}". Only one project name allowed.`);
      process.exit(1);
    }
  }

  return opts;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const opts = parseArgs(process.argv);

  if (opts.help) {
    printUsage();
    process.exit(0);
  }

  if (!opts.name) {
    console.error("Error: Please provide a project name.\n");
    printUsage();
    process.exit(1);
  }

  const validation = validateProjectName(opts.name);
  if (!validation.valid) {
    console.error(`Error: ${validation.reason}`);
    process.exit(1);
  }

  const projectDir = resolve(process.cwd(), opts.name);

  if (dirExists(projectDir) && readdirSync(projectDir).length > 0) {
    console.error(`Error: Directory "${opts.name}" already exists and is not empty.`);
    process.exit(1);
  }

  // Locate templates directory (bundled inside the npm package).
  const templatesDir = join(__dirname, "..", "templates", "fullstack");
  if (!existsSync(templatesDir)) {
    console.error(
      `Error: Templates directory not found at "${templatesDir}".\n` +
        "This is a packaging issue — please report it.",
    );
    process.exit(1);
  }

  console.log(`\n🚀 Creating project "${opts.name}" in ${projectDir}\n`);

  // Placeholder replacements applied to every text file in the template.
  const replacements = {
    "{{PROJECT_NAME}}": opts.name,
  };

  copyDir(templatesDir, projectDir, replacements);

  // Write .env / .env.example
  writeEnvFiles(projectDir, opts.db, opts.name);

  console.log("✅ Project files created.");

  // ---- Optional: git init ----
  if (opts.git) {
    try {
      execSync("git init", { cwd: projectDir, stdio: "ignore" });
      console.log("✅ Initialized git repository.");
    } catch {
      console.warn("⚠️  Could not run git init. Skipping.");
    }
  }

  // ---- Optional: install deps ----
  if (opts.install) {
    if (opts.python && existsSync(join(projectDir, "backend"))) {
      console.log("📦 Installing Python dependencies (uv sync)...");
      try {
        execSync("uv sync", { cwd: join(projectDir, "backend"), stdio: "inherit" });
        console.log("✅ Python dependencies installed.");
      } catch {
        console.warn("⚠️  uv sync failed. You can run it manually later.");
      }
    }

    if (opts.node && existsSync(join(projectDir, "web"))) {
      console.log("📦 Installing Node dependencies (npm install)...");
      try {
        execSync("npm install", { cwd: join(projectDir, "web"), stdio: "inherit" });
        console.log("✅ Node dependencies installed.");
      } catch {
        console.warn("⚠️  npm install failed. You can run it manually later.");
      }
    }
  }

  // ---- Success ----
  console.log(`
🎉 Done! Your project is ready.

Next steps:

  cd ${opts.name}

  # Start the backend
  cd backend && uv run uvicorn app.main:app --reload

  # Start the frontend (in another terminal)
  cd web && npm run dev

  # Open http://localhost:5173

Happy hacking! 🏴‍☠️
`);
}

main();
