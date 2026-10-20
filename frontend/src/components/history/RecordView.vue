<!-- Read-only view of a saved discussion record (route `discussion-record`, ticket 09).
     Renders straight from the record JSON; it offers no way to continue the discussion. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { fetchDiscussion } from '../../api/discussions'
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { DiscussionRecord } from '../../contracts/record'
import { renderMarkdown } from '../discussion/markdown'
import ParticipantAvatar from '../discussion/ParticipantAvatar.vue'
import { JUDGE_LABELS, MODE_LABELS, formatTime, outcomeLabel } from './labels'
import RecordRound from './RecordRound.vue'

const props = defineProps<{ id: string }>()

const record = ref<DiscussionRecord | null>(null)
const loadError = ref<string | null>(null)

watch(
  () => props.id,
  async (id) => {
    record.value = null
    loadError.value = null
    try {
      const loaded = await fetchDiscussion(id)
      if (props.id === id) record.value = loaded
    } catch (err) {
      if (props.id === id) loadError.value = err instanceof Error ? err.message : String(err)
    }
  },
  { immediate: true },
)

const participantById = (id: string): ParticipantSnapshot | undefined =>
  record.value?.participants.find((p) => p.id === id)
const name = (id: string) => participantById(id)?.display_name ?? id

const roundNumbers = computed(() => new Set(record.value?.rounds.map((r) => r.number) ?? []))
const inRound = <T extends { round: number }>(items: T[], n: number) => items.filter((x) => x.round === n)
const interjectionsFor = (n: number) => record.value?.interjections.filter((i) => i.applies_to_round === n) ?? []

// Events that point at a round that never ran (e.g. an interjection queued just before the end).
const leftovers = computed(() => {
  const r = record.value
  if (!r) return { interjections: [], removals: [], moderatorChanges: [] }
  const has = (n: number) => roundNumbers.value.has(n)
  return {
    interjections: r.interjections.filter((i) => !has(i.applies_to_round)),
    removals: r.removed_participants.filter((x) => !has(x.round)),
    moderatorChanges: r.moderator_changes.filter((x) => !has(x.round)),
  }
})
const hasLeftovers = computed(
  () =>
    leftovers.value.interjections.length + leftovers.value.removals.length + leftovers.value.moderatorChanges.length >
    0,
)

const resultTitle = computed(() =>
  record.value?.result?.kind === 'no_consensus' ? '最終立場與分歧' : '共識結果',
)
const resultHtml = computed(() => {
  const result = record.value?.result
  return result && result.kind !== 'answers' && result.text ? renderMarkdown(result.text) : ''
})
</script>

