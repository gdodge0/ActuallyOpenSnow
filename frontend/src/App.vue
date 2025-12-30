<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
import { useResortsStore } from '@/stores/resorts'
import { useForecastStore } from '@/stores/forecast'

const resortsStore = useResortsStore()
const forecastStore = useForecastStore()

onMounted(async () => {
  // Load resorts and models on app mount
  await Promise.all([
    resortsStore.loadResorts(),
    forecastStore.loadModels(),
  ])
})
</script>

<template>
  <div class="min-h-screen bg-mountain-950 flex flex-col">
    <!-- Header -->
    <AppHeader />
    
    <!-- Main layout -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar (hidden on mobile) -->
      <AppSidebar class="hidden lg:block" />
      
      <!-- Main content -->
      <main class="flex-1 overflow-y-auto scrollbar-thin">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

