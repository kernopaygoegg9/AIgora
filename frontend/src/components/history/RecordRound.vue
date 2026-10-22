<!-- One round of a saved record (read-only), in the live page's look (ui-redesign 07): what
     happened before it (interjections, moderator changes), the turns side by side, removals,
     then draft | verdicts and confirmations. -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'

import type { ParticipantSnapshot, Stance } from '../../contracts/messages'
import type {
  RecordInterjection,
  RecordModeratorChange,
  RecordRemoval,
  RecordRound,
  RecordTurn,
} from '../../contracts/record'
import type { TurnState } from '../../stores/discussion'
import ConfirmationList from '../discussion/ConfirmationList.vue'
import JevProbability from '../discussion/JevProbability.vue'
import { renderMarkdown } from '../discussion/markdown'
import StanceList from '../discussion/StanceList.vue'
import TurnCard from '../discussion/TurnCard.vue'
import { JUDGE_LABELS, formatTime, judgeOutcomeLabel, stanceLabel } from './labels'

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
    failure:
      t.status === 'ok'
        ? null
        : { kind: t.status === 'timeout' ? 'timeout' : 'unknown', reason: t.error ?? '' },
  }
}

const turns = computed(() => props.round.turns.map((t) => ({ record: t, state: toTurnState(t) })))
const draftHtml = computed(() => (props.round.draft ? renderMarkdown(props.round.draft) : ''))
const stanceRows = (stances: Record<string, Stance | null>) =>
  Object.entries(stances).map(([id, stance]) => ({ id, stance }))

// Every verdict of the round (judge B: `confirm`, then the final one); older records only have `judge`.
const verdicts = computed(() => {
  const history = props.round.judge_history ?? []
  if (history.length) return history
  return props.round.judge ? [props.round.judge] : []
})
</script>

<template>
  <section class="record-round d-round" data-testid="record-round" :data-round="round.number">
    <header v-if="showNumber" class="d-round-head">
      <h2 class="d-round-title">第 {{ round.number }} 輪</h2>
      <span v-if="interjections.length" class="pill">含插話</span>
    </header>

    <p
      v-for="(i, k) in interjections"
      :key="`i${k}`"
      class="d-notice is-interjection"
      data-testid="record-interjection"
    >
      <span class="d-notice-label">使用者插話</span>
      <time :datetime="i.at">{{ formatTime(i.at) }}</time>
      <span class="event-text">{{ i.text }}</span>
    </p>
    <p
      v-for="(c, k) in moderatorChanges"
      :key="`m${k}`"
      class="d-notice"
      data-testid="record-moderator-change"
    >
      <span class="d-notice-label">主持人接手</span>
      <span>改由 {{ name(c.participant_id) }} 擔任主持人</span>
    </p>

    <div class="d-cols" :style="{ '--columns': Math.max(turns.length, 1) }">
      <div
        v-for="t in turns"
        :key="t.record.participant_id"
        class="record-turn"
        data-testid="record-turn"
      >
        <TurnCard :turn="t.state" :participant="participantById(t.record.participant_id)">
          <template #stance>
            <p v-if="t.record.stance" class="d-stance-line" :class="`is-${t.record.stance}`">
              STANCE: {{ t.record.stance }} ·
              <span data-testid="record-stance">{{ stanceLabel(t.record.stance) }}</span>
            </p>
          </template>
        </TurnCard>
      </div>
    </div>

    <p
      v-for="(r, k) in removals"
      :key="`r${k}`"
      class="d-notice is-bad"
      data-testid="record-removal"
    >
      <span class="d-notice-label">移出討論</span>
      <span>{{ name(r.participant_id) }}：{{ r.reason }}</span>
    </p>

    <div v-if="round.draft || verdicts.length || round.confirmations?.length" class="d-between">
      <div class="d-between-cell">
        <article v-if="round.draft" class="d-block is-draft" data-testid="record-draft">
          <header class="d-block-head">
            <span class="d-block-title">共識草案</span>
            <span>第 {{ round.number }} 輪後</span>
          </header>
          <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
          <div class="d-md" v-html="draftHtml" />
        </article>
      </div>

      <div class="d-between-cell">
        <section
          v-for="(judge, k) in verdicts"
          :key="`j${k}`"
          class="d-block"
          :class="{ 'is-ok': judge.outcome === 'reached' }"
          data-testid="record-judge"
        >
          <header class="d-block-head">
            <span class="d-block-title">{{ JUDGE_LABELS[judge.judge] ?? judge.judge }}</span>
            <span
              class="d-push pill"
              :class="judge.outcome === 'reached' ? 'pill-ok' : 'pill-warn'"
              >{{ judgeOutcomeLabel(judge.judge, judge.outcome) }}</span
            >
          </header>
          <StanceList
            v-if="judge.detail.stances"
            :stances="stanceRows(judge.detail.stances)"
            :participant-by-id="participantById"
          />
          <JevProbability
            v-if="judge.detail.probability != null"
            :probability="judge.detail.probability"
            :threshold="judge.detail.threshold ?? null"
          />
        </section>

        <section
          v-if="round.confirmations?.length"
          class="d-block"
          data-testid="record-confirmation"
        >
          <header class="d-block-head">
            <span class="d-block-title">反問確認</span>
          </header>
          <ConfirmationList
            :answers="round.confirmations"
            :participant-by-id="participantById"
            agree-reasons
          />
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.record-turn {
  display: flex;
  min-width: 0;
}
.record-turn > :deep(.d-turn) {
  flex: 1;
}
.d-notice.is-interjection {
  border-style: solid;
  border-left: 2px solid var(--accent);
}
.d-notice time {
  font-size: var(--fs-xs);
}
.event-text {
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
