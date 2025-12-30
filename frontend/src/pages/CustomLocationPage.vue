<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useCustomLocationsStore } from '@/stores/customLocations'
import { useForecastStore } from '@/stores/forecast'
import { useSettingsStore } from '@/stores/settings'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import SnowfallCard from '@/components/forecast/SnowfallCard.vue'
import DailyBreakdown from '@/components/forecast/DailyBreakdown.vue'
import SnowGraph from '@/components/forecast/SnowGraph.vue'
import ModelSelector from '@/components/forecast/ModelSelector.vue'
import WeatherStats from '@/components/forecast/WeatherStats.vue'
import { formatModelRunTime, getDailySummaries, getTotalSnowfall, getSnowfallNextHours } from '@/utils/forecast'
import { convertElevation, formatElevation } from '@/utils/units'
import { fetchForecast } from '@/utils/api'
import type { Forecast } from '@/types'

const route = useRoute()
const customLocationsStore = useCustomLocationsStore()
const forecastStore = useForecastStore()
const settingsStore = useSettingsStore()

const locationId = computed(() => route.params.id as string)
const location = computed(() => customLocationsStore.getLocationById(locationId.value))

// Local forecast state (not using store cache for custom locations)
const forecast = ref<Forecast | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const selectedModel = ref('blend')

// Load forecast
async function loadForecast() {
  if (!location.value) return
  
  loading.value = true
  error.value = null
  
  try {
    forecast.value = await fetchForecast(
      location.value.lat,
      location.value.lon,
      selectedModel.value,
      location.value.elevation_m
    )
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load forecast'
    console.error('Failed to load forecast:', e)
  } finally {
    loading.value = false
  }
}

watch([locationId, selectedModel], loadForecast, { immediate: true })

onMounted(() => {
  forecastStore.loadModels()
})

// Computed values
const elevationDisplay = computed(() => {
  if (!location.value?.elevation_m) return null
  return formatElevation(
    convertElevation(location.value.elevation_m, 'm', settingsStore.elevationUnit),
    settingsStore.elevationUnit
  )
})

const modelRunTime = computed(() => {
  return formatModelRunTime(forecast.value?.model_run_utc ?? null)
})

const dailySummaries = computed(() => {
  if (!forecast.value) return []
  return getDailySummaries(forecast.value)
})

const totalSnowfall = computed(() => {
  if (!forecast.value) return 0
  return getTotalSnowfall(forecast.value)
})

const snowfall24h = computed(() => {
  if (!forecast.value) return 0
  return getSnowfallNextHours(forecast.value, 24)
})

const snowfall72h = computed(() => {
  if (!forecast.value) return 0
  return getSnowfallNextHours(forecast.value, 72)
})

const forecastDays = computed(() => {
  if (!forecast.value) return 0
  return Math.ceil(forecast.value.times_utc.length / 24)
})

// Handle model change
function handleModelChange(modelId: string) {
  selectedModel.value = modelId
}
</script>

<template>
  <div class="space-y-6">
    <!-- Back button -->
    <RouterLink 
      to="/custom" 
      class="inline-flex items-center gap-2 text-mountain-400 hover:text-white transition-colors"
    >
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Back to Custom Locations
    </RouterLink>
    
    <!-- Location Header -->
    <div v-if="location" class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-3xl md:text-4xl font-display font-bold text-white">
            {{ location.name }}
          </h1>
          <span class="px-2 py-1 rounded-full bg-mountain-700 text-mountain-300 text-xs">
            Custom
          </span>
        </div>
        <p class="text-mountain-400 mt-1">
          📍 {{ location.lat.toFixed(4) }}°, {{ location.lon.toFixed(4) }}°
          <template v-if="elevationDisplay">
            <span class="mx-2">•</span>
            Elevation: {{ elevationDisplay }}
          </template>
        </p>
      </div>
      
      <ModelSelector 
        :current-model="selectedModel"
        @update:model="handleModelChange"
      />
    </div>
    
    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-16">
      <LoadingSpinner size="lg" text="Loading forecast..." />
    </div>
    
    <!-- Error -->
    <ErrorAlert 
      v-else-if="error"
      :message="error"
      @retry="loadForecast"
    />
    
    <!-- Forecast Content -->
    <template v-else-if="forecast">
      <!-- Snow Summary Row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SnowfallCard
          :total-snow-cm="snowfall24h"
          :snow-unit="forecast.hourly_units.snowfall"
          period="Next 24 Hours"
          :model-id="selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="snowfall72h"
          :snow-unit="forecast.hourly_units.snowfall"
          period="Next 72 Hours"
          :model-id="selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="totalSnowfall"
          :snow-unit="forecast.hourly_units.snowfall"
          :period="`${forecastDays}-Day Total`"
          :model-id="selectedModel"
          :model-run-time="modelRunTime"
        />
      </div>
      
      <!-- Current Conditions -->
      <WeatherStats :forecast="forecast" />
      
      <!-- Snow Graph -->
      <SnowGraph 
        :forecast="forecast" 
        :initial-hours="72"
      />
      
      <!-- Daily Breakdown -->
      <DailyBreakdown
        :summaries="dailySummaries"
        :temp-unit="forecast.hourly_units.temperature_2m"
        :snow-unit="forecast.hourly_units.snowfall"
        :wind-unit="forecast.hourly_units.wind_speed_10m"
      />
    </template>
    
    <!-- Location not found -->
    <div v-else-if="!location" class="text-center py-16">
      <p class="text-mountain-400">Custom location not found.</p>
      <RouterLink to="/custom" class="btn-primary mt-4 inline-block">
        Back to Custom Locations
      </RouterLink>
    </div>
  </div>
</template>

