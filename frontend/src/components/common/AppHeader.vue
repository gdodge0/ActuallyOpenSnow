<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useResortsStore } from '@/stores/resorts'

const router = useRouter()
const settingsStore = useSettingsStore()
const resortsStore = useResortsStore()

const searchQuery = ref('')
const showSearch = ref(false)
const mobileMenuOpen = ref(false)

// Computed search results
const searchResults = computed(() => {
  if (!searchQuery.value.trim()) return []
  const query = searchQuery.value.toLowerCase()
  return resortsStore.resorts
    .filter(r => r.name.toLowerCase().includes(query) || r.state.toLowerCase().includes(query))
    .slice(0, 5)
})

function selectResult(slug: string) {
  router.push(`/resort/${slug}`)
  searchQuery.value = ''
  showSearch.value = false
}

function toggleUnits() {
  if (settingsStore.temperatureUnit === 'F') {
    settingsStore.setMetric()
  } else {
    settingsStore.setImperial()
  }
}
</script>

<template>
  <header class="bg-mountain-900/80 backdrop-blur-md border-b border-mountain-700/50 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <RouterLink to="/" class="flex items-center gap-3 group">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-snow-400 to-snow-600 flex items-center justify-center shadow-lg shadow-snow-500/20 group-hover:shadow-snow-500/40 transition-shadow">
            <svg class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M19.07 4.93L4.93 19.07"/>
            </svg>
          </div>
          <div class="hidden sm:block">
            <h1 class="text-xl font-display font-bold text-white">ActuallyOpenSnow</h1>
            <p class="text-xs text-mountain-400 -mt-0.5">Mountain Weather</p>
          </div>
        </RouterLink>
        
        <!-- Desktop Navigation -->
        <nav class="hidden md:flex items-center gap-6">
          <RouterLink 
            to="/" 
            class="text-mountain-300 hover:text-white transition-colors font-medium"
            active-class="text-white"
          >
            Home
          </RouterLink>
          <RouterLink 
            to="/favorites" 
            class="text-mountain-300 hover:text-white transition-colors font-medium"
            active-class="text-white"
          >
            Favorites
          </RouterLink>
          <RouterLink 
            to="/custom" 
            class="text-mountain-300 hover:text-white transition-colors font-medium"
            active-class="text-white"
          >
            Custom
          </RouterLink>
          <RouterLink 
            to="/compare" 
            class="text-mountain-300 hover:text-white transition-colors font-medium"
            active-class="text-white"
          >
            Compare
          </RouterLink>
        </nav>
        
        <!-- Right side -->
        <div class="flex items-center gap-3">
          <!-- Search -->
          <div class="relative">
            <button 
              @click="showSearch = !showSearch"
              class="p-2 rounded-lg bg-mountain-800 hover:bg-mountain-700 text-mountain-300 hover:text-white transition-colors"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            </button>
            
            <!-- Search dropdown -->
            <div 
              v-if="showSearch"
              class="absolute right-0 mt-2 w-72 bg-mountain-800 rounded-xl shadow-xl border border-mountain-700 overflow-hidden"
            >
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search resorts..."
                class="w-full px-4 py-3 bg-transparent text-white placeholder-mountain-400 focus:outline-none"
                autofocus
              />
              <div v-if="searchResults.length > 0" class="border-t border-mountain-700">
                <button
                  v-for="resort in searchResults"
                  :key="resort.slug"
                  @click="selectResult(resort.slug)"
                  class="w-full px-4 py-2.5 text-left hover:bg-mountain-700 transition-colors flex items-center justify-between"
                >
                  <span class="text-white">{{ resort.name }}</span>
                  <span class="text-mountain-400 text-sm">{{ resort.state }}</span>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Unit toggle -->
          <button
            @click="toggleUnits"
            class="px-3 py-2 rounded-lg bg-mountain-800 hover:bg-mountain-700 text-mountain-200 font-mono text-sm transition-colors"
          >
            {{ settingsStore.temperatureUnit === 'F' ? '°F / in' : '°C / cm' }}
          </button>
          
          <!-- Settings -->
          <RouterLink 
            to="/settings"
            class="p-2 rounded-lg bg-mountain-800 hover:bg-mountain-700 text-mountain-300 hover:text-white transition-colors"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </RouterLink>
          
          <!-- Mobile menu button -->
          <button 
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="md:hidden p-2 rounded-lg bg-mountain-800 hover:bg-mountain-700 text-mountain-300"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path v-if="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Mobile menu -->
      <div v-if="mobileMenuOpen" class="md:hidden py-4 border-t border-mountain-700">
        <nav class="flex flex-col gap-2">
          <RouterLink to="/" class="px-4 py-2 rounded-lg hover:bg-mountain-800 text-mountain-200" @click="mobileMenuOpen = false">Home</RouterLink>
          <RouterLink to="/favorites" class="px-4 py-2 rounded-lg hover:bg-mountain-800 text-mountain-200" @click="mobileMenuOpen = false">Favorites</RouterLink>
          <RouterLink to="/custom" class="px-4 py-2 rounded-lg hover:bg-mountain-800 text-mountain-200" @click="mobileMenuOpen = false">Custom Locations</RouterLink>
          <RouterLink to="/compare" class="px-4 py-2 rounded-lg hover:bg-mountain-800 text-mountain-200" @click="mobileMenuOpen = false">Compare</RouterLink>
        </nav>
      </div>
    </div>
  </header>
</template>

