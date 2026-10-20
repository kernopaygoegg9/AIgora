<!--
  設定面板: question + per-discussion settings. Defaults come from `/api/options`
  (participants.toml `[defaults]`); only the fields the chosen mode uses are shown
  and sent. `locked` (the discussion is running) disables everything.
  Laid out as stage (question, mode, participants) + inspector (other settings, start).
  Emits `submit` with the question and the `start` settings.
-->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import '../../styles/inspector.css'
import type { OptionsResponse, ParticipantInfo } from '../../contracts/http'
import type { ExtraParticipant, JudgeId, ModeId, SpeakingOrderId, StartSettings } from '../../contracts/messages'
import ParticipantLabel from '../discussion/ParticipantLabel.vue'
import ModelSelect, { OTHER_MODEL } from './ModelSelect.vue'

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

// Model picked per participant id: choice '' = the participants file's model.
const modelPicks = reactive<Record<string, { choice: string; custom: string }>>({})
watch(
  () => props.participants,
  (list) => {
    for (const p of list) modelPicks[p.id] ??= { choice: '', custom: '' }
  },
  { immediate: true },
)

const MAX_MODEL_LENGTH = 100
/** The model asked for: null = the file's (or template's) model, '' = invalid 其他 text. */
function requestedModel(id: string): string | null {
  const pick = modelPicks[id]
  if (!pick || pick.choice === '') return null
  if (pick.choice !== OTHER_MODEL) return pick.choice
  const model = pick.custom.trim()
  return model.length <= MAX_MODEL_LENGTH && !/\s/.test(model) ? model : ''
}

const uses = computed(() => new Set(props.options?.modes.find((m) => m.id === mode.value)?.uses_settings ?? []))

// Extra participants (臨時參與者): copies of a configured participant (the template),
// only for this discussion. They come after the configured ones, in the order added.
interface Extra {
  id: string
  template: ParticipantInfo
}
const extras = ref<Extra[]>([])

/** A table row: a configured participant, or an extra one (`template` = its template). */
interface Row {
  id: string
  info: ParticipantInfo
  extra: boolean
}
const rows = computed<Row[]>(() => [
  ...props.participants.map((p) => ({ id: p.id, info: p, extra: false })),
  ...extras.value.map((e) => ({ id: e.id, info: e.template, extra: true })),
])

// Chosen participants in table order (not click order).
const chosenRows = computed(() => rows.value.filter((r) => selected.value.includes(r.id)))
const selectedIds = computed(() => chosenRows.value.map((r) => r.id))

/** The model the row will use: its pick, else the file's (or template's) model. */
function effectiveModel(row: Row): string | null {
  return requestedModel(row.id) || row.info.model
}

// Display names follow the backend's rule among the chosen participants: duplicated names
// get "（模型）", names still duplicated get " 2", " 3"... (the snapshot has the final say).
const names = computed(() => {
  const chosen = chosenRows.value
  const count = (list: string[]) => list.reduce((m, n) => m.set(n, (m.get(n) ?? 0) + 1), new Map<string, number>())
  const base = count(chosen.map((r) => r.info.display_name))
  const withModel = chosen.map((r) =>
    base.get(r.info.display_name)! > 1 ? `${r.info.display_name}（${effectiveModel(r) ?? '預設模型'}）` : r.info.display_name,
  )
  const again = count(withModel)
  const taken = new Set(withModel)
  const seen = new Set<string>()
  const out = new Map<string, string>()
  chosen.forEach((r, i) => {
    let name = withModel[i]!
    if (again.get(name)! > 1 && seen.has(name)) {
      seen.add(name)
      let n = 2
      while (taken.has(`${name} ${n}`)) n++
      name = `${name} ${n}`
      taken.add(name)
    } else {
      seen.add(name)
    }
    out.set(r.id, name)
  })
  return out
})
const nameOf = (row: Row) => names.value.get(row.id) ?? row.info.display_name

const moderatorChoices = computed(() => chosenRows.value)

// 「＋ 新增參與者」: one choice per Adapter that has an available participant; the template
// is that Adapter's first available participant in the participants file.
const adapterTemplates = computed(() => {
  const byAdapter = new Map<string, ParticipantInfo>()
  for (const p of props.participants) if (p.available && !byAdapter.has(p.adapter)) byAdapter.set(p.adapter, p)
  return [...byAdapter.values()]
})
const adding = ref(false)
const newAdapter = ref('')
const NEW_ID = '__new__'
const newTemplate = computed(() => adapterTemplates.value.find((t) => t.adapter === newAdapter.value))

