<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useCustomLocationsStore } from '@/stores/customLocations'
import { useSettingsStore } from '@/stores/settings'
import { convertElevation, formatElevation } from '@/utils/units'

const router = useRouter()
const customLocationsStore = useCustomLocationsStore()
const settingsStore = useSettingsStore()

// Form state
const showForm = ref(false)
const editingId = ref<string | null>(null)
const formName = ref('')
const formLat = ref('')
const formLon = ref('')
const formElevation = ref('')
const formError = ref('')

// Reset form
function resetForm() {
  formName.value = ''
  formLat.value = ''
  formLon.value = ''
  formElevation.value = ''
  formError.value = ''
  editingId.value = null
}

// Open form for new location
function openNewForm() {
  resetForm()
  showForm.value = true
}

// Open form for editing
function openEditForm(id: string) {
  const location = customLocationsStore.getLocationById(id)
  if (!location) return
  
  editingId.value = id
  formName.value = location.name
  formLat.value = location.lat.toString()
  formLon.value = location.lon.toString()
  formElevation.value = location.elevation_m?.toString() ?? ''
  formError.value = ''
  showForm.value = true
}

// Cancel form
function cancelForm() {
  showForm.value = false
  resetForm()
}

// Validate and save
function saveLocation() {
  formError.value = ''
  
  // Validate name
  if (!formName.value.trim()) {
    formError.value = 'Please enter a name for this location'
    return
  }
  
  // Validate latitude
  const lat = parseFloat(formLat.value)
  if (isNaN(lat) || lat < -90 || lat > 90) {
    formError.value = 'Latitude must be between -90 and 90'
    return
  }
  
  // Validate longitude
  const lon = parseFloat(formLon.value)
  if (isNaN(lon) || lon < -180 || lon > 180) {
    formError.value = 'Longitude must be between -180 and 180'
    return
  }
  
  // Validate elevation (optional)
  let elevation: number | undefined
  if (formElevation.value.trim()) {
    elevation = parseFloat(formElevation.value)
    if (isNaN(elevation) || elevation < 0 || elevation > 9000) {
      formError.value = 'Elevation must be between 0 and 9000 meters'
      return
    }
  }
  
  if (editingId.value) {
    // Update existing
    customLocationsStore.updateLocation(editingId.value, {
      name: formName.value.trim(),
      lat,
      lon,
      elevation_m: elevation,
    })
  } else {
    // Create new
    const location = customLocationsStore.addLocation(
      formName.value.trim(),
      lat,
      lon,
      elevation
    )
    // Navigate to the new location
    router.push(`/custom/${location.id}`)
  }
  
  showForm.value = false
  resetForm()
}

// Delete location
function deleteLocation(id: string) {
  if (confirm('Are you sure you want to delete this location?')) {
    customLocationsStore.removeLocation(id)
  }
}

