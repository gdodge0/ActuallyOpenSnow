<script setup lang="ts">
import { computed, ref } from 'vue'
import { Chart } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  LineController,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import type { Forecast } from '@/types'
import { useSettingsStore } from '@/stores/settings'
import { convertPrecipitation } from '@/utils/units'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  LineController,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps<{
  forecast: Forecast
  initialHours?: number
}>()

const settingsStore = useSettingsStore()
const chartRef = ref()

// Time range options
interface TimeRange {
  label: string
  hours: number
}

const timeRanges: TimeRange[] = [
  { label: '24h', hours: 24 },
  { label: '48h', hours: 48 },
  { label: '72h', hours: 72 },
  { label: '5 Day', hours: 120 },
  { label: '7 Day', hours: 168 },
  { label: 'Full', hours: 9999 },
]

// Selected time range
const selectedHours = ref(props.initialHours ?? 72)

// Actual hours to display (capped by available data)
const displayHours = computed(() => {
  const available = props.forecast.times_utc.length
  return Math.min(selectedHours.value, available)
})

// Computed total snow for selected period
const periodTotal = computed(() => {
  const snowfall = props.forecast.hourly_data.snowfall ?? []
  const fromUnit = props.forecast.hourly_units.snowfall ?? 'cm'
  
  let total = 0
  for (let i = 0; i < displayHours.value; i++) {
    total += snowfall[i] ?? 0
  }
  
  const converted = convertPrecipitation(total, fromUnit, settingsStore.precipitationUnit) ?? 0
  return converted
})

// Determine label interval based on time range
const labelInterval = computed(() => {
  if (selectedHours.value <= 24) return 3      // Every 3 hours
  if (selectedHours.value <= 48) return 6      // Every 6 hours
  if (selectedHours.value <= 72) return 12     // Every 12 hours
  if (selectedHours.value <= 120) return 24    // Every day
  return 24                                     // Every day for longer ranges
})

