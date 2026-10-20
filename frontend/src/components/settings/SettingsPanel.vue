<!--
  設定面板: question + per-discussion settings. Defaults come from `/api/options`
  (participants.toml `[defaults]`); only the fields the chosen mode uses are shown
  and sent. `locked` (the discussion is running) disables everything.
  Emits `submit` with the question and the `start` settings.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { OptionsResponse, ParticipantInfo } from '../../contracts/http'
import type { JudgeId, ModeId, SpeakingOrderId, StartSettings } from '../../contracts/messages'
import ParticipantAvatar from '../discussion/ParticipantAvatar.vue'

const props = defineProps<{
  participants: ParticipantInfo[]
  options: OptionsResponse | null
  locked?: boolean
}>()
const emit = defineEmits<{
  submit: [question: string, settings: StartSettings]
}>()

const question = ref('')
const mode = ref<ModeId>('ask')
const selected = ref<string[]>([])
const judge = ref<JudgeId>('stance_vote')
const moderatorId = ref('')
const speakingOrder = ref<SpeakingOrderId>('parallel')
const maxRounds = ref(15)
const turnTimeout = ref(300)
const jevThreshold = ref(0.8)

// Fill in the defaults once the options arrive.
watch(
  () => props.options,
  (options) => {
    if (!options) return
    const d = options.defaults
    mode.value = d.mode
    const defaultJudge = options.judges.find((j) => j.id === d.judge)
    judge.value = defaultJudge?.available ? d.judge : (options.judges.find((j) => j.available)?.id ?? d.judge)
    speakingOrder.value = d.speaking_order
    maxRounds.value = d.max_rounds
    turnTimeout.value = d.turn_timeout_seconds
    jevThreshold.value = d.jev_threshold
  },
  { immediate: true },
)

const uses = computed(() => new Set(props.options?.modes.find((m) => m.id === mode.value)?.uses_settings ?? []))

// Chosen participants in file order (not click order).
const selectedIds = computed(() => props.participants.map((p) => p.id).filter((id) => selected.value.includes(id)))
const moderatorChoices = computed(() => props.participants.filter((p) => selected.value.includes(p.id)))

// The moderator is one of the chosen participants: the user's pick while it stays chosen,
// otherwise the default moderator if chosen, else the first chosen.
const moderatorPicked = ref(false)
watch(
  [selectedIds, () => props.options],
  ([ids]) => {
    if (moderatorPicked.value && ids.includes(moderatorId.value)) return
    moderatorPicked.value = false
    const preferred = props.options?.defaults.moderator_id
    moderatorId.value = preferred && ids.includes(preferred) ? preferred : (ids[0] ?? '')
  },
  { immediate: true },
)

// A discussion needs at least 2 participants (the backend rejects fewer too).
const MIN_PARTICIPANTS = 2
const tooFewParticipants = computed(() => selectedIds.value.length < MIN_PARTICIPANTS)

const canSubmit = computed(
  () =>
    !props.locked &&
    props.options !== null &&
    question.value.trim() !== '' &&
    !tooFewParticipants.value &&
    (!uses.value.has('max_rounds') || maxRounds.value >= 1) &&
    (!uses.value.has('turn_timeout_seconds') || turnTimeout.value > 0),
)

function submit() {
  if (!canSubmit.value) return
  const u = uses.value
  const settings: StartSettings = {
    mode: mode.value,
    participant_ids: selectedIds.value,
  }
  if (u.has('speaking_order')) settings.speaking_order = speakingOrder.value
  if (u.has('turn_timeout_seconds')) settings.turn_timeout_seconds = turnTimeout.value
  if (u.has('moderator_id')) settings.moderator_id = moderatorId.value
  if (u.has('judge')) settings.judge = judge.value
  if (u.has('max_rounds')) settings.max_rounds = maxRounds.value
  if (u.has('judge') && u.has('jev_threshold') && judge.value === 'jev') {
    settings.jev_threshold = jevThreshold.value
  }
  emit('submit', question.value.trim(), settings)
}
</script>

