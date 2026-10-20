<!--
  設定面板: question + per-discussion settings. Defaults come from `/api/options`
  (participants.toml `[defaults]`); only the fields the chosen mode uses are shown
  and sent. `locked` (the discussion is running) disables everything.
  Laid out as stage (question, mode, participants) + inspector (other settings, start).
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

function orderLabel(name: string, implemented: boolean): string {
  return implemented ? name : `${name}（尚未提供）`
}
</script>

<template>
  <form class="settings-panel" data-testid="settings-panel" @submit.prevent="submit">
    <fieldset class="layout" :disabled="locked">
      <!-- Stage: the question, the mode and who takes part. -->
      <div class="stage">
        <p v-if="locked" class="locked" data-testid="settings-locked">討論進行中，設定已鎖定</p>

        <label class="visually-hidden" for="question-input">問題</label>
        <textarea
          id="question-input"
          v-model="question"
          class="question-input"
          rows="4"
          placeholder="輸入要問參與者的問題（Ctrl+Enter 開始討論）"
          @keydown.enter.ctrl.prevent="submit"
        />

        <fieldset v-if="options" class="mode-row">
          <legend class="row-label">討論模式</legend>
          <div class="segmented">
            <label v-for="m in options.modes" :key="m.id" class="segment" :class="{ on: mode === m.id }">
              <input v-model="mode" type="radio" name="mode" :value="m.id" />
              <span>{{ m.name }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="participants">
          <legend class="section-label">參與者</legend>
          <p v-if="participants.length === 0" class="muted">沒有可用的參與者（請檢查 participants.toml）</p>
          <table v-else class="participant-table">
            <thead>
              <tr>
                <th scope="col">參與者</th>
                <th scope="col">Adapter · 模型</th>
                <th scope="col">能力</th>
                <th scope="col">狀態</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in participants"
                :key="p.id"
                :class="{ unavailable: !p.available, chosen: selected.includes(p.id) }"
                data-testid="participant-option"
                :title="p.available ? undefined : (p.unavailable_reason ?? '不可用')"
              >
                <td>
                  <label class="participant-name">
                    <input v-model="selected" type="checkbox" :value="p.id" :disabled="!p.available" />
                    <ParticipantAvatar :avatar="p.avatar" :size="22" />
                    <span>{{ p.display_name }}</span>
                  </label>
                </td>
                <td class="muted">{{ p.adapter }} · {{ p.model ?? 'Adapter 預設' }}</td>
                <td>
                  <span v-if="p.capabilities.web_access" class="pill">可上網</span>
                  <span v-else class="pill pill-warn">無上網</span>
                </td>
                <td>
                  <span v-if="p.available" class="pill pill-ok">可用</span>
                  <span v-else class="pill pill-bad reason">不可用：{{ p.unavailable_reason ?? '原因不明' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="tooFewParticipants && participants.length > 0" class="hint" data-testid="participants-hint">
            請選擇至少 {{ MIN_PARTICIPANTS }} 個參與者
          </p>
        </fieldset>
      </div>

      <!-- Inspector: the rest of this discussion's settings, and start. -->
      <aside class="inspector">
        <section v-if="options && uses.has('judge')" class="section" data-testid="judge-options">
          <h3 class="section-title">共識裁定方式</h3>
          <label
            v-for="j in options.judges"
            :key="j.id"
            class="judge"
            :class="{ on: judge === j.id, unavailable: !j.available }"
            data-testid="judge-option"
          >
            <input v-model="judge" type="radio" name="judge" :value="j.id" :disabled="!j.available" />
            <span class="judge-text">
              <span>{{ j.name }}</span>
              <small v-if="!j.available">不可用：{{ j.unavailable_reason ?? '原因不明' }}</small>
            </span>
          </label>
        </section>

        <section v-if="options" class="section">
          <h3 class="section-title">討論設定</h3>
          <div class="fields">
            <div v-if="uses.has('moderator_id')" class="field wide">
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
            </div>

            <div v-if="uses.has('speaking_order')" class="field wide">
              <label for="speaking-order-select">發言順序</label>
              <select id="speaking-order-select" v-model="speakingOrder">
                <option v-for="o in options.speaking_orders" :key="o.id" :value="o.id" :disabled="!o.implemented">
                  {{ orderLabel(o.name, o.implemented) }}
                </option>
              </select>
            </div>

            <div v-if="uses.has('max_rounds')" class="field">
              <label for="max-rounds-input">輪數上限</label>
              <input id="max-rounds-input" v-model.number="maxRounds" type="number" min="1" step="1" />
            </div>

            <div v-if="uses.has('turn_timeout_seconds')" class="field">
              <label for="turn-timeout-input">逾時（秒）</label>
              <input id="turn-timeout-input" v-model.number="turnTimeout" type="number" min="1" step="1" />
            </div>

            <div v-if="uses.has('judge') && uses.has('jev_threshold') && judge === 'jev'" class="field">
              <label for="jev-threshold-input">Jev 門檻</label>
              <input id="jev-threshold-input" v-model.number="jevThreshold" type="number" min="0" max="1" step="0.05" />
            </div>
          </div>
        </section>

        <section class="section">
          <button type="submit" class="btn btn-primary submit" :disabled="!canSubmit">開始討論</button>
          <p class="submit-note muted">已選 {{ selectedIds.length }} 個參與者 · 預設值來自 participants.toml</p>
        </section>
      </aside>
    </fieldset>
  </form>
</template>

<style scoped>
fieldset {
  border: none;
  margin: 0;
  padding: 0;
  min-width: 0;
}
.layout {
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
.locked {
  font-size: var(--fs-sm);
  color: var(--muted);
}
.question-input {
  width: 100%;
  min-height: 110px;
  padding: var(--space-3);
  font-size: var(--fs-md);
  line-height: 1.6;
  background: var(--panel);
  border-radius: var(--radius-lg);
  resize: vertical;
}

/* Mode: a segmented control over native radios. Each radio covers its whole segment
   (transparent), so clicks and tests hit the input itself. */
.mode-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.row-label {
  float: left;
  padding: 0;
  margin-right: var(--space-3);
  color: var(--muted);
}
.segmented {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel);
}
.segment {
  position: relative;
  padding: 6px 16px;
  cursor: pointer;
}
.segment + .segment {
  border-left: 1px solid var(--line);
}
.segment input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}
.segment.on {
  background: var(--accent);
  color: var(--on-accent);
  font-weight: 600;
}
.segment:has(input:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.section-label {
  padding: 0;
  margin-bottom: var(--space-2);
  font-size: var(--fs-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.participant-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.participant-table th,
.participant-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}
.participant-table tbody tr:last-child td {
  border-bottom: none;
}
.participant-table th {
  font-weight: normal;
  font-size: var(--fs-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--panel-2);
}
.participant-table tbody tr:hover {
  background: var(--panel-2);
}
.participant-table tr.chosen {
  background: var(--accent-bg);
}
.participant-table tr.unavailable td {
  color: var(--muted);
}
.participant-table tr.unavailable .participant-name {
  cursor: not-allowed;
}
.participant-name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  font-weight: 500;
}
.reason {
  white-space: normal;
}
.hint {
  margin-top: var(--space-2);
  font-size: var(--fs-sm);
  color: var(--bad);
}

/* Inspector column. */
.inspector {
  position: sticky;
  top: var(--space-4);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
}
.section {
  padding: var(--space-3) 14px;
  border-bottom: 1px solid var(--line);
}
.section:last-child {
  border-bottom: none;
}
.section-title {
  margin-bottom: var(--space-2);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.judge {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: 8px 10px;
  margin-bottom: 6px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  cursor: pointer;
}
.judge:last-child {
  margin-bottom: 0;
}
.judge input {
  margin-top: 3px;
}
.judge.on {
  border-color: var(--accent);
  background: var(--accent-bg);
}
.judge.unavailable {
  opacity: 0.6;
  cursor: not-allowed;
}
.judge-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.judge-text small {
  color: var(--muted);
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
.fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--fs-sm);
  min-width: 0;
}
.field.wide {
  grid-column: 1 / -1;
}
.field label {
  color: var(--muted);
}
.submit {
  width: 100%;
  padding: 9px 14px;
}
.submit-note {
  margin-top: var(--space-2);
  font-size: var(--fs-xs);
}

@media (max-width: 1023px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .inspector {
    position: static;
  }
}
@media (max-width: 640px) {
  .participant-table th:nth-child(2),
  .participant-table td:nth-child(2) {
    display: none;
  }
}
</style>
