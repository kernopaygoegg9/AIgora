<!-- Failure-handling notices for one round of a live discussion (ticket 07): participants
     removed after failing 2 rounds in a row, and moderator handoffs. -->
<script setup lang="ts">
import type { ParticipantSnapshot } from '../../contracts/messages'
import type { ModeratorChange, RemovedParticipant } from '../../stores/discussion'

const props = defineProps<{
  removed: RemovedParticipant[]
  moderatorChanges: ModeratorChange[]
  participantById: (id: string) => ParticipantSnapshot | undefined
}>()

const name = (id: string) => props.participantById(id)?.display_name ?? id
</script>

<template>
  <div v-if="removed.length || moderatorChanges.length" class="round-notices">
    <p
      v-for="r in removed"
      :key="`r-${r.participantId}`"
      class="notice removal"
      data-testid="participant-removed"
      :data-participant-id="r.participantId"
    >
      <span class="label">移出討論</span>
      <span>{{ name(r.participantId) }}：{{ r.reason }}</span>
    </p>
    <p
      v-for="(c, k) in moderatorChanges"
      :key="`m-${k}`"
      class="notice"
      data-testid="moderator-changed"
      :data-participant-id="c.participantId"
    >
      <span class="label">主持人接手</span>
      <span>改由 {{ name(c.participantId) }} 擔任主持人</span>
    </p>
  </div>
</template>

<style scoped>
.round-notices {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.notice {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  margin: 0;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  background: #f3f4f6;
  font-size: 0.9rem;
}
.notice.removal {
  background: #fdeeec;
  color: #a1260d;
}
.label {
  flex: none;
  font-weight: 600;
  font-size: 0.8rem;
}
</style>
