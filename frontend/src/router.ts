// Frontend routes. HOT FILE (owner: ticket 01): other tickets must not edit it.
import { createRouter, createWebHistory } from 'vue-router'

import DiscussionPage from './pages/DiscussionPage.vue'
import HistoryPage from './pages/HistoryPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'discussion', component: DiscussionPage },
    // Read-only view of a past discussion (ticket 09).
    { path: '/discussions/:id', name: 'discussion-record', component: DiscussionPage, props: true },
    { path: '/history', name: 'history', component: HistoryPage },
  ],
})
