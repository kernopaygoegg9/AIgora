import { createApp } from 'vue'
import { createPinia } from 'pinia'

import './styles/tokens.css'
import './styles/base.css'

import App from './App.vue'
import { router } from './router'
import { useTheme } from './composables/useTheme'

// Applies the stored theme (index.html already did; this keeps the state in sync).
useTheme()

createApp(App).use(createPinia()).use(router).mount('#app')

const ciAcceptanceUnused = 1
