<script setup lang="ts">
import { computed } from 'vue'
import type { Forecast } from '@/types'
import { useSettingsStore } from '@/stores/settings'
import { 
  convertTemperature, 
  convertWindSpeed, 
  convertElevation,
  formatTemperature,
  formatWindSpeed,
  formatElevation
} from '@/utils/units'

const props = defineProps<{
  forecast: Forecast
}>()

const settingsStore = useSettingsStore()

// Get current conditions (first hour)
const currentTemp = computed(() => {
  const temps = props.forecast.hourly_data.temperature_2m
  if (!temps || temps.length === 0) return null
  const fromUnit = (props.forecast.hourly_units.temperature_2m || '°C').replace('°', '') as 'C' | 'F'
  return convertTemperature(temps[0], fromUnit, settingsStore.temperatureUnit)
})

const currentWind = computed(() => {
  const winds = props.forecast.hourly_data.wind_speed_10m
  if (!winds || winds.length === 0) return null
  const fromUnit = props.forecast.hourly_units.wind_speed_10m || 'km/h'
  return convertWindSpeed(winds[0], fromUnit, settingsStore.windSpeedUnit)
})

const currentGusts = computed(() => {
  const gusts = props.forecast.hourly_data.wind_gusts_10m
  if (!gusts || gusts.length === 0) return null
  const fromUnit = props.forecast.hourly_units.wind_gusts_10m || 'km/h'
  return convertWindSpeed(gusts[0], fromUnit, settingsStore.windSpeedUnit)
})

const currentFreezingLevel = computed(() => {
  const levels = props.forecast.hourly_data.freezing_level_height
  if (!levels || levels.length === 0) return null
  return convertElevation(levels[0], 'm', settingsStore.elevationUnit)
})

const elevation = computed(() => {
  return convertElevation(props.forecast.elevation_m, 'm', settingsStore.elevationUnit)
})
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <!-- Temperature -->
    <div class="glass-card p-4">
      <div class="flex items-center gap-2 text-mountain-400 text-sm mb-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        Temperature
      </div>
      <div class="text-2xl font-display font-bold text-white">
        {{ formatTemperature(currentTemp, settingsStore.temperatureUnit) }}
      </div>
    </div>
    
    <!-- Wind -->
    <div class="glass-card p-4">
      <div class="flex items-center gap-2 text-mountain-400 text-sm mb-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
        </svg>
        Wind
      </div>
      <div class="text-2xl font-display font-bold text-white">
        {{ formatWindSpeed(currentWind, settingsStore.windSpeedUnit) }}
      </div>
      <div v-if="currentGusts" class="text-sm text-mountain-400 mt-1">
        Gusts: {{ formatWindSpeed(currentGusts, settingsStore.windSpeedUnit) }}
      </div>
    </div>
    
    <!-- Freezing Level -->
    <div class="glass-card p-4">
      <div class="flex items-center gap-2 text-mountain-400 text-sm mb-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
        </svg>
        Snow Level
      </div>
      <div class="text-2xl font-display font-bold text-white">
        {{ formatElevation(currentFreezingLevel, settingsStore.elevationUnit) }}
      </div>
    </div>
    
    <!-- Elevation -->
    <div class="glass-card p-4">
      <div class="flex items-center gap-2 text-mountain-400 text-sm mb-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
        </svg>
        Elevation
      </div>
      <div class="text-2xl font-display font-bold text-white">
        {{ formatElevation(elevation, settingsStore.elevationUnit) }}
      </div>
    </div>
  </div>
</template>

