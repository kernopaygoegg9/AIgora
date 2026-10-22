<!-- Everyone's 表態 in a judge A verdict: one row per participant with a coloured pill.
     Shared by the live round (RoundConsensus) and the record (RecordRound). -->
<script setup lang="ts">
import '../../styles/discussion.css'

import type { ParticipantSnapshot, Stance } from '../../contracts/messages'
import { stanceLabel } from '../labels'
import ParticipantLabel from './ParticipantLabel.vue'

defineProps<{
  stances: { id: string; stance: Stance | null }[]
  participantById: (id: string) => ParticipantSnapshot | undefined
  /** data-testid of each row (the live page's E2E finds rows by `stance`). */
  itemTestid?: string
}>()

const STANCE_PILLS = { AGREE: 'pill-ok', DISAGREE: 'pill-bad', none: 'pill-bad' } as const
</script>

<template>
  <ul class="d-list">
    <li
      v-for="s in stances"
      :key="s.id"
      class="stance d-list-row"
      :class="`stance-${s.stance ?? 'none'}`"
      :data-testid="itemTestid"
    >
      <ParticipantLabel :id="s.id" :participant="participantById(s.id)" :size="18" hide-web />
      <span class="pill" :class="STANCE_PILLS[s.stance ?? 'none']">{{
        stanceLabel(s.stance)
      }}</span>
    </li>
  </ul>
</template>
