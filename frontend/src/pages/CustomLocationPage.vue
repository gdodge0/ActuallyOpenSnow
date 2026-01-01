<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useCustomLocationsStore } from '@/stores/customLocations'
import { useForecastStore } from '@/stores/forecast'
import { useSettingsStore } from '@/stores/settings'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import RateLimitError from '@/components/common/RateLimitError.vue'
import SnowfallCard from '@/components/forecast/SnowfallCard.vue'
import DailyBreakdown from '@/components/forecast/DailyBreakdown.vue'
import SnowGraph from '@/components/forecast/SnowGraph.vue'
import ModelSelector from '@/components/forecast/ModelSelector.vue'
import WeatherStats from '@/components/forecast/WeatherStats.vue'
import { 
  formatModelRunTime, 
  getDailySummaries, 
  getTotalSnowfall, 
  getTotalEnhancedSnowfall,
  getTotalRain,
  getSnowfallNextHours,
  getEnhancedSnowfallNextHours,
  getRainNextHours,
} from '@/utils/forecast'
import { convertElevation, formatElevation } from '@/utils/units'
import { fetchForecast } from '@/utils/api'
import type { Forecast } from '@/types'

const route = useRoute()
const customLocationsStore = useCustomLocationsStore()
const forecastStore = useForecastStore()
const settingsStore = useSettingsStore()

const locationId = computed(() => route.params.id as string)
const location = computed(() => customLocationsStore.getLocationById(locationId.value))

// Update page title when location loads
watch(location, (loc) => {
  if (loc) {
    document.title = `${loc.name} Forecast | ActuallyOpenSnow`
  }
}, { immediate: true })

// Local forecast state (not using store cache for custom locations)
const forecast = ref<Forecast | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const isRateLimitError = ref(false)
const selectedModel = ref('blend')

// Elevation override state (always stored in meters internally)
const elevationOverrideMeters = ref<number | undefined>(undefined)
const showElevationInput = ref(false)

// Initialize elevation from location when it loads
watch(location, (loc) => {
  if (loc && elevationOverrideMeters.value === undefined) {
    elevationOverrideMeters.value = loc.elevation_m
  }
}, { immediate: true })

// The effective elevation used for the forecast (in meters)
const effectiveElevation = computed(() => {
  return elevationOverrideMeters.value ?? location.value?.elevation_m
})

// Display value for the input (in user's preferred unit)
const elevationInputDisplayValue = computed(() => {
  if (elevationOverrideMeters.value === undefined) return ''
  const converted = convertElevation(elevationOverrideMeters.value, 'm', settingsStore.elevationUnit)
  return Math.round(converted ?? 0)
})

// Get the reciprocal unit for display
const reciprocalUnit = computed(() => settingsStore.elevationUnit === 'ft' ? 'm' : 'ft')

// Format elevation in the reciprocal unit
function formatReciprocalElev(meters: number | undefined): string {
  if (meters === undefined) return '--'
  const converted = convertElevation(meters, 'm', reciprocalUnit.value)
  return formatElevation(converted, reciprocalUnit.value)
}

// Load forecast
async function loadForecast() {
  if (!location.value) return
  
  loading.value = true
  error.value = null
  isRateLimitError.value = false
  
  try {
    forecast.value = await fetchForecast(
      location.value.lat,
      location.value.lon,
      selectedModel.value,
      effectiveElevation.value
    )
  } catch (e: unknown) {
    // Check for rate limit error (429 status)
    if (e && typeof e === 'object' && 'response' in e) {
      const axiosError = e as { response?: { status?: number } }
      if (axiosError.response?.status === 429) {
        isRateLimitError.value = true
        error.value = 'Rate limit exceeded'
        console.warn('Rate limit exceeded for custom location forecast')
        return
      }
    }
    error.value = e instanceof Error ? e.message : 'Failed to load forecast'
    console.error('Failed to load forecast:', e)
  } finally {
    loading.value = false
  }
}

watch([locationId, selectedModel, effectiveElevation], loadForecast, { immediate: true })

// Handle elevation input (input is in user's preferred unit)
function handleElevationChange(event: Event) {
  const input = event.target as HTMLInputElement
  const inputValue = parseInt(input.value, 10)
  
  if (isNaN(inputValue)) return
  
  // Convert from display unit to meters
  const valueInMeters = Math.round(
    convertElevation(inputValue, settingsStore.elevationUnit, 'm') ?? 0
  )
  
  // Validate range (0 to 9000m)
  if (valueInMeters >= 0 && valueInMeters <= 9000) {
    elevationOverrideMeters.value = valueInMeters
  }
}

function clearElevationOverride() {
  elevationOverrideMeters.value = location.value?.elevation_m
  showElevationInput.value = false
}

