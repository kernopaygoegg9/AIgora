<!-- One participant's turn: who (ParticipantLabel), status, the (streamed) text and the 表態. -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { TurnState } from '../../stores/discussion'
import { stanceLabel } from '../labels'
import { renderMarkdown } from './markdown'
import ParticipantLabel from './ParticipantLabel.vue'

const props = defineProps<{ turn: TurnState; participant: ParticipantSnapshot | undefined }>()

const STATUS_LABELS: Record<TurnState['status'], string> = {
  running: '回覆中',
  ok: '完成',
  failed: '失敗',
  timeout: '逾時',
}
const STATUS_PILLS: Record<TurnState['status'], string> = {
  running: 'pill-accent',
  ok: '',
  failed: 'pill-bad',
  timeout: 'pill-bad',
}

const html = computed(() => renderMarkdown(props.turn.text))
const failed = computed(() => props.turn.status === 'failed' || props.turn.status === 'timeout')
</script>

<template>
  <article
    class="turn-card d-turn"
    :class="[`status-${turn.status}`, { 'is-running': turn.status === 'running', 'is-failed': failed }]"
    data-testid="turn-card"
    :data-participant-id="turn.participantId"
  >
    <header class="d-turn-head">
      <ParticipantLabel :participant="participant" :id="turn.participantId" />
      <span class="pill" :class="STATUS_PILLS[turn.status]" data-testid="turn-status">{{ STATUS_LABELS[turn.status] }}</span>
    </header>
    <p v-if="turn.failure" class="d-failure" data-testid="turn-failure">{{ turn.failure.reason }}</p>
    <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
    <div class="turn-text d-md" :class="{ 'd-caret': turn.status === 'running' }" data-testid="turn-text" v-html="html" />
    <p v-if="turn.status === 'running' && !turn.text" class="muted waiting">回覆中…</p>
    <p v-if="turn.stance" class="d-stance-line" :class="`is-${turn.stance}`">STANCE: {{ turn.stance }} · {{ stanceLabel(turn.stance) }}</p>
  </article>
</template>

<style scoped>
.waiting {
  margin: 0;
  font-size: var(--fs-sm);
}
.d-stance-line {
  margin: 0;
}
</style>
