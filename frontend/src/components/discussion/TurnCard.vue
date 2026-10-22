<!-- One participant's turn: who (ParticipantLabel), status, the (streamed) text and the 表態. -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { TurnState } from '../../stores/discussion'
import { TURN_STATUS_LABELS, TURN_STATUS_PILLS, stanceLabel } from '../labels'
import { renderMarkdown } from './markdown'
import ParticipantLabel from './ParticipantLabel.vue'

const props = defineProps<{ turn: TurnState; participant: ParticipantSnapshot | undefined }>()

// The reply ends with its raw `STANCE: …` line; with a parsed stance the footer below shows
// it, so leave that line out of the text (display only; same rule as backend stance.py).
const STANCE_LINE = /^STANCE:\s*(AGREE|DISAGREE)$/i
function withoutStanceLine(text: string): string {
  const lines = text.trimEnd().split(/\r?\n/)
  const last = lines[lines.length - 1]
  return last !== undefined && STANCE_LINE.test(last.trim())
    ? lines.slice(0, -1).join('\n').trimEnd()
    : text
}

const html = computed(() =>
  renderMarkdown(props.turn.stance ? withoutStanceLine(props.turn.text) : props.turn.text),
)
const failed = computed(() => props.turn.status === 'failed' || props.turn.status === 'timeout')
</script>

<template>
  <article
    class="turn-card d-turn"
    :class="[
      `status-${turn.status}`,
      { 'is-running': turn.status === 'running', 'is-failed': failed },
    ]"
    data-testid="turn-card"
    :data-participant-id="turn.participantId"
  >
    <header class="d-turn-head">
      <ParticipantLabel :id="turn.participantId" :participant="participant" />
      <span class="pill" :class="TURN_STATUS_PILLS[turn.status]" data-testid="turn-status">{{
        TURN_STATUS_LABELS[turn.status]
      }}</span>
    </header>
    <p v-if="turn.failure" class="d-failure" data-testid="turn-failure">
      {{ turn.failure.reason }}
    </p>
    <!-- eslint-disable vue/no-v-html -- sanitised in renderMarkdown -->
    <div
      class="turn-text d-md"
      :class="{ 'd-caret': turn.status === 'running' }"
      data-testid="turn-text"
      v-html="html"
    />
    <!-- eslint-enable vue/no-v-html -->
    <p v-if="turn.status === 'running' && !turn.text" class="muted waiting">回覆中…</p>
    <!-- `stance` slot: the read-only record (07) adds its own testid to the same line. -->
    <slot name="stance">
      <p v-if="turn.stance" class="d-stance-line" :class="`is-${turn.stance}`">
        STANCE: {{ turn.stance }} · {{ stanceLabel(turn.stance) }}
      </p>
    </slot>
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
