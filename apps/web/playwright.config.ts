import { defineConfig, devices } from "@playwright/test";

// BASE_URL=https://... runs against a deployment; otherwise a local dev server is started.
const baseURL = process.env.BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "e2e",
  timeout: 120_000,
  retries: 0,
  use: { baseURL, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.BASE_URL
    ? undefined
    : { command: "pnpm build && pnpm start", url: baseURL, reuseExistingServer: false, timeout: 600_000 },
});
