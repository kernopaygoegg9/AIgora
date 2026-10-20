<!-- The inspector beside a live / finished discussion (ui-redesign 04, 05): participants,
     the stance tracker (consensus), queued interjections and the locked settings snapshot.
     Participants and stances are derived from the store here and passed to props-only
     components, which the read-only record (07) feeds from a saved record instead. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { OptionsResponse } from '../../contracts/http'
import type { DiscussionSettings, ParticipantSnapshot } from '../../contracts/messages'
import { useDiscussionStore, type Interjection, type TurnStateStatus } from '../../stores/discussion'
import { JUDGE_LABELS, MODE_LABELS } from '../labels'
import InspectorParticipants from './InspectorParticipants.vue'
import StanceTracker, { type StanceCell } from './StanceTracker.vue'

const props = defineProps<{
  settings: DiscussionSettings | null
  options: OptionsResponse | null
  interjections: Interjection[]
  participantById: (id: string) => ParticipantSnapshot | undefined
}>()

const store = useDiscussionStore()
const consensus = computed(() => props.settings?.mode === 'consensus')

const removedIds = computed(() => store.removed.map((r) => r.participantId))

// Each participant's latest turn status, over all rounds.
const statuses = computed(() => {
  const out: Record<string, TurnStateStatus | undefined> = {}
  for (const round of store.rounds) for (const t of round.turns) out[t.participantId] = t.status
  return out
})

// Stances are taken on the previous round's draft, so they start in round 2.
const stanceRounds = computed(() =>
  store.rounds
    .filter((r) => r.number >= 2)
    .map((r) => {
      const cells: Record<string, StanceCell | undefined> = {}
      for (const t of r.turns) cells[t.participantId] = { status: t.status, stance: t.stance }
      return { number: r.number, cells }
    }),
)

const rows = computed(() => {
  const s = props.settings
  if (!s) return []
  const order = props.options?.speaking_orders.find((o) => o.id === s.speaking_order)?.name ?? s.speaking_order
  const out: [string, string][] = [['討論模式', MODE_LABELS[s.mode] ?? s.mode]]
  if (consensus.value) {
    out.push(['共識裁定方式', JUDGE_LABELS[s.judge] ?? s.judge])
    if (s.judge === 'jev') out.push(['Jev 門檻', String(s.jev_threshold)])
    if (s.moderator_id) out.push(['主持人', props.participantById(s.moderator_id)?.display_name ?? s.moderator_id])
  }
  out.push(['發言順序', order])
  if (consensus.value) out.push(['輪數上限', String(s.max_rounds)])
  out.push(['逾時', `${s.turn_timeout_seconds} 秒`])
  return out
})
</script>

<template>
  <aside class="inspector" aria-label="檢視器" data-testid="discussion-inspector">
    <section class="section">
      <h3 class="section-title">參與者</h3>
      <InspectorParticipants
        :participants="store.participants"
        :moderator-id="consensus ? store.moderatorId : null"
        :removed-ids="removedIds"
        :statuses="statuses"
      />
    </section>

    <section v-if="consensus && stanceRounds.length" class="section">
      <h3 class="section-title">表態追蹤</h3>
      <StanceTracker :participants="store.participants" :rounds="stanceRounds" />
    </section>

    <section v-if="consensus" class="section">
      <h3 class="section-title">插話佇列</h3>
      <ul v-if="interjections.length" class="queue">
        <li v-for="(item, i) in interjections" :key="i" class="interjection" data-testid="interjection">
          <small class="applies">第 {{ item.appliesToRound }} 輪起生效</small>
          <span class="text">{{ item.text }}</span>
        </li>
      </ul>
      <p v-else class="muted empty">還沒有插話</p>
    </section>

    <section class="section" data-testid="settings-locked">
      <h3 class="section-title">設定（已鎖定）</h3>
      <dl class="kv">
        <template v-for="[k, v] in rows" :key="k">
          <dt>{{ k }}</dt>
          <dd>{{ v }}</dd>
        </template>
      </dl>
    </section>
  </aside>
</template>

<style scoped>
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
.queue {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.interjection {
  padding: 6px 8px;
  font-size: var(--fs-sm);
  background: var(--panel-2);
  border-left: 2px solid var(--accent);
  border-radius: var(--radius-sm);
}
.applies {
  display: block;
  font-size: var(--fs-xs);
  color: var(--accent);
}
.text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.empty {
  margin: 0;
  font-size: var(--fs-sm);
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
  .inspector {
    position: static;
    max-height: none;
  }
}
</style>
