<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
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
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps<{
  forecast: Forecast
  hoursToShow?: number
}>()

const settingsStore = useSettingsStore()
const chartRef = ref()

const hours = computed(() => props.hoursToShow ?? 72)

const chartData = computed(() => {
  const snowfall = props.forecast.hourly_data.snowfall ?? []
  const times = props.forecast.times_utc
  const fromUnit = props.forecast.hourly_units.snowfall ?? 'cm'
  
  // Get hourly values for display period
  const displayHours = Math.min(hours.value, snowfall.length)
  const hourlySnow: number[] = []
  const accumulated: number[] = []
  const labels: string[] = []
  
  let total = 0
  for (let i = 0; i < displayHours; i++) {
    const raw = snowfall[i] ?? 0
    const converted = convertPrecipitation(raw, fromUnit, settingsStore.precipitationUnit) ?? 0
    hourlySnow.push(converted)
    total += converted
    accumulated.push(total)
    
    // Format label
    const date = new Date(times[i])
    const hour = date.getHours()
    const day = date.toLocaleDateString('en-US', { weekday: 'short' })
    labels.push(hour === 0 ? day : `${hour}:00`)
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
        autoSkip: true,
        maxTicksLimit: 12,
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
</script>

<template>
  <div class="glass-card p-6">
    <h3 class="font-display font-semibold text-white mb-4">
      Snowfall Forecast ({{ hours }}h)
    </h3>
    <div class="h-64">
      <Bar ref="chartRef" :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