<template>
  <section class="record-view" data-testid="record-view">
    <RouterLink class="back" :to="{ name: 'history' }">← 回到歷史</RouterLink>
    <p v-if="loadError" class="error" data-testid="record-error">{{ loadError }}</p>
    <p v-else-if="!record" class="muted">載入中…</p>

    <template v-else>
      <header class="record-header">
        <h1 class="question" data-testid="record-question">{{ record.question }}</h1>
        <span class="outcome" :class="{ running: !record.outcome }" data-testid="record-outcome">{{
          outcomeLabel(record.outcome)
        }}</span>
      </header>

      <dl class="meta" data-testid="record-meta">
        <div>
          <dt>討論模式</dt>
          <dd>{{ MODE_LABELS[record.settings.mode] ?? record.settings.mode }}</dd>
        </div>
        <div>
          <dt>開始</dt>
          <dd><time :datetime="record.created_at">{{ formatTime(record.created_at) }}</time></dd>
        </div>
        <div v-if="record.finished_at">
          <dt>結束</dt>
          <dd><time :datetime="record.finished_at">{{ formatTime(record.finished_at) }}</time></dd>
        </div>
        <template v-if="record.settings.mode !== 'ask'">
          <div v-if="record.settings.judge">
            <dt>共識裁定方式</dt>
            <dd>{{ JUDGE_LABELS[record.settings.judge] ?? record.settings.judge }}</dd>
          </div>
          <div v-if="record.settings.moderator_id">
            <dt>主持人</dt>
            <dd>{{ name(record.settings.moderator_id) }}</dd>
          </div>
          <div>
            <dt>輪數上限</dt>
            <dd>{{ record.settings.max_rounds }}</dd>
          </div>
        </template>
        <div v-if="record.derived_from">
          <dt>轉換自</dt>
          <dd>
            <RouterLink
              data-testid="record-derived-from"
              :to="{ name: 'discussion-record', params: { id: record.derived_from } }"
              >原本的提問</RouterLink
            >
          </dd>
        </div>
      </dl>

      <ul class="participants">
        <li v-for="p in record.participants" :key="p.id" class="participant">
          <ParticipantAvatar :avatar="p.avatar" :size="24" />
          <span>{{ p.display_name }}</span>
          <span v-if="!p.capabilities.web_access" class="badge">無上網</span>
        </li>
      </ul>

      <RecordRound
        v-for="round in record.rounds"
        :key="round.number"
        :round="round"
        :participant-by-id="participantById"
        :show-number="record.settings.mode !== 'ask'"
        :interjections="interjectionsFor(round.number)"
        :moderator-changes="inRound(record.moderator_changes, round.number)"
        :removals="inRound(record.removed_participants, round.number)"
      />

      <section v-if="hasLeftovers" class="leftovers">
        <p v-for="(i, k) in leftovers.interjections" :key="`i${k}`" class="event" data-testid="record-interjection">
          <span class="event-label">使用者插話（未生效）</span>
          <span class="event-text">{{ i.text }}</span>
        </p>
        <p v-for="(c, k) in leftovers.moderatorChanges" :key="`m${k}`" class="event" data-testid="record-moderator-change">
          <span class="event-label">主持人接手</span>
          <span>{{ name(c.participant_id) }} 成為主持人</span>
        </p>
        <p v-for="(r, k) in leftovers.removals" :key="`r${k}`" class="event removal" data-testid="record-removal">
          <span class="event-label">移出討論</span>
          <span>{{ name(r.participant_id) }}：{{ r.reason }}</span>
        </p>
      </section>

      <section v-if="resultHtml" class="result" data-testid="record-result">
        <h2 class="result-title">{{ resultTitle }}</h2>
        <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
        <div class="result-text" v-html="resultHtml" />
      </section>
    </template>
  </section>
</template>

<style scoped>
.record-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.back {
  color: #2f6feb;
  text-decoration: none;
  font-size: 0.9rem;
}
.record-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}
.question {
  font-size: 1.15rem;
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.outcome {
  font-size: 0.85rem;
  color: #6b7280;
  white-space: nowrap;
}
.outcome.running {
  color: #2f6feb;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  margin: 0;
  font-size: 0.85rem;
}
.meta div {
  display: flex;
  gap: 0.4rem;
}
.meta dt {
  color: #6b7280;
}
.meta dd {
  margin: 0;
}
.participants {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
}
.participant {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.badge {
  font-size: 0.75rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: #e8ebef;
  color: #4a5159;
}
.leftovers {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
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
.event-text {
  white-space: pre-wrap;
}
.removal {
  color: #a1260d;
}
.result {
  padding: 0.75rem 1rem;
  background: #fff;
  border: 2px solid #2f6feb;
  border-radius: 8px;
}
.result-title {
  font-size: 1rem;
  margin: 0 0 0.5rem;
}
.result-text {
  overflow-wrap: anywhere;
  line-height: 1.55;
}
.result-text :deep(p) {
  margin: 0 0 0.5rem;
}
.muted {
  color: #6b7280;
  margin: 0;
}
.error {
  color: #a1260d;
  margin: 0;
}
</style>
