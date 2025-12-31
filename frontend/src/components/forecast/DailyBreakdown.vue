<script setup lang="ts">
import { computed } from 'vue'
import type { DailySummary } from '@/types'
import { useSettingsStore } from '@/stores/settings'
import { 
  convertTemperature, 
  convertPrecipitation, 
  convertWindSpeed,
  convertElevation,
  formatTemperature,
  formatSnowfall,
  formatWindSpeed,
  formatElevation
} from '@/utils/units'
import { getWeatherCondition, getWeatherEmoji } from '@/utils/forecast'

const props = defineProps<{
  summaries: DailySummary[]
  tempUnit?: string
  snowUnit?: string
  windUnit?: string
}>()

const settingsStore = useSettingsStore()

interface DisplayRow {
  date: Date
  dayName: string
  dateStr: string
  emoji: string
  highTemp: string
  lowTemp: string
  snow: string
  snowConservative: string
  snowEnhanced: string
  snowRatio: string | null
  snowRatioRaw: number | null
  rain: string | null
  hasRain: boolean
  wind: string
  freezingLevel: string
  freezingLevelRaw: number | null  // Raw value in user's unit for color coding
  isToday: boolean
}

const rows = computed<DisplayRow[]>(() => {
  const today = new Date().toISOString().split('T')[0]
  
  return props.summaries.map(s => {
    const condition = getWeatherCondition(s)
    const fromTemp = (props.tempUnit || '°C').replace('°', '') as 'C' | 'F'
    const fromSnow = props.snowUnit || 'cm'
    const fromWind = props.windUnit || 'km/h'
    
    // Convert values
    const high = convertTemperature(s.highTemp, fromTemp, settingsStore.temperatureUnit)
    const low = convertTemperature(s.lowTemp, fromTemp, settingsStore.temperatureUnit)
    
    // Get snowfall based on mode
    const snowConservative = convertPrecipitation(s.snowfall, fromSnow, settingsStore.precipitationUnit) ?? 0
    const snowEnhanced = convertPrecipitation(s.enhancedSnowfall, fromSnow, settingsStore.precipitationUnit) ?? snowConservative
    const snow = settingsStore.snowfallMode === 'enhanced' ? snowEnhanced : snowConservative
    
    // Rain (convert from mm)
    const rainMm = s.rain ?? 0
    const rainConverted = rainMm > 0.1 ? convertPrecipitation(rainMm, 'mm', settingsStore.precipitationUnit) : null
    
    const wind = convertWindSpeed(s.maxWind, fromWind, settingsStore.windSpeedUnit)
    const freezing = convertElevation(s.avgFreezingLevel, 'm', settingsStore.elevationUnit)
    
    return {
      date: s.date,
      dayName: s.dayName,
      dateStr: s.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      emoji: getWeatherEmoji(condition),
      highTemp: formatTemperature(high, settingsStore.temperatureUnit),
      lowTemp: formatTemperature(low, settingsStore.temperatureUnit),
      snow: formatSnowfall(snow, settingsStore.precipitationUnit),
      snowConservative: formatSnowfall(snowConservative, settingsStore.precipitationUnit),
      snowEnhanced: formatSnowfall(snowEnhanced, settingsStore.precipitationUnit),
      snowRatio: s.avgSnowRatio !== null ? `${Math.round(s.avgSnowRatio)}:1` : null,
      snowRatioRaw: s.avgSnowRatio,
      rain: rainConverted !== null && rainConverted >= 0.1 
        ? (rainConverted < 1 ? rainConverted.toFixed(1) : Math.round(rainConverted).toString())
        : null,
      hasRain: rainMm > 0.5,
      wind: formatWindSpeed(wind, settingsStore.windSpeedUnit),
      freezingLevel: formatElevation(freezing, settingsStore.elevationUnit),
      freezingLevelRaw: freezing,
      isToday: s.dateStr === today,
    }
  })
})

// Check if we should show comparison
const showSnowComparison = computed(() => {
  if (!settingsStore.showBothSnowfallModes) return false
  // Check if any day has meaningful difference
  return props.summaries.some(s => {
    const diff = Math.abs(s.enhancedSnowfall - s.snowfall)
    return diff > 1 || (s.snowfall > 0 && diff > s.snowfall * 0.1)
  })
})

// Get CSS class for snow level based on elevation
// Lower snow levels = better for skiing (more mountain gets snow)
function getSnowLevelClass(elevation: number): string {
  // Thresholds in user's unit (ft or m)
  const isFeet = settingsStore.elevationUnit === 'ft'
  
  // Typical resort base elevations:
  // - Low: ~6,000 ft / 1,800 m
  // - Mid: ~8,000 ft / 2,400 m  
  // - High: ~10,000 ft / 3,000 m
  
  const lowThreshold = isFeet ? 6000 : 1800
  const midThreshold = isFeet ? 8000 : 2400
  const highThreshold = isFeet ? 10000 : 3000
  
  if (elevation <= lowThreshold) {
    // Snow to valley floor - excellent
    return 'text-snow-400 font-medium'
  } else if (elevation <= midThreshold) {
    // Snow to mid-mountain - good
    return 'text-green-400'
  } else if (elevation <= highThreshold) {
    // Snow only at upper elevations - fair
    return 'text-yellow-400'
  } else {
    // Very high snow level - may be rain at base
    return 'text-orange-400'
  }
}

