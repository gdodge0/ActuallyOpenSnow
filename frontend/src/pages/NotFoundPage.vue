<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-[70vh] text-center px-4">
    <!-- Decorative snowflakes -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div 
        v-for="i in 12" 
        :key="i"
        class="absolute text-snow-400/20 animate-snow-fall"
        :style="{
          left: `${(i * 8) + Math.random() * 5}%`,
          animationDelay: `${i * 0.3}s`,
          animationDuration: `${3 + Math.random() * 2}s`,
          fontSize: `${1 + Math.random() * 1.5}rem`
        }"
      >
        ❄
      </div>
    </div>

    <!-- Main content -->
    <div class="relative z-10">
      <!-- 404 Number with mountain silhouette effect -->
      <div class="relative mb-8">
        <h1 class="text-[10rem] md:text-[14rem] font-display font-bold leading-none select-none">
          <span class="text-gradient-404">4</span>
          <span class="inline-block mx-2 md:mx-4">
            <!-- Mountain icon as the "0" -->
            <svg 
              class="w-24 h-24 md:w-32 md:h-32 inline-block text-snow-400" 
              viewBox="0 0 24 24" 
              fill="currentColor"
            >
              <path d="M12 2L2 22h20L12 2zm0 4l7 14H5l7-14z" opacity="0.3"/>
              <path d="M12 2L2 22h20L12 2zm0 3.5L18.5 20h-13L12 5.5z"/>
            </svg>
          </span>
          <span class="text-gradient-404">4</span>
        </h1>
        
        <!-- Fog/mist effect at the base -->
        <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-16 bg-gradient-to-t from-mountain-950 via-mountain-950/80 to-transparent"></div>
      </div>

      <!-- Message -->
      <div class="space-y-4 mb-10">
        <h2 class="text-2xl md:text-3xl font-display font-semibold text-white">
          Lost in the Backcountry
        </h2>
        <p class="text-mountain-400 text-lg max-w-md mx-auto">
          This trail doesn't exist. The page you're looking for may have been moved or buried under fresh powder.
        </p>
      </div>

      <!-- Actions -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
        <RouterLink 
          to="/" 
          class="btn-primary flex items-center gap-2 text-lg px-6 py-3"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          Back to Base Lodge
        </RouterLink>
        
        <button 
          @click="$router.back()" 
          class="btn-secondary flex items-center gap-2 text-lg px-6 py-3"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          Go Back
        </button>
      </div>

      <!-- Helpful links -->
      <div class="mt-12 pt-8 border-t border-mountain-800">
        <p class="text-mountain-500 text-sm mb-4">Or check out these trails:</p>
        <div class="flex flex-wrap justify-center gap-4 text-sm">
          <RouterLink 
            to="/favorites" 
            class="text-snow-400 hover:text-snow-300 transition-colors flex items-center gap-1"
          >
            <span>⭐</span> Favorites
          </RouterLink>
          <RouterLink 
            to="/compare" 
            class="text-snow-400 hover:text-snow-300 transition-colors flex items-center gap-1"
          >
            <span>📊</span> Compare Models
          </RouterLink>
          <RouterLink 
            to="/custom" 
            class="text-snow-400 hover:text-snow-300 transition-colors flex items-center gap-1"
          >
            <span>📍</span> Custom Locations
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.text-gradient-404 {
  @apply bg-gradient-to-b from-mountain-600 via-mountain-700 to-mountain-800 bg-clip-text text-transparent;
}

/* Override snow-fall animation for continuous effect */
@keyframes snow-fall-continuous {
  0% {
    transform: translateY(-20px);
    opacity: 0;
  }
  10% {
    opacity: 0.5;
  }
  90% {
    opacity: 0.5;
  }
  100% {
    transform: translateY(calc(70vh));
    opacity: 0;
  }
}

.animate-snow-fall {
  animation: snow-fall-continuous 5s linear infinite;
}
</style>

