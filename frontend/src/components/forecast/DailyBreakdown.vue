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
  wind: string
  freezingLevel: string
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
    const snow = convertPrecipitation(s.snowfall, fromSnow, settingsStore.precipitationUnit) ?? 0
    const wind = convertWindSpeed(s.maxWind, fromWind, settingsStore.windSpeedUnit)
    const freezing = convertElevation(s.avgFreezingLevel, 'm', settingsStore.elevationUnit)
    
    return {
      date: s.date,
      dayName: s.dayName,
      dateStr: s.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      emoji: getWeatherEmoji(condition),
      highTemp: formatTemperature(high, settingsStore.temperatureUnit),
      lowTemp: formatTemperature(low, settingsStore.temperatureUnit),
      snow: formatSnowfall(snow),
      wind: formatWindSpeed(wind, settingsStore.windSpeedUnit),
      freezingLevel: formatElevation(freezing, settingsStore.elevationUnit),
      isToday: s.dateStr === today,
    }
  })
})
</script>

<template>
  <div class="glass-card overflow-hidden">
    <div class="px-6 py-4 border-b border-mountain-700/50">
      <h3 class="font-display font-semibold text-white">Daily Breakdown</h3>
    </div>
    
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="text-left text-xs text-mountain-400 uppercase tracking-wider">
            <th class="px-6 py-3 font-medium">Day</th>
            <th class="px-4 py-3 font-medium text-center">Cond</th>
            <th class="px-4 py-3 font-medium text-center">Hi / Lo</th>
            <th class="px-4 py-3 font-medium text-center">Snow</th>
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
              <span 
                class="font-mono font-medium"
                :class="row.snow === 'trace' ? 'text-mountain-400' : 'text-snow-400'"
              >
                {{ row.snow }}
              </span>
            </td>
            <td class="px-4 py-4 text-center text-mountain-300 font-mono">
              {{ row.wind }}
            </td>
            <td class="px-4 py-4 text-center text-mountain-300 font-mono">
              {{ row.freezingLevel }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

