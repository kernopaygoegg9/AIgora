<!-- What happens after a round's turns in a consensus discussion: the judge result
     (everyone's stance on the previous draft) and the moderator's extra calls
     (the new consensus draft, or the final summary while it is being written). -->
<script setup lang="ts">
import { computed } from 'vue'

import type { ParticipantSnapshot, Stance, TurnPurpose } from '../../contracts/messages'
import type { RoundState, TurnState } from '../../stores/discussion'
import { renderMarkdown } from './markdown'
import ParticipantAvatar from './ParticipantAvatar.vue'

const props = defineProps<{
  round: RoundState
  participantById: (id: string) => ParticipantSnapshot | undefined
  /** Fallback author of a draft loaded from a record (records keep no extra calls). */
  moderatorId?: string | null
}>()

const OUTCOME_LABELS = { reached: '全員同意，取得共識', not_reached: '尚未取得共識', confirm: '需要反問確認' } as const
const PURPOSE_LABELS: Record<TurnPurpose, string> = {
  turn: '發言',
  draft: '共識草案',
  final_result: '最終共識結果',
  no_consensus_summary: '最終立場與分歧點',
  confirmation: '反問確認',
}

function stanceLabel(stance: Stance | null): string {
  if (stance === 'AGREE') return '同意'
  if (stance === 'DISAGREE') return '不同意'
  return '未表態（視為不同意）'
}

function nameOf(id: string): string {
  return props.participantById(id)?.display_name ?? id
}

const stances = computed(() =>
  Object.entries(props.round.judge?.detail.stances ?? {}).map(([id, stance]) => ({ id, stance })),
)

/** Extra calls still worth showing here: running / failed ones, and drafts.
 *  A finished summary or final result is shown by DiscussionOutcome instead. */
const extraCalls = computed(() =>
  props.round.extraCalls.filter((c) => c.purpose === 'draft' || c.status !== 'ok'),
)

const draftFromRecord = computed(() =>
  props.round.draft && !props.round.extraCalls.some((c) => c.purpose === 'draft') ? props.round.draft : null,
)

function callText(call: TurnState): string {
  return call.purpose === 'draft' && call.status === 'ok' && props.round.draft ? props.round.draft : call.text
}
</script>

<template>
  <section
    v-if="round.judge"
    class="judge-result"
    :class="`outcome-${round.judge.outcome}`"
    data-testid="judge-result"
  >
    <header class="block-header">
      <span class="block-title">第 {{ round.number }} 輪表態</span>
      <span class="outcome">{{ OUTCOME_LABELS[round.judge.outcome] }}</span>
    </header>
    <ul class="stances">
      <li v-for="s in stances" :key="s.id" class="stance" :class="`stance-${s.stance ?? 'none'}`" data-testid="stance">
        <ParticipantAvatar :avatar="participantById(s.id)?.avatar ?? 'default.png'" :size="18" />
        <span class="stance-name">{{ nameOf(s.id) }}</span>
        <span class="stance-value">{{ stanceLabel(s.stance) }}</span>
      </li>
    </ul>
    <p v-if="round.judge.detail.probability != null" class="muted">
      Jev 機率 {{ round.judge.detail.probability.toFixed(2) }}
      <template v-if="round.judge.detail.threshold != null">（門檻 {{ round.judge.detail.threshold }}）</template>
    </p>
  </section>

  <article
    v-for="(call, i) in extraCalls"
    :key="`${call.purpose}-${i}`"
    class="extra-call"
    :class="[`status-${call.status}`, `purpose-${call.purpose}`]"
    :data-testid="call.purpose === 'draft' && call.status === 'ok' ? 'consensus-draft' : 'extra-call'"
  >
    <header class="block-header">
      <span class="block-title">{{ PURPOSE_LABELS[call.purpose] }}（第 {{ round.number }} 輪後）</span>
      <ParticipantAvatar :avatar="participantById(call.participantId)?.avatar ?? 'default.png'" :size="18" />
      <span class="author">主持人 {{ nameOf(call.participantId) }}</span>
      <span v-if="call.status === 'running'" class="muted">撰寫中…</span>
    </header>
    <p v-if="call.failure" class="failure">失敗：{{ call.failure.reason }}</p>
    <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
    <div class="text" v-html="renderMarkdown(callText(call))" />
  </article>

  <article v-if="draftFromRecord" class="extra-call purpose-draft" data-testid="consensus-draft">
    <header class="block-header">
      <span class="block-title">共識草案（第 {{ round.number }} 輪後）</span>
      <span v-if="moderatorId" class="author">主持人 {{ nameOf(moderatorId) }}</span>
    </header>
    <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
    <div class="text" v-html="renderMarkdown(draftFromRecord)" />
  </article>
</template>

<style scoped>
.judge-result,
.extra-call {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #d8dde3;
  background: #f7f8fa;
}
.extra-call.purpose-draft {
  background: #f2f6ff;
  border-color: #c5d5f5;
}
.extra-call.status-failed,
.extra-call.status-timeout {
  border-color: #e5a29a;
}
.judge-result.outcome-reached {
  border-color: #9fd3ae;
  background: #f0faf3;
}
.block-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.block-title {
  font-weight: 600;
}
.outcome {
  margin-left: auto;
  font-size: 0.85rem;
  color: #4a5159;
}
.outcome-reached .outcome {
  color: #1b7a3a;
}
.stances {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.stance {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.stance-value {
  font-size: 0.85rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  background: #e8ebef;
}
.stance-AGREE .stance-value {
  background: #dcf3e3;
  color: #1b7a3a;
}
.stance-DISAGREE .stance-value,
.stance-none .stance-value {
  background: #fdecea;
  color: #a1260d;
}
.author {
  font-size: 0.85rem;
  color: #4a5159;
}
.failure {
  margin: 0;
  color: #a1260d;
  font-size: 0.9rem;
}
.text {
  overflow-wrap: anywhere;
  line-height: 1.55;
}
.text :deep(p) {
  margin: 0 0 0.5rem;
}
.muted {
  color: #6b7280;
  font-size: 0.85rem;
  margin: 0;
}
</style>
