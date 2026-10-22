<!-- What happens after a round's turns in a consensus discussion: the judge result
     (judge A: everyone's stance on the previous draft; judge B: Jev's probability),
     judge B's confirmation answers, and the extra calls (the new consensus draft;
     confirmations / final result / summary while they run or when they fail). -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'

import type { ParticipantSnapshot, TurnPurpose } from '../../contracts/messages'
import type { RoundState, TurnState } from '../../stores/discussion'
import { judgeOutcomeLabel } from '../labels'
import ConfirmationList from './ConfirmationList.vue'
import JevProbability from './JevProbability.vue'
import { renderMarkdown } from './markdown'
import ParticipantLabel from './ParticipantLabel.vue'
import StanceList from './StanceList.vue'

const props = defineProps<{
  round: RoundState
  participantById: (id: string) => ParticipantSnapshot | undefined
  /** Fallback author of a draft loaded from a record (records keep no extra calls). */
  moderatorId?: string | null
}>()

const isJev = computed(() => props.round.judge?.judge === 'jev')
const outcomeLabel = computed(() => {
  const judge = props.round.judge
  return judge ? judgeOutcomeLabel(judge.judge, judge.outcome) : ''
})
const PURPOSE_LABELS: Record<TurnPurpose, string> = {
  turn: '發言',
  draft: '共識草案',
  final_result: '最終共識結果',
  no_consensus_summary: '最終立場與分歧點',
  confirmation: '反問確認',
}

const allAgree = computed(() => (props.round.confirmations ?? []).every((a) => a.agree))

const stances = computed(() =>
  Object.entries(props.round.judge?.detail.stances ?? {}).map(([id, stance]) => ({ id, stance })),
)

/** Extra calls still worth showing here: running / failed ones, and drafts.
 *  A finished summary or final result is shown by DiscussionOutcome instead. */
const extraCalls = computed(() =>
  props.round.extraCalls.filter((c) => c.purpose === 'draft' || c.status !== 'ok'),
)

const draftFromRecord = computed(() =>
  props.round.draft && !props.round.extraCalls.some((c) => c.purpose === 'draft')
    ? props.round.draft
    : null,
)

const probability = computed(() => props.round.judge?.detail.probability ?? null)
const threshold = computed(() => props.round.judge?.detail.threshold ?? null)

const hasLeft = computed(() => extraCalls.value.length > 0 || draftFromRecord.value !== null)
const hasRight = computed(
  () => props.round.judge !== null || (props.round.confirmations?.length ?? 0) > 0,
)

function callText(call: TurnState): string {
  return call.purpose === 'draft' && call.status === 'ok' && props.round.draft
    ? props.round.draft
    : call.text
}
</script>

<template>
  <div v-if="hasLeft || hasRight" class="d-between">
    <!-- Left: the moderator's draft and other extra calls. -->
    <div class="d-between-cell">
      <article
        v-for="(call, i) in extraCalls"
        :key="`${call.purpose}-${i}`"
        class="extra-call d-block"
        :class="[
          `status-${call.status}`,
          `purpose-${call.purpose}`,
          {
            'is-draft': call.purpose === 'draft',
            'is-failed': call.status === 'failed' || call.status === 'timeout',
          },
        ]"
        :data-testid="
          call.purpose === 'draft' && call.status === 'ok' ? 'consensus-draft' : 'extra-call'
        "
      >
        <header class="d-block-head">
          <span class="d-block-title">{{ PURPOSE_LABELS[call.purpose] }}</span>
          <span
            >第 {{ round.number }} 輪後 ·
            {{ call.purpose === 'confirmation' ? '' : '主持人' }}</span
          >
          <ParticipantLabel
            :participant="participantById(call.participantId)"
            :id="call.participantId"
            :size="16"
            hide-web
          />
          <span v-if="call.status === 'running'" class="d-push pill pill-accent">撰寫中…</span>
        </header>
        <p v-if="call.failure" class="d-failure">失敗：{{ call.failure.reason }}</p>
        <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
        <div
          class="d-md"
          :class="{ 'd-caret': call.status === 'running' }"
          v-html="renderMarkdown(callText(call))"
        />
      </article>

      <article
        v-if="draftFromRecord"
        class="extra-call purpose-draft d-block is-draft"
        data-testid="consensus-draft"
      >
        <header class="d-block-head">
          <span class="d-block-title">共識草案</span>
          <span>第 {{ round.number }} 輪後<template v-if="moderatorId"> · 主持人</template></span>
          <ParticipantLabel
            v-if="moderatorId"
            :participant="participantById(moderatorId)"
            :id="moderatorId"
            :size="16"
            hide-web
          />
        </header>
        <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
        <div class="d-md" v-html="renderMarkdown(draftFromRecord)" />
      </article>
    </div>

    <!-- Right: the verdict (judge A: stances; judge B: Jev's probability) and confirmations. -->
    <div class="d-between-cell">
      <section
        v-if="round.judge"
        class="judge-result d-block"
        :class="[`outcome-${round.judge.outcome}`, { 'is-ok': round.judge.outcome === 'reached' }]"
        data-testid="judge-result"
      >
        <header class="d-block-head">
          <span class="d-block-title"
            >第 {{ round.number }} 輪{{ isJev ? ' Jev 判斷' : '表態' }}</span
          >
          <span
            class="d-push pill"
            :class="round.judge.outcome === 'reached' ? 'pill-ok' : 'pill-warn'"
            >{{ outcomeLabel }}</span
          >
        </header>
        <StanceList
          v-if="stances.length"
          :stances="stances"
          :participant-by-id="participantById"
          item-testid="stance"
        />
        <JevProbability
          v-if="probability != null"
          class="jev-probability"
          data-testid="jev-probability"
          :probability="probability"
          :threshold="threshold"
        />
        <p v-else-if="isJev" class="d-failure" data-testid="jev-probability">
          Jev 這輪無法判斷，視為未取得共識
        </p>
      </section>

      <section
        v-if="round.confirmations?.length"
        class="confirmations d-block"
        :class="{ 'all-agree': allAgree, 'is-ok': allAgree }"
        data-testid="confirmation-result"
      >
        <header class="d-block-head">
          <span class="d-block-title">反問確認</span>
          <span class="d-push pill" :class="allAgree ? 'pill-ok' : 'pill-warn'">{{
            allAgree ? '全員同意已取得共識' : '有參與者不同意'
          }}</span>
        </header>
        <ConfirmationList
          :answers="round.confirmations"
          :participant-by-id="participantById"
          item-testid="confirmation-answer"
        />
      </section>
    </div>
  </div>
</template>
