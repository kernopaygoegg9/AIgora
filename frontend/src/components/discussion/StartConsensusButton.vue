<!-- 提問轉共識討論 (ticket 10): after an ask has finished normally, offers to start a
     consensus discussion with the same question and participants. The ask's answers become
     its round 1 (the backend copies them), so it starts with the moderator's first draft.
     The other settings are the defaults; the judge falls back to an available one. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { OptionsResponse } from '../../contracts/http'
import type { DiscussionSettings, Outcome, StartSettings } from '../../contracts/messages'

const props = defineProps<{
  discussionId: string | null
  settings: DiscussionSettings | null
  outcome: Outcome | null
  options: OptionsResponse | null
}>()

const emit = defineEmits<{ start: [settings: StartSettings, fromDiscussionId: string] }>()

const visible = computed(
  () => props.discussionId !== null && props.settings?.mode === 'ask' && props.outcome === 'completed',
)

function start() {
  if (!props.discussionId || !props.settings) return
  const judges = props.options?.judges ?? []
  const preferred = judges.find((j) => j.id === props.options?.defaults.judge && j.available)
  const judge = preferred?.id ?? judges.find((j) => j.available)?.id ?? null
  emit(
    'start',
    { mode: 'consensus', participant_ids: [...props.settings.participant_ids], judge },
    props.discussionId,
  )
}
</script>

<template>
  <div v-if="visible" class="start-consensus">
    <button type="button" data-testid="start-consensus" @click="start">開始共識討論</button>
    <span class="hint">沿用這個問題與參與者，現有的發言當作第 1 輪</span>
  </div>
</template>

<style scoped>
.start-consensus {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
button {
  padding: 0.45rem 1rem;
  border-radius: 8px;
  border: 1px solid #2f6f4f;
  background: #2f6f4f;
  color: #fff;
  font: inherit;
  cursor: pointer;
}
button:hover {
  background: #265a40;
}
.hint {
  font-size: 0.85rem;
  color: #6b7280;
}
</style>