// Format elevation for display
function formatLocationElevation(elevation_m?: number): string {
  if (!elevation_m) return '--'
  return formatElevation(
    convertElevation(elevation_m, 'm', settingsStore.elevationUnit),
    settingsStore.elevationUnit
  )
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-display font-bold text-white">Custom Locations</h1>
        <p class="text-mountain-400 mt-1">
          Add your own coordinates to get forecasts for any location
        </p>
      </div>
      
      <button
        @click="openNewForm"
        class="btn-primary inline-flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Add Location
      </button>
    </div>
    
    <!-- Add/Edit Form Modal -->
    <div v-if="showForm" class="glass-card p-6">
      <h2 class="text-xl font-display font-semibold text-white mb-4">
        {{ editingId ? 'Edit Location' : 'Add Custom Location' }}
      </h2>
      
      <form @submit.prevent="saveLocation" class="space-y-4">
        <!-- Name -->
        <div>
          <label class="block text-sm font-medium text-mountain-300 mb-1">
            Location Name *
          </label>
          <input
            v-model="formName"
            type="text"
            placeholder="e.g., My Backcountry Spot"
            class="w-full px-4 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white placeholder-mountain-500 focus:outline-none focus:ring-2 focus:ring-snow-500"
          />
        </div>
        
        <!-- Coordinates -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-mountain-300 mb-1">
              Latitude * (-90 to 90)
            </label>
            <input
              v-model="formLat"
              type="text"
              placeholder="e.g., 40.5884"
              class="w-full px-4 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white placeholder-mountain-500 focus:outline-none focus:ring-2 focus:ring-snow-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-mountain-300 mb-1">
              Longitude * (-180 to 180)
            </label>
            <input
              v-model="formLon"
              type="text"
              placeholder="e.g., -111.6387"
              class="w-full px-4 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white placeholder-mountain-500 focus:outline-none focus:ring-2 focus:ring-snow-500"
            />
          </div>
        </div>
        
        <!-- Elevation (optional) -->
        <div>
          <label class="block text-sm font-medium text-mountain-300 mb-1">
            Elevation (meters, optional)
          </label>
          <input
            v-model="formElevation"
            type="text"
            placeholder="e.g., 3000"
            class="w-full sm:w-1/2 px-4 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white placeholder-mountain-500 focus:outline-none focus:ring-2 focus:ring-snow-500"
          />
          <p class="text-mountain-500 text-xs mt-1">
            If not specified, elevation will be determined from terrain data
          </p>
        </div>
        
        <!-- Error -->
        <div v-if="formError" class="text-red-400 text-sm">
          {{ formError }}
        </div>
        
        <!-- Buttons -->
        <div class="flex gap-3">
          <button
            type="submit"
            class="btn-primary"
          >
            {{ editingId ? 'Save Changes' : 'Add Location' }}
          </button>
          <button
            type="button"
            @click="cancelForm"
            class="px-4 py-2 rounded-lg bg-mountain-700 text-mountain-300 hover:bg-mountain-600 hover:text-white transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
    
    <!-- Locations List -->
    <div v-if="customLocationsStore.sortedLocations.length > 0" class="space-y-3">
      <div
        v-for="location in customLocationsStore.sortedLocations"
        :key="location.id"
        class="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <RouterLink
          :to="`/custom/${location.id}`"
          class="flex-1 group"
        >
          <h3 class="font-display font-semibold text-white group-hover:text-snow-400 transition-colors">
            {{ location.name }}
          </h3>
          <p class="text-mountain-400 text-sm">
            {{ location.lat.toFixed(4) }}°, {{ location.lon.toFixed(4) }}°
            <template v-if="location.elevation_m">
              <span class="mx-1">•</span>
              {{ formatLocationElevation(location.elevation_m) }}
            </template>
          </p>
        </RouterLink>
        
        <div class="flex items-center gap-2">
          <RouterLink
            :to="`/custom/${location.id}`"
            class="px-3 py-1.5 rounded-lg bg-snow-500/20 text-snow-300 text-sm hover:bg-snow-500/30 transition-colors"
          >
            View Forecast
          </RouterLink>
          <button
            @click="openEditForm(location.id)"
            class="p-2 rounded-lg text-mountain-400 hover:text-white hover:bg-mountain-700 transition-colors"
            title="Edit"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>
          <button
            @click="deleteLocation(location.id)"
            class="p-2 rounded-lg text-mountain-400 hover:text-red-400 hover:bg-mountain-700 transition-colors"
            title="Delete"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-else-if="!showForm" class="text-center py-16 glass-card">
      <div class="text-5xl mb-4">📍</div>
      <h2 class="text-xl font-display font-semibold text-white mb-2">
        No Custom Locations Yet
      </h2>
      <p class="text-mountain-400 mb-6 max-w-md mx-auto">
        Add your own coordinates to get forecasts for backcountry zones, 
        remote peaks, or anywhere not on the resort list.
      </p>
      <button
        @click="openNewForm"
        class="btn-primary inline-flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Add Your First Location
      </button>
    </div>
    
    <!-- Tips -->
    <div class="glass-card p-4 text-sm text-mountain-400">
      <p class="font-medium text-mountain-300 mb-2">💡 Tips for finding coordinates:</p>
      <ul class="list-disc list-inside space-y-1">
        <li>Right-click on Google Maps and select the coordinates</li>
        <li>Use a GPS app on your phone while at the location</li>
        <li>Search for the location on CalTopo or other mapping tools</li>
      </ul>
    </div>
  </div>
</template>

