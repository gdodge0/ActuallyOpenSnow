<script setup lang="ts">
import { computed } from 'vue'
import { useForecastStore } from '@/stores/forecast'

const props = defineProps<{
  currentModel: string
}>()

const emit = defineEmits<{
  'update:model': [modelId: string]
}>()

const forecastStore = useForecastStore()

const models = computed(() => forecastStore.models)

function selectModel(modelId: string) {
  emit('update:model', modelId)
}
</script>

<template>
  <div class="flex items-center gap-2">
    <span class="text-mountain-400 text-sm">Model:</span>
    <div class="flex gap-1">
      <button
        v-for="model in models"
        :key="model.model_id"
        @click="selectModel(model.model_id)"
        class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
        :class="currentModel === model.model_id 
          ? 'bg-snow-500 text-mountain-950 shadow-lg shadow-snow-500/20' 
          : 'bg-mountain-800 text-mountain-300 hover:bg-mountain-700 hover:text-white'"
        :title="model.description"
      >
        {{ model.display_name }}
      </button>
    </div>
  </div>
</template>

