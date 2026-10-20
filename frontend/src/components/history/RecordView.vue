<!-- Read-only view of a saved discussion record (route `discussion-record`, ticket 09).
     Renders straight from the record JSON in the live page's layout (ui-redesign 07): top bar,
     result block, rounds, and an inspector with participants, stances and the settings
     snapshot. It offers no way to continue the discussion: no buttons, no text input. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import '../../styles/discussion.css'
import { fetchDiscussion } from '../../api/discussions'
import { fetchOptions } from '../../api/options'
import type { OptionsResponse } from '../../contracts/http'
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { DiscussionRecord } from '../../contracts/record'
import type { TurnStateStatus } from '../../stores/discussion'
import InspectorParticipants from '../discussion/InspectorParticipants.vue'
import { renderMarkdown } from '../discussion/markdown'
import StanceTracker, { type StanceCell } from '../discussion/StanceTracker.vue'
import { JUDGE_LABELS, MODE_LABELS, formatTime, outcomeLabel, outcomePillClass } from './labels'
import RecordRound from './RecordRound.vue'

const props = defineProps<{ id: string }>()

const record = ref<DiscussionRecord | null>(null)
const loadError = ref<string | null>(null)

// Speaking order names come from the backend (`/api/options`); without them, the id is shown.
const options = ref<OptionsResponse | null>(null)
const optionsLoaded = fetchOptions().catch(() => null)

