<!--
  A participant's model picker (ui-redesign 11): 「預設（…）」, the listed models and, when
  the Adapter accepts any model name, 「其他…」 with a text box. `choice` is '' for the
  default, a listed model id, or OTHER_MODEL; `custom` is the text typed for 其他.
-->
<script lang="ts">
export const OTHER_MODEL = '__other__'
</script>

<script setup lang="ts">
import type { ModelOption } from '../../contracts/http'

defineProps<{
  /** Accessible name of the select (「<顯示名稱> 的模型」). */
  label: string
  /** The model in the participants file; null = Adapter 預設. */
  defaultModel: string | null
  models: ModelOption[]
  freeText: boolean
  error?: string | null
  disabled?: boolean
}>()
const choice = defineModel<string>('choice', { required: true })
const custom = defineModel<string>('custom', { required: true })
</script>

<template>
  <span class="model-select">
    <select v-model="choice" :aria-label="label" :disabled="disabled">
      <option value="">預設（{{ defaultModel ?? 'Adapter 預設' }}）</option>
      <option v-for="m in models" :key="m.id" :value="m.id">{{ m.label }}</option>
      <option v-if="freeText" :value="OTHER_MODEL">其他…</option>
    </select>
    <input
      v-if="choice === OTHER_MODEL && !disabled"
      v-model="custom"
      class="custom"
      type="text"
      :aria-label="label.replace(/的模型$/, '的自訂模型')"
      placeholder="模型名稱"
      spellcheck="false"
    />
    <small v-if="error" class="error" data-testid="models-error" :title="error"
      >清單載入失敗：{{ error }}</small
    >
  </span>
</template>

<style scoped>
.model-select {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  min-width: 0;
}
select,
.custom {
  padding: 4px 8px;
  font-size: var(--fs-sm);
}
select {
  width: 100%;
  min-width: 6rem;
  max-width: 13rem;
}
.custom {
  width: 10rem;
  font-family: var(--font-mono);
}
.error {
  flex-basis: 100%;
  color: var(--warn);
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
</style>
