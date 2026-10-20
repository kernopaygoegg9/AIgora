<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchDiscussions } from '../api/discussions'
import { MODE_LABELS, formatTime, outcomeLabel } from '../components/history/labels'
import type { DiscussionSummary } from '../contracts/http'

const router = useRouter()
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

// Result pill colour per outcome (null = still in progress).
function outcomePill(d: DiscussionSummary): string {
  switch (d.outcome) {
    case null:
      return 'pill-accent'
    case 'consensus':
      return 'pill-ok'
    case 'no_consensus':
      return 'pill-warn'
    case 'completed':
      return ''
    default:
      return 'pill-bad'
  }
}

// The whole row opens the record; the question itself is the real link.
function open(d: DiscussionSummary) {
  router.push({ name: 'discussion-record', params: { id: d.id } })
}
</script>

<template>
  <section class="history-page" data-testid="history-page">
    <header class="topbar">
      <h1 class="page-title">歷史</h1>
      <span v-if="!loading && !loadError" class="pill">{{ discussions.length }} 場討論</span>
    </header>

    <p v-if="loadError" class="state error">{{ loadError }}</p>
    <p v-else-if="loading" class="state muted">載入中…</p>
    <p v-else-if="!discussions.length" class="state muted" data-testid="history-empty">還沒有任何討論</p>
    <table v-else class="history-table">
      <thead>
        <tr>
          <th scope="col">問題</th>
          <th scope="col">討論模式</th>
          <th scope="col">開始時間</th>
          <th scope="col">結果</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in discussions" :key="d.id" class="history-item" data-testid="history-item" @click="open(d)">
          <td class="question-cell">
            <RouterLink class="history-link" :to="{ name: 'discussion-record', params: { id: d.id } }" @click.stop>
              {{ d.question }}
            </RouterLink>
          </td>
          <td class="muted nowrap">{{ MODE_LABELS[d.mode] ?? d.mode }}</td>
          <td class="muted nowrap">
            <time :datetime="d.created_at">{{ formatTime(d.created_at) }}</time>
          </td>
          <td>
            <span class="pill" :class="outcomePill(d)" data-testid="history-outcome">{{ outcomeLabel(d.outcome) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.page-title {
  font-size: var(--fs-lg);
  font-weight: 600;
}
.state {
  padding: var(--space-4) 0;
}
.error {
  color: var(--bad);
}
.history-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.history-table th,
.history-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}
.history-table tbody tr:last-child td {
  border-bottom: none;
}
.history-table th {
  font-weight: normal;
  font-size: var(--fs-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  background: var(--panel-2);
}
.history-item {
  cursor: pointer;
}
.history-item:hover td {
  background: var(--panel-2);
}
.question-cell {
  width: 100%;
}
.history-link {
  color: var(--text);
  text-decoration: none;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.history-item:hover .history-link {
  color: var(--accent);
}
.nowrap {
  white-space: nowrap;
}

/* Narrow screens: drop the mode column, let the time wrap. */
@media (max-width: 640px) {
  .history-table th:nth-child(2),
  .history-table td:nth-child(2) {
    display: none;
  }
  .nowrap {
    white-space: normal;
  }
}
</style>
