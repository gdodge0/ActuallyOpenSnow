/**
 * Forecast data processing utilities.
 */

import type { Forecast, DailySummary, WeatherCondition } from '@/types'

/**
 * Get snow-to-liquid ratio based on temperature (Celsius).
 * Uses linear interpolation between reference points.
 */
function getSnowRatio(tempC: number): number {
  // Reference points: [temperature_celsius, ratio]
  const points: [number, number][] = [
    [2, 0],      // Above freezing - rain
    [0, 8],      // Freezing - wet snow
    [-3, 10],    // Just below freezing
    [-6, 12],    // Cold
    [-9, 15],    // Colder - powder
    [-12, 18],   // Very cold
    [-15, 20],   // Extremely cold
    [-20, 25],   // Arctic
    [-25, 30],   // Ultra-cold
  ]
  
  // Above warmest point
  if (tempC >= points[0][0]) return points[0][1]
  // Below coldest point
  if (tempC <= points[points.length - 1][0]) return points[points.length - 1][1]
  
  // Find and interpolate between two points
  for (let i = 0; i < points.length - 1; i++) {
    const [t1, r1] = points[i]
    const [t2, r2] = points[i + 1]
    
    if (t2 <= tempC && tempC < t1) {
      const fraction = (t1 - tempC) / (t1 - t2)
      return r1 + (r2 - r1) * fraction
    }
  }
  
  return 10 // Fallback
}

/**
 * Group hourly forecast data into daily summaries.
 */
export function getDailySummaries(forecast: Forecast): DailySummary[] {
  const { times_utc, hourly_data, enhanced_hourly_data } = forecast
  
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
    
    // Conservative snowfall (raw model) - sum hourly values
    const snowfall = hourly_data.snowfall
      ? indices.reduce((sum, i) => sum + (hourly_data.snowfall[i] ?? 0), 0)
      : 0
    
    // Enhanced snowfall (temperature-adjusted)
    const enhancedSnowfall = enhanced_hourly_data?.enhanced_snowfall
      ? indices.reduce((sum, i) => sum + (enhanced_hourly_data.enhanced_snowfall[i] ?? 0), 0)
      : snowfall  // Fall back to conservative if enhanced not available
    
    // Rain (liquid precipitation)
    const rain = enhanced_hourly_data?.rain
      ? indices.reduce((sum, i) => sum + (enhanced_hourly_data.rain[i] ?? 0), 0)
      : 0
    
    // Precipitation (total water equivalent) - sum hourly values
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
    
    // Calculate average snow ratio (weighted by precipitation)
    let avgSnowRatio: number | null = null
    if (hourly_data.temperature_2m && hourly_data.precipitation) {
      let totalPrecip = 0
      let weightedRatioSum = 0
      
      for (const i of indices) {
        const temp = hourly_data.temperature_2m[i]
        const precip = hourly_data.precipitation[i]
        
        if (temp !== null && precip !== null && precip > 0 && temp <= 2) {
          const ratio = getSnowRatio(temp)
          weightedRatioSum += ratio * precip
          totalPrecip += precip
        }
      }
      
      if (totalPrecip > 0) {
        avgSnowRatio = weightedRatioSum / totalPrecip
      } else if (temps.length > 0) {
        // No precip, just use average temp to show what ratio would be
        const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length
        if (avgTemp <= 2) {
          avgSnowRatio = getSnowRatio(avgTemp)
        }
      }
    }
    
    summaries.push({
      date,
      dateStr,
      dayName: date.toLocaleDateString('en-US', { weekday: 'short' }),
      highTemp: temps.length > 0 ? Math.max(...temps) : null,
      lowTemp: temps.length > 0 ? Math.min(...temps) : null,
      snowfall,
      enhancedSnowfall,
      rain,
      precipitation,
      avgSnowRatio,
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
 * Calculate total snowfall for a forecast (conservative/raw model).
 */
export function getTotalSnowfall(forecast: Forecast): number {
  const snowfall = forecast.hourly_data.snowfall
  if (!snowfall) return 0
  return snowfall.reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Calculate total enhanced snowfall for a forecast (temperature-adjusted).
 */
export function getTotalEnhancedSnowfall(forecast: Forecast): number {
  const enhancedSnowfall = forecast.enhanced_hourly_data?.enhanced_snowfall
  if (!enhancedSnowfall) return getTotalSnowfall(forecast)  // Fall back to conservative
  return enhancedSnowfall.reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Calculate total rain for a forecast.
 */
export function getTotalRain(forecast: Forecast): number {
  const rain = forecast.enhanced_hourly_data?.rain
  if (!rain) return 0
  return rain.reduce((sum, v) => sum + (v ?? 0), 0)
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
 * Get snowfall for next N hours (conservative).
 */
export function getSnowfallNextHours(forecast: Forecast, hours: number): number {
  const snowfall = forecast.hourly_data.snowfall
  if (!snowfall) return 0
  return snowfall.slice(0, hours).reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Get enhanced snowfall for next N hours (temperature-adjusted).
 */
export function getEnhancedSnowfallNextHours(forecast: Forecast, hours: number): number {
  const enhancedSnowfall = forecast.enhanced_hourly_data?.enhanced_snowfall
  if (!enhancedSnowfall) return getSnowfallNextHours(forecast, hours)
  return enhancedSnowfall.slice(0, hours).reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Get rain for next N hours.
 */
export function getRainNextHours(forecast: Forecast, hours: number): number {
  const rain = forecast.enhanced_hourly_data?.rain
  if (!rain) return 0
  return rain.slice(0, hours).reduce((sum, v) => sum + (v ?? 0), 0)
}

/**
 * Determine weather condition from daily summary.
 * Uses enhanced snowfall for more accurate condition detection.
 */
export function getWeatherCondition(summary: DailySummary): WeatherCondition {
  // Use enhanced snowfall for condition detection
  const snowfall = summary.enhancedSnowfall
  
  // Heavy snow: > 6 inches (~15cm)
  if (snowfall > 15) return 'heavy-snow'
  if (snowfall > 5) return 'snow'          // ~5cm = 2in
  if (snowfall > 1) return 'light-snow'    // ~1cm = trace
  
  // Rain if significant rain expected
  if (summary.rain > 2) return 'rain'  // > 2mm rain
  
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

