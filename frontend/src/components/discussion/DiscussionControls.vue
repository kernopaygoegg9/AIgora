<!-- Controls of a live discussion: interject (插話, applies from the next round) and stop (停止).
     Also lists the queued interjections and says when the user stopped the discussion. -->
<script setup lang="ts">
import { ref } from 'vue'

import type { ModeId, Outcome } from '../../contracts/messages'
import type { DiscussionStatus, Interjection } from '../../stores/discussion'

defineProps<{
  status: DiscussionStatus
  /** A one-round ask has no next round, so it offers no interjection. */
  mode: ModeId | null
  interjections: Interjection[]
  outcome: Outcome | null
  readOnly?: boolean
}>()

const emit = defineEmits<{ interject: [text: string]; stop: [] }>()

const draft = ref('')
const stopping = ref(false)

function interject() {
  const text = draft.value.trim()
  if (!text) return
  emit('interject', text)
  draft.value = ''
}

function stop() {
  stopping.value = true
  emit('stop')
}
</script>

<template>
  <section v-if="status !== 'idle'" class="discussion-controls" data-testid="discussion-controls">
    <form
      v-if="status === 'running' && !readOnly && mode !== 'ask'"
      class="interject"
      @submit.prevent="interject"
    >
      <label class="interject-label" for="interject-text">插話</label>
      <textarea
        id="interject-text"
        v-model="draft"
        rows="2"
        placeholder="補充資訊或修正問題；從下一輪開始生效"
        @keydown.enter.ctrl.prevent="interject"
      />
      <button type="submit" :disabled="!draft.trim()">送出插話</button>
    </form>

    <ul v-if="interjections.length" class="interjections">
      <li v-for="(item, i) in interjections" :key="i" class="interjection" data-testid="interjection">
        <span class="applies">插話（第 {{ item.appliesToRound }} 輪起生效）</span>
        <span class="text">{{ item.text }}</span>
      </li>
    </ul>

    <div v-if="status === 'running' && !readOnly" class="stop-row">
      <button type="button" class="stop" :disabled="stopping" @click="stop">停止</button>
    </div>

    <p v-if="outcome === 'stopped'" class="stopped" data-testid="discussion-stopped">
      討論已停止：進行中的發言已取消，目前的內容已存檔。
    </p>
  </section>
</template>

<style scoped>
.discussion-controls {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.interject {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.25rem 0.5rem;
  align-items: end;
}
.interject-label {
  grid-column: 1 / -1;
  font-size: 0.85rem;
  color: #4a5159;
}
.interject textarea {
  font: inherit;
  padding: 0.4rem 0.5rem;
  border: 1px solid #c9ced4;
  border-radius: 6px;
  resize: vertical;
  min-width: 0;
}
.interjections {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.interjection {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border-left: 3px solid #2f6feb;
  background: #f2f6fe;
  border-radius: 4px;
}
.applies {
  font-size: 0.8rem;
  color: #2f6feb;
}
.text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.stop-row {
  display: flex;
  justify-content: flex-end;
}
.stop {
  color: #fff;
  background: #a1260d;
  border: none;
  border-radius: 6px;
  padding: 0.4rem 1rem;
  cursor: pointer;
}
.stop:disabled {
  opacity: 0.6;
  cursor: default;
}
.stopped {
  margin: 0;
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  background: #fdf0ee;
  color: #a1260d;
}
</style>
