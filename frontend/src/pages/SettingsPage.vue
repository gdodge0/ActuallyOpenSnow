<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
</script>

<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <h1 class="text-3xl font-display font-bold text-white">Settings</h1>
    
    <!-- Units -->
    <div class="glass-card p-6">
      <h2 class="font-display font-semibold text-white mb-4">Unit Preferences</h2>
      
      <div class="space-y-4">
        <!-- Quick toggle -->
        <div class="flex gap-4">
          <button
            @click="settingsStore.setImperial"
            class="flex-1 py-3 rounded-lg font-medium transition-all"
            :class="settingsStore.temperatureUnit === 'F' 
              ? 'bg-snow-500 text-mountain-950' 
              : 'bg-mountain-800 text-mountain-300 hover:bg-mountain-700'"
          >
            Imperial (°F, inches, mph, ft)
          </button>
          <button
            @click="settingsStore.setMetric"
            class="flex-1 py-3 rounded-lg font-medium transition-all"
            :class="settingsStore.temperatureUnit === 'C' 
              ? 'bg-snow-500 text-mountain-950' 
              : 'bg-mountain-800 text-mountain-300 hover:bg-mountain-700'"
          >
            Metric (°C, cm, km/h, m)
          </button>
        </div>
        
        <!-- Individual settings -->
        <div class="grid grid-cols-2 gap-4 pt-4 border-t border-mountain-700">
          <!-- Temperature -->
          <div>
            <label class="block text-sm font-medium text-mountain-400 mb-2">Temperature</label>
            <select
              v-model="settingsStore.temperatureUnit"
              class="w-full px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white focus:outline-none focus:ring-2 focus:ring-snow-500"
            >
              <option value="F">Fahrenheit (°F)</option>
              <option value="C">Celsius (°C)</option>
            </select>
          </div>
          
          <!-- Precipitation -->
          <div>
            <label class="block text-sm font-medium text-mountain-400 mb-2">Snowfall</label>
            <select
              v-model="settingsStore.precipitationUnit"
              class="w-full px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white focus:outline-none focus:ring-2 focus:ring-snow-500"
            >
              <option value="in">Inches (in)</option>
              <option value="cm">Centimeters (cm)</option>
            </select>
          </div>
          
          <!-- Wind Speed -->
          <div>
            <label class="block text-sm font-medium text-mountain-400 mb-2">Wind Speed</label>
            <select
              v-model="settingsStore.windSpeedUnit"
              class="w-full px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white focus:outline-none focus:ring-2 focus:ring-snow-500"
            >
              <option value="mph">Miles per hour (mph)</option>
              <option value="kmh">Kilometers per hour (km/h)</option>
              <option value="ms">Meters per second (m/s)</option>
            </select>
          </div>
          
          <!-- Elevation -->
          <div>
            <label class="block text-sm font-medium text-mountain-400 mb-2">Elevation</label>
            <select
              v-model="settingsStore.elevationUnit"
              class="w-full px-3 py-2 rounded-lg bg-mountain-800 border border-mountain-700 text-white focus:outline-none focus:ring-2 focus:ring-snow-500"
            >
              <option value="ft">Feet (ft)</option>
              <option value="m">Meters (m)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
    
    <!-- About -->
    <div class="glass-card p-6">
      <h2 class="font-display font-semibold text-white mb-4">About</h2>
      <div class="space-y-3 text-mountain-300">
        <p>
          <strong class="text-white">ActuallyOpenSnow</strong> provides mountain weather forecasts 
          powered by multiple global weather models including GFS, ECMWF IFS, and ECMWF AIFS.
        </p>
        <p>
          Weather data is sourced from 
          <a href="https://open-meteo.com" target="_blank" class="text-snow-400 hover:text-snow-300">
            Open-Meteo
          </a>, 
          providing free access to high-resolution forecast data.
        </p>
        <p class="text-sm text-mountain-500">
          Forecasts are updated multiple times daily. Always check current conditions before heading to the mountain.
        </p>
      </div>
    </div>
  </div>
</template>

