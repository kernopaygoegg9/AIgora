<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { openDiscussionSocket, type DiscussionSocket } from '../api/discussionSocket'
import { fetchParticipants } from '../api/participants'
import AskForm from '../components/discussion/AskForm.vue'
import DiscussionOutcome from '../components/discussion/DiscussionOutcome.vue'
import RoundSection from '../components/discussion/RoundSection.vue'
import type { ParticipantInfo } from '../contracts/http'
import type { ModeId } from '../contracts/messages'
import { useDiscussionStore } from '../stores/discussion'

// `id` is set when viewing a past discussion read-only (route `discussion-record`, ticket 09).
const props = defineProps<{ id?: string }>()

const store = useDiscussionStore()
const participants = ref<ParticipantInfo[]>([])
const loadError = ref<string | null>(null)
const connectionLost = ref(false)
let socket: DiscussionSocket | null = null

const STATUS_LABELS = { idle: '', running: '討論中', finished: '已結束' } as const
const statusLabel = computed(() => STATUS_LABELS[store.status])

onMounted(async () => {
  if (props.id) return
  try {
    participants.value = await fetchParticipants()
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  }
})

onBeforeUnmount(() => socket?.close())

function startAsk(question: string, participantIds: string[], mode: ModeId = 'ask') {
  socket?.close()
  store.reset()
  connectionLost.value = false
  const current = openDiscussionSocket(
    (msg) => store.applyMessage(msg),
    () => {
      if (socket === current && store.status === 'running') connectionLost.value = true
    },
  )
  socket = current
  current.start(question, { mode, participant_ids: participantIds })
}
</script>

<template>
  <section class="discussion-page" data-testid="discussion-page">
    <h1 class="page-title">討論</h1>

    <template v-if="!id">
      <p v-if="loadError" class="error">{{ loadError }}</p>
      <AskForm :participants="participants" :disabled="store.status === 'running'" @submit="startAsk" />
    </template>

    <p v-for="(message, i) in store.errors" :key="i" class="error" data-testid="discussion-error">{{ message }}</p>
    <p v-if="connectionLost" class="error">與後端的連線中斷</p>

    <div v-if="store.status !== 'idle'" class="discussion">
      <header class="discussion-header">
        <h2 class="question" data-testid="discussion-question">{{ store.question }}</h2>
        <span class="discussion-status" data-testid="discussion-status">{{ statusLabel }}</span>
      </header>
      <RoundSection
        v-for="round in store.rounds"
        :key="round.number"
        :round="round"
        :participant-by-id="store.participantById"
        :show-number="store.settings?.mode !== 'ask'"
        :moderator-id="store.moderatorId"
      />
      <DiscussionOutcome :outcome="store.outcome" :result="store.result" :reason="store.finishReason" />
    </div>
  </section>
</template>

<style scoped>
.discussion-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.page-title {
  font-size: 1.25rem;
  margin: 0;
}
.discussion {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.discussion-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}
.question {
  font-size: 1.1rem;
  margin: 0;
  white-space: pre-wrap;
}
.discussion-status {
  font-size: 0.85rem;
  color: #6b7280;
}
.error {
  color: #a1260d;
  margin: 0;
}
</style>
