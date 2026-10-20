<!-- The inspector's participant list (ui-redesign 05): who takes part, the moderator, each
     one's current status, and who was removed. Props only, so the read-only record (07)
     can feed it from a saved record. -->
<script setup lang="ts">
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { TurnStateStatus } from '../../stores/discussion'
import ParticipantLabel from './ParticipantLabel.vue'

defineProps<{
  participants: ParticipantSnapshot[]
  moderatorId: string | null
  removedIds: string[]
  /** Each participant's latest turn status; missing = no turn yet. */
  statuses: Record<string, TurnStateStatus | undefined>
}>()

const STATUS_LABELS: Record<TurnStateStatus, string> = {
  running: '回覆中',
  ok: '完成',
  failed: '失敗',
  timeout: '逾時',
}
const STATUS_PILLS: Record<TurnStateStatus, string> = {
  running: 'pill-accent',
  ok: '',
  failed: 'pill-bad',
  timeout: 'pill-bad',
}
</script>

<template>
  <ul class="seats">
    <li
      v-for="p in participants"
      :key="p.id"
      class="seat"
      :class="{ removed: removedIds.includes(p.id) }"
      data-testid="inspector-participant"
      :data-participant-id="p.id"
    >
      <div class="who">
        <ParticipantLabel :participant="p" :id="p.id" :size="22" />
        <span v-if="p.id === moderatorId" class="pill pill-accent" data-testid="inspector-moderator">主持人</span>
      </div>
      <span v-if="removedIds.includes(p.id)" class="pill pill-bad state">已移出</span>
      <span v-else-if="statuses[p.id]" class="pill state" :class="STATUS_PILLS[statuses[p.id]!]">
        {{ STATUS_LABELS[statuses[p.id]!] }}
      </span>
      <span v-else class="muted state">—</span>
    </li>
  </ul>
</template>

<style scoped>
.seats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.seat {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}
.who {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  min-width: 0;
  font-size: var(--fs-sm);
}
.state {
  flex: none;
  margin-left: auto;
  font-size: var(--fs-xs);
}
.seat.removed .who {
  opacity: 0.5;
  text-decoration: line-through;
}
</style>
