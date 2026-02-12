<template>
  <el-card class="dual-axis-chart-panel">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>{{ title || '双轴图表' }}</span>
        <el-button size="small" @click="handleSaveAsPng" :disabled="!data">
          <el-icon><Download /></el-icon>
          保存为PNG
        </el-button>
      </div>
    </template>
    <div ref="chartRef" style="width: 100%; height: 500px;" v-loading="loading"></div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { axisLabelDecimalFormatter } from '@/utils/chart-style'

export interface DualAxisData {
  series1: {
    name: string
    data: Array<{ date: string; value: number | null }>
    unit: string
  }
  series2: {
    name: string
    data: Array<{ date: string; value: number | null }>
    unit: string
  }
}

const props = defineProps<{
  data: DualAxisData | null
  loading?: boolean
  title?: string
  axis1?: 'left' | 'right'
  axis2?: 'left' | 'right'
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const updateChart = () => {
  if (!chartInstance || !props.data) return

  const { series1, series2 } = props.data

  // 合并日期，获取所有唯一日期
  const allDates = new Set<string>()
  series1.data.forEach(item => allDates.add(item.date))
  series2.data.forEach(item => allDates.add(item.date))
  const sortedDates = Array.from(allDates).sort()

  // 构建数据
  const data1 = sortedDates.map(date => {
    const item = series1.data.find(d => d.date === date)
    return item?.value ?? null
  })

  const data2 = sortedDates.map(date => {
    const item = series2.data.find(d => d.date === date)
    return item?.value ?? null
  })
  
  // 计算Y轴范围（自动调整）
  const values1 = data1.filter(v => v !== null && v !== undefined) as number[]
  const values2 = data2.filter(v => v !== null && v !== undefined) as number[]
  
  const y1Min = values1.length > 0 ? Math.min(...values1) : 0
  const y1Max = values1.length > 0 ? Math.max(...values1) : 100
  const y1Padding = (y1Max - y1Min) * 0.1
  
  const y2Min = values2.length > 0 ? Math.min(...values2) : 0
  const y2Max = values2.length > 0 ? Math.max(...values2) : 100
  const y2Padding = (y2Max - y2Min) * 0.1

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: [series1.name, series2.name],
      top: 10,
      type: 'plain',
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: sortedDates,
      name: '',
      axisLabel: {
        rotate: 45,
        formatter: (value: string) => {
          const date = new Date(value)
          const y = date.getFullYear()
          const m = date.getMonth() + 1
          const d = date.getDate()
          return `${y}/${m}/${d}`
        }
      }
    },
    yAxis: [
      {
        type: 'value',
        // Y轴不显示单位
        name: '',
        position: props.axis1 || 'left',
        min: y1Min - y1Padding,
        max: y1Max + y1Padding,
        scale: false,
        axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
      },
      {
        type: 'value',
        name: '',
        position: props.axis2 || 'right',
        min: y2Min - y2Padding,
        max: y2Max + y2Padding,
        scale: false,
        axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
      }
    ],
    series: [
      {
        name: series1.name,
        type: 'line',
        yAxisIndex: 0,
        data: data1,
        smooth: true,
        // 移除数据点
        symbol: 'none',
        // 处理断点：使用连续曲线
        connectNulls: true,
        itemStyle: {
          color: '#409EFF'
        }
      },
      {
        name: series2.name,
        type: 'line',
        yAxisIndex: 1,
        data: data2,
        smooth: true,
        // 移除数据点
        symbol: 'none',
        // 处理断点：使用连续曲线
        connectNulls: true,
        itemStyle: {
          color: '#67C23A'
        }
      }
    ]
  }

  chartInstance.setOption(option, true)
}

/** 获取图表为 base64 PNG（用于 Word 导出） */
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

const handleSaveAsPng = () => {
  if (!chartInstance) {
    ElMessage.warning('图表未初始化')
    return
  }

  try {
    const url = chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })

    const link = document.createElement('a')
    link.download = `${props.title || 'chart'}_${new Date().getTime()}.png`
    link.href = url
    link.click()

    ElMessage.success('图表已保存为PNG')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
})

watch(() => props.data, updateChart, { deep: true })

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.dual-axis-chart-panel {
  width: 100%;
  margin-bottom: 8px;
}
</style>
