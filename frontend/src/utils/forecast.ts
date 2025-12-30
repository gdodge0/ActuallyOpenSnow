/**
 * Forecast data processing utilities.
 */

import type { Forecast, DailySummary, WeatherCondition } from '@/types'

/**
 * Group hourly forecast data into daily summaries.
 */
export function getDailySummaries(forecast: Forecast): DailySummary[] {
  const { times_utc, hourly_data, hourly_units } = forecast
  
  // Group hours by date
  const dailyGroups = new Map<string, number[]>()
  
  times_utc.forEach((timeStr, idx) => {
    const date = new Date(timeStr)
    const dateKey = date.toISOString().split('T')[0]
    
    if (!dailyGroups.has(dateKey)) {
      dailyGroups.set(dateKey, [])
    }
    dailyGroups.get(dateKey)!.push(idx)
  })
  
  // Build summaries for each day
  const summaries: DailySummary[] = []
  
  for (const [dateStr, indices] of dailyGroups) {
    const date = new Date(dateStr + 'T12:00:00Z')
    
    // Temperature
    const temps = hourly_data.temperature_2m 
      ? indices.map(i => hourly_data.temperature_2m[i]).filter((v): v is number => v !== null)
      : []
    
    // Snowfall - sum hourly values
    const snowfall = hourly_data.snowfall
      ? indices.reduce((sum, i) => sum + (hourly_data.snowfall[i] ?? 0), 0)
      : 0
    
    // Precipitation - sum hourly values
    const precipitation = hourly_data.precipitation
      ? indices.reduce((sum, i) => sum + (hourly_data.precipitation[i] ?? 0), 0)
      : 0
    
    // Wind
    const winds = hourly_data.wind_speed_10m
      ? indices.map(i => hourly_data.wind_speed_10m[i]).filter((v): v is number => v !== null)
      : []
    
    const gusts = hourly_data.wind_gusts_10m
      ? indices.map(i => hourly_data.wind_gusts_10m[i]).filter((v): v is number => v !== null)
      : []
    
    // Freezing level
    const freezingLevels = hourly_data.freezing_level_height
      ? indices.map(i => hourly_data.freezing_level_height[i]).filter((v): v is number => v !== null)
      : []
    
    summaries.push({
      date,
      dateStr,
      dayName: date.toLocaleDateString('en-US', { weekday: 'short' }),
      highTemp: temps.length > 0 ? Math.max(...temps) : null,
      lowTemp: temps.length > 0 ? Math.min(...temps) : null,
      snowfall,
      precipitation,
      maxWind: winds.length > 0 ? Math.max(...winds) : null,
      maxGusts: gusts.length > 0 ? Math.max(...gusts) : null,
      avgFreezingLevel: freezingLevels.length > 0
        ? freezingLevels.reduce((a, b) => a + b, 0) / freezingLevels.length
        : null,
      hours: indices.length,
    })
  }
  
  return summaries
}

/**
 * Calculate total snowfall for a forecast.
 */
export function getTotalSnowfall(forecast: Forecast): number {
  const snowfall = forecast.hourly_data.snowfall
  if (!snowfall) return 0
  return snowfall.reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Calculate total precipitation for a forecast.
 */
export function getTotalPrecipitation(forecast: Forecast): number {
  const precip = forecast.hourly_data.precipitation
  if (!precip) return 0
  return precip.reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Get snowfall for next N hours.
 */
export function getSnowfallNextHours(forecast: Forecast, hours: number): number {
  const snowfall = forecast.hourly_data.snowfall
  if (!snowfall) return 0
  return snowfall.slice(0, hours).reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Determine weather condition from daily summary.
 */
export function getWeatherCondition(summary: DailySummary): WeatherCondition {
  // Heavy snow: > 6 inches
  if (summary.snowfall > 15) return 'heavy-snow'  // ~15cm = 6in
  if (summary.snowfall > 5) return 'snow'          // ~5cm = 2in
  if (summary.snowfall > 1) return 'light-snow'    // ~1cm = trace
  
  // Rain if precipitation but no snow
  if (summary.precipitation > 5 && summary.snowfall < 1) return 'rain'
  
  // Temperature-based if dry
  if (summary.highTemp !== null && summary.highTemp < -10) return 'cold'
  if (summary.precipitation < 1) return 'sunny'
  
  return 'partly-cloudy'
}

/**
 * Get emoji for weather condition.
 */
export function getWeatherEmoji(condition: WeatherCondition): string {
  const emojis: Record<WeatherCondition, string> = {
    'heavy-snow': '🌨️',
    'snow': '❄️',
    'light-snow': '🌨️',
    'rain': '🌧️',
    'cloudy': '☁️',
    'partly-cloudy': '⛅',
    'sunny': '☀️',
    'cold': '🥶',
  }
  return emojis[condition]
}

/**
 * Format model run time.
 */
export function formatModelRunTime(isoString: string | null): string {
  if (!isoString) return 'Unknown'
  const date = new Date(isoString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

/**
 * Get the number of forecast days available.
 */
export function getForecastDays(forecast: Forecast): number {
  return Math.ceil(forecast.times_utc.length / 24)
}