const chartData = computed(() => {
  const snowfall = props.forecast.hourly_data.snowfall ?? []
  const times = props.forecast.times_utc
  const fromUnit = props.forecast.hourly_units.snowfall ?? 'cm'
  
  const hourlySnow: number[] = []
  const accumulated: number[] = []
  const labels: string[] = []
  
  let total = 0
  for (let i = 0; i < displayHours.value; i++) {
    const raw = snowfall[i] ?? 0
    const converted = convertPrecipitation(raw, fromUnit, settingsStore.precipitationUnit) ?? 0
    hourlySnow.push(converted)
    total += converted
    accumulated.push(total)
    
    // Always generate a label - we'll filter display in the tick callback
    const date = new Date(times[i])
    const hour = date.getHours()
    const dayShort = date.toLocaleDateString('en-US', { weekday: 'short' })
    const dateShort = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    
    // Format based on time range
    if (selectedHours.value <= 48) {
      // Short range: show day name at midnight, otherwise hour
      if (hour === 0) {
        labels.push(dayShort)
      } else {
        labels.push(`${hour}:00`)
      }
    } else if (selectedHours.value <= 120) {
      // Medium range: show day name at midnight
      if (hour === 0) {
        labels.push(dayShort)
      } else if (hour === 12) {
        labels.push('12pm')
      } else {
        labels.push('')
      }
    } else {
      // Long range: show date at midnight only
      if (hour === 0) {
        labels.push(dateShort)
      } else {
        labels.push('')
      }
    }
  }
  
  return {
    labels,
    datasets: [
      {
        type: 'bar' as const,
        label: 'Hourly Snow',
        data: hourlySnow,
        backgroundColor: 'rgba(56, 189, 248, 0.6)',
        borderColor: 'rgba(56, 189, 248, 1)',
        borderWidth: 1,
        borderRadius: 2,
        yAxisID: 'y',
      },
      {
        type: 'line' as const,
        label: 'Accumulated',
        data: accumulated,
        borderColor: 'rgba(168, 85, 247, 0.8)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
        yAxisID: 'y1',
      },
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      labels: {
        color: '#94a3b8',
        usePointStyle: true,
        pointStyle: 'rect',
        padding: 20,
      },
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(71, 85, 105, 0.5)',
      borderWidth: 1,
      titleColor: '#f8fafc',
      bodyColor: '#cbd5e1',
      padding: 12,
      displayColors: true,
      callbacks: {
        title: (items: any[]) => {
          if (!items.length) return ''
          const idx = items[0].dataIndex
          const date = new Date(props.forecast.times_utc[idx])
          return date.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
          })
        },
        label: (context: any) => {
          const unit = settingsStore.precipitationUnit === 'in' ? '"' : ' cm'
          return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}${unit}`
        },
      },
    },
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(71, 85, 105, 0.3)',
      },
      ticks: {
        color: '#64748b',
        maxRotation: 0,
        autoSkip: false,
        callback: function(value: any, index: number) {
          const label = chartData.value.labels[index]
          // Only show non-empty labels at appropriate intervals
          if (!label) return null
          
          // For short ranges, show all labels
          if (selectedHours.value <= 48) {
            // Show every 3rd hour label, but always show day names
            const date = new Date(props.forecast.times_utc[index])
            if (date.getHours() === 0) return label
            if (index % 3 === 0) return label
            return null
          }
          
          // For medium/long ranges, show all non-empty labels
          return label
        },
      },
    },
    y: {
      type: 'linear' as const,
      display: true,
      position: 'left' as const,
      title: {
        display: true,
        text: settingsStore.precipitationUnit === 'in' ? 'Hourly (in)' : 'Hourly (cm)',
        color: '#64748b',
      },
      grid: {
        color: 'rgba(71, 85, 105, 0.3)',
      },
      ticks: {
        color: '#64748b',
      },
      beginAtZero: true,
    },
    y1: {
      type: 'linear' as const,
      display: true,
      position: 'right' as const,
      title: {
        display: true,
        text: settingsStore.precipitationUnit === 'in' ? 'Total (in)' : 'Total (cm)',
        color: '#64748b',
      },
      grid: {
        drawOnChartArea: false,
      },
      ticks: {
        color: '#a855f7',
      },
      beginAtZero: true,
    },
  },
}))

function selectTimeRange(hours: number) {
  selectedHours.value = hours
}

function formatTotal(value: number): string {
  if (value < 0.1) return 'trace'
  const unit = settingsStore.precipitationUnit === 'in' ? '"' : ' cm'
  return value < 10 ? value.toFixed(1) + unit : Math.round(value) + unit
}
</script>

<template>
  <div class="glass-card p-6">
    <!-- Header with time range selector -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
      <div>
        <h3 class="font-display font-semibold text-white">
          Snowfall Forecast
        </h3>
        <p class="text-sm text-mountain-400 mt-0.5">
          {{ displayHours }}h total: 
          <span class="text-snow-400 font-medium">{{ formatTotal(periodTotal) }}</span>
        </p>
      </div>
      
      <!-- Time range buttons -->
      <div class="flex gap-1 bg-mountain-800/50 rounded-lg p-1">
        <button
          v-for="range in timeRanges"
          :key="range.hours"
          @click="selectTimeRange(range.hours)"
          class="px-3 py-1.5 rounded-md text-sm font-medium transition-all"
          :class="selectedHours === range.hours
            ? 'bg-snow-500 text-mountain-950 shadow-sm'
            : 'text-mountain-400 hover:text-white hover:bg-mountain-700/50'"
        >
          {{ range.label }}
        </button>
      </div>
    </div>
    
    <!-- Chart -->
    <div class="h-64">
      <Chart 
        ref="chartRef" 
        type="bar" 
        :data="chartData" 
        :options="chartOptions"
        :key="selectedHours"
      />
    </div>
  </div>
</template>
