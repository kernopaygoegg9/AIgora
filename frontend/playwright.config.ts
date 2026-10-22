import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { mkdtempSync } from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))

// Ask the OS for `count` free ports on 127.0.0.1. All are held open until every
// one is known, so they are distinct.
async function freePorts(count: number): Promise<number[]> {
  const servers = await Promise.all(
    Array.from(
      { length: count },
      () =>
        new Promise<net.Server>((resolve, reject) => {
          const server = net.createServer()
          server.once('error', reject)
          server.listen(0, '127.0.0.1', () => resolve(server))
        }),
    ),
  )
  const ports = servers.map((s) => (s.address() as net.AddressInfo).port)
  await Promise.all(servers.map((s) => new Promise((resolve) => s.close(resolve))))
  return ports
}

// Ports and the records folder are chosen once, in the main process, and written
// back to process.env: Playwright workers reload this file and inherit the
// environment, so they see the same values instead of picking new ones.
// Set AIGORA_E2E_BACKEND_PORT / AIGORA_E2E_FRONTEND_PORT to pin the ports.
if (!process.env.AIGORA_E2E_BACKEND_PORT || !process.env.AIGORA_E2E_FRONTEND_PORT) {
  const [backend, frontend] = await freePorts(2)
  process.env.AIGORA_E2E_BACKEND_PORT ||= String(backend)
  process.env.AIGORA_E2E_FRONTEND_PORT ||= String(frontend)
}
// A fresh records folder per run, outside test-results (which a parallel run wipes).
process.env.AIGORA_E2E_DATA_DIR ||= mkdtempSync(path.join(os.tmpdir(), 'aigora-e2e-'))

const backendPort: string = process.env.AIGORA_E2E_BACKEND_PORT
const frontendPort: string = process.env.AIGORA_E2E_FRONTEND_PORT
const dataDir: string = process.env.AIGORA_E2E_DATA_DIR

// E2E runs against the real backend with Fake Adapter participants only
// (no AI quota).
const backendEnv = {
  AIGORA_PORT: backendPort,
  AIGORA_PARTICIPANTS_FILE: path.join(here, 'e2e', 'participants.e2e.toml'),
  AIGORA_DATA_DIR: dataDir,
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
      env: { AIGORA_PORT: backendPort },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
