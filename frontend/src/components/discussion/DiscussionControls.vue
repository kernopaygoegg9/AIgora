<!-- The interjection dock (插話, applies from the next round), fixed to the bottom of the stage.
     Only while a multi-round discussion runs; stop (停止) lives in the top bar and the queued
     interjections in the inspector (ui-redesign 04). -->
<script setup lang="ts">
import { ref } from 'vue'

import type { ModeId } from '../../contracts/messages'
import type { DiscussionStatus } from '../../stores/discussion'

defineProps<{
  status: DiscussionStatus
  /** A one-round ask has no next round, so it offers no interjection. */
  mode: ModeId | null
  readOnly?: boolean
}>()

const emit = defineEmits<{ interject: [text: string] }>()

const draft = ref('')

function interject() {
  const text = draft.value.trim()
  if (!text) return
  emit('interject', text)
  draft.value = ''
}
</script>

<template>
  <form
    v-if="status === 'running' && !readOnly && mode !== 'ask'"
    class="discussion-controls dock"
    data-testid="discussion-controls"
    @submit.prevent="interject"
  >
    <label class="visually-hidden" for="interject-text">插話</label>
    <textarea
      id="interject-text"
      v-model="draft"
      rows="1"
      placeholder="插話：補充資訊或修正問題；從下一輪開始生效（Ctrl+Enter 送出）"
      @keydown.enter.ctrl.prevent="interject"
    />
    <button type="submit" class="btn btn-primary" :disabled="!draft.trim()">送出插話</button>
  </form>
</template>

<style scoped>
.dock {
  position: sticky;
  bottom: 0;
  z-index: 2;
  display: flex;
  gap: var(--space-2);
  align-items: flex-end;
  padding: 10px var(--space-3);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}
.dock textarea {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  max-height: 30vh;
  padding: 8px 10px;
  background: var(--bg);
  border-radius: var(--radius);
  resize: vertical;
}
</style>
