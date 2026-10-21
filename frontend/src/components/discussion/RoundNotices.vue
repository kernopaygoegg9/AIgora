<!-- Failure-handling notices for one round of a live discussion (ticket 07): participants
     removed after failing 2 rounds in a row, and moderator handoffs. -->
<script setup lang="ts">
import '../../styles/discussion.css'
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
  <p
    v-for="r in removed"
    :key="`r-${r.participantId}`"
    class="d-notice is-bad"
    data-testid="participant-removed"
    :data-participant-id="r.participantId"
  >
    <span class="d-notice-label">移出討論</span>
    <span>{{ name(r.participantId) }}：{{ r.reason }}</span>
  </p>
  <p
    v-for="(c, k) in moderatorChanges"
    :key="`m-${k}`"
    class="d-notice"
    data-testid="moderator-changed"
    :data-participant-id="c.participantId"
  >
    <span class="d-notice-label">主持人接手</span>
    <span>改由 {{ name(c.participantId) }} 擔任主持人</span>
  </p>
</template>
