<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useResortsStore } from '@/stores/resorts'

const resortsStore = useResortsStore()
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-display font-bold text-white">Your Favorites</h1>
    
    <div v-if="resortsStore.favoriteResorts.length === 0" class="text-center py-16">
      <div class="text-5xl mb-4">⭐</div>
      <h2 class="text-xl font-display font-semibold text-white mb-2">No favorites yet</h2>
      <p class="text-mountain-400 mb-6">
        Add resorts to your favorites for quick access to their forecasts.
      </p>
      <RouterLink to="/" class="btn-primary">
        Browse Resorts
      </RouterLink>
    </div>
    
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <RouterLink
        v-for="resort in resortsStore.favoriteResorts"
        :key="resort.slug"
        :to="`/resort/${resort.slug}`"
        class="glass-card p-5 hover:bg-mountain-800/60 transition-all group"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-display font-semibold text-white group-hover:text-snow-400 transition-colors">
              {{ resort.name }}
            </h3>
            <p class="text-mountain-400 text-sm">{{ resort.state }}, {{ resort.country }}</p>
          </div>
          <button
            @click.prevent="resortsStore.removeFavorite(resort.slug)"
            class="p-1.5 rounded-lg hover:bg-mountain-700 text-yellow-400"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
            </svg>
          </button>
        </div>
        
        <div class="mt-3 flex items-center gap-4 text-sm text-mountain-400">
          <span>{{ Math.round(resort.summit_elevation_m * 3.281) }}' summit</span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

