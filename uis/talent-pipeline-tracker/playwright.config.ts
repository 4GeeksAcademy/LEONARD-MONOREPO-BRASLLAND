import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { randomBytes } from "node:crypto";
import os from "node:os";
import path from "node:path";

const root = path.resolve(__dirname, "../..");
const data = mkdtempSync(path.join(os.tmpdir(), "brasaland-auth02-"));

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  fullyParallel: false,
  timeout: 45000,
  use: { baseURL: "http://127.0.0.1:3011", browserName: "chromium", trace: "retain-on-failure" },
  webServer: [
    {
      command: "uv run --project services/api uvicorn services.api.app.main:app --host 127.0.0.1 --port 8013",
      cwd: root,
      url: "http://127.0.0.1:8013/docs",
      env: {
        JWT_SECRET_KEY: randomBytes(48).toString("hex"),
        AUTH_DB_PATH: path.join(data, "auth.json"),
        SUPPLIERS_DB_PATH: path.join(data, "suppliers.json"),
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011/login",
      env: { AUTH_API_URL: "http://127.0.0.1:8013" },
      timeout: 120000,
    },
  ],
});