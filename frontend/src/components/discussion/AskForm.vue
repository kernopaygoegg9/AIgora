<!-- Question input + mode + participant picker. Emits `submit` with the question, the chosen ids and the mode. -->
<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ParticipantInfo } from '../../contracts/http'
import type { ModeId } from '../../contracts/messages'
import ParticipantAvatar from './ParticipantAvatar.vue'

const props = defineProps<{ participants: ParticipantInfo[]; disabled?: boolean }>()
const emit = defineEmits<{ submit: [question: string, participantIds: string[], mode: ModeId] }>()

const question = ref('')
const selected = ref<string[]>([])
const mode = ref<ModeId>('ask')

const canSubmit = computed(() => !props.disabled && question.value.trim() !== '' && selected.value.length > 0)

function submit() {
  if (!canSubmit.value) return
  // Keep the participant file's order, not the click order.
  const ids = props.participants.map((p) => p.id).filter((id) => selected.value.includes(id))
  emit('submit', question.value.trim(), ids, mode.value)
}
</script>

<template>
  <form class="ask-form" data-testid="ask-form" @submit.prevent="submit">
    <label class="question-label" for="question-input">問題</label>
    <textarea
      id="question-input"
      v-model="question"
      class="question-input"
      rows="3"
      placeholder="輸入要問參與者的問題"
      :disabled="disabled"
      @keydown.enter.ctrl.prevent="submit"
    />

    <fieldset class="modes" :disabled="disabled">
      <legend>討論模式</legend>
      <label><input v-model="mode" type="radio" value="ask" /> 提問</label>
      <label><input v-model="mode" type="radio" value="consensus" /> 共識討論</label>
    </fieldset>

    <fieldset class="participants" :disabled="disabled">
      <legend>參與者</legend>
      <p v-if="participants.length === 0" class="muted">沒有可用的參與者（請檢查 participants.toml）</p>
      <label
        v-for="p in participants"
        :key="p.id"
        class="participant-option"
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
    </fieldset>

    <button type="submit" class="submit" :disabled="!canSubmit">送出</button>
  </form>
</template>

<style scoped>
.ask-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 60rem;
}
.question-label {
  font-weight: 600;
}
.question-input {
  font: inherit;
  padding: 0.5rem;
  border: 1px solid #c4cad1;
  border-radius: 6px;
  resize: vertical;
}
.modes {
  display: flex;
  gap: 1rem;
  border: 1px solid #d8dde3;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}
.participants {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  border: 1px solid #d8dde3;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}
.participant-option {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}
.participant-option.unavailable {
  color: #8a9097;
  cursor: not-allowed;
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
.muted {
  color: #6b7280;
  margin: 0;
}
</style>