watch(
  () => props.id,
  async (id) => {
    record.value = null
    loadError.value = null
    try {
      // Wait for the options too, so the order name does not flicker from id to name.
      const [loaded, opts] = await Promise.all([fetchDiscussion(id), optionsLoaded])
      options.value = opts
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

const consensus = computed(() => record.value?.settings.mode === 'consensus')
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

// Result block, worded and coloured like the live page's DiscussionOutcome.
const resultTitle = computed(() => {
  const r = record.value
  if (r?.result?.kind === 'consensus') return '共識結果'
  if (r?.result?.kind === 'no_consensus') return '未取得共識：各參與者最終立場與仍有分歧的重點'
  if (r?.outcome === 'insufficient_participants') return '討論結束：在場參與者不足'
  return null
})
const resultTone = computed(() => {
  const r = record.value
  if (r?.result?.kind === 'no_consensus') return 'is-warn'
  if (r?.outcome === 'insufficient_participants') return 'is-bad'
  return ''
})
const resultHtml = computed(() => {
  const result = record.value?.result
  return result && result.kind !== 'answers' && result.text ? renderMarkdown(result.text) : ''
})


// --- inspector ---------------------------------------------------------------------------
const removedIds = computed(() => record.value?.removed_participants.map((r) => r.participant_id) ?? [])
const moderatorId = computed(() => {
  const r = record.value
  if (!r || !consensus.value) return null
  return r.moderator_changes[r.moderator_changes.length - 1]?.participant_id ?? r.settings.moderator_id
})
const statuses = computed(() => {
  const out: Record<string, TurnStateStatus | undefined> = {}
  for (const round of record.value?.rounds ?? []) for (const t of round.turns) out[t.participant_id] = t.status
  return out
})
const stanceRounds = computed(() =>
  (record.value?.rounds ?? [])
    .filter((r) => r.number >= 2)
    .map((r) => {
      const cells: Record<string, StanceCell | undefined> = {}
      for (const t of r.turns) cells[t.participant_id] = { status: t.status, stance: t.stance }
      return { number: r.number, cells }
    }),
)
const orderName = computed(() => {
  const id = record.value?.settings.speaking_order ?? ''
  return options.value?.speaking_orders.find((o) => o.id === id)?.name ?? id
})
</script>

<template>
  <section class="record-view" data-testid="record-view">
    <p v-if="loadError" class="error-bar" data-testid="record-error">{{ loadError }}</p>
    <p v-else-if="!record" class="muted">載入中…</p>

    <div v-else class="record">
      <div class="stage">
        <header class="topbar">
          <h1 class="question" data-testid="record-question" :title="record.question">{{ record.question }}</h1>
          <span class="pill read-only">唯讀紀錄</span>
          <span class="pill" :class="outcomePillClass(record.outcome)" data-testid="record-outcome">{{ outcomeLabel(record.outcome) }}</span>
        </header>
        <p class="sub">
          <RouterLink class="back" :to="{ name: 'history' }">← 回到歷史</RouterLink>
          <span v-if="record.derived_from">
            由
            <RouterLink
              data-testid="record-derived-from"
              :to="{ name: 'discussion-record', params: { id: record.derived_from } }"
              >原本的提問</RouterLink
            >
            轉換而來
          </span>
        </p>

        <section
          v-if="resultTitle"
          class="d-result"
          :class="resultTone"
          :data-testid="resultHtml ? 'record-result' : undefined"
        >
          <h2 class="d-result-title">
            <span v-if="record.result?.kind === 'consensus'" aria-hidden="true">✓ </span>{{ resultTitle }}
          </h2>
          <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
          <div v-if="resultHtml" class="d-md" v-html="resultHtml" />
        </section>
        <p v-if="record.outcome === 'stopped'" class="d-result is-bad stopped">討論已停止：進行中的發言已取消，當時的內容已存檔。</p>

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
          <p v-for="(i, k) in leftovers.interjections" :key="`i${k}`" class="d-notice" data-testid="record-interjection">
            <span class="d-notice-label">使用者插話（未生效）</span>
            <span class="event-text">{{ i.text }}</span>
          </p>
          <p v-for="(c, k) in leftovers.moderatorChanges" :key="`m${k}`" class="d-notice" data-testid="record-moderator-change">
            <span class="d-notice-label">主持人接手</span>
            <span>改由 {{ name(c.participant_id) }} 擔任主持人</span>
          </p>
          <p v-for="(r, k) in leftovers.removals" :key="`r${k}`" class="d-notice is-bad" data-testid="record-removal">
            <span class="d-notice-label">移出討論</span>
            <span>{{ name(r.participant_id) }}：{{ r.reason }}</span>
          </p>
        </section>
      </div>

      <aside class="inspector" aria-label="檢視器">
        <section class="section">
          <h3 class="section-title">參與者</h3>
          <InspectorParticipants
            :participants="record.participants"
            :moderator-id="moderatorId"
            :removed-ids="removedIds"
            :statuses="statuses"
          />
        </section>
        <section v-if="consensus && stanceRounds.length" class="section">
          <h3 class="section-title">表態追蹤</h3>
          <StanceTracker :participants="record.participants" :rounds="stanceRounds" />
        </section>
        <section class="section">
          <h3 class="section-title">設定快照</h3>
          <dl class="kv" data-testid="record-meta">
            <dt>討論模式</dt>
            <dd>{{ MODE_LABELS[record.settings.mode] ?? record.settings.mode }}</dd>
            <template v-if="consensus">
              <template v-if="record.settings.judge">
                <dt>共識裁定方式</dt>
                <dd>{{ JUDGE_LABELS[record.settings.judge] ?? record.settings.judge }}</dd>
              </template>
              <template v-if="record.settings.judge === 'jev'">
                <dt>Jev 門檻</dt>
                <dd>{{ record.settings.jev_threshold }}</dd>
              </template>
              <template v-if="record.settings.moderator_id">
                <dt>主持人</dt>
                <dd>{{ name(record.settings.moderator_id) }}</dd>
              </template>
            </template>
            <dt>發言順序</dt>
            <dd>{{ orderName }}</dd>
            <template v-if="consensus">
              <dt>輪數上限</dt>
              <dd>{{ record.settings.max_rounds }}</dd>
            </template>
            <dt>逾時</dt>
            <dd>{{ record.settings.turn_timeout_seconds }} 秒</dd>
            <dt>開始</dt>
            <dd><time :datetime="record.created_at">{{ formatTime(record.created_at) }}</time></dd>
            <template v-if="record.finished_at">
              <dt>結束</dt>
              <dd><time :datetime="record.finished_at">{{ formatTime(record.finished_at) }}</time></dd>
            </template>
          </dl>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.record {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--inspector-width);
  gap: var(--space-4);
  align-items: start;
}
.stage {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}
.topbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) 10px;
}
.question {
  flex: 1 1 12rem;
  min-width: 0;
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.read-only {
  border-style: dashed;
}
.sub {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  margin: calc(-1 * var(--space-2)) 0 0;
  padding-bottom: var(--space-3);
  font-size: var(--fs-sm);
  color: var(--muted);
  border-bottom: 1px solid var(--line);
}
.back {
  color: var(--accent);
  text-decoration: none;
}
.stopped {
  margin: 0;
  color: var(--bad);
}
.leftovers {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.event-text {
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.error-bar {
  margin: 0;
  padding: 8px 12px;
  color: var(--bad);
  background: var(--bad-bg);
  border: 1px solid var(--bad-line);
  border-radius: var(--radius);
}

/* Inspector: same look as the live page's DiscussionInspector. */
.inspector {
  position: sticky;
  top: var(--space-4);
  max-height: calc(100vh - 2 * var(--space-4));
  overflow: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
}
.section {
  padding: var(--space-3) 14px;
  border-bottom: 1px solid var(--line);
}
.section:last-child {
  border-bottom: none;
}
.section-title {
  margin: 0 0 var(--space-2);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.kv {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 5px var(--space-3);
  margin: 0;
  font-size: var(--fs-sm);
}
.kv dt {
  color: var(--muted);
}
.kv dd {
  margin: 0;
  overflow-wrap: anywhere;
}
@media (max-width: 1023px) {
  .record {
    grid-template-columns: minmax(0, 1fr);
  }
  .inspector {
    position: static;
    max-height: none;
  }
}
</style>
