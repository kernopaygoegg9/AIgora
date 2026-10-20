import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const backendPort = 8766
const frontendPort = 5174

// E2E runs against the real backend with Fake Adapter participants only
// (no AI quota). Records go to a throwaway folder ignored by git.
const backendEnv = {
  AIGORA_PORT: String(backendPort),
  AIGORA_PARTICIPANTS_FILE: path.join(here, 'e2e', 'participants.e2e.toml'),
  AIGORA_DATA_DIR: path.join(here, 'test-results', 'discussions'),
  AIGORA_ENV_FILE: path.join(here, 'e2e', 'e2e.env'),
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run --directory ../backend aigora',
      url: `http://127.0.0.1:${backendPort}/docs`,
      env: backendEnv,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --port ${frontendPort} --strictPort`,
      url: `http://127.0.0.1:${frontendPort}`,
      env: { AIGORA_BACKEND_PORT: String(backendPort) },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
