import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

// In CI the h4ckath0n library is installed from the repo root.
// Locally, the same `uv run` from repo root makes the library available.
const repoRoot = resolve(__dirname, "../../../../..");
const apiDir = resolve(__dirname, "../api");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  webServer: [
    {
      command: `uv run --directory ${repoRoot} --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: apiDir,
      url: "http://127.0.0.1:8000/healthz",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npx vite --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
