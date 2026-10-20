<!-- One round: the participants' turns side by side, then (consensus) the judge result and draft. -->
<script setup lang="ts">
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { RoundState } from '../../stores/discussion'
import RoundConsensus from './RoundConsensus.vue'
import TurnCard from './TurnCard.vue'

defineProps<{
  round: RoundState
  participantById: (id: string) => ParticipantSnapshot | undefined
  showNumber?: boolean
  moderatorId?: string | null
}>()
</script>

<template>
  <section class="round" data-testid="round" :data-round="round.number">
    <h2 v-if="showNumber" class="round-title">第 {{ round.number }} 輪</h2>
    <div class="turns" :style="{ '--columns': Math.max(round.turns.length, 1) }">
      <TurnCard
        v-for="turn in round.turns"
        :key="turn.participantId"
        :turn="turn"
        :participant="participantById(turn.participantId)"
      />
    </div>
    <RoundConsensus :round="round" :participant-by-id="participantById" :moderator-id="moderatorId" />
  </section>
</template>

<style scoped>
.round {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.round-title {
  font-size: 1rem;
  margin: 0;
}
.turns {
  display: grid;
  grid-template-columns: repeat(var(--columns), minmax(16rem, 1fr));
  gap: 0.75rem;
  align-items: start;
  overflow-x: auto;
}
</style>
