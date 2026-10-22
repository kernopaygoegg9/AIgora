<script setup lang="ts">
import { ref } from 'vue'

import { avatarUrl } from '../../contracts/http'

defineProps<{ avatar: string; size?: number }>()
const missing = ref(false)
</script>

<template>
  <img
    v-if="!missing"
    class="avatar"
    :src="avatarUrl(avatar)"
    alt=""
    :width="size ?? 32"
    :height="size ?? 32"
    @error="missing = true"
  />
  <span
    v-else
    class="avatar avatar-missing"
    :style="{ width: `${size ?? 32}px`, height: `${size ?? 32}px` }"
  />
</template>

<style scoped>
.avatar {
  border-radius: 50%;
  flex-shrink: 0;
  object-fit: cover;
}
.avatar-missing {
  display: inline-block;
  background: var(--line);
}
</style>
