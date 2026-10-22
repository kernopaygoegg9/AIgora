<!-- The inspector's participant list (ui-redesign 05): who takes part, the moderator, each
     one's current status, and who was removed. Props only, so the read-only record (07)
     can feed it from a saved record. -->
<script setup lang="ts">
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { TurnStateStatus } from '../../stores/discussion'
import { TURN_STATUS_LABELS, TURN_STATUS_PILLS } from '../labels'
import ParticipantLabel from './ParticipantLabel.vue'

defineProps<{
  participants: ParticipantSnapshot[]
  moderatorId: string | null
  removedIds: string[]
  /** Each participant's latest turn status; missing = no turn yet. */
  statuses: Record<string, TurnStateStatus | undefined>
}>()
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
        <ParticipantLabel :id="p.id" :participant="p" :size="22" />
        <span v-if="p.id === moderatorId" class="pill pill-accent" data-testid="inspector-moderator"
          >主持人</span
        >
      </div>
      <span v-if="removedIds.includes(p.id)" class="pill pill-bad state">已移出</span>
      <span
        v-else-if="statuses[p.id]"
        class="pill state"
        :class="TURN_STATUS_PILLS[statuses[p.id]!]"
      >
        {{ TURN_STATUS_LABELS[statuses[p.id]!] }}
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
/* Faded with the muted colour, not opacity, so the name keeps WCAG AA contrast (ticket 08). */
.seat.removed .who {
  color: var(--muted);
  text-decoration: line-through;
}
.seat.removed .who :deep(.avatar) {
  opacity: 0.5;
}
</style>
