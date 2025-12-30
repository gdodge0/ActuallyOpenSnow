/**
 * Unit conversion utilities.
 */

import type { TemperatureUnit, PrecipitationUnit, WindSpeedUnit, ElevationUnit } from '@/types'

// Temperature conversions
export function convertTemperature(
  value: number | null,
  from: TemperatureUnit,
  to: TemperatureUnit
): number | null {
  if (value === null) return null
  if (from === to) return value

  // Convert to Celsius first
  let celsius: number
  if (from === 'C') {
    celsius = value
  } else {
    celsius = (value - 32) * (5 / 9)
  }

  // Convert from Celsius to target
  if (to === 'C') {
    return celsius
  } else {
    return celsius * (9 / 5) + 32
  }
}

// Precipitation / length conversions
export function convertPrecipitation(
  value: number | null,
  from: string,
  to: PrecipitationUnit
): number | null {
  if (value === null) return null

  // Normalize 'from' unit
  const fromNorm = from.toLowerCase()
  const toNorm = to.toLowerCase()

  // Convert to mm first
  let mm: number
  if (fromNorm === 'mm') {
    mm = value
  } else if (fromNorm === 'cm') {
    mm = value * 10
  } else if (fromNorm === 'in' || fromNorm === 'inch') {
    mm = value * 25.4
  } else if (fromNorm === 'm') {
    mm = value * 1000
  } else {
    mm = value // Assume mm
  }

  // Convert from mm to target
  if (toNorm === 'cm') {
    return mm / 10
  } else if (toNorm === 'in') {
    return mm / 25.4
  } else {
    return mm
  }
}

// Wind speed conversions
export function convertWindSpeed(
  value: number | null,
  from: string,
  to: WindSpeedUnit
): number | null {
  if (value === null) return null

  const fromNorm = from.toLowerCase()
  const toNorm = to.toLowerCase()

  // Convert to km/h first
  let kmh: number
  if (fromNorm === 'kmh' || fromNorm === 'km/h') {
    kmh = value
  } else if (fromNorm === 'ms' || fromNorm === 'm/s') {
    kmh = value * 3.6
  } else if (fromNorm === 'mph') {
    kmh = value * 1.60934
  } else if (fromNorm === 'kn' || fromNorm === 'knots') {
    kmh = value * 1.852
  } else {
    kmh = value
  }

  // Convert from km/h to target
  if (toNorm === 'kmh') {
    return kmh
  } else if (toNorm === 'ms') {
    return kmh / 3.6
  } else if (toNorm === 'mph') {
    return kmh / 1.60934
  } else {
    return kmh
  }
}

// Elevation conversions
export function convertElevation(
  value: number | null,
  from: string,
  to: ElevationUnit
): number | null {
  if (value === null) return null

  const fromNorm = from.toLowerCase()
  const toNorm = to.toLowerCase()

  // Convert to meters first
  let m: number
  if (fromNorm === 'm' || fromNorm === 'meters') {
    m = value
  } else if (fromNorm === 'ft' || fromNorm === 'feet') {
    m = value * 0.3048
  } else {
    m = value
  }

  // Convert from meters to target
  if (toNorm === 'm') {
    return m
  } else {
    return m / 0.3048
  }
}

// Formatting functions
export function formatTemperature(value: number | null, unit: TemperatureUnit): string {
  if (value === null) return '--'
  return `${Math.round(value)}°${unit}`
}

export function formatSnowfall(inches: number): string {
  if (inches < 0.1) return 'trace'
  if (inches < 1) return inches.toFixed(1) + '"'
  return Math.round(inches) + '"'
}

export function formatPrecipitation(value: number, unit: PrecipitationUnit): string {
  if (value < 0.01) return 'trace'
  if (unit === 'in') {
    return value < 1 ? value.toFixed(2) + '"' : value.toFixed(1) + '"'
  }
  return value < 1 ? value.toFixed(1) + ' cm' : Math.round(value) + ' cm'
}

export function formatWindSpeed(value: number | null, unit: WindSpeedUnit): string {
  if (value === null) return '--'
  const unitLabel = unit === 'kmh' ? ' km/h' : unit === 'mph' ? ' mph' : ' m/s'
  return Math.round(value) + unitLabel
}

export function formatElevation(value: number | null, unit: ElevationUnit): string {
  if (value === null) return '--'
  if (unit === 'ft') {
    return Math.round(value).toLocaleString() + "'"
  }
  return Math.round(value).toLocaleString() + ' m'
}

