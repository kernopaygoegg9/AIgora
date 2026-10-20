// Light / dark theme (ui-redesign spec "設計 token 與主題"). HOT FILE (owner: ui-redesign ticket 01).
//
// `system` follows prefers-color-scheme (no data-theme attribute); `light` / `dark` force a
// theme with <html data-theme>. The choice is kept in localStorage; index.html applies it
// before the app loads so the page does not flash the other theme. Storage may be blocked
// (private window, cleared site data): then the theme simply follows the system.
import { readonly, ref } from 'vue'

export type ThemeMode = 'system' | 'light' | 'dark'

export const THEME_STORAGE_KEY = 'aigora.theme'
const MODES: readonly ThemeMode[] = ['system', 'light', 'dark']

function readStored(): ThemeMode {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY)
    return MODES.includes(value as ThemeMode) ? (value as ThemeMode) : 'system'
  } catch {
    return 'system'
  }
}

function apply(mode: ThemeMode): void {
  const root = document.documentElement
  if (mode === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', mode)
}

// One state for the whole app.
const mode = ref<ThemeMode>(readStored())
apply(mode.value)

function setMode(next: ThemeMode): void {
  mode.value = next
  apply(next)
  try {
    if (next === 'system') localStorage.removeItem(THEME_STORAGE_KEY)
    else localStorage.setItem(THEME_STORAGE_KEY, next)
  } catch {
    // Not stored: the choice lasts until the page is reloaded.
  }
}

/** Next mode in the cycle 跟隨系統 → 亮色 → 暗色. */
function cycle(): void {
  setMode(MODES[(MODES.indexOf(mode.value) + 1) % MODES.length])
}

export function useTheme() {
  return { mode: readonly(mode), setMode, cycle }
}
