/**
 * TypeScript types matching the Python weather API.
 */

// Resort type matching backend
export interface Resort {
  slug: string
  name: string
  state: string
  country: string
  lat: number
  lon: number
  base_elevation_m: number
  summit_elevation_m: number
}

// Model info type
export interface ModelInfo {
  model_id: string
  display_name: string
  provider: string
  max_forecast_days: number
  resolution_degrees: number
  description: string
}

// Forecast response matching Python Forecast.to_dict()
export interface Forecast {
  lat: number
  lon: number
  api_lat: number
  api_lon: number
  elevation_m: number | null
  model_id: string
  model_run_utc: string | null
  times_utc: string[]
  hourly_data: Record<string, (number | null)[]>
  hourly_units: Record<string, string>
  // Enhanced snowfall data (calculated from precipitation + temperature)
  enhanced_hourly_data?: {
    enhanced_snowfall: number[]
    rain: number[]
  }
  enhanced_hourly_units?: {
    enhanced_snowfall: string
    rain: string
  }
  // Ensemble prediction ranges (10th/90th percentile from GEFS/ECMWF ENS)
  ensemble_ranges?: {
    enhanced_snowfall?: { p10: number[]; p90: number[] }
    temperature_2m?: { p10: number[]; p90: number[] }
    precipitation?: { p10: number[]; p90: number[] }
  }
}

// Multi-model comparison response
export interface ComparisonResponse {
  lat: number
  lon: number
  elevation_m: number | null
  forecasts: Record<string, Forecast>
}

// Unit preferences
export type TemperatureUnit = 'C' | 'F'
export type PrecipitationUnit = 'cm' | 'in'
export type WindSpeedUnit = 'kmh' | 'mph' | 'ms'
export type ElevationUnit = 'm' | 'ft'

// Snowfall calculation mode
// - 'conservative': Use raw model snowfall (typically 10:1 ratio)
// - 'enhanced': Use temperature-adjusted ratios (more accurate for cold powder)
export type SnowfallMode = 'conservative' | 'enhanced'

export interface UnitPreferences {
  temperature: TemperatureUnit
  precipitation: PrecipitationUnit
  windSpeed: WindSpeedUnit
  elevation: ElevationUnit
}

// Daily summary computed from hourly data
export interface DailySummary {
  date: Date
  dateStr: string
  dayName: string
  highTemp: number | null
  lowTemp: number | null
  snowfall: number              // Conservative (raw model) snowfall
  enhancedSnowfall: number      // Enhanced (temperature-adjusted) snowfall
  rain: number                  // Liquid precipitation (rain)
  precipitation: number         // Total precipitation (water equivalent)
  avgSnowRatio: number | null   // Average snow-to-liquid ratio used
  maxWind: number | null
  maxGusts: number | null
  avgFreezingLevel: number | null
  hours: number
}

// Weather condition for icons
export type WeatherCondition = 
  | 'heavy-snow'
  | 'snow'
  | 'light-snow'
  | 'rain'
  | 'cloudy'
  | 'partly-cloudy'
  | 'sunny'
  | 'cold'

// Custom location saved by user
export interface CustomLocation {
  id: string
  name: string
  lat: number
  lon: number
  elevation_m?: number
  createdAt: number
}

