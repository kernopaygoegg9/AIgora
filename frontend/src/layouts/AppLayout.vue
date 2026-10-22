<!-- Main layout: sidebar (brand, nav, recent discussions, theme) + main area.
     Pages lay out their own stage + inspector inside <main>.
     HOT FILE (owner: ui-redesign ticket 02). -->
<script setup lang="ts">
import { useRoute } from 'vue-router'

import SidebarHistory from '../components/layout/SidebarHistory.vue'
import ThemeToggle from '../components/layout/ThemeToggle.vue'
import { useDiscussionStore } from '../stores/discussion'

const route = useRoute()
const store = useDiscussionStore()

// 「討論」 on the discussion page after a discussion ended: back to the settings for a new
// one. A running discussion is never reset; navigating to it just shows it.
function onDiscussionLink() {
  if (route.name === 'discussion' && store.status === 'finished') store.reset()
}
</script>

<template>
  <div class="app-layout">
    <div class="sidebar">
      <header class="brand-block">
        <div class="brand">
          <!-- App icon from assets/brand (Vite publicDir; served at the site root). -->
          <img
            class="app-logo"
            data-testid="app-logo"
            src="/app-icon.png"
            alt=""
            width="24"
            height="24"
          />
          <span class="app-title">AIgora</span>
        </div>
        <nav class="app-nav" aria-label="主要">
          <RouterLink
            class="nav-link nav-primary"
            :to="{ name: 'discussion' }"
            @click="onDiscussionLink"
          >
            <span class="plus" aria-hidden="true">＋</span>討論
          </RouterLink>
          <RouterLink class="nav-link" :to="{ name: 'history' }">歷史</RouterLink>
        </nav>
      </header>
      <SidebarHistory class="history" />
      <div class="sidebar-foot">
        <ThemeToggle />
      </div>
    </div>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-right: 1px solid var(--line);
  min-width: 0;
}
.brand-block {
  padding: 14px 12px 4px;
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 2px 12px;
}
.app-title {
  font-weight: 700;
  font-size: var(--fs-md);
  letter-spacing: 0.02em;
}
.app-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 7px 10px;
  border-radius: var(--radius);
  color: var(--muted);
  text-decoration: none;
}
.nav-link:hover {
  color: var(--text);
  background: var(--panel-2);
}
.nav-link.router-link-exact-active {
  color: var(--text);
  font-weight: 600;
}
.nav-primary {
  margin-bottom: 4px;
  border: 1px solid var(--line);
  background: var(--panel-2);
  color: var(--text);
}
.nav-primary:hover {
  border-color: var(--accent);
}
.nav-primary.router-link-exact-active {
  border-color: var(--accent-line);
  background: var(--accent-bg);
}
.plus {
  color: var(--accent);
}
.history {
  margin-top: 6px;
}
.sidebar-foot {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--line);
}
.app-main {
  min-width: 0;
  padding: var(--space-4) var(--space-5) var(--space-5);
}

/* Narrow screens: the sidebar becomes a top bar (no recent list). */
@media (max-width: 759px) {
  .app-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .sidebar {
    position: static;
    height: auto;
    flex-direction: row;
    align-items: center;
    gap: var(--space-2);
    padding: 0 var(--space-3);
    border-right: none;
    border-bottom: 1px solid var(--line);
  }
  .brand-block {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: 8px 0;
    flex: 1;
    min-width: 0;
  }
  .brand {
    padding: 0;
  }
  .app-nav {
    flex-direction: row;
  }
  .nav-primary {
    margin-bottom: 0;
  }
  .history {
    display: none;
  }
  .sidebar-foot {
    padding: 0;
    border-top: none;
  }
  .app-main {
    padding: var(--space-3) var(--space-4) var(--space-5);
  }
}
</style>
