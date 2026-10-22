<!-- Judge B's 反問確認 answers: one row per participant (agree / disagree) with the reason.
     Shared by the live round (RoundConsensus) and the record (RecordRound). -->
<script setup lang="ts">
import '../../styles/discussion.css'

import type { ConfirmationAnswer, ParticipantSnapshot } from '../../contracts/messages'
import { agreeLabel } from '../labels'
import ParticipantLabel from './ParticipantLabel.vue'

defineProps<{
  answers: ConfirmationAnswer[]
  participantById: (id: string) => ParticipantSnapshot | undefined
  /** Also show the reason of an agreeing answer (the record does; live shows disagreements only). */
  agreeReasons?: boolean
  /** data-testid of each row (the live page's E2E finds rows by `confirmation-answer`). */
  itemTestid?: string
}>()
</script>

<template>
  <ul class="d-list">
    <li
      v-for="a in answers"
      :key="a.participant_id"
      class="answer"
      :class="a.agree ? 'answer-agree' : 'answer-disagree'"
      :data-testid="itemTestid"
    >
      <div class="d-list-row">
        <ParticipantLabel
          :participant="participantById(a.participant_id)"
          :id="a.participant_id"
          :size="18"
          hide-web
        />
        <span class="pill" :class="a.agree ? 'pill-ok' : 'pill-bad'">{{
          agreeLabel(a.agree)
        }}</span>
      </div>
      <p v-if="a.reason && (agreeReasons || !a.agree)" class="d-reason">{{ a.reason }}</p>
    </li>
  </ul>
</template>
