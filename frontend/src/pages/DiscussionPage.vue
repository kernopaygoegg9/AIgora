<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { openDiscussionSocket, type DiscussionSocket } from '../api/discussionSocket'
import { fetchOptions } from '../api/options'
import { fetchParticipants } from '../api/participants'
import DiscussionControls from '../components/discussion/DiscussionControls.vue'
import DiscussionInspector from '../components/discussion/DiscussionInspector.vue'
import DiscussionOutcome from '../components/discussion/DiscussionOutcome.vue'
import RecordView from '../components/history/RecordView.vue'
import RoundSection from '../components/discussion/RoundSection.vue'
import StartConsensusButton from '../components/discussion/StartConsensusButton.vue'
import SettingsPanel from '../components/settings/SettingsPanel.vue'
import type { OptionsResponse, ParticipantInfo } from '../contracts/http'
import type { StartSettings } from '../contracts/messages'
import { useDiscussionStore } from '../stores/discussion'
import { outcomeLabel, outcomePillClass } from '../components/labels'
import '../styles/discussion.css'

// `id` is set when viewing a past discussion read-only (route `discussion-record`, ticket 09).
const props = defineProps<{ id?: string }>()

const store = useDiscussionStore()
const participants = ref<ParticipantInfo[]>([])
const options = ref<OptionsResponse | null>(null)
const loadError = ref<string | null>(null)
const connectionLost = ref(false)
let socket: DiscussionSocket | null = null

const STATUS_LABELS = { idle: '', running: '討論中', finished: '已結束' } as const
const statusLabel = computed(() => STATUS_LABELS[store.status])
const currentRound = computed(() => store.rounds[store.rounds.length - 1]?.number ?? null)

// Stop is pressed once; a new discussion gets a fresh button.
const stopping = ref(false)
function stop() {
  stopping.value = true
  socket?.stop()
}

// The router reuses this instance between `/` and `/discussions/:id`, so load whenever
// the live view is shown, not only on mount.
watch(
  () => props.id,
  async (id) => {
    // Coming back to the live view after a discussion finished (it is in the history now):
    // start from the settings again. A running discussion keeps showing while this page
    // still holds its socket; one left behind (the page was left, closing the socket and
    // cancelling it; it is in the history) can never update again, so start over too.
    if (!id && (store.status === 'finished' || (store.status === 'running' && !socket)))
      store.reset()
    if (id || participants.value.length) return
    try {
      ;[participants.value, options.value] = await Promise.all([
        fetchParticipants(),
        fetchOptions(),
      ])
    } catch (err) {
      loadError.value = err instanceof Error ? err.message : String(err)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => socket?.close())

// `fromDiscussionId`: 提問轉共識討論 (ticket 10); the backend takes the question and
// participants from that ask.
function startDiscussion(
  question: string,
  settings: StartSettings,
  fromDiscussionId: string | null = null,
) {
  socket?.close()
  store.reset()
  connectionLost.value = false
  stopping.value = false
  const current = openDiscussionSocket(
    (msg) => store.applyMessage(msg),
    () => {
      if (socket === current && store.status === 'running') connectionLost.value = true
    },
  )
  socket = current
  current.start(question, settings, fromDiscussionId)
}
</script>

<template>
  <!-- Past discussion: read-only record view only (ticket 09). -->
  <RecordView v-if="id" :id="id" />
  <section v-else class="discussion-page" data-testid="discussion-page">
    <!-- Settings stay mounted while a discussion runs, so the inputs survive (ui-redesign 04). -->
    <div v-show="store.status === 'idle'" class="setup">
      <h1 class="page-title">新討論</h1>
      <p v-if="loadError" class="error-bar">{{ loadError }}</p>
      <p
        v-for="(message, i) in store.status === 'idle' ? store.errors : []"
        :key="i"
        class="error-bar"
        data-testid="discussion-error"
      >
        {{ message }}
      </p>
      <SettingsPanel
        :participants="participants"
        :options="options"
        :locked="store.status === 'running'"
        @submit="startDiscussion"
      />
    </div>

    <div v-if="store.status !== 'idle'" class="discussion">
      <div class="stage">
        <header class="topbar">
          <h1 class="question" data-testid="discussion-question" :title="store.question">
            {{ store.question }}
          </h1>
          <span class="pill" :class="{ 'pill-accent': store.status === 'running' }">
            <span v-if="store.status === 'running'" aria-hidden="true">●</span>
            <span data-testid="discussion-status">{{ statusLabel }}</span>
            <span
              v-if="store.status === 'running' && currentRound && store.settings?.mode !== 'ask'"
            >
              · 第 {{ currentRound }} 輪</span
            >
          </span>
          <span v-if="store.outcome" class="pill" :class="outcomePillClass(store.outcome)">{{
            outcomeLabel(store.outcome)
          }}</span>
          <button
            v-if="store.status === 'running' && !store.readOnly"
            type="button"
            class="btn btn-danger"
            :disabled="stopping"
            @click="stop"
          >
            <span aria-hidden="true">■ </span>停止
          </button>
          <StartConsensusButton
            :discussion-id="store.discussionId"
            :settings="store.settings"
            :outcome="store.outcome"
            :options="options"
            @start="(settings, fromId) => startDiscussion(store.question, settings, fromId)"
          />
        </header>

        <p
          v-for="(message, i) in store.errors"
          :key="i"
          class="error-bar"
          data-testid="discussion-error"
        >
          {{ message }}
        </p>
        <p v-if="connectionLost" class="error-bar">與後端的連線中斷</p>

        <DiscussionOutcome
          :outcome="store.outcome"
          :result="store.result"
          :reason="store.finishReason"
        />
        <RoundSection
          v-for="round in store.rounds"
          :key="round.number"
          :round="round"
          :participant-by-id="store.participantById"
          :show-number="store.settings?.mode !== 'ask'"
          :moderator-id="store.moderatorId"
          :removed="store.removed.filter((r) => r.round === round.number)"
          :moderator-changes="store.moderatorChanges.filter((c) => c.round === round.number)"
        />
        <DiscussionControls
          :key="store.discussionId ?? ''"
          :status="store.status"
          :mode="store.settings?.mode ?? null"
          :read-only="store.readOnly"
          @interject="(text) => socket?.interject(text)"
        />
      </div>
      <DiscussionInspector
        :settings="store.settings"
        :options="options"
        :interjections="store.interjections"
        :participant-by-id="store.participantById"
      />
    </div>
  </section>
</template>

<style scoped>
.setup {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.page-title {
  font-size: var(--fs-lg);
  font-weight: 600;
}
.discussion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--inspector-width);
  gap: var(--space-4);
  align-items: start;
}
.stage {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}
.topbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) 10px;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--line);
}
.question {
  flex: 1 1 12rem;
  min-width: 0;
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.error-bar {
  margin: 0;
  padding: 8px 12px;
  color: var(--bad);
  background: var(--bad-bg);
  border: 1px solid var(--bad-line);
  border-radius: var(--radius);
  overflow-wrap: anywhere;
}
@media (max-width: 1023px) {
  .discussion {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