// Get CSS class for snow ratio
// Higher ratios = lighter, fluffier powder
function getSnowRatioClass(ratio: number): string {
  if (ratio >= 20) {
    // Ultra-light powder (cold smoke)
    return 'text-snow-300 font-semibold'
  } else if (ratio >= 15) {
    // Light powder - excellent
    return 'text-snow-400 font-medium'
  } else if (ratio >= 12) {
    // Good powder
    return 'text-green-400'
  } else if (ratio >= 10) {
    // Average snow
    return 'text-mountain-300'
  } else {
    // Heavy/wet snow
    return 'text-yellow-400'
  }
}
</script>

<template>
  <div class="glass-card overflow-hidden">
    <div class="px-6 py-4 border-b border-mountain-700/50 flex items-center justify-between">
      <h3 class="font-display font-semibold text-white">Daily Breakdown</h3>
      <span v-if="showSnowComparison" class="text-xs text-mountain-400">
        Showing {{ settingsStore.snowfallMode === 'enhanced' ? 'enhanced' : 'conservative' }} snowfall
      </span>
    </div>
    
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="text-left text-xs text-mountain-400 uppercase tracking-wider">
            <th class="px-6 py-3 font-medium">Day</th>
            <th class="px-4 py-3 font-medium text-center">Cond</th>
            <th class="px-4 py-3 font-medium text-center">Hi / Lo</th>
            <th class="px-4 py-3 font-medium text-center">Snow</th>
            <th class="px-3 py-3 font-medium text-center">Ratio</th>
            <th class="px-4 py-3 font-medium text-center">Rain</th>
            <th class="px-4 py-3 font-medium text-center">Wind</th>
            <th class="px-4 py-3 font-medium text-center">Snow Level</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-mountain-700/30">
          <tr 
            v-for="row in rows" 
            :key="row.dateStr"
            class="hover:bg-mountain-800/30 transition-colors"
            :class="{ 'bg-snow-500/5': row.isToday }"
          >
            <td class="px-6 py-4">
              <div class="flex flex-col">
                <span class="text-white font-medium" :class="{ 'text-snow-400': row.isToday }">
                  {{ row.isToday ? 'Today' : row.dayName }}
                </span>
                <span class="text-mountain-400 text-sm">{{ row.dateStr }}</span>
              </div>
            </td>
            <td class="px-4 py-4 text-center text-2xl">
              {{ row.emoji }}
            </td>
            <td class="px-4 py-4 text-center">
              <span class="text-white font-mono">{{ row.highTemp }}</span>
              <span class="text-mountain-500 mx-1">/</span>
              <span class="text-mountain-400 font-mono">{{ row.lowTemp }}</span>
            </td>
            <td class="px-4 py-4 text-center">
              <div class="flex flex-col items-center gap-0.5">
                <span 
                  class="font-mono font-medium"
                  :class="row.snow === 'trace' ? 'text-mountain-400' : 'text-snow-400'"
                >
                  {{ row.snow }}
                </span>
                <!-- Show comparison when enabled and values differ -->
                <div v-if="showSnowComparison && row.snowConservative !== row.snowEnhanced" class="flex items-center gap-1 text-xs">
                  <span class="text-mountain-500">{{ row.snowConservative }}</span>
                  <span class="text-mountain-600">→</span>
                  <span class="text-snow-400/70">{{ row.snowEnhanced }}</span>
                </div>
              </div>
            </td>
            <td class="px-3 py-4 text-center font-mono text-sm">
              <span 
                v-if="row.snowRatioRaw !== null"
                :class="getSnowRatioClass(row.snowRatioRaw)"
                :title="`${row.snowRatioRaw?.toFixed(1)}:1 snow-to-liquid ratio`"
              >
                {{ row.snowRatio }}
              </span>
              <span v-else class="text-mountain-600">—</span>
            </td>
            <td class="px-4 py-4 text-center">
              <span 
                v-if="row.rain" 
                class="font-mono text-blue-400"
              >
                {{ row.rain }}"
              </span>
              <span v-else class="text-mountain-600">—</span>
            </td>
            <td class="px-4 py-4 text-center text-mountain-300 font-mono">
              {{ row.wind }}
            </td>
            <td class="px-4 py-4 text-center font-mono">
              <span 
                v-if="row.freezingLevelRaw !== null"
                :class="getSnowLevelClass(row.freezingLevelRaw)"
              >
                {{ row.freezingLevel }}
              </span>
              <span v-else class="text-mountain-600">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

