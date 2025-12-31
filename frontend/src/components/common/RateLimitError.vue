<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  retryAfterSeconds?: number
}>()

const emit = defineEmits<{
  retry: []
}>()

// Countdown timer
const countdown = ref(props.retryAfterSeconds ?? 60)
let intervalId: number | undefined

onMounted(() => {
  if (countdown.value > 0) {
    intervalId = window.setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(intervalId)
      }
    }, 1000)
  }
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <div class="rounded-xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/30 p-8">
    <div class="flex flex-col items-center text-center gap-6">
      <!-- Animated hourglass icon -->
      <div class="relative">
        <div class="w-20 h-20 rounded-full bg-amber-500/20 flex items-center justify-center">
          <svg class="w-10 h-10 text-amber-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <!-- Decorative ring -->
        <div class="absolute inset-0 rounded-full border-2 border-amber-500/20 animate-ping"></div>
      </div>
      
      <!-- Title -->
      <div>
        <h3 class="text-xl font-display font-bold text-amber-300">
          Slow Down There, Powder Chaser! ❄️
        </h3>
        <p class="text-amber-200/70 mt-2 max-w-md">
          You're checking forecasts faster than fresh tracks disappear on a powder day. 
          Take a breather and try again in a moment.
        </p>
      </div>
      
      <!-- Rate limit explanation -->
      <div class="bg-mountain-900/50 rounded-lg p-4 text-sm text-mountain-300 max-w-md">
        <p class="flex items-center gap-2">
          <svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>
            Custom locations are limited to <strong class="text-white">10 requests per minute</strong> 
            to keep the snow reports flowing for everyone.
          </span>
        </p>
      </div>
      
      <!-- Countdown and retry -->
      <div class="flex flex-col items-center gap-3">
        <div v-if="countdown > 0" class="text-mountain-400 text-sm">
          Ready to try again in 
          <span class="font-mono text-amber-300 font-semibold">{{ countdown }}s</span>
        </div>
        
        <button 
          @click="handleRetry"
          :disabled="countdown > 0"
          class="px-6 py-3 rounded-lg font-medium transition-all duration-200"
          :class="countdown > 0 
            ? 'bg-mountain-800 text-mountain-500 cursor-not-allowed' 
            : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 hover:text-amber-200'"
        >
          <span v-if="countdown > 0" class="flex items-center gap-2">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Waiting...
          </span>
          <span v-else class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Try Again
          </span>
        </button>
      </div>
      
      <!-- Tips -->
      <div class="text-xs text-mountain-500 mt-2">
        💡 Tip: Resort forecasts have higher limits — check your favorite mountains instead!
      </div>
    </div>
  </div>
</template>

