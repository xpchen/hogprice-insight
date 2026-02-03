<template>
  <div class="slaughter-page">
    <FilterBar
      :show-region-filter="true"
      :show-year-filter="true"
      :show-freq-filter="false"
      :available-years="[2024, 2025, 2026]"
      @change="handleFilterChange"
    />
    <SeasonalityChart
      :data="seasonalityData"
      :loading="loading"
      title="日度屠宰量季节性"
      :lunar-alignment="true"
      :show-year-filter="true"
      :available-years="[2024, 2025, 2026]"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FilterBar from '../components/FilterBar.vue'
import SeasonalityChart from '../components/SeasonalityChart.vue'
import type { SeasonalityData } from '../components/SeasonalityChart.vue'

const loading = ref(false)
const seasonalityData = ref<SeasonalityData | null>(null)

const handleFilterChange = (filters: any) => {
  // 加载屠宰数据
  loadSlaughterData(filters)
}

const loadSlaughterData = async (filters: any) => {
  loading.value = true
  try {
    // 调用季节性查询API
    // seasonalityData.value = ...
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.slaughter-page {
  padding: 20px;
}
</style>
