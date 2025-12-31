<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useResortsStore } from '@/stores/resorts'
import { useForecastStore } from '@/stores/forecast'
import { useSettingsStore } from '@/stores/settings'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import SnowfallCard from '@/components/forecast/SnowfallCard.vue'
import DailyBreakdown from '@/components/forecast/DailyBreakdown.vue'
import SnowGraph from '@/components/forecast/SnowGraph.vue'
import ModelSelector from '@/components/forecast/ModelSelector.vue'
import ElevationSelector from '@/components/forecast/ElevationSelector.vue'
import type { ElevationOption } from '@/components/forecast/ElevationSelector.vue'
import WeatherStats from '@/components/forecast/WeatherStats.vue'
import { formatModelRunTime } from '@/utils/forecast'
import { convertPrecipitation, convertElevation, formatElevation } from '@/utils/units'

const route = useRoute()
const resortsStore = useResortsStore()
const forecastStore = useForecastStore()
const settingsStore = useSettingsStore()

const slug = computed(() => route.params.slug as string)
const resort = computed(() => resortsStore.getResortBySlug(slug.value))

// Elevation selection state
const selectedElevation = ref<ElevationOption>('peak')
const customElevationM = ref<number | undefined>(undefined)

// Get the elevation value to pass to the API
const elevationValue = computed(() => {
  if (!resort.value) return 'summit'
  
  switch (selectedElevation.value) {
    case 'peak':
      return 'summit'
    case 'mid':
      // Calculate mid-mountain and pass as meters
      return Math.round((resort.value.base_elevation_m + resort.value.summit_elevation_m) / 2)
    case 'base':
      return 'base'
    case 'custom':
      return customElevationM.value ?? resort.value.summit_elevation_m
    default:
      return 'summit'
  }
})

// Update page title when resort loads
watch(resort, (r) => {
  if (r) {
    document.title = `${r.name} Snow Forecast | ActuallyOpenSnow`
  }
}, { immediate: true })

// Load forecast when slug, model, or elevation changes
async function loadForecast() {
  if (!slug.value) return
  await forecastStore.loadForecast(slug.value, forecastStore.selectedModel, elevationValue.value)
}

watch([slug, () => forecastStore.selectedModel, elevationValue], loadForecast, { immediate: true })

// Handle elevation change from selector
function handleElevationChange(elevationM: number) {
  // The watch on elevationValue will trigger the forecast reload
}

onMounted(() => {
  if (resortsStore.resorts.length === 0) {
    resortsStore.loadResorts()
  }
})

// Favorite toggle
function toggleFavorite() {
  if (resort.value) {
    resortsStore.toggleFavorite(resort.value.slug)
  }
}

const isFavorite = computed(() => {
  return resort.value ? resortsStore.isFavorite(resort.value.slug) : false
})

// Formatted values
const summitElevation = computed(() => {
  if (!resort.value) return '--'
  return formatElevation(
    convertElevation(resort.value.summit_elevation_m, 'm', settingsStore.elevationUnit),
    settingsStore.elevationUnit
  )
})

const baseElevation = computed(() => {
  if (!resort.value) return '--'
  return formatElevation(
    convertElevation(resort.value.base_elevation_m, 'm', settingsStore.elevationUnit),
    settingsStore.elevationUnit
  )
})

const modelRunTime = computed(() => {
  return formatModelRunTime(forecastStore.modelRunTime)
})

// Handle model change
function handleModelChange(modelId: string) {
  forecastStore.setModel(modelId)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Back button -->
    <RouterLink 
      to="/" 
      class="inline-flex items-center gap-2 text-mountain-400 hover:text-white transition-colors"
    >
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Back to Resorts
    </RouterLink>
    
    <!-- Resort Header -->
    <div v-if="resort" class="space-y-4">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-3xl md:text-4xl font-display font-bold text-white">
              {{ resort.name }}
            </h1>
            <button
              @click="toggleFavorite"
              class="p-2 rounded-lg hover:bg-mountain-800 transition-colors"
              :class="isFavorite ? 'text-yellow-400' : 'text-mountain-500 hover:text-yellow-400'"
            >
              <svg 
                class="w-6 h-6" 
                :fill="isFavorite ? 'currentColor' : 'none'" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
              </svg>
            </button>
          </div>
          <p class="text-mountain-400 mt-1">
            📍 {{ resort.lat.toFixed(4) }}°, {{ resort.lon.toFixed(4) }}° 
            <span class="mx-2">•</span>
            Base: {{ baseElevation }} | Summit: {{ summitElevation }}
          </p>
        </div>
        
        <ModelSelector 
          :current-model="forecastStore.selectedModel"
          @update:model="handleModelChange"
        />
      </div>
      
      <!-- Elevation Selector -->
      <div class="bg-mountain-900/50 rounded-xl p-4 border border-mountain-800">
        <ElevationSelector
          v-model="selectedElevation"
          v-model:custom-elevation-m="customElevationM"
          :base-elevation-m="resort.base_elevation_m"
          :summit-elevation-m="resort.summit_elevation_m"
          @change="handleElevationChange"
        />
      </div>
    </div>
    
    <!-- Loading -->
    <div v-if="forecastStore.loading" class="flex justify-center py-16">
      <LoadingSpinner size="lg" text="Loading forecast..." />
    </div>
    
    <!-- Error -->
    <ErrorAlert 
      v-else-if="forecastStore.error"
      :message="forecastStore.error"
      @retry="loadForecast"
    />
    
    <!-- Forecast Content -->
    <template v-else-if="forecastStore.currentForecast">
      <!-- Snow Summary Row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SnowfallCard
          :total-snow-cm="forecastStore.snowfall24h"
          :enhanced-snow-cm="forecastStore.enhancedSnowfall24h"
          :rain-mm="forecastStore.rain24h"
          :snow-unit="forecastStore.currentForecast.hourly_units.snowfall"
          period="Next 24 Hours"
          :model-id="forecastStore.selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="forecastStore.snowfall72h"
          :enhanced-snow-cm="forecastStore.enhancedSnowfall72h"
          :rain-mm="forecastStore.rain72h"
          :snow-unit="forecastStore.currentForecast.hourly_units.snowfall"
          period="Next 72 Hours"
          :model-id="forecastStore.selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="forecastStore.totalSnowfall"
          :enhanced-snow-cm="forecastStore.totalEnhancedSnowfall"
          :rain-mm="forecastStore.totalRain"
          :snow-unit="forecastStore.currentForecast.hourly_units.snowfall"
          :period="`${forecastStore.forecastDays}-Day Total`"
          :model-id="forecastStore.selectedModel"
          :model-run-time="modelRunTime"
        />
      </div>
      
      <!-- Current Conditions -->
      <WeatherStats :forecast="forecastStore.currentForecast" />
      
      <!-- Snow Graph with time range selector -->
      <SnowGraph 
        :forecast="forecastStore.currentForecast" 
        :initial-hours="72"
      />
      
      <!-- Daily Breakdown -->
      <DailyBreakdown
        :summaries="forecastStore.dailySummaries"
        :temp-unit="forecastStore.currentForecast.hourly_units.temperature_2m"
        :snow-unit="forecastStore.currentForecast.hourly_units.snowfall"
        :wind-unit="forecastStore.currentForecast.hourly_units.wind_speed_10m"
      />
    </template>
    
    <!-- No resort found -->
    <div v-else-if="!resort" class="text-center py-16">
      <p class="text-mountain-400">Resort not found.</p>
      <RouterLink to="/" class="btn-primary mt-4 inline-block">
        Back to Home
      </RouterLink>
    </div>
  </div>
</template>

