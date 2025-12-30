<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useResortsStore } from '@/stores/resorts'

const resortsStore = useResortsStore()
const expandedStates = ref<Set<string>>(new Set())

// Group resorts by state
const statesWithResorts = computed(() => {
  const states = Array.from(resortsStore.resortsByState.entries())
    .sort(([a], [b]) => a.localeCompare(b))
  return states
})

function toggleState(state: string) {
  if (expandedStates.value.has(state)) {
    expandedStates.value.delete(state)
  } else {
    expandedStates.value.add(state)
  }
}
</script>

<template>
  <aside class="w-64 bg-mountain-900/50 border-r border-mountain-700/50 overflow-y-auto scrollbar-thin flex-shrink-0">
    <div class="p-4">
      <!-- Favorites section -->
      <div v-if="resortsStore.favoriteResorts.length > 0" class="mb-6">
        <h3 class="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-mountain-400 uppercase tracking-wider">
          <svg class="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
          </svg>
          Favorites
        </h3>
        <nav class="space-y-1">
          <RouterLink
            v-for="resort in resortsStore.favoriteResorts"
            :key="resort.slug"
            :to="`/resort/${resort.slug}`"
            class="block px-3 py-2 rounded-lg text-mountain-200 hover:bg-mountain-800 hover:text-white transition-colors"
          >
            {{ resort.name }}
          </RouterLink>
        </nav>
      </div>
      
      <!-- All resorts by state -->
      <div>
        <h3 class="px-3 py-2 text-xs font-semibold text-mountain-400 uppercase tracking-wider">
          All Resorts
        </h3>
        
        <div class="space-y-1">
          <div v-for="[state, resorts] in statesWithResorts" :key="state">
            <button
              @click="toggleState(state)"
              class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-mountain-300 hover:bg-mountain-800 hover:text-white transition-colors"
            >
              <span class="flex items-center gap-2">
                <span class="text-sm font-medium">{{ state }}</span>
                <span class="text-xs text-mountain-500">({{ resorts.length }})</span>
              </span>
              <svg 
                class="w-4 h-4 transition-transform" 
                :class="{ 'rotate-180': expandedStates.has(state) }"
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            
            <!-- Expanded resorts -->
            <div v-if="expandedStates.has(state)" class="ml-4 mt-1 space-y-1">
              <RouterLink
                v-for="resort in resorts"
                :key="resort.slug"
                :to="`/resort/${resort.slug}`"
                class="block px-3 py-1.5 rounded-lg text-sm text-mountain-300 hover:bg-mountain-800 hover:text-white transition-colors"
              >
                {{ resort.name }}
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

