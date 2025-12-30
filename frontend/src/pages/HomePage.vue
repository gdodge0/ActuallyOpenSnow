<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useResortsStore } from '@/stores/resorts'
import { useSettingsStore } from '@/stores/settings'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { Resort, Forecast } from '@/types'
import { fetchBatchForecasts } from '@/utils/api'
import { getTotalSnowfall } from '@/utils/forecast'
import { convertPrecipitation, formatSnowfall } from '@/utils/units'

const resortsStore = useResortsStore()
const settingsStore = useSettingsStore()

// Featured resorts with quick forecasts
const featuredSlugs = ['jackson-hole', 'alta', 'mammoth-mountain', 'vail', 'big-sky', 'whistler-blackcomb']
const featuredForecasts = ref<Map<string, Forecast>>(new Map())
const loadingFeatured = ref(true)

// Load featured resort forecasts using batch endpoint (single HTTP request)
onMounted(async () => {
  loadingFeatured.value = true
  
  try {
    // Fetch all blend forecasts in a single batch request
    const forecasts = await fetchBatchForecasts(featuredSlugs, 'blend')
    featuredForecasts.value = forecasts
  } catch (e) {
    console.error('Failed to load featured forecasts:', e)
  }
  
  loadingFeatured.value = false
})

// Get featured resorts with data
const featuredResorts = computed(() => {
  return featuredSlugs
    .map(slug => resortsStore.getResortBySlug(slug))
    .filter((r): r is Resort => r !== undefined)
})

// Get snow total for a resort
function getSnowTotal(slug: string): string {
  const forecast = featuredForecasts.value.get(slug)
  if (!forecast) return '--'
  
  const totalCm = getTotalSnowfall(forecast)
  const converted = convertPrecipitation(totalCm, forecast.hourly_units.snowfall || 'cm', settingsStore.precipitationUnit)
  return formatSnowfall(converted ?? 0)
}

// Check if resort has powder (> 6" expected)
function hasPowder(slug: string): boolean {
  const forecast = featuredForecasts.value.get(slug)
  if (!forecast) return false
  
  const totalCm = getTotalSnowfall(forecast)
  const inches = convertPrecipitation(totalCm, forecast.hourly_units.snowfall || 'cm', 'in')
  return (inches ?? 0) >= 6
}

// Get the resort with most snow
const topSnowResort = computed(() => {
  let maxSnowCm = 0
  let topSlug = ''
  let topForecast: Forecast | null = null
  
  for (const [slug, forecast] of featuredForecasts.value) {
    const totalCm = getTotalSnowfall(forecast)
    if (totalCm > maxSnowCm) {
      maxSnowCm = totalCm
      topSlug = slug
      topForecast = forecast
    }
  }
  
  if (!topSlug || !topForecast) return null
  
  const resort = resortsStore.getResortBySlug(topSlug)
  
  // Convert to inches for powder threshold check (6" = powder day)
  const inches = convertPrecipitation(maxSnowCm, 'cm', 'in') ?? 0
  
  // Convert to user's preferred unit for display
  const snowUnit = topForecast.hourly_units.snowfall || 'cm'
  const displayValue = convertPrecipitation(maxSnowCm, snowUnit, settingsStore.precipitationUnit) ?? 0
  const unitLabel = settingsStore.precipitationUnit === 'in' ? '"' : ' cm'
  
  return resort ? { resort, inches, displayValue, unitLabel } : null
})
</script>