// A new Adapter has its own model list: start again from its default.
watch(newAdapter, () => {
  modelPicks[NEW_ID] = { choice: '', custom: '' }
})

function startAdding() {
  newAdapter.value = adapterTemplates.value[0]?.adapter ?? ''
  modelPicks[NEW_ID] = { choice: '', custom: '' }
  adding.value = true
}

// Extra ids: `<template id>-x<n>`, matching ^[a-z0-9][a-z0-9_-]{0,63}$ and unused here.
// The backend also rejects ids of disabled participants, which this page never sees, so the
// `-x<n>` suffix keeps clear of the usual `<name>-2` style of configured ids.
function newExtraId(template: ParticipantInfo): string {
  const base = template.id.toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^[^a-z0-9]+/, '').slice(0, 54) || 'extra'
  const used = new Set(rows.value.map((r) => r.id))
  let n = 2
  while (used.has(`${base}-x${n}`)) n++
  return `${base}-x${n}`
}

function addExtra() {
  const template = newTemplate.value
  if (!template) return
  const id = newExtraId(template)
  modelPicks[id] = { ...modelPicks[NEW_ID]! }
  extras.value = [...extras.value, { id, template }]
  selected.value = [...selected.value, id]
  adding.value = false
}

function removeExtra(id: string) {
  extras.value = extras.value.filter((e) => e.id !== id)
  selected.value = selected.value.filter((s) => s !== id)
  delete modelPicks[id]
}

// Every chosen 其他 model needs a valid name.
const invalidModel = computed(() => chosenRows.value.some((r) => requestedModel(r.id) === ''))

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
    !invalidModel.value &&
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
  // `models`: only chosen configured participants whose model differs from the file.
  const models: Record<string, string> = {}
  const extraParticipants: ExtraParticipant[] = []
  for (const row of chosenRows.value) {
    const model = requestedModel(row.id)
    if (row.extra) extraParticipants.push({ id: row.id, template_id: row.info.id, model })
    else if (model && model !== row.info.model) models[row.id] = model
  }
  if (Object.keys(models).length) settings.models = models
  if (extraParticipants.length) settings.extra_participants = extraParticipants
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

