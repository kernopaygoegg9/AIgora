<!-- 表態追蹤 (ui-redesign 05): rounds × participants, each cell the participant's stance on
     the previous draft (同意 green, 不同意 red, failed / no stance hollow red, no turn blank).
     Props only, so the read-only record (07) can feed it from a saved record. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { ParticipantSnapshot, Stance } from '../../contracts/messages'
import type { TurnStateStatus } from '../../stores/discussion'
import ParticipantAvatar from './ParticipantAvatar.vue'

export interface StanceCell {
  status: TurnStateStatus
  stance: Stance | null
}

const props = defineProps<{
  participants: ParticipantSnapshot[]
  /** Rounds to show (from round 2 on), each with its turns by participant id. */
  rounds: { number: number; cells: Record<string, StanceCell | undefined> }[]
}>()

type Kind = 'AGREE' | 'DISAGREE' | 'missing' | 'running' | 'none'
const KIND_LABELS: Record<Kind, string> = {
  AGREE: '同意',
  DISAGREE: '不同意',
  missing: '失敗或未表態',
  running: '回覆中',
  none: '沒有發言',
}

function kind(cell: StanceCell | undefined): Kind {
  if (!cell) return 'none'
  if (cell.stance) return cell.stance
  if (cell.status === 'running') return 'running'
  return 'missing'
}

const label = (p: ParticipantSnapshot) => `${p.display_name}（${p.model ?? '預設模型'}）`
const columns = computed(() => `4.5rem repeat(${props.participants.length}, minmax(22px, 1fr))`)
</script>

<template>
  <div class="tracker" data-testid="stance-tracker">
    <div class="grid" :style="{ gridTemplateColumns: columns }" role="table" aria-label="表態追蹤">
      <div class="row" role="row">
        <span role="columnheader" />
        <span
          v-for="p in participants"
          :key="p.id"
          class="head"
          role="columnheader"
          :title="label(p)"
          :aria-label="label(p)"
        >
          <ParticipantAvatar :avatar="p.avatar" :size="18" />
        </span>
      </div>
      <div v-for="r in rounds" :key="r.number" class="row" role="row">
        <span class="round" role="rowheader">第 {{ r.number }} 輪</span>
        <span v-for="p in participants" :key="p.id" class="cell" role="cell">
          <i
            class="dot"
            :class="`is-${kind(r.cells[p.id])}`"
            :title="`${label(p)}：${KIND_LABELS[kind(r.cells[p.id])]}`"
            :aria-label="KIND_LABELS[kind(r.cells[p.id])]"
          />
        </span>
      </div>
    </div>
    <p class="legend">
      <span><i class="dot is-AGREE" />同意</span>
      <span><i class="dot is-DISAGREE" />不同意</span>
      <span><i class="dot is-missing" />失敗或未表態</span>
    </p>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  gap: 6px 4px;
  align-items: center;
  font-size: var(--fs-xs);
}
.row {
  display: contents;
}
.head,
.cell {
  display: flex;
  justify-content: center;
}
.round {
  color: var(--muted);
  white-space: nowrap;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: none;
}
.dot.is-AGREE {
  background: var(--ok);
}
.dot.is-DISAGREE {
  background: var(--bad);
}
.dot.is-missing {
  border: 1.5px solid var(--bad);
}
.dot.is-running {
  border: 1.5px dashed var(--accent);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px var(--space-3);
  margin: var(--space-2) 0 0;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
