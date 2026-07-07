import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "pnpm run dev",
      port: 3000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8000",
      },
    },
    {
      command:
        "cd ../../apps/api && uvicorn src.app.main:app --port 8000",
      port: 8000,
      reuseExistingServer: !process.env.CI,
      env: {
        CORS_ALLOWED_ORIGINS: "http://localhost:3000",
        APP_ENV: "test",
        DATABASE_URL: process.env.DATABASE_URL || "",
        VALKEY_URL: process.env.VALKEY_URL || "",
        JWT_PRIVATE_KEY: process.env.JWT_PRIVATE_KEY || "",
        JWT_PUBLIC_KEY: process.env.JWT_PUBLIC_KEY || "",
      },
    },
  ],
});
