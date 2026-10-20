<!-- One round of a saved record (read-only): what happened before it (interjections,
     moderator changes), the turns side by side, then draft, verdict, confirmations, removals. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { ParticipantSnapshot } from '../../contracts/messages'
import type {
  RecordInterjection,
  RecordModeratorChange,
  RecordRemoval,
  RecordRound,
  RecordTurn,
} from '../../contracts/record'
import type { TurnState } from '../../stores/discussion'
import { renderMarkdown } from '../discussion/markdown'
import TurnCard from '../discussion/TurnCard.vue'
import { JUDGE_LABELS, JUDGE_OUTCOME_LABELS, formatTime, stanceLabel } from './labels'

const props = defineProps<{
  round: RecordRound
  participantById: (id: string) => ParticipantSnapshot | undefined
  showNumber: boolean
  interjections: RecordInterjection[]
  moderatorChanges: RecordModeratorChange[]
  removals: RecordRemoval[]
}>()

const name = (id: string) => props.participantById(id)?.display_name ?? id

// TurnCard renders the live store's TurnState; a saved turn maps onto it directly.
function toTurnState(t: RecordTurn): TurnState {
  return {
    round: props.round.number,
    participantId: t.participant_id,
    purpose: 'turn',
    status: t.status,
    text: t.text ?? '',
    stance: t.stance,
    failure: t.status === 'ok' ? null : { kind: t.status === 'timeout' ? 'timeout' : 'unknown', reason: t.error ?? '' },
  }
}

const turns = computed(() => props.round.turns.map((t) => ({ record: t, state: toTurnState(t) })))
const draftHtml = computed(() => (props.round.draft ? renderMarkdown(props.round.draft) : ''))
const judge = computed(() => props.round.judge ?? null)
const stances = computed(() => Object.entries(judge.value?.detail.stances ?? {}))
</script>

<template>
  <section class="record-round" data-testid="record-round" :data-round="round.number">
    <h2 v-if="showNumber" class="round-title">第 {{ round.number }} 輪</h2>

    <p v-for="(i, k) in interjections" :key="`i${k}`" class="event interjection" data-testid="record-interjection">
      <span class="event-label">使用者插話</span>
      <time :datetime="i.at">{{ formatTime(i.at) }}</time>
      <span class="event-text">{{ i.text }}</span>
    </p>
    <p v-for="(c, k) in moderatorChanges" :key="`m${k}`" class="event" data-testid="record-moderator-change">
      <span class="event-label">主持人接手</span>
      <span>{{ name(c.participant_id) }} 成為主持人</span>
    </p>

    <div class="turns" :style="{ '--columns': Math.max(turns.length, 1) }">
      <div v-for="t in turns" :key="t.record.participant_id" class="record-turn" data-testid="record-turn">
        <TurnCard :turn="t.state" :participant="participantById(t.record.participant_id)" />
        <span v-if="t.record.stance" class="stance" :class="t.record.stance" data-testid="record-stance">{{
          stanceLabel(t.record.stance)
        }}</span>
      </div>
    </div>

    <div v-if="round.draft" class="block draft" data-testid="record-draft">
      <h3 class="block-title">共識草案</h3>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
      <div class="block-text" v-html="draftHtml" />
    </div>

    <div v-if="judge" class="block" data-testid="record-judge">
      <h3 class="block-title">
        共識裁定（{{ JUDGE_LABELS[judge.judge] ?? judge.judge }}）：{{ JUDGE_OUTCOME_LABELS[judge.outcome] ?? judge.outcome }}
      </h3>
      <ul v-if="stances.length" class="plain-list">
        <li v-for="[pid, stance] in stances" :key="pid">{{ name(pid) }}：{{ stanceLabel(stance) }}</li>
      </ul>
      <p v-if="judge.detail.probability != null" class="block-text">
        Jev 機率 {{ judge.detail.probability }}<template v-if="judge.detail.threshold != null">
          （門檻 {{ judge.detail.threshold }}）</template
        >
      </p>
    </div>

    <div v-if="round.confirmations?.length" class="block" data-testid="record-confirmation">
      <h3 class="block-title">反問確認</h3>
      <ul class="plain-list">
        <li v-for="c in round.confirmations" :key="c.participant_id">
          {{ name(c.participant_id) }}：{{ c.agree ? '同意' : '不同意' }}<template v-if="c.reason">（{{ c.reason }}）</template>
        </li>
      </ul>
    </div>

    <p v-for="(r, k) in removals" :key="`r${k}`" class="event removal" data-testid="record-removal">
      <span class="event-label">移出討論</span>
      <span>{{ name(r.participant_id) }}：{{ r.reason }}</span>
    </p>
  </section>
</template>

<style scoped>
.record-round {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.round-title {
  font-size: 1rem;
  margin: 0;
}
.turns {
  display: grid;
  grid-template-columns: repeat(var(--columns), minmax(16rem, 1fr));
  gap: 0.75rem;
  align-items: start;
  overflow-x: auto;
}
.record-turn {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}
.stance {
  align-self: flex-start;
  font-size: 0.8rem;
  padding: 0 0.5rem;
  border-radius: 999px;
  background: #e8ebef;
}
.stance.AGREE {
  background: #dcf2e3;
  color: #1a6b37;
}
.stance.DISAGREE {
  background: #fbe4e1;
  color: #a1260d;
}
.block {
  padding: 0.75rem;
  background: #fff;
  border: 1px dashed #b7c0cc;
  border-radius: 8px;
}
.block-title {
  font-size: 0.95rem;
  margin: 0 0 0.25rem;
}
.block-text {
  margin: 0;
  overflow-wrap: anywhere;
  line-height: 1.55;
}
.block-text :deep(p) {
  margin: 0 0 0.5rem;
}
.plain-list {
  margin: 0;
  padding-left: 1.25rem;
}
.event {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.9rem;
}
.event-label {
  font-weight: 600;
}
.event time {
  color: #6b7280;
}
.event-text {
  white-space: pre-wrap;
}
.removal {
  color: #a1260d;
}
</style>
