// Smoke test for the Hot Seat lecture runner. Runs against the static files in local test mode (no Firebase).
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests",
  timeout: 30000,
  retries: 0,
  use: { baseURL: "http://localhost:8788", headless: true },
  webServer: { command: "python3 -m http.server 8788", url: "http://localhost:8788/present.html", reuseExistingServer: true, timeout: 10000 },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
