<!-- One round of a saved record (read-only), in the live page's look (ui-redesign 07): what
     happened before it (interjections, moderator changes), the turns side by side, removals,
     then draft | verdicts and confirmations. -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'

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
import ParticipantLabel from '../discussion/ParticipantLabel.vue'
import TurnCard from '../discussion/TurnCard.vue'
import { JUDGE_LABELS, agreeLabel, formatTime, judgeOutcomeLabel, stanceLabel } from './labels'

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
const pct = (v: number) => `${Math.min(Math.max(v, 0), 1) * 100}%`
const STANCE_PILLS = { AGREE: 'pill-ok', DISAGREE: 'pill-bad', none: 'pill-bad' } as const

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

    <p v-for="(i, k) in interjections" :key="`i${k}`" class="d-notice is-interjection" data-testid="record-interjection">
      <span class="d-notice-label">使用者插話</span>
      <time :datetime="i.at">{{ formatTime(i.at) }}</time>
      <span class="event-text">{{ i.text }}</span>
    </p>
    <p v-for="(c, k) in moderatorChanges" :key="`m${k}`" class="d-notice" data-testid="record-moderator-change">
      <span class="d-notice-label">主持人接手</span>
      <span>改由 {{ name(c.participant_id) }} 擔任主持人</span>
    </p>

    <div class="d-cols" :style="{ '--columns': Math.max(turns.length, 1) }">
      <div v-for="t in turns" :key="t.record.participant_id" class="record-turn" data-testid="record-turn">
        <TurnCard :turn="t.state" :participant="participantById(t.record.participant_id)">
          <template #stance>
            <p v-if="t.record.stance" class="d-stance-line" :class="`is-${t.record.stance}`">
              STANCE: {{ t.record.stance }} · <span data-testid="record-stance">{{ stanceLabel(t.record.stance) }}</span>
            </p>
          </template>
        </TurnCard>
      </div>
    </div>

    <p v-for="(r, k) in removals" :key="`r${k}`" class="d-notice is-bad" data-testid="record-removal">
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
            <span class="d-push pill" :class="judge.outcome === 'reached' ? 'pill-ok' : 'pill-warn'">{{
              judgeOutcomeLabel(judge.judge, judge.outcome)
            }}</span>
          </header>
          <ul v-if="judge.detail.stances" class="d-list">
            <li v-for="(stance, pid) in judge.detail.stances" :key="pid" class="d-list-row">
              <ParticipantLabel :participant="participantById(String(pid))" :id="String(pid)" :size="18" hide-web />
              <span class="pill" :class="STANCE_PILLS[stance ?? 'none']">{{ stanceLabel(stance) }}</span>
            </li>
          </ul>
          <div v-if="judge.detail.probability != null">
            <p class="prob-text">
              已取得共識的機率 <strong>{{ judge.detail.probability.toFixed(2) }}</strong>
              <template v-if="judge.detail.threshold != null">（門檻 {{ judge.detail.threshold }}）</template>
            </p>
            <div class="d-bar" aria-hidden="true">
              <i
                class="d-bar-fill"
                :class="{ 'is-over': judge.detail.threshold != null && judge.detail.probability >= judge.detail.threshold }"
                :style="{ width: pct(judge.detail.probability) }"
              />
              <i v-if="judge.detail.threshold != null" class="d-bar-tick" :style="{ left: pct(judge.detail.threshold) }" />
            </div>
          </div>
        </section>

        <section v-if="round.confirmations?.length" class="d-block" data-testid="record-confirmation">
          <header class="d-block-head">
            <span class="d-block-title">反問確認</span>
          </header>
          <ul class="d-list">
            <li v-for="c in round.confirmations" :key="c.participant_id">
              <div class="d-list-row">
                <ParticipantLabel :participant="participantById(c.participant_id)" :id="c.participant_id" :size="18" hide-web />
                <span class="pill" :class="c.agree ? 'pill-ok' : 'pill-bad'">{{ agreeLabel(c.agree) }}</span>
              </div>
              <p v-if="c.reason" class="d-reason">{{ c.reason }}</p>
            </li>
          </ul>
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
.prob-text {
  margin: 0;
}
</style>
