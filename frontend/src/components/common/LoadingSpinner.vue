<script setup lang="ts">
defineProps<{
  size?: 'sm' | 'md' | 'lg'
  text?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-4">
    <div 
      class="animate-spin rounded-full border-t-2 border-b-2 border-snow-400"
      :class="{
        'w-6 h-6': size === 'sm',
        'w-10 h-10': size === 'md' || !size,
        'w-16 h-16': size === 'lg',
      }"
    />
    <p v-if="text" class="text-mountain-400 text-sm">{{ text }}</p>
  </div>
</template>