<template>
  <div class="space-y-8">
    <!-- Powder Alert Banner -->
    <div 
      v-if="topSnowResort && topSnowResort.inches >= 6"
      class="powder-alert rounded-2xl p-6 md:p-8"
    >
      <div class="flex items-center gap-4">
        <div class="text-5xl animate-pulse-slow">🌨️</div>
        <div>
          <h2 class="text-2xl md:text-3xl font-display font-bold text-white">
            Powder Alert!
          </h2>
          <p class="text-mountain-200 mt-1">
            <RouterLink 
              :to="`/resort/${topSnowResort.resort.slug}`"
              class="text-snow-400 hover:text-snow-300 font-semibold"
            >
              {{ topSnowResort.resort.name }}
            </RouterLink>
            expecting 
            <span class="text-snow-400 font-bold">
              {{ Math.round(topSnowResort.inches) }}"
            </span>
            in the next 7 days
          </p>
        </div>
      </div>
    </div>
    
    <!-- Welcome Section -->
    <div class="text-center py-8">
      <h1 class="text-4xl md:text-5xl font-display font-bold text-white mb-4">
        Mountain Weather Forecasts
      </h1>
      <p class="text-mountain-400 text-lg max-w-2xl mx-auto">
        Real-time snow forecasts from multiple weather models. 
        Find the best powder days at your favorite ski resorts.
      </p>
    </div>
    
    <!-- Featured Resorts Grid -->
    <section>
      <h2 class="text-xl font-display font-semibold text-white mb-4 flex items-center gap-2">
        <span>📍</span>
        Featured Resorts
      </h2>
      
      <div v-if="loadingFeatured" class="flex justify-center py-12">
        <LoadingSpinner text="Loading forecasts..." />
      </div>
      
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <RouterLink
          v-for="resort in featuredResorts"
          :key="resort.slug"
          :to="`/resort/${resort.slug}`"
          class="glass-card p-5 hover:bg-mountain-800/60 transition-all group relative overflow-hidden"
          :class="{ 'ring-2 ring-snow-400/50': hasPowder(resort.slug) }"
        >
          <!-- Powder badge -->
          <div 
            v-if="hasPowder(resort.slug)"
            class="absolute top-3 right-3 px-2 py-1 rounded-full bg-snow-500/20 text-snow-300 text-xs font-medium"
          >
            🌨️ Powder
          </div>
          
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-display font-semibold text-white group-hover:text-snow-400 transition-colors">
                {{ resort.name }}
              </h3>
              <p class="text-mountain-400 text-sm">{{ resort.state }}, {{ resort.country }}</p>
            </div>
          </div>
          
          <div class="mt-4 flex items-baseline gap-2">
            <span class="text-3xl font-display font-bold text-gradient-snow">
              {{ getSnowTotal(resort.slug) }}
            </span>
            <span class="text-mountain-400 text-sm">7-day snow</span>
          </div>
          
          <div class="mt-3 flex items-center gap-4 text-sm text-mountain-400">
            <span>{{ Math.round(resort.summit_elevation_m * 3.281) }}' summit</span>
          </div>
        </RouterLink>
      </div>
    </section>
    
    <!-- Favorites Section -->
    <section v-if="resortsStore.favoriteResorts.length > 0">
      <h2 class="text-xl font-display font-semibold text-white mb-4 flex items-center gap-2">
        <span>⭐</span>
        Your Favorites
      </h2>
      
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <RouterLink
          v-for="resort in resortsStore.favoriteResorts"
          :key="resort.slug"
          :to="`/resort/${resort.slug}`"
          class="glass-card p-5 hover:bg-mountain-800/60 transition-all group"
        >
          <h3 class="font-display font-semibold text-white group-hover:text-snow-400 transition-colors">
            {{ resort.name }}
          </h3>
          <p class="text-mountain-400 text-sm">{{ resort.state }}, {{ resort.country }}</p>
        </RouterLink>
      </div>
    </section>
    
    <!-- All Resorts by Region -->
    <section>
      <h2 class="text-xl font-display font-semibold text-white mb-4 flex items-center gap-2">
        <span>🏔️</span>
        All Resorts
      </h2>
      
      <div v-if="resortsStore.loading" class="flex justify-center py-8">
        <LoadingSpinner />
      </div>
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div 
          v-for="state in resortsStore.states" 
          :key="state"
          class="glass-card p-5"
        >
          <h3 class="font-display font-semibold text-white mb-3 flex items-center gap-2">
            <span class="text-lg">{{ state }}</span>
            <span class="text-mountain-500 text-sm font-normal">
              ({{ resortsStore.resortsByState.get(state)?.length ?? 0 }})
            </span>
          </h3>
          <ul class="space-y-2">
            <li 
              v-for="resort in resortsStore.resortsByState.get(state)"
              :key="resort.slug"
            >
              <RouterLink
                :to="`/resort/${resort.slug}`"
                class="flex items-center justify-between text-mountain-300 hover:text-snow-400 transition-colors"
              >
                <span>{{ resort.name }}</span>
                <svg class="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

