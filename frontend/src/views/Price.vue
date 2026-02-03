<template>
  <div class="price-page">
    <FilterBar
      :show-region-filter="true"
      :show-year-filter="false"
      :show-freq-filter="true"
      @change="handleFilterChange"
    />
    <ChartPanel :data="chartData" :loading="loading" title="价格分析" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FilterBar from '../components/FilterBar.vue'
import ChartPanel from '../components/ChartPanel.vue'
import { tsApi } from '../api/ts'

const loading = ref(false)
const chartData = ref(null)

const handleFilterChange = (filters: any) => {
  // 加载价格数据
  loadPriceData(filters)
}

const loadPriceData = async (filters: any) => {
  loading.value = true
  try {
    const result = await tsApi.getTimeseries({
      indicator_code: 'hog_price_nation',
      region_code: filters.region,
      freq: filters.freq || 'D',
      from_date: filters.dateRange.start,
      to_date: filters.dateRange.end
    })
    
    // 转换数据格式
    chartData.value = {
      series: [{
        name: result.indicator_name,
        data: result.series.map(s => [s.date, s.value]),
        unit: result.unit
      }],
      categories: result.series.map(s => s.date)
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.price-page {
  padding: 20px;
}
</style>
