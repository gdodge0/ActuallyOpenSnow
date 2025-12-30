/**
 * Resorts store for ski resort data.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Resort } from '@/types'
import { fetchResorts } from '@/utils/api'

const FAVORITES_KEY = 'actuallyopensnow-favorites'

function loadFavorites(): string[] {
  if (typeof localStorage === 'undefined') return []
  try {
    const stored = localStorage.getItem(FAVORITES_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch {
    // Ignore localStorage errors
  }
  return []
}

function saveFavorites(favorites: string[]) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites))
}

export const useResortsStore = defineStore('resorts', () => {
  const resorts = ref<Resort[]>([])
  const favorites = ref<string[]>(loadFavorites())
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Computed: favorite resorts
  const favoriteResorts = computed(() => {
    return resorts.value.filter(r => favorites.value.includes(r.slug))
  })
  
  // Computed: resorts grouped by state
  const resortsByState = computed(() => {
    const grouped = new Map<string, Resort[]>()
    for (const resort of resorts.value) {
      const state = resort.state
      if (!grouped.has(state)) {
        grouped.set(state, [])
      }
      grouped.get(state)!.push(resort)
    }
    return grouped
  })
  
  // Computed: unique states
  const states = computed(() => {
    const stateSet = new Set(resorts.value.map(r => r.state))
    return Array.from(stateSet).sort()
  })
  
  // Load resorts from API
  async function loadResorts() {
    if (resorts.value.length > 0) return // Already loaded
    
    loading.value = true
    error.value = null
    
    try {
      resorts.value = await fetchResorts()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load resorts'
      console.error('Failed to load resorts:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Get resort by slug
  function getResortBySlug(slug: string): Resort | undefined {
    return resorts.value.find(r => r.slug === slug)
  }
  
  // Favorite management
  function isFavorite(slug: string): boolean {
    return favorites.value.includes(slug)
  }
  
  function addFavorite(slug: string) {
    if (!favorites.value.includes(slug)) {
      favorites.value.push(slug)
      saveFavorites(favorites.value)
    }
  }
  
  function removeFavorite(slug: string) {
    const idx = favorites.value.indexOf(slug)
    if (idx !== -1) {
      favorites.value.splice(idx, 1)
      saveFavorites(favorites.value)
    }
  }
  
  function toggleFavorite(slug: string) {
    if (isFavorite(slug)) {
      removeFavorite(slug)
    } else {
      addFavorite(slug)
    }
  }
  
  return {
    resorts,
    favorites,
    favoriteResorts,
    resortsByState,
    states,
    loading,
    error,
    loadResorts,
    getResortBySlug,
    isFavorite,
    addFavorite,
    removeFavorite,
    toggleFavorite,
  }
})

