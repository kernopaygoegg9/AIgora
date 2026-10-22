import { rmSync } from 'node:fs'

// Removes the records folder playwright.config.ts created for this run. A folder
// given through AIGORA_E2E_DATA_DIR is left alone.
export default function globalTeardown(): void {
  const dir = process.env.AIGORA_E2E_CREATED_DATA_DIR
  if (!dir || dir !== process.env.AIGORA_E2E_DATA_DIR) return
  try {
    rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  } catch (error) {
    console.warn(`could not remove E2E records folder ${dir}:`, error)
  }
}
