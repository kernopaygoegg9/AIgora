<!-- One round: the participants' turns side by side, removals / moderator handoffs, then (consensus) draft | verdict. -->
<script setup lang="ts">
import '../../styles/discussion.css'
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { ModeratorChange, RemovedParticipant, RoundState } from '../../stores/discussion'
import RoundConsensus from './RoundConsensus.vue'
import RoundNotices from './RoundNotices.vue'
import TurnCard from './TurnCard.vue'

defineProps<{
  round: RoundState
  participantById: (id: string) => ParticipantSnapshot | undefined
  showNumber?: boolean
  moderatorId?: string | null
  /** This round's removals and moderator handoffs (ticket 07). */
  removed?: RemovedParticipant[]
  moderatorChanges?: ModeratorChange[]
}>()
</script>

<template>
  <section class="round d-round" data-testid="round" :data-round="round.number">
    <header v-if="showNumber" class="d-round-head">
      <h2 class="d-round-title">第 {{ round.number }} 輪</h2>
      <span v-if="round.status === 'running'" class="pill pill-accent">進行中</span>
    </header>
    <div class="d-cols" :style="{ '--columns': Math.max(round.turns.length, 1) }">
      <TurnCard
        v-for="turn in round.turns"
        :key="turn.participantId"
        :turn="turn"
        :participant="participantById(turn.participantId)"
      />
    </div>
    <RoundNotices :removed="removed ?? []" :moderator-changes="moderatorChanges ?? []" :participant-by-id="participantById" />
    <RoundConsensus :round="round" :participant-by-id="participantById" :moderator-id="moderatorId" />
  </section>
</template>
