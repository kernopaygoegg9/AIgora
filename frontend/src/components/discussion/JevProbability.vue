<!-- Jev's probability that consensus is reached: the number, the threshold and a bar with a
     tick at the threshold. Shared by the live round (RoundConsensus) and the record (RecordRound);
     each passes its own class / testid on the root. -->
<script setup lang="ts">
import '../../styles/discussion.css'

defineProps<{ probability: number; threshold: number | null }>()

const pct = (v: number) => `${Math.min(Math.max(v, 0), 1) * 100}%`
</script>

<template>
  <div>
    <p class="prob-text">
      已取得共識的機率 <strong>{{ probability.toFixed(2) }}</strong>
      <template v-if="threshold != null">（門檻 {{ threshold }}）</template>
    </p>
    <div class="d-bar" aria-hidden="true">
      <i class="d-bar-fill" :class="{ 'is-over': threshold != null && probability >= threshold }" :style="{ width: pct(probability) }" />
      <i v-if="threshold != null" class="d-bar-tick" :style="{ left: pct(threshold) }" />
    </div>
  </div>
</template>

<style scoped>
.prob-text {
  margin: 0;
}
</style>
