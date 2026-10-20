<!-- Theme switch in the sidebar: 跟隨系統 → 亮色 → 暗色 (composables/useTheme.ts). -->
<script setup lang="ts">
import { computed } from 'vue'

import { useTheme, type ThemeMode } from '../../composables/useTheme'

const { mode, cycle } = useTheme()

const LABELS: Record<ThemeMode, string> = { system: '跟隨系統', light: '亮色', dark: '暗色' }
const ICONS: Record<ThemeMode, string> = { system: '◐', light: '☀', dark: '☾' }
const label = computed(() => LABELS[mode.value])
</script>

<template>
  <button type="button" class="theme-toggle" data-testid="theme-toggle" :data-mode="mode" title="切換主題" @click="cycle">
    <span class="icon" aria-hidden="true">{{ ICONS[mode] }}</span>
    <span>主題：{{ label }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-2);
  color: var(--muted);
  font-size: var(--fs-sm);
  cursor: pointer;
}
.theme-toggle:hover {
  color: var(--text);
  border-color: var(--muted);
}
.icon {
  width: 1em;
  text-align: center;
}
</style>
