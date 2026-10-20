<!-- The end of a consensus discussion, shown on its own: the consensus result, or the
     moderator's final positions and remaining disagreements, or (ticket 07) why it ended
     with too few participants. Ask results are the turns themselves, so nothing extra is
     shown for them. -->
<script setup lang="ts">
import { computed } from 'vue'

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
</script>

<template>
  <section
    v-if="title"
    class="discussion-result"
    :class="`kind-${kind}`"
    data-testid="discussion-result"
    :data-outcome="outcome"
  >
    <h2 class="result-title">{{ title }}</h2>
    <p v-if="reason" class="reason">{{ reason }}</p>
    <template v-if="result">
      <!-- eslint-disable-next-line vue/no-v-html -- sanitised in renderMarkdown -->
      <div v-if="result.text" class="text" v-html="renderMarkdown(result.text)" />
      <p v-else class="reason">（沒有內容）</p>
    </template>
  </section>
</template>

<style scoped>
.discussion-result {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.9rem 1rem;
  border-radius: 10px;
  border: 2px solid #9fd3ae;
  background: #f0faf3;
}
.discussion-result.kind-insufficient_participants {
  border-color: #e5a29a;
  background: #fdeeec;
}
.discussion-result.kind-no_consensus {
  border-color: #e8c27a;
  background: #fff8ea;
}
.result-title {
  font-size: 1.05rem;
  margin: 0;
}
.reason {
  margin: 0;
  font-size: 0.9rem;
  color: #4a5159;
}
.text {
  overflow-wrap: anywhere;
  line-height: 1.6;
}
.text :deep(p) {
  margin: 0 0 0.5rem;
}
</style>
