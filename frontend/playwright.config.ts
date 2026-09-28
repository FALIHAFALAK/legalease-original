import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const FRONTEND_PORT = 3000;
const BACKEND_PORT = 8000;
const AUTH_FILE = path.join(__dirname, 'e2e', '.auth', 'user.json');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list']],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'desktop',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        storageState: AUTH_FILE,
      },
    },
    {
      name: 'tablet',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 834, height: 1112 },
        storageState: AUTH_FILE,
      },
    },
    {
      name: 'mobile',
      dependencies: ['setup'],
      use: { ...devices['Pixel 7'], storageState: AUTH_FILE },
    },
  ],
  webServer: [
    {
      // The API does not create its own schema on startup, so apply migrations first.
      // `&&` is intentional: Playwright runs this through the platform shell.
      command:
        `python -m alembic upgrade head && ` +
        `python -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT} --log-level warning`,
      cwd: '../backend',
      url: `http://127.0.0.1:${BACKEND_PORT}/api/auth/csrf`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        APP_ENV: 'development',
        AI_PROVIDER: 'mock',
        SECRET_KEY: 'e2e-verification-key-not-a-real-secret-000',
        DATABASE_URL: 'sqlite:///./e2e_playwright.db',
        CORS_ORIGINS: `http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}`,
      },
    },
    {
      command: `npm run start -- -p ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
