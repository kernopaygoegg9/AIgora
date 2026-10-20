<!-- Main layout. HOT FILE (owner: ticket 01; ticket 17 may swap in final assets). -->

<template>
  <div class="app-layout">
    <header class="app-header">
      <!-- App icon from assets/brand (Vite publicDir; served at the site root). -->
      <img class="app-logo" data-testid="app-logo" src="/app-icon.png" alt="" width="28" height="28" />
      <span class="app-title">AIgora</span>
      <nav class="app-nav">
        <RouterLink :to="{ name: 'discussion' }">討論</RouterLink>
        <RouterLink :to="{ name: 'history' }">歷史</RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style>
:root {
  font-family: system-ui, -apple-system, 'Segoe UI', 'Noto Sans TC', sans-serif;
  color: #1f2328;
  background: #f6f7f9;
}
body {
  margin: 0;
}
</style>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #ffffff;
  border-bottom: 1px solid #d8dde3;
}
.app-title {
  font-weight: 600;
  font-size: 1.1rem;
}
.app-nav {
  display: flex;
  gap: 1rem;
  margin-left: 2rem;
}
.app-nav a {
  color: inherit;
  text-decoration: none;
}
.app-nav a.router-link-exact-active {
  font-weight: 600;
  text-decoration: underline;
}
.app-main {
  flex: 1;
  padding: 1rem;
}
</style>