function snapshot(row: Row) {
  const p = row.info
  return {
    id: row.id,
    display_name: nameOf(row),
    adapter: p.adapter,
    model: effectiveModel(row),
    avatar: p.avatar,
    capabilities: p.capabilities,
  }
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
                <th scope="col">Adapter</th>
                <th scope="col">模型</th>
                <th scope="col">能力</th>
                <th scope="col">狀態</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in rows"
                :key="row.id"
                :class="{ unavailable: !row.info.available, chosen: selected.includes(row.id), extra: row.extra }"
                data-testid="participant-option"
                :title="row.info.available ? undefined : (row.info.unavailable_reason ?? '不可用')"
              >
                <td>
                  <span class="participant-cell">
                    <label class="participant-name">
                      <input
                        v-model="selected"
                        type="checkbox"
                        :value="row.id"
                        :disabled="!row.info.available"
                        :aria-label="nameOf(row)"
                      />
                      <ParticipantLabel :participant="snapshot(row)" :id="row.id" hide-web />
                    </label>
                    <span v-if="row.extra" class="pill pill-accent" data-testid="extra-participant">臨時</span>
                  </span>
                </td>
                <td class="muted">{{ row.info.adapter }}</td>
                <td>
                  <ModelSelect
                    v-model:choice="modelPicks[row.id]!.choice"
                    v-model:custom="modelPicks[row.id]!.custom"
                    :label="`${nameOf(row)} 的模型`"
                    :default-model="row.info.model"
                    :models="row.info.models"
                    :free-text="row.info.free_text_model"
                    :error="row.info.models_error"
                    :disabled="!row.info.available"
                  />
                </td>
                <td>
                  <span v-if="row.info.capabilities.web_access" class="pill">可上網</span>
                  <span v-else class="pill pill-warn">無上網</span>
                </td>
                <td>
                  <span class="status-cell">
                    <span v-if="row.info.available" class="pill pill-ok">可用</span>
                    <span v-else class="pill pill-bad reason">不可用：{{ row.info.unavailable_reason ?? '原因不明' }}</span>
                    <button
                      v-if="row.extra"
                      type="button"
                      class="btn remove"
                      :aria-label="`移除 ${nameOf(row)}`"
                      title="移除"
                      @click="removeExtra(row.id)"
                    >
                      ✕
                    </button>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="adapterTemplates.length" class="add-participant">
            <button v-if="!adding" type="button" class="btn" @click="startAdding">＋ 新增參與者</button>
            <div v-else class="add-row" data-testid="add-participant">
              <select v-model="newAdapter" aria-label="新參與者的 Adapter">
                <option v-for="t in adapterTemplates" :key="t.adapter" :value="t.adapter">{{ t.adapter }}</option>
              </select>
              <ModelSelect
                v-if="newTemplate"
                :key="newTemplate.id"
                v-model:choice="modelPicks[NEW_ID]!.choice"
                v-model:custom="modelPicks[NEW_ID]!.custom"
                label="新參與者的模型"
                :default-model="newTemplate.model"
                :models="newTemplate.models"
                :free-text="newTemplate.free_text_model"
                :error="newTemplate.models_error"
              />
              <span class="add-actions">
                <button type="button" class="btn btn-primary" :disabled="requestedModel(NEW_ID) === ''" @click="addExtra">
                  加入
                </button>
                <button type="button" class="btn" @click="adding = false">取消</button>
              </span>
              <small class="muted add-note">以 {{ newTemplate?.display_name }} 為範本，只在這場討論中存在</small>
            </div>
          </div>

          <p v-if="tooFewParticipants && participants.length > 0" class="hint" data-testid="participants-hint">
            請選擇至少 {{ MIN_PARTICIPANTS }} 個參與者
          </p>
          <p v-if="invalidModel" class="hint" data-testid="models-hint">請輸入模型名稱（1–100 個字元，不能有空白）</p>
        </fieldset>
      </div>

      <!-- Inspector: the rest of this discussion's settings, and start. -->
      <aside class="inspector">
        <section v-if="options && uses.has('judge')" class="inspector-section" data-testid="judge-options">
          <h3 class="inspector-title">共識裁定方式</h3>
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

        <section v-if="options" class="inspector-section">
          <h3 class="inspector-title">討論設定</h3>
          <div class="fields">
            <div v-if="uses.has('moderator_id')" class="field wide">
              <label for="moderator-select">主持人</label>
              <select
                id="moderator-select"
                v-model="moderatorId"
                @change="moderatorPicked = true"
                :disabled="moderatorChoices.length === 0"
              >
                <option v-for="row in moderatorChoices" :key="row.id" :value="row.id">
                  {{ nameOf(row) }}
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

        <section class="inspector-section">
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
  padding: 8px 10px;
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
.participant-cell,
.status-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
}
/* Wide screens: name, model badge and 臨時 on one line (narrower ones may wrap; below
   1280px the unwrapped table overflowed the stage under the inspector, ticket 08). */
@media (min-width: 1280px) {
  .participant-cell,
  .participant-name :deep(.participant-label) {
    flex-wrap: nowrap;
    white-space: nowrap;
  }
}
.reason {
  white-space: normal;
}
.remove {
  padding: 2px 8px;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.remove:hover:not(:disabled) {
  color: var(--bad);
  border-color: var(--bad-line);
}
.add-participant {
  margin-top: var(--space-2);
}
.add-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--panel);
  border: 1px dashed var(--accent-line);
  border-radius: var(--radius-lg);
}
.add-row > select {
  padding: 4px 8px;
  font-size: var(--fs-sm);
}
.add-actions {
  display: inline-flex;
  gap: var(--space-2);
}
.add-note {
  flex-basis: 100%;
  font-size: var(--fs-xs);
}
.hint {
  margin-top: var(--space-2);
  font-size: var(--fs-sm);
  color: var(--bad);
}

/* Inspector column: shared look (styles/inspector.css); titles spaced a little wider here. */
.inspector-title {
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
}
@media (max-width: 640px) {
  .participant-table th:nth-child(2),
  .participant-table td:nth-child(2),
  .participant-table th:nth-child(4),
  .participant-table td:nth-child(4) {
    display: none;
  }
  .participant-table th,
  .participant-table td {
    padding: 6px 8px;
  }
}
</style>
