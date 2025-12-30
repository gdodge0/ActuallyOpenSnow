/**
 * API client for the ActuallyOpenSnow backend.
 */

import axios from 'axios'
import type { Resort, ModelInfo, Forecast, ComparisonResponse } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
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
 * Fetch forecast for a resort.
 */
export async function fetchResortForecast(
  slug: string,
  model: string = 'gfs',
  elevation: string = 'summit'
): Promise<Forecast> {
  const { data } = await api.get<Forecast>(`/resorts/${slug}/forecast`, {
    params: { model, elevation },
  })
  return data
}

/**
 * Fetch forecast for coordinates.
 */
export async function fetchForecast(
  lat: number,
  lon: number,
  model: string = 'gfs',
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
  models: string[] = ['gfs', 'ifs', 'aifs'],
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
  models: string[] = ['gfs', 'ifs', 'aifs'],
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

