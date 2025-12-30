<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useResortsStore } from '@/stores/resorts'
import { useForecastStore } from '@/stores/forecast'
import { useSettingsStore } from '@/stores/settings'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { getDailySummaries, getTotalSnowfall } from '@/utils/forecast'
import { convertPrecipitation, formatSnowfall } from '@/utils/units'
import type { Forecast } from '@/types'

const resortsStore = useResortsStore()
const forecastStore = useForecastStore()
const settingsStore = useSettingsStore()

const selectedResort = ref('')
const selectedModels = ref<string[]>(['blend', 'gfs', 'ifs', 'aifs'])

// Load comparison when resort changes
watch(selectedResort, async (slug) => {
  if (slug) {
    await forecastStore.loadComparison(slug, selectedModels.value)
  }
})

// Get snow total for a forecast
function getSnowTotal(forecast: Forecast): string {
  const totalCm = getTotalSnowfall(forecast)
  const converted = convertPrecipitation(totalCm, forecast.hourly_units.snowfall || 'cm', settingsStore.precipitationUnit)
  return formatSnowfall(converted ?? 0)
}

// Daily comparison data
const dailyComparison = computed(() => {
  if (!forecastStore.comparison) return []
  
  const result: { date: string; dayName: string; models: Record<string, string> }[] = []
  const models = Object.keys(forecastStore.comparison.forecasts)
  
  if (models.length === 0) return []
  
  // Get daily summaries for first model as reference
  const firstForecast = forecastStore.comparison.forecasts[models[0]]
  const summaries = getDailySummaries(firstForecast)
  
  for (const summary of summaries) {
    const row: { date: string; dayName: string; models: Record<string, string> } = {
      date: summary.dateStr,
      dayName: summary.dayName,
      models: {},
    }
    
    for (const modelId of models) {
      const forecast = forecastStore.comparison.forecasts[modelId]
      const modelSummaries = getDailySummaries(forecast)
      const daySummary = modelSummaries.find(s => s.dateStr === summary.dateStr)
      
      if (daySummary) {
        const snowCm = daySummary.snowfall
        const converted = convertPrecipitation(snowCm, forecast.hourly_units.snowfall || 'cm', settingsStore.precipitationUnit)
        row.models[modelId] = formatSnowfall(converted ?? 0)
      } else {
        row.models[modelId] = '--'
      }
    }
    
    result.push(row)
  }
  
  return result
})
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-display font-bold text-white">Model Comparison</h1>
    <p class="text-mountain-400">
      Compare snowfall predictions from different weather models side-by-side.
    </p>
    
    <!-- Resort selector -->
    <div class="glass-card p-6">
      <label class="block text-sm font-medium text-mountain-300 mb-2">
        Select a Resort
      </label>
      <select
        v-model="selectedResort"
        class="w-full md:w-96 px-4 py-3 rounded-lg bg-mountain-800 border border-mountain-700 text-white focus:outline-none focus:ring-2 focus:ring-snow-500"
      >
        <option value="" disabled>Choose a resort...</option>
        <option 
          v-for="resort in resortsStore.resorts" 
          :key="resort.slug" 
          :value="resort.slug"
        >
          {{ resort.name }} ({{ resort.state }})
        </option>
      </select>
    </div>
    
    <!-- Loading -->
    <div v-if="forecastStore.loading" class="flex justify-center py-16">
      <LoadingSpinner size="lg" text="Loading comparison..." />
    </div>
    
    <!-- Error -->
    <ErrorAlert 
      v-else-if="forecastStore.error"
      :message="forecastStore.error"
    />
    
    <!-- Comparison Results -->
    <template v-else-if="forecastStore.comparison">
      <!-- Total comparison -->
      <div class="glass-card p-6">
        <h2 class="font-display font-semibold text-white mb-4">7-Day Snowfall Total</h2>
        <div class="space-y-3">
          <div 
            v-for="(forecast, modelId) in forecastStore.comparison.forecasts"
            :key="modelId"
            class="flex items-center gap-4"
          >
            <div class="w-16 text-mountain-300 font-medium">
              {{ modelId.toUpperCase() }}
            </div>
            <div class="flex-1 h-8 bg-mountain-800 rounded-lg overflow-hidden">
              <div 
                class="h-full bg-gradient-to-r from-snow-500 to-snow-400 rounded-lg flex items-center justify-end px-3"
                :style="{ width: `${Math.min(100, getTotalSnowfall(forecast) * 5)}%` }"
              >
                <span class="text-mountain-950 font-mono text-sm font-bold">
                  {{ getSnowTotal(forecast) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Daily comparison table -->
      <div class="glass-card overflow-hidden">
        <div class="px-6 py-4 border-b border-mountain-700/50">
          <h2 class="font-display font-semibold text-white">Daily Comparison</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-left text-xs text-mountain-400 uppercase tracking-wider">
                <th class="px-6 py-3 font-medium">Day</th>
                <th 
                  v-for="modelId in Object.keys(forecastStore.comparison.forecasts)"
                  :key="modelId"
                  class="px-4 py-3 font-medium text-center"
                >
                  {{ modelId.toUpperCase() }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-mountain-700/30">
              <tr 
                v-for="row in dailyComparison"
                :key="row.date"
                class="hover:bg-mountain-800/30 transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex flex-col">
                    <span class="text-white font-medium">{{ row.dayName }}</span>
                    <span class="text-mountain-400 text-sm">{{ row.date }}</span>
                  </div>
                </td>
                <td 
                  v-for="(value, modelId) in row.models"
                  :key="modelId"
                  class="px-4 py-4 text-center"
                >
                  <span 
                    class="font-mono font-medium"
                    :class="value === 'trace' || value === '--' ? 'text-mountain-500' : 'text-snow-400'"
                  >
                    {{ value }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
    
    <!-- No selection -->
    <div v-else-if="!selectedResort" class="text-center py-16">
      <div class="text-5xl mb-4">📊</div>
      <p class="text-mountain-400">
        Select a resort above to compare model forecasts.
      </p>
    </div>
  </div>
</template>

