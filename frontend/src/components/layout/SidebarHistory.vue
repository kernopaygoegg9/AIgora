<!-- 最近的討論 in the sidebar: the newest discussions, each opening its read-only record.
     Reloaded when a discussion starts (its record now exists) and when it finishes. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchDiscussions } from '../../api/discussions'
import type { DiscussionSummary } from '../../contracts/http'
import { useDiscussionStore } from '../../stores/discussion'
import { MODE_LABELS, formatTime, outcomeLabel } from '../history/labels'

const LIMIT = 20

const store = useDiscussionStore()
const route = useRoute()
const discussions = ref<DiscussionSummary[]>([])
const loadError = ref<string | null>(null)

async function load() {
  try {
    discussions.value = (await fetchDiscussions()).slice(0, LIMIT)
    loadError.value = null
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
watch(
  () => store.status,
  (status) => {
    if (status === 'running' || status === 'finished') load()
  },
)

// The record being viewed, or the live discussion while the discussion page shows it.
const currentId = computed(() => {
  if (route.name === 'discussion-record') return String(route.params.id)
  if (route.name === 'discussion') return store.discussionId
  return null
})

function outcomeClass(d: DiscussionSummary): string {
  switch (d.outcome) {
    case null:
      return 'running'
    case 'consensus':
      return 'ok'
    case 'no_consensus':
      return 'warn'
    case 'completed':
      return ''
    default:
      return 'bad'
  }
}
</script>

<template>
  <nav class="sidebar-history" aria-label="最近的討論" data-testid="sidebar-history">
    <h2 class="label">最近的討論</h2>
    <p v-if="loadError" class="empty">{{ loadError }}</p>
    <p v-else-if="!discussions.length" class="empty">還沒有任何討論</p>
    <ul v-else class="list">
      <li v-for="d in discussions" :key="d.id">
        <RouterLink
          class="item"
          :class="{ current: d.id === currentId }"
          :to="{ name: 'discussion-record', params: { id: d.id } }"
          :title="d.question"
          data-testid="sidebar-history-item"
        >
          <span class="question">{{ d.question }}</span>
          <span class="meta">
            <span>{{ MODE_LABELS[d.mode] ?? d.mode }}</span>
            <time :datetime="d.created_at">{{ formatTime(d.created_at) }}</time>
            <span class="outcome" :class="outcomeClass(d)">{{ outcomeLabel(d.outcome) }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
    <RouterLink class="all" :to="{ name: 'history' }">查看全部 →</RouterLink>
  </nav>
</template>

<style scoped>
.sidebar-history {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}
.label {
  padding: var(--space-3) 14px 6px;
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0 6px;
  overflow-y: auto;
  min-height: 0;
}
.item {
  display: block;
  padding: 7px 8px;
  border-radius: var(--radius-sm);
  color: var(--text);
  text-decoration: none;
}
.item:hover,
.item.current {
  background: var(--panel-2);
}
.item.current {
  box-shadow: inset 2px 0 0 var(--accent);
}
.question {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 6px;
  margin-top: 2px;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.outcome.running {
  color: var(--accent);
}
.outcome.ok {
  color: var(--ok);
}
.outcome.warn {
  color: var(--warn);
}
.outcome.bad {
  color: var(--bad);
}
.empty {
  padding: 4px 14px;
  font-size: var(--fs-sm);
  color: var(--muted);
}
.all {
  margin: 6px 14px 0;
  font-size: var(--fs-sm);
  color: var(--muted);
  text-decoration: none;
}
.all:hover {
  color: var(--accent);
}
</style>
