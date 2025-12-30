/**
 * Forecast store for weather data.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Forecast, ModelInfo, ComparisonResponse } from '@/types'
import { fetchResortForecast, fetchResortComparison, fetchModels } from '@/utils/api'
import { getDailySummaries, getTotalSnowfall, getSnowfallNextHours } from '@/utils/forecast'

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
  
  // Computed: total snowfall
  const totalSnowfall = computed(() => {
    if (!currentForecast.value) return 0
    return getTotalSnowfall(currentForecast.value)
  })
  
  // Computed: snowfall next 24h
  const snowfall24h = computed(() => {
    if (!currentForecast.value) return 0
    return getSnowfallNextHours(currentForecast.value, 24)
  })
  
  // Computed: snowfall next 72h
  const snowfall72h = computed(() => {
    if (!currentForecast.value) return 0
    return getSnowfallNextHours(currentForecast.value, 72)
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
  
  // Cache key generator
  function getCacheKey(slug: string, model: string): string {
    return `${slug}:${model}`
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
  async function loadForecast(slug: string, model?: string) {
    const modelId = model ?? selectedModel.value
    const cacheKey = getCacheKey(slug, modelId)
    
    // Check cache
    if (isCacheValid(cacheKey)) {
      currentForecast.value = cache.value.get(cacheKey)!.forecast
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const forecast = await fetchResortForecast(slug, modelId)
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
  async function loadComparison(slug: string, modelIds?: string[]) {
    loading.value = true
    error.value = null
    
    try {
      comparison.value = await fetchResortComparison(
        slug,
        modelIds ?? ['blend', 'gfs', 'ifs', 'aifs']
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
    snowfall24h,
    snowfall72h,
    forecastDays,
    modelRunTime,
    
    // Actions
    loadModels,
    loadForecast,
    loadComparison,
    setModel,
    clearCache,
    clearForecast,
  }
})

