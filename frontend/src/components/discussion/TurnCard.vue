<!-- One participant's turn: name, avatar, status and the (streamed) text. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { ParticipantSnapshot } from '../../contracts/messages'
import type { TurnState } from '../../stores/discussion'
import { renderMarkdown } from './markdown'
import ParticipantAvatar from './ParticipantAvatar.vue'

const props = defineProps<{ turn: TurnState; participant: ParticipantSnapshot | undefined }>()

const STATUS_LABELS: Record<TurnState['status'], string> = {
  running: '回覆中',
  ok: '完成',
  failed: '失敗',
  timeout: '逾時',
}

const html = computed(() => renderMarkdown(props.turn.text))
const name = computed(() => props.participant?.display_name ?? props.turn.participantId)
</script>

<template>
  <article class="turn-card" :class="`status-${turn.status}`" data-testid="turn-card" :data-participant-id="turn.participantId">
    <header class="turn-header">
      <ParticipantAvatar :avatar="participant?.avatar ?? 'default.png'" />
      <span class="turn-name">{{ name }}</span>
      <span v-if="participant && !participant.capabilities.web_access" class="badge">無上網</span>
      <span class="turn-status" data-testid="turn-status">{{ STATUS_LABELS[turn.status] }}</span>
    </header>
    <p v-if="turn.failure" class="turn-failure" data-testid="turn-failure">{{ turn.failure.reason }}</p>
    <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
    <div class="turn-text" data-testid="turn-text" v-html="html" />
    <p v-if="turn.status === 'running' && !turn.text" class="muted">回覆中…</p>
  </article>
</template>

<style scoped>
.turn-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.75rem;
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 8px;
}
.turn-card.status-failed,
.turn-card.status-timeout {
  border-color: #e5a29a;
}
.turn-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.turn-name {
  font-weight: 600;
}
.turn-status {
  margin-left: auto;
  font-size: 0.8rem;
  color: #6b7280;
}
.status-running .turn-status {
  color: #2f6feb;
}
.status-failed .turn-status,
.status-timeout .turn-status {
  color: #a1260d;
}
.badge {
  font-size: 0.75rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: #e8ebef;
  color: #4a5159;
}
.turn-failure {
  margin: 0;
  color: #a1260d;
  font-size: 0.9rem;
}
.turn-text {
  overflow-wrap: anywhere;
  line-height: 1.55;
}
.turn-text :deep(p) {
  margin: 0 0 0.5rem;
}
.turn-text :deep(pre) {
  overflow-x: auto;
  background: #f3f4f6;
  padding: 0.5rem;
  border-radius: 4px;
}
.muted {
  color: #6b7280;
  margin: 0;
}
</style>
