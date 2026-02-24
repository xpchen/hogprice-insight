<template>
  <div ref="chartRef" class="dashboard-line-chart" v-loading="loading"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { axisLabelDecimalFormatter, yAxisHideMinMaxLabel } from '@/utils/chart-style'

const props = withDefaults(
  defineProps<{
    data: { categories: string[]; series: { name: string; data: (number | null)[] }[] } | null
    loading?: boolean
  }>(),
  { loading: false }
)

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const updateChart = () => {
  if (!chartRef.value || !chartInstance || !props.data || props.data.series.length === 0) return
  const { categories, series } = props.data
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: {
      data: series.map(s => s.name),
      top: 4,
      left: 'left',
      type: 'plain',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8
    },
    grid: { left: '3%', right: '4%', top: '20%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: categories, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: {
      type: 'value',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) },
      splitLine: { lineStyle: { type: 'dashed', color: '#eee' } }
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      connectNulls: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 }
    }))
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
.dashboard-line-chart {
  width: 100%;
  height: 280px;
}
</style>
