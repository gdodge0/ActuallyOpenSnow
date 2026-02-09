/**
 * Forecast store for weather data.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Forecast, ModelInfo, ComparisonResponse } from '@/types'
import { fetchResortForecast, fetchResortComparison, fetchModels } from '@/utils/api'
import { 
  getDailySummaries, 
  getTotalSnowfall, 
  getTotalEnhancedSnowfall,
  getTotalRain,
  getSnowfallNextHours,
  getEnhancedSnowfallNextHours,
  getRainNextHours,
} from '@/utils/forecast'

interface ForecastCache {
  forecast: Forecast
  timestamp: number
}

const CACHE_TTL = 30 * 60 * 1000 // 30 minutes

export const useForecastStore = defineStore('forecast', () => {
  // State
  const currentForecast = ref<Forecast | null>(null)
  const comparison = ref<ComparisonResponse | null>(null)
  const models = ref<ModelInfo[]>([])
  const selectedModel = ref<string>('blend')  // Default to blend model
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Cache
  const cache = ref<Map<string, ForecastCache>>(new Map())
  
  // Computed: daily summaries for current forecast
  const dailySummaries = computed(() => {
    if (!currentForecast.value) return []
    return getDailySummaries(currentForecast.value)
  })
  
  // Computed: total snowfall (conservative)
  const totalSnowfall = computed(() => {
    if (!currentForecast.value) return 0
    return getTotalSnowfall(currentForecast.value)
  })
  
  // Computed: total enhanced snowfall (temperature-adjusted)
  const totalEnhancedSnowfall = computed(() => {
    if (!currentForecast.value) return 0
    return getTotalEnhancedSnowfall(currentForecast.value)
  })
  
  // Computed: total rain
  const totalRain = computed(() => {
    if (!currentForecast.value) return 0
    return getTotalRain(currentForecast.value)
  })
  
  // Computed: snowfall next 24h (conservative)
  const snowfall24h = computed(() => {
    if (!currentForecast.value) return 0
    return getSnowfallNextHours(currentForecast.value, 24)
  })
  
  // Computed: enhanced snowfall next 24h
  const enhancedSnowfall24h = computed(() => {
    if (!currentForecast.value) return 0
    return getEnhancedSnowfallNextHours(currentForecast.value, 24)
  })
  
  // Computed: rain next 24h
  const rain24h = computed(() => {
    if (!currentForecast.value) return 0
    return getRainNextHours(currentForecast.value, 24)
  })
  
  // Computed: snowfall next 72h (conservative)
  const snowfall72h = computed(() => {
    if (!currentForecast.value) return 0
    return getSnowfallNextHours(currentForecast.value, 72)
  })
  
  // Computed: enhanced snowfall next 72h
  const enhancedSnowfall72h = computed(() => {
    if (!currentForecast.value) return 0
    return getEnhancedSnowfallNextHours(currentForecast.value, 72)
  })
  
  // Computed: rain next 72h
  const rain72h = computed(() => {
    if (!currentForecast.value) return 0
    return getRainNextHours(currentForecast.value, 72)
  })
  
  // Computed: forecast days
  const forecastDays = computed(() => {
    if (!currentForecast.value) return 0
    return Math.ceil(currentForecast.value.times_utc.length / 24)
  })
  
  // Computed: model run time
  const modelRunTime = computed(() => {
    return currentForecast.value?.model_run_utc ?? null
  })

  // Computed: whether ensemble prediction ranges are available
  const hasEnsembleRanges = computed(() => {
    return !!currentForecast.value?.ensemble_ranges?.enhanced_snowfall
  })

  // Computed: ensemble snowfall range totals for next 72h
  const ensembleSnowfall72h = computed(() => {
    if (!currentForecast.value?.ensemble_ranges?.enhanced_snowfall) return null
    const { p10, p90 } = currentForecast.value.ensemble_ranges.enhanced_snowfall
    const hours = Math.min(72, p10.length)
    let totalP10 = 0
    let totalP90 = 0
    for (let i = 0; i < hours; i++) {
      totalP10 += p10[i] ?? 0
      totalP90 += p90[i] ?? 0
    }
    return { p10: totalP10, p90: totalP90 }
  })
  
  // Cache key generator - includes elevation for proper caching
  function getCacheKey(slug: string, model: string, elevation?: string | number): string {
    const elevStr = elevation !== undefined ? String(elevation) : 'summit'
    return `${slug}:${model}:${elevStr}`
  }
  
  // Check if cache is valid
  function isCacheValid(key: string): boolean {
    const cached = cache.value.get(key)
    if (!cached) return false
    return Date.now() - cached.timestamp < CACHE_TTL
  }
  
  // Load available models
  async function loadModels() {
    if (models.value.length > 0) return
    
    try {
      models.value = await fetchModels()
    } catch (e) {
      console.error('Failed to load models:', e)
    }
  }
  
  // Load forecast for a resort
  // elevation can be 'base', 'summit', or a number in meters
  async function loadForecast(slug: string, model?: string, elevation?: string | number) {
    const modelId = model ?? selectedModel.value
    const elevStr = elevation !== undefined ? String(elevation) : 'summit'
    const cacheKey = getCacheKey(slug, modelId, elevStr)
    
    // Check cache
    if (isCacheValid(cacheKey)) {
      currentForecast.value = cache.value.get(cacheKey)!.forecast
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const forecast = await fetchResortForecast(slug, modelId, elevStr)
      currentForecast.value = forecast
      
      // Update cache
      cache.value.set(cacheKey, {
        forecast,
        timestamp: Date.now(),
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load forecast'
      console.error('Failed to load forecast:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Load comparison for a resort
  async function loadComparison(slug: string, modelIds?: string[], elevation?: string | number) {
    loading.value = true
    error.value = null
    
    const elevStr = elevation !== undefined ? String(elevation) : 'summit'
    
    try {
      comparison.value = await fetchResortComparison(
        slug,
        modelIds ?? ['blend', 'gfs', 'ifs', 'aifs'],
        elevStr
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load comparison'
      console.error('Failed to load comparison:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Change selected model
  function setModel(modelId: string) {
    selectedModel.value = modelId
  }
  
  // Clear cache
  function clearCache() {
    cache.value.clear()
  }
  
  // Clear current forecast
  function clearForecast() {
    currentForecast.value = null
    comparison.value = null
    error.value = null
  }
  
  return {
    // State
    currentForecast,
    comparison,
    models,
    selectedModel,
    loading,
    error,
    
    // Computed
    dailySummaries,
    totalSnowfall,
    totalEnhancedSnowfall,
    totalRain,
    snowfall24h,
    enhancedSnowfall24h,
    rain24h,
    snowfall72h,
    enhancedSnowfall72h,
    rain72h,
    forecastDays,
    modelRunTime,
    hasEnsembleRanges,
    ensembleSnowfall72h,
    
    // Actions
    loadModels,
    loadForecast,
    loadComparison,
    setModel,
    clearCache,
    clearForecast,
  }
})