<template>
  <form class="settings-panel" data-testid="settings-panel" @submit.prevent="submit">
    <p v-if="locked" class="locked" data-testid="settings-locked">討論進行中，設定已鎖定</p>

    <fieldset class="all" :disabled="locked">
      <label class="field-label" for="question-input">問題</label>
      <textarea
        id="question-input"
        v-model="question"
        class="question-input"
        rows="3"
        placeholder="輸入要問參與者的問題"
        @keydown.enter.ctrl.prevent="submit"
      />

      <fieldset v-if="options" class="group">
        <legend>討論模式</legend>
        <label v-for="m in options.modes" :key="m.id" class="choice">
          <input v-model="mode" type="radio" name="mode" :value="m.id" />
          <span>{{ m.name }}</span>
        </label>
      </fieldset>

      <fieldset class="group">
        <legend>參與者</legend>
        <p v-if="participants.length === 0" class="muted">沒有可用的參與者（請檢查 participants.toml）</p>
        <label
          v-for="p in participants"
          :key="p.id"
          class="choice"
          :class="{ unavailable: !p.available }"
          data-testid="participant-option"
          :title="p.available ? undefined : (p.unavailable_reason ?? '不可用')"
        >
          <input v-model="selected" type="checkbox" :value="p.id" :disabled="!p.available" />
          <ParticipantAvatar :avatar="p.avatar" :size="20" />
          <span>{{ p.display_name }}</span>
          <span v-if="!p.capabilities.web_access" class="badge">無上網</span>
          <span v-if="!p.available" class="badge badge-warn">不可用：{{ p.unavailable_reason ?? '原因不明' }}</span>
        </label>
        <p v-if="tooFewParticipants && participants.length > 0" class="hint" data-testid="participants-hint">
          請選擇至少 {{ MIN_PARTICIPANTS }} 個參與者
        </p>
      </fieldset>

      <fieldset v-if="options && uses.has('judge')" class="group" data-testid="judge-options">
        <legend>共識裁定方式</legend>
        <label
          v-for="j in options.judges"
          :key="j.id"
          class="choice"
          :class="{ unavailable: !j.available }"
          data-testid="judge-option"
        >
          <input v-model="judge" type="radio" name="judge" :value="j.id" :disabled="!j.available" />
          <span>{{ j.name }}</span>
          <span v-if="!j.available" class="badge badge-warn">不可用：{{ j.unavailable_reason ?? '原因不明' }}</span>
        </label>
      </fieldset>

      <div v-if="options" class="row">
        <span v-if="uses.has('moderator_id')" class="inline">
          <label for="moderator-select">主持人</label>
          <select
            id="moderator-select"
            v-model="moderatorId"
            @change="moderatorPicked = true"
            :disabled="moderatorChoices.length === 0"
          >
            <option v-for="p in moderatorChoices" :key="p.id" :value="p.id">
              {{ p.display_name }}
            </option>
          </select>
        </span>

        <span v-if="uses.has('speaking_order')" class="inline">
          <label for="speaking-order-select">發言順序</label>
          <select id="speaking-order-select" v-model="speakingOrder">
            <option v-for="o in options.speaking_orders" :key="o.id" :value="o.id" :disabled="!o.implemented">
              {{ o.implemented ? o.name : `${o.name}（尚未提供）` }}
            </option>
          </select>
        </span>

        <span v-if="uses.has('max_rounds')" class="inline">
          <label for="max-rounds-input">輪數上限</label>
          <input id="max-rounds-input" v-model.number="maxRounds" type="number" min="1" step="1" class="number" />
        </span>

        <span v-if="uses.has('turn_timeout_seconds')" class="inline">
          <label for="turn-timeout-input">逾時（秒）</label>
          <input id="turn-timeout-input" v-model.number="turnTimeout" type="number" min="1" step="1" class="number" />
        </span>

        <span v-if="uses.has('judge') && uses.has('jev_threshold') && judge === 'jev'" class="inline">
          <label for="jev-threshold-input">Jev 門檻</label>
          <input
            id="jev-threshold-input"
            v-model.number="jevThreshold"
            type="number"
            min="0"
            max="1"
            step="0.05"
            class="number"
          />
        </span>
      </div>

      <button type="submit" class="submit" :disabled="!canSubmit">送出</button>
    </fieldset>
  </form>
</template>

<style scoped>
.settings-panel {
  max-width: 60rem;
}
.all {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border: none;
  margin: 0;
  padding: 0;
  min-width: 0;
}
.field-label {
  font-weight: 600;
}
.question-input {
  font: inherit;
  padding: 0.5rem;
  border: 1px solid #c4cad1;
  border-radius: 6px;
  resize: vertical;
}
.group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  border: 1px solid #d8dde3;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}
.choice {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}
.choice.unavailable {
  color: #8a9097;
  cursor: not-allowed;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
}
.inline {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.inline select,
.number {
  font: inherit;
  padding: 0.2rem 0.4rem;
  border: 1px solid #c4cad1;
  border-radius: 6px;
}
.number {
  width: 6rem;
}
.badge {
  font-size: 0.75rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: #e8ebef;
  color: #4a5159;
}
.badge-warn {
  background: #fdecea;
  color: #a1260d;
}
.locked {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  color: #6b7280;
}
.submit {
  align-self: flex-start;
  font: inherit;
  padding: 0.4rem 1.2rem;
  border: none;
  border-radius: 6px;
  background: #2f6feb;
  color: #fff;
  cursor: pointer;
}
.submit:disabled {
  background: #a9bde6;
  cursor: not-allowed;
}
.hint {
  flex-basis: 100%;
  margin: 0;
  font-size: 0.85rem;
  color: #a1260d;
}
.muted {
  color: #6b7280;
  margin: 0;
}
</style>
