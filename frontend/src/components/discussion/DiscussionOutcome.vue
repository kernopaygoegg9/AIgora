<!-- The end of a consensus discussion, shown at the top of the stage: the consensus result,
     or the moderator's final positions and remaining disagreements, or (ticket 07) why it
     ended with too few participants; also the note when the user stopped it. Ask results
     are the turns themselves, so nothing extra is shown for them. -->
<script setup lang="ts">
import { computed } from 'vue'

import '../../styles/discussion.css'

import type { DiscussionResult, Outcome } from '../../contracts/messages'
import { renderMarkdown } from './markdown'

const props = defineProps<{
  outcome: Outcome | null
  result: DiscussionResult | null
  reason: string | null
}>()

const title = computed(() => {
  if (props.result?.kind === 'consensus') return '共識結果'
  if (props.result?.kind === 'no_consensus') return '未取得共識：各參與者最終立場與仍有分歧的重點'
  if (props.outcome === 'insufficient_participants') return '討論結束：在場參與者不足'
  return null
})
const kind = computed(() => props.result?.kind ?? props.outcome)
const tone = computed(() => {
  if (kind.value === 'no_consensus') return 'is-warn'
  if (kind.value === 'insufficient_participants') return 'is-bad'
  return ''
})
</script>

<template>
  <section
    v-if="title"
    class="discussion-result d-result"
    :class="[`kind-${kind}`, tone]"
    data-testid="discussion-result"
    :data-outcome="outcome"
  >
    <h2 class="d-result-title">
      <span v-if="kind === 'consensus'" aria-hidden="true">✓ </span>{{ title }}
    </h2>
    <p v-if="reason" class="d-result-reason">{{ reason }}</p>
    <template v-if="result">
      <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
      <div v-if="result.text" class="d-md" v-html="renderMarkdown(result.text)" />
      <p v-else class="d-result-reason">（沒有內容）</p>
    </template>
  </section>
  <p v-if="outcome === 'stopped'" class="d-result is-bad stopped" data-testid="discussion-stopped">
    討論已停止：進行中的發言已取消，目前的內容已存檔。
  </p>
</template>

<style scoped>
.stopped {
  margin: 0;
  color: var(--bad);
}
</style>
