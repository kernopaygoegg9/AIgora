<script setup lang="ts">
// `id` is set when viewing a past discussion read-only (route `discussion-record`).
defineProps<{ id?: string }>()
</script>

<template>
  <section data-testid="discussion-page">
    <h1>討論</h1>
  </section>
</template>
