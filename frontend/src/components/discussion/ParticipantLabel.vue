<!-- A participant's avatar, name, 無上網 pill and model badge (ui-redesign 04). Shared by
     turn cards, stance / confirmation lists, the inspector and the read-only record. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { ParticipantSnapshot } from '../../contracts/messages'
import ParticipantAvatar from './ParticipantAvatar.vue'

const props = defineProps<{
  participant: ParticipantSnapshot | undefined
  /** Shown as the name when the snapshot is missing. */
  id: string
  size?: number
  /** Hide the 無上網 pill (compact lists). */
  hideWeb?: boolean
}>()

const name = computed(() => props.participant?.display_name ?? props.id)
const model = computed(() => props.participant?.model ?? '預設模型')
</script>

<template>
  <span class="participant-label">
    <ParticipantAvatar :avatar="participant?.avatar ?? 'default.png'" :size="size ?? 22" />
    <span class="name">{{ name }}</span>
    <span v-if="!hideWeb && participant && !participant.capabilities.web_access" class="pill pill-warn">無上網</span>
    <span class="pill model" data-testid="participant-model" :title="`模型：${model}`">{{ model }}</span>
  </span>
</template>

<style scoped>
.participant-label {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  min-width: 0;
}
.name {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.model {
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 0 6px;
  opacity: 0.85;
}
</style>
