<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchDiscussions } from '../api/discussions'
import { MODE_LABELS, formatTime, outcomeLabel } from '../components/history/labels'
import type { DiscussionSummary } from '../contracts/http'

const discussions = ref<DiscussionSummary[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)

onMounted(async () => {
  try {
    discussions.value = await fetchDiscussions()
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="history-page" data-testid="history-page">
    <h1 class="page-title">歷史</h1>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">載入中…</p>
    <p v-else-if="!discussions.length" class="muted" data-testid="history-empty">還沒有任何討論</p>
    <ul v-else class="history-list">
      <li v-for="d in discussions" :key="d.id" class="history-item" data-testid="history-item">
        <RouterLink class="history-link" :to="{ name: 'discussion-record', params: { id: d.id } }">
          <span class="history-question">{{ d.question }}</span>
          <span class="history-meta">
            <span>{{ MODE_LABELS[d.mode] ?? d.mode }}</span>
            <time :datetime="d.created_at">{{ formatTime(d.created_at) }}</time>
            <span class="history-outcome" :class="{ running: !d.outcome }" data-testid="history-outcome">{{
              outcomeLabel(d.outcome)
            }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.page-title {
  font-size: 1.25rem;
  margin: 0;
}
.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.history-link {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 8px;
  color: inherit;
  text-decoration: none;
}
.history-link:hover {
  border-color: #2f6feb;
}
.history-question {
  font-weight: 600;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: #6b7280;
}
.history-outcome.running {
  color: #2f6feb;
}
.muted {
  color: #6b7280;
  margin: 0;
}
.error {
  color: #a1260d;
  margin: 0;
}
</style>
