/**
 * Settings store for user preferences.
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { TemperatureUnit, PrecipitationUnit, WindSpeedUnit, ElevationUnit } from '@/types'

const STORAGE_KEY = 'actuallyopensnow-settings'

interface SettingsState {
  temperatureUnit: TemperatureUnit
  precipitationUnit: PrecipitationUnit
  windSpeedUnit: WindSpeedUnit
  elevationUnit: ElevationUnit
  theme: 'dark' | 'light'
}

const defaultSettings: SettingsState = {
  temperatureUnit: 'F',
  precipitationUnit: 'in',
  windSpeedUnit: 'mph',
  elevationUnit: 'ft',
  theme: 'dark',
}

function loadSettings(): SettingsState {
  if (typeof localStorage === 'undefined') {
    return defaultSettings
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) }
    }
  } catch {
    // Ignore localStorage errors
  }
  return defaultSettings
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = loadSettings()
  
  const temperatureUnit = ref<TemperatureUnit>(initial.temperatureUnit)
  const precipitationUnit = ref<PrecipitationUnit>(initial.precipitationUnit)
  const windSpeedUnit = ref<WindSpeedUnit>(initial.windSpeedUnit)
  const elevationUnit = ref<ElevationUnit>(initial.elevationUnit)
  const theme = ref<'dark' | 'light'>(initial.theme)
  
  // Persist settings on change
  function saveSettings() {
    if (typeof localStorage === 'undefined') return
    const settings: SettingsState = {
      temperatureUnit: temperatureUnit.value,
      precipitationUnit: precipitationUnit.value,
      windSpeedUnit: windSpeedUnit.value,
      elevationUnit: elevationUnit.value,
      theme: theme.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  }
  
  // Watch all settings for changes
  watch([temperatureUnit, precipitationUnit, windSpeedUnit, elevationUnit, theme], saveSettings)
  
  // Toggle between imperial and metric
  function setImperial() {
    temperatureUnit.value = 'F'
    precipitationUnit.value = 'in'
    windSpeedUnit.value = 'mph'
    elevationUnit.value = 'ft'
  }
  
  function setMetric() {
    temperatureUnit.value = 'C'
    precipitationUnit.value = 'cm'
    windSpeedUnit.value = 'kmh'
    elevationUnit.value = 'm'
  }
  
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', theme.value === 'dark')
    }
  }
  
  // Initialize theme (only in browser)
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
  }
  
  return {
    temperatureUnit,
    precipitationUnit,
    windSpeedUnit,
    elevationUnit,
    theme,
    setImperial,
    setMetric,
    toggleTheme,
  }
})

