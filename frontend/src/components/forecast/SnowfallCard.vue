<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { convertPrecipitation, formatSnowfall } from '@/utils/units'

const props = defineProps<{
  totalSnowCm: number
  snowUnit?: string
  period?: string
  modelId?: string
  modelRunTime?: string | null
}>()

const settingsStore = useSettingsStore()

const displayValue = computed(() => {
  const fromUnit = props.snowUnit || 'cm'
  const converted = convertPrecipitation(props.totalSnowCm, fromUnit, settingsStore.precipitationUnit)
  
  if (converted === null) return '--'
  if (converted < 0.1) return 'trace'
  
  // Show big number without unit for hero display
  if (settingsStore.precipitationUnit === 'in') {
    return converted < 10 ? converted.toFixed(1) : Math.round(converted).toString()
  }
  return converted < 10 ? converted.toFixed(1) : Math.round(converted).toString()
})

const unitLabel = computed(() => {
  return settingsStore.precipitationUnit === 'in' ? 'inches' : 'cm'
})

const isPowderDay = computed(() => {
  // Powder alert if > 6 inches (15 cm) expected
  const inInches = convertPrecipitation(props.totalSnowCm, props.snowUnit || 'cm', 'in') ?? 0
  return inInches >= 6
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
        <span v-if="modelId" class="model-badge">
          {{ modelId.toUpperCase() }}
        </span>
      </div>
      
      <!-- Big number -->
      <div class="flex items-baseline gap-2 mb-2">
        <span class="stat-number">{{ displayValue }}</span>
        <span class="stat-unit">{{ unitLabel }}</span>
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

