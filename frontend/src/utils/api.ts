/**
 * API client for the ActuallyOpenSnow backend.
 */

import axios from 'axios'
import type { Resort, ModelInfo, Forecast, ComparisonResponse } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,  // 3 minutes — must exceed nginx proxy_read_timeout (180s)
})

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// In-memory cache for forecasts
interface CacheEntry {
  data: Forecast
  timestamp: number
}
const forecastCache = new Map<string, CacheEntry>()
const CACHE_TTL = 30 * 60 * 1000  // 30 minutes

function getCacheKey(slug: string, model: string, elevation: string = 'summit'): string {
  return `${slug}:${model}:${elevation}`
}

function getCachedForecast(key: string): Forecast | null {
  const entry = forecastCache.get(key)
  if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
    return entry.data
  }
  if (entry) {
    forecastCache.delete(key)  // Expired
  }
  return null
}

function setCachedForecast(key: string, data: Forecast): void {
  forecastCache.set(key, { data, timestamp: Date.now() })
  
  // Simple cache eviction
  if (forecastCache.size > 50) {
    const oldestKey = forecastCache.keys().next().value
    if (oldestKey) forecastCache.delete(oldestKey)
  }
}

/**
 * Fetch all available ski resorts.
 */
export async function fetchResorts(state?: string): Promise<Resort[]> {
  const params = state ? { state } : {}
  const { data } = await api.get<Resort[]>('/resorts', { params })
  return data
}

/**
 * Fetch a single resort by slug.
 */
export async function fetchResort(slug: string): Promise<Resort> {
  const { data } = await api.get<Resort>(`/resorts/${slug}`)
  return data
}

/**
 * Fetch all available forecast models.
 */
export async function fetchModels(): Promise<ModelInfo[]> {
  const { data } = await api.get<ModelInfo[]>('/models')
  return data
}

/**
 * Fetch forecast for a resort (with caching).
 */
export async function fetchResortForecast(
  slug: string,
  model: string = 'blend',
  elevation: string = 'summit'
): Promise<Forecast> {
  const cacheKey = getCacheKey(slug, model, elevation)
  
  // Check cache first
  const cached = getCachedForecast(cacheKey)
  if (cached) {
    console.log(`[API] Cache hit for ${slug}:${model}:${elevation}`)
    return cached
  }
  
  const { data } = await api.get<Forecast>(`/resorts/${slug}/forecast`, {
    params: { model, elevation },
  })
  
  // Cache the result
  setCachedForecast(cacheKey, data)
  
  return data
}

/**
 * Batch fetch forecasts for multiple resorts (single HTTP request).
 */
export async function fetchBatchForecasts(
  slugs: string[],
  model: string = 'blend',
  elevation: string = 'summit'
): Promise<Map<string, Forecast>> {
  const result = new Map<string, Forecast>()
  const uncachedSlugs: string[] = []
  
  // Check cache first for each slug
  for (const slug of slugs) {
    const cacheKey = getCacheKey(slug, model, elevation)
    const cached = getCachedForecast(cacheKey)
    if (cached) {
      result.set(slug, cached)
    } else {
      uncachedSlugs.push(slug)
    }
  }
  
  // If all cached, return immediately
  if (uncachedSlugs.length === 0) {
    console.log('[API] All forecasts from cache')
    return result
  }
  
  // Fetch uncached forecasts in batch
  console.log(`[API] Batch fetching ${uncachedSlugs.length} forecasts`)
  const { data } = await api.get<{ forecasts: Record<string, Forecast>; errors: Record<string, string> }>(
    '/resorts/batch/forecast',
    { params: { slugs: uncachedSlugs.join(','), model, elevation } }
  )
  
  // Cache and add to result
  for (const [slug, forecast] of Object.entries(data.forecasts)) {
    const cacheKey = getCacheKey(slug, model, elevation)
    setCachedForecast(cacheKey, forecast)
    result.set(slug, forecast)
  }
  
  // Log errors
  for (const [slug, error] of Object.entries(data.errors)) {
    console.warn(`[API] Failed to fetch ${slug}: ${error}`)
  }
  
  return result
}

/**
 * Fetch forecast for coordinates.
 */
export async function fetchForecast(
  lat: number,
  lon: number,
  model: string = 'blend',
  elevation?: number
): Promise<Forecast> {
  const params: Record<string, unknown> = { lat, lon, model }
  if (elevation !== undefined) {
    params.elevation = elevation
  }
  const { data } = await api.get<Forecast>('/forecast', { params })
  return data
}

/**
 * Compare forecasts from multiple models for a resort.
 */
export async function fetchResortComparison(
  slug: string,
  models: string[] = ['blend', 'gfs', 'ifs', 'aifs'],
  elevation: string = 'summit'
): Promise<ComparisonResponse> {
  const { data } = await api.get<ComparisonResponse>(`/resorts/${slug}/compare`, {
    params: { models: models.join(','), elevation },
  })
  return data
}

/**
 * Compare forecasts from multiple models for coordinates.
 */
export async function fetchComparison(
  lat: number,
  lon: number,
  models: string[] = ['blend', 'gfs', 'ifs', 'aifs'],
  elevation?: number
): Promise<ComparisonResponse> {
  const params: Record<string, unknown> = {
    lat,
    lon,
    models: models.join(','),
  }
  if (elevation !== undefined) {
    params.elevation = elevation
  }
  const { data } = await api.get<ComparisonResponse>('/compare', { params })
  return data
}

export default api

