<template>
  <div ref="chartRef" class="dashboard-bar-chart" v-loading="loading"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(
  defineProps<{
    data: { categories: string[]; values: (number | null)[] } | null
    loading?: boolean
    barColor?: string
  }>(),
  { loading: false, barColor: '#5470c6' }
)

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const updateChart = () => {
  if (!chartRef.value || !chartInstance || !props.data) return
  const { categories, values } = props.data
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', top: '8%', bottom: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: 30, fontSize: 11 }
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: { color: props.barColor },
      barWidth: '60%'
    }]
  }
  chartInstance.setOption(option, true)
}

watch(() => props.data, updateChart, { deep: true })

const getChartImage = (): string | null => {
  if (!chartInstance) return null
  try {
    return chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
  } catch {
    return null
  }
}

defineExpose({ getChartImage })

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
})

onBeforeUnmount(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-bar-chart {
  width: 100%;
  height: 280px;
}
</style>
