<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { convertPrecipitation } from '@/utils/units'

const props = defineProps<{
  totalSnowCm: number             // Conservative (raw model) snowfall in cm
  enhancedSnowCm?: number         // Enhanced (temperature-adjusted) snowfall in cm
  rainMm?: number                 // Rain (liquid precipitation) in mm
  snowUnit?: string
  period?: string
  modelId?: string
  modelRunTime?: string | null
}>()

const settingsStore = useSettingsStore()

// Determine which snowfall value to use based on settings
const activeSnowfall = computed(() => {
  if (settingsStore.snowfallMode === 'enhanced' && props.enhancedSnowCm !== undefined) {
    return props.enhancedSnowCm
  }
  return props.totalSnowCm
})

const displayValue = computed(() => {
  const fromUnit = props.snowUnit || 'cm'
  const converted = convertPrecipitation(activeSnowfall.value, fromUnit, settingsStore.precipitationUnit)
  
  if (converted === null) return '--'
  if (converted < 0.1) return 'trace'
  
  // Always round to whole numbers for clean, consistent display
  return Math.round(converted).toString()
})

// For comparison mode: show both values
const conservativeDisplay = computed(() => {
  const converted = convertPrecipitation(props.totalSnowCm, 'cm', settingsStore.precipitationUnit)
  if (converted === null) return '--'
  if (converted < 0.1) return 'trace'
  return Math.round(converted).toString()
})

const enhancedDisplay = computed(() => {
  if (props.enhancedSnowCm === undefined) return conservativeDisplay.value
  const converted = convertPrecipitation(props.enhancedSnowCm, 'cm', settingsStore.precipitationUnit)
  if (converted === null) return '--'
  if (converted < 0.1) return 'trace'
  return Math.round(converted).toString()
})

// Rain display (convert from mm)
const rainDisplay = computed(() => {
  if (!props.rainMm || props.rainMm < 0.1) return null
  const converted = convertPrecipitation(props.rainMm, 'mm', settingsStore.precipitationUnit)
  if (converted === null || converted < 0.1) return null
  return converted < 1 ? converted.toFixed(1) : Math.round(converted).toString()
})

const unitLabel = computed(() => {
  return settingsStore.precipitationUnit === 'in' ? 'inches' : 'cm'
})

const isPowderDay = computed(() => {
  // Powder alert if > 6 inches (15 cm) expected - use enhanced if available
  const snowCm = props.enhancedSnowCm ?? props.totalSnowCm
  const inInches = convertPrecipitation(snowCm, 'cm', 'in') ?? 0
  return inInches >= 6
})

// Show comparison when enabled and values differ
const showComparison = computed(() => {
  if (!settingsStore.showBothSnowfallModes) return false
  if (props.enhancedSnowCm === undefined) return false
  // Show if there's a meaningful difference (>10% or >1cm)
  const diff = Math.abs(props.enhancedSnowCm - props.totalSnowCm)
  return diff > 1 || diff > props.totalSnowCm * 0.1
})
</script>

<template>
  <div 
    class="glass-card p-6 relative overflow-hidden"
    :class="{ 'powder-alert': isPowderDay }"
  >
    <!-- Snowflake decorations for powder days -->
    <div v-if="isPowderDay" class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-4 right-8 text-3xl opacity-20 animate-float" style="animation-delay: 0s">❄️</div>
      <div class="absolute top-12 right-24 text-2xl opacity-15 animate-float" style="animation-delay: 0.5s">❄️</div>
      <div class="absolute top-6 right-40 text-xl opacity-10 animate-float" style="animation-delay: 1s">❄️</div>
    </div>
    
    <div class="relative">
      <!-- Label -->
      <div class="flex items-center justify-between mb-2">
        <span class="text-mountain-400 text-sm font-medium">
          {{ period || 'Total Snowfall' }}
        </span>
        <span v-if="modelId" class="model-badge" :class="{ 'bg-gradient-to-r from-snow-500/20 to-mountain-700': modelId === 'blend' }">
          <span v-if="modelId === 'blend'" class="inline-flex items-center gap-1">
            <span class="text-xs">✨</span>
            BLEND
          </span>
          <span v-else>{{ modelId.toUpperCase() }}</span>
        </span>
      </div>
      
      <!-- Big number -->
      <div class="flex items-baseline gap-2 mb-2">
        <span class="stat-number">{{ displayValue }}</span>
        <span class="stat-unit">{{ unitLabel }}</span>
      </div>
      
      <!-- Comparison display when enabled -->
      <div v-if="showComparison" class="flex items-center gap-3 mb-3 text-sm">
        <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-mountain-700/50">
          <span class="text-mountain-400">Conservative:</span>
          <span class="text-mountain-200 font-medium">{{ conservativeDisplay }}</span>
        </div>
        <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-snow-500/20">
          <span class="text-snow-400">Enhanced:</span>
          <span class="text-snow-200 font-medium">{{ enhancedDisplay }}</span>
        </div>
      </div>
      
      <!-- Rain indicator -->
      <div v-if="rainDisplay" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-sm font-medium mb-3 mr-2">
        <span>🌧️</span>
        <span>{{ rainDisplay }} {{ unitLabel }} rain</span>
      </div>
      
      <!-- Powder alert badge -->
      <div v-if="isPowderDay" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-snow-500/20 text-snow-300 text-sm font-medium mb-3">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
        </svg>
        Powder Alert!
      </div>
      
      <!-- Model run time -->
      <p v-if="modelRunTime" class="text-mountain-500 text-xs">
        Model run: {{ modelRunTime }}
      </p>
    </div>
  </div>
</template>

