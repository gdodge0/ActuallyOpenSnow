/**
 * Store for user-defined custom locations.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CustomLocation } from '@/types'

const STORAGE_KEY = 'actuallyopensnow:custom-locations'

export const useCustomLocationsStore = defineStore('customLocations', () => {
  // State
  const locations = ref<CustomLocation[]>([])

  // Load from localStorage on init
  function loadFromStorage() {
    if (typeof window === 'undefined') return
    
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        locations.value = JSON.parse(stored)
      }
    } catch (e) {
      console.error('Failed to load custom locations:', e)
    }
  }

  // Save to localStorage
  function saveToStorage() {
    if (typeof window === 'undefined') return
    
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(locations.value))
    } catch (e) {
      console.error('Failed to save custom locations:', e)
    }
  }

  // Generate unique ID
  function generateId(): string {
    return `loc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // Add a new custom location
  function addLocation(name: string, lat: number, lon: number, elevation_m?: number): CustomLocation {
    const location: CustomLocation = {
      id: generateId(),
      name: name.trim(),
      lat: Math.round(lat * 10000) / 10000,  // Round to 4 decimal places
      lon: Math.round(lon * 10000) / 10000,
      elevation_m: elevation_m ? Math.round(elevation_m) : undefined,
      createdAt: Date.now(),
    }
    
    locations.value.push(location)
    saveToStorage()
    
    return location
  }

  // Update an existing location
  function updateLocation(id: string, updates: Partial<Omit<CustomLocation, 'id' | 'createdAt'>>) {
    const index = locations.value.findIndex(l => l.id === id)
    if (index !== -1) {
      locations.value[index] = {
        ...locations.value[index],
        ...updates,
        lat: updates.lat !== undefined ? Math.round(updates.lat * 10000) / 10000 : locations.value[index].lat,
        lon: updates.lon !== undefined ? Math.round(updates.lon * 10000) / 10000 : locations.value[index].lon,
      }
      saveToStorage()
    }
  }

  // Remove a location
  function removeLocation(id: string) {
    const index = locations.value.findIndex(l => l.id === id)
    if (index !== -1) {
      locations.value.splice(index, 1)
      saveToStorage()
    }
  }

  // Get location by ID
  function getLocationById(id: string): CustomLocation | undefined {
    return locations.value.find(l => l.id === id)
  }

  // Computed: sorted by name
  const sortedLocations = computed(() => {
    return [...locations.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  // Initialize
  loadFromStorage()

  return {
    // State
    locations,
    
    // Computed
    sortedLocations,
    
    // Actions
    addLocation,
    updateLocation,
    removeLocation,
    getLocationById,
    loadFromStorage,
  }
})

