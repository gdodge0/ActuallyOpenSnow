<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { convertElevation, formatElevation } from '@/utils/units'

export type ElevationOption = 'peak' | 'mid' | 'base' | 'custom'

interface Props {
  baseElevationM: number
  summitElevationM: number
  modelValue: ElevationOption
  customElevationM?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: ElevationOption]
  'update:customElevationM': [value: number]
  'change': [elevationM: number]
}>()

const settingsStore = useSettingsStore()

// Calculate mid-mountain elevation
const midElevationM = computed(() => {
  return Math.round((props.baseElevationM + props.summitElevationM) / 2)
})

// Local state for custom elevation in METERS (internal storage is always meters)
const customElevationMeters = ref(props.customElevationM ?? midElevationM.value)

// Watch for external custom elevation changes
watch(() => props.customElevationM, (newVal) => {
  if (newVal !== undefined) {
    customElevationMeters.value = newVal
  }
})

// Convert meters to display unit for the input field
const customInputDisplayValue = computed(() => {
  const converted = convertElevation(customElevationMeters.value, 'm', settingsStore.elevationUnit)
  return Math.round(converted ?? 0)
})

// Get the reciprocal unit
const reciprocalUnit = computed(() => settingsStore.elevationUnit === 'ft' ? 'm' : 'ft')

// Format elevation in the reciprocal unit
function formatReciprocalElev(meters: number): string {
  const targetUnit = reciprocalUnit.value
  const converted = convertElevation(meters, 'm', targetUnit)
  return formatElevation(converted, targetUnit)
}

// Format elevation for display in user's preferred unit
function formatElev(meters: number): string {
  const converted = convertElevation(meters, 'm', settingsStore.elevationUnit)
  return formatElevation(converted, settingsStore.elevationUnit)
}

// Get the current elevation in meters based on selection
const currentElevationM = computed(() => {
  switch (props.modelValue) {
    case 'peak':
      return props.summitElevationM
    case 'mid':
      return midElevationM.value
    case 'base':
      return props.baseElevationM
    case 'custom':
      return customElevationMeters.value
    default:
      return props.summitElevationM
  }
})

// Options for the selector
const options = computed(() => [
  { value: 'peak' as const, label: 'Peak', elevation: props.summitElevationM },
  { value: 'mid' as const, label: 'Mid-Mountain', elevation: midElevationM.value },
  { value: 'base' as const, label: 'Base', elevation: props.baseElevationM },
  { value: 'custom' as const, label: 'Custom', elevation: null },
])

// Handle option click
function selectOption(option: ElevationOption) {
  emit('update:modelValue', option)
  
  if (option !== 'custom') {
    const elev = option === 'peak' 
      ? props.summitElevationM 
      : option === 'mid' 
        ? midElevationM.value 
        : props.baseElevationM
    emit('change', elev)
  } else {
    emit('change', customElevationMeters.value)
  }
}

// Handle custom elevation input (input is in user's preferred unit)
function handleCustomInput(event: Event) {
  const input = event.target as HTMLInputElement
  let inputValue = parseInt(input.value, 10)
  
  if (isNaN(inputValue)) {
    return // Invalid input, ignore
  }
  
  // Convert from display unit to meters
  const valueInMeters = Math.round(
    convertElevation(inputValue, settingsStore.elevationUnit, 'm') ?? 0
  )
  
  // Validate range in meters (allow some buffer beyond resort elevations)
  const minElevM = Math.max(0, props.baseElevationM - 500)
  const maxElevM = props.summitElevationM + 500
  
  const clampedMeters = Math.max(minElevM, Math.min(maxElevM, valueInMeters))
  
  customElevationMeters.value = clampedMeters
  emit('update:customElevationM', clampedMeters)
  
  if (props.modelValue === 'custom') {
    emit('change', clampedMeters)
  }
}

// Compute min/max for the input field in display units
const inputMin = computed(() => {
  const minM = Math.max(0, props.baseElevationM - 500)
  return Math.round(convertElevation(minM, 'm', settingsStore.elevationUnit) ?? 0)
})

const inputMax = computed(() => {
  const maxM = props.summitElevationM + 500
  return Math.round(convertElevation(maxM, 'm', settingsStore.elevationUnit) ?? 0)
})

const inputStep = computed(() => {
  return settingsStore.elevationUnit === 'ft' ? 100 : 50
})
</script>

<template>
  <div class="elevation-selector">
    <div class="flex items-center gap-2 text-sm text-mountain-400 mb-2">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
          d="M13 7l5 5m0 0l-5 5m5-5H6"/>
      </svg>
      <span>Forecast Elevation</span>
    </div>
    
    <!-- Option buttons -->
    <div class="flex flex-wrap gap-2">
      <button
        v-for="option in options"
        :key="option.value"
        @click="selectOption(option.value)"
        class="elevation-btn"
        :class="{ 'elevation-btn-active': modelValue === option.value }"
      >
        <span class="font-medium">{{ option.label }}</span>
        <span v-if="option.elevation !== null" class="text-xs opacity-75">
          {{ formatElev(option.elevation) }}
        </span>
      </button>
    </div>
    
    <!-- Custom elevation input (shown when custom is selected) -->
    <div 
      v-if="modelValue === 'custom'"
      class="mt-3 flex items-center gap-3"
    >
      <label class="text-sm text-mountain-400">Elevation:</label>
      <div class="flex items-center gap-2">
        <input
          type="number"
          :value="customInputDisplayValue"
          @change="handleCustomInput"
          :min="inputMin"
          :max="inputMax"
          :step="inputStep"
          class="custom-elevation-input"
        />
        <span class="text-sm text-mountain-400">{{ settingsStore.elevationUnit }}</span>
        <span class="text-xs text-mountain-500">
          ({{ formatReciprocalElev(customElevationMeters) }})
        </span>
      </div>
    </div>
    
    <!-- Current elevation display -->
    <div class="mt-2 text-xs text-mountain-500">
      Showing forecast for {{ formatElev(currentElevationM) }}
    </div>
  </div>
</template>

<style scoped>
.elevation-btn {
  @apply flex flex-col items-center px-3 py-2 rounded-lg 
         bg-mountain-800 border border-mountain-700
         hover:bg-mountain-700 hover:border-mountain-600
         transition-all duration-200
         text-mountain-300;
}

.elevation-btn-active {
  @apply bg-snow-600/20 border-snow-500 text-white;
}

.custom-elevation-input {
  @apply w-24 px-2 py-1 rounded-md 
         bg-mountain-800 border border-mountain-600
         text-white text-sm
         focus:border-snow-500 focus:outline-none focus:ring-1 focus:ring-snow-500/50;
}

/* Hide spin buttons on number input */
.custom-elevation-input::-webkit-inner-spin-button,
.custom-elevation-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.custom-elevation-input[type=number] {
  -moz-appearance: textfield;
}
</style>