// Input constraints in display units
const inputMin = computed(() => 0)
const inputMax = computed(() => {
  return Math.round(convertElevation(9000, 'm', settingsStore.elevationUnit) ?? 0)
})
const inputStep = computed(() => settingsStore.elevationUnit === 'ft' ? 100 : 50)

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

const totalEnhancedSnowfall = computed(() => {
  if (!forecast.value) return 0
  return getTotalEnhancedSnowfall(forecast.value)
})

const totalRain = computed(() => {
  if (!forecast.value) return 0
  return getTotalRain(forecast.value)
})

const snowfall24h = computed(() => {
  if (!forecast.value) return 0
  return getSnowfallNextHours(forecast.value, 24)
})

const enhancedSnowfall24h = computed(() => {
  if (!forecast.value) return 0
  return getEnhancedSnowfallNextHours(forecast.value, 24)
})

const rain24h = computed(() => {
  if (!forecast.value) return 0
  return getRainNextHours(forecast.value, 24)
})

const snowfall72h = computed(() => {
  if (!forecast.value) return 0
  return getSnowfallNextHours(forecast.value, 72)
})

const enhancedSnowfall72h = computed(() => {
  if (!forecast.value) return 0
  return getEnhancedSnowfallNextHours(forecast.value, 72)
})

const rain72h = computed(() => {
  if (!forecast.value) return 0
  return getRainNextHours(forecast.value, 72)
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
    <div v-if="location" class="space-y-4">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
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
      
      <!-- Elevation Override -->
      <div class="bg-mountain-900/50 rounded-xl p-4 border border-mountain-800">
        <div class="flex items-center gap-2 text-sm text-mountain-400 mb-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M13 7l5 5m0 0l-5 5m5-5H6"/>
          </svg>
          <span>Forecast Elevation</span>
        </div>
        
        <div class="flex items-center gap-4">
          <button
            v-if="!showElevationInput"
            @click="showElevationInput = true"
            class="px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-700 
                   hover:bg-mountain-700 hover:border-mountain-600 transition-colors
                   text-white text-sm"
          >
            <span v-if="effectiveElevation">
              {{ formatElevation(convertElevation(effectiveElevation, 'm', settingsStore.elevationUnit), settingsStore.elevationUnit) }}
            </span>
            <span v-else class="text-mountain-400">Not set (uses model default)</span>
            <span class="ml-2 text-mountain-400">✏️</span>
          </button>
          
          <div v-else class="flex items-center gap-3">
            <input
              type="number"
              :value="elevationInputDisplayValue"
              @change="handleElevationChange"
              :min="inputMin"
              :max="inputMax"
              :step="inputStep"
              :placeholder="`Elevation in ${settingsStore.elevationUnit}`"
              class="w-32 px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-600
                     text-white text-sm focus:border-snow-500 focus:outline-none focus:ring-1 focus:ring-snow-500/50"
            />
            <span class="text-sm text-mountain-400">{{ settingsStore.elevationUnit }}</span>
            <span v-if="effectiveElevation" class="text-xs text-mountain-500">
              ({{ formatReciprocalElev(effectiveElevation) }})
            </span>
            <button
              @click="showElevationInput = false"
              class="px-3 py-2 rounded-lg bg-snow-600/20 border border-snow-500 
                     text-white text-sm hover:bg-snow-600/30 transition-colors"
            >
              Done
            </button>
            <button
              v-if="location.elevation_m !== undefined"
              @click="clearElevationOverride"
              class="text-sm text-mountain-400 hover:text-white transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
        
        <div class="mt-2 text-xs text-mountain-500">
          <span v-if="effectiveElevation">
            Showing forecast for {{ formatElevation(convertElevation(effectiveElevation, 'm', settingsStore.elevationUnit), settingsStore.elevationUnit) }}
          </span>
          <span v-else>
            Using weather model's default elevation for this location
          </span>
        </div>
      </div>
    </div>
    
    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-16">
      <LoadingSpinner size="lg" text="Loading forecast..." />
    </div>
    
    <!-- Rate Limit Error -->
    <RateLimitError 
      v-else-if="isRateLimitError"
      :retry-after-seconds="60"
      @retry="loadForecast"
    />
    
    <!-- General Error -->
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
          :enhanced-snow-cm="enhancedSnowfall24h"
          :rain-mm="rain24h"
          :snow-unit="forecast.hourly_units.snowfall"
          period="Next 24 Hours"
          :model-id="selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="snowfall72h"
          :enhanced-snow-cm="enhancedSnowfall72h"
          :rain-mm="rain72h"
          :snow-unit="forecast.hourly_units.snowfall"
          period="Next 72 Hours"
          :model-id="selectedModel"
        />
        <SnowfallCard
          :total-snow-cm="totalSnowfall"
          :enhanced-snow-cm="totalEnhancedSnowfall"
          :rain-mm="totalRain"
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

