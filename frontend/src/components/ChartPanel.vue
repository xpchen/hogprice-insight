<template>
  <el-card class="chart-panel">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>{{ title || '图表' }}</span>
        <div style="display: flex; gap: 10px; align-items: center">
          <el-radio-group v-model="chartMode" size="small" @change="handleModeChange">
            <el-radio-button label="normal">常规</el-radio-button>
            <el-radio-button label="compare">多年对比</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="handleSaveAsPng" :disabled="!data">
            <el-icon><Download /></el-icon>
            保存为PNG
          </el-button>
        </div>
      </div>
    </template>
    <div ref="chartRef" style="width: 100%; height: 500px;" v-loading="loading"></div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { axisLabelDecimalFormatter, yAxisHideMinMaxLabel } from '@/utils/chart-style'

export interface ChartSeries {
  name: string
  data: Array<[string, number | null]>
  yAxisIndex?: number  // 指定使用哪个Y轴（0=左，1=右）
  unit?: string  // 单位
  color?: string  // 颜色
}

export interface ChartData {
  series: ChartSeries[]
  categories: string[]
}

const props = defineProps<{
  data: ChartData | null
  loading?: boolean
  title?: string
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const chartMode = ref<'normal' | 'compare'>('normal')

// 检测是否需要双Y轴：如果数值范围差异很大，使用双Y轴
const needsDualYAxis = computed(() => {
  if (!props.data || props.data.series.length < 2) return false
  
  const ranges = props.data.series.map(series => {
    const values = series.data.map(([_, v]) => v).filter(v => v !== null && v !== undefined) as number[]
    if (values.length === 0) return { min: 0, max: 0, range: 0 }
    const min = Math.min(...values)
    const max = Math.max(...values)
    return { min, max, range: max - min }
  })
  
  // 如果最大值和最小值的比例超过5倍，使用双Y轴
  const maxRange = Math.max(...ranges.map(r => r.range))
  const minRange = Math.min(...ranges.filter(r => r.range > 0).map(r => r.range))
  
  if (minRange === 0) return false
  return maxRange / minRange > 5
})

// 自动分配Y轴：数值范围大的用左轴，小的用右轴
const assignYAxis = (series: ChartSeries[]): ChartSeries[] => {
  if (!needsDualYAxis.value || series.length < 2) {
    return series.map(s => ({ ...s, yAxisIndex: 0 }))
  }
  
  const ranges = series.map(s => {
    const values = s.data.map(([_, v]) => v).filter(v => v !== null && v !== undefined) as number[]
    if (values.length === 0) return 0
    const min = Math.min(...values)
    const max = Math.max(...values)
    return max - min
  })
  
  const maxRange = Math.max(...ranges)
  const threshold = maxRange / 5
  
  return series.map((s, idx) => {
    const range = ranges[idx]
    // 范围大的用左轴（0），范围小的用右轴（1）
    return {
      ...s,
      yAxisIndex: range >= threshold ? 0 : 1
    }
  })
}

// 获取Y轴配置
const getYAxisConfig = (series: ChartSeries[]) => {
  // 计算Y轴范围（自动调整）
  const allValues = series.flatMap(s => s.data.map(([_, v]) => v).filter(v => v !== null && v !== undefined) as number[])
  const yMin = allValues.length > 0 ? Math.min(...allValues) : 0
  const yMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const yPadding = (yMax - yMin) * 0.1 // 10% padding
  
  if (!needsDualYAxis.value) {
    return [{
      type: 'value',
      name: '',
      nameLocation: 'end',
      nameGap: 20,
      min: yMin - yPadding,
      max: yMax + yPadding,
      scale: false,
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
    }]
  }
  
  // 双Y轴配置
  const leftSeries = series.filter(s => s.yAxisIndex === 0)
  const rightSeries = series.filter(s => s.yAxisIndex === 1)
  
  const leftValues = leftSeries.flatMap(s => s.data.map(([_, v]) => v).filter(v => v !== null && v !== undefined) as number[])
  const rightValues = rightSeries.flatMap(s => s.data.map(([_, v]) => v).filter(v => v !== null && v !== undefined) as number[])
  
  const leftMin = leftValues.length > 0 ? Math.min(...leftValues) : 0
  const leftMax = leftValues.length > 0 ? Math.max(...leftValues) : 100
  const leftPadding = (leftMax - leftMin) * 0.1
  
  const rightMin = rightValues.length > 0 ? Math.min(...rightValues) : 0
  const rightMax = rightValues.length > 0 ? Math.max(...rightValues) : 100
  const rightPadding = (rightMax - rightMin) * 0.1
  
  return [
    {
      type: 'value',
      name: '',
      nameLocation: 'end',
      nameGap: 20,
      position: 'left',
      min: leftMin - leftPadding,
      max: leftMax + leftPadding,
      scale: false,
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    {
      type: 'value',
      name: '',
      nameLocation: 'end',
      nameGap: 20,
      position: 'right',
      min: rightMin - rightPadding,
      max: rightMax + rightPadding,
      scale: false,
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
    }
  ]
}

// 处理多年对比模式：将同指标不同年份的数据分组
const processCompareMode = (data: ChartData): ChartData => {
  // 提取年份信息（假设categories格式为 YYYY-MM-DD 或 YYYY-WNN 等）
  const seriesByMetric = new Map<string, Map<string, ChartSeries>>()
  
  data.series.forEach(series => {
    // 尝试从名称中提取指标名和年份
    // 例如："商品猪：出栏均价：中国(2025)" -> 指标："商品猪：出栏均价：中国"，年份：2025
    const match = series.name.match(/^(.+?)(?:\((\d{4})\))?$/)
    const metricName = match ? match[1] : series.name
    const year = match ? match[2] : null
    
    if (!seriesByMetric.has(metricName)) {
      seriesByMetric.set(metricName, new Map())
    }
    
    const yearMap = seriesByMetric.get(metricName)!
    if (year) {
      yearMap.set(year, series)
    } else {
      // 如果没有年份，尝试从数据中提取
      const firstDate = series.data[0]?.[0]
      if (firstDate) {
        const yearMatch = firstDate.match(/^(\d{4})/)
        const extractedYear = yearMatch ? yearMatch[1] : '未知'
        yearMap.set(extractedYear, series)
      }
    }
  })
  
  // 转换为多年对比格式：X轴为年内日期，多条线代表不同年份
  // 这里简化处理，如果检测到多年对比模式，保持原样
  // 实际应该重新组织数据，将X轴改为年内日期格式
  return data
}

const updateChart = () => {
  if (!chartInstance || !props.data) return
  
  let processedData = props.data
  
  // 多年对比模式处理
  if (chartMode.value === 'compare') {
    processedData = processCompareMode(props.data)
  }
  
  // 自动分配Y轴
  const assignedSeries = assignYAxis(processedData.series)
  const yAxisConfig = getYAxisConfig(assignedSeries)
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        
        let result = `<div style="margin-bottom: 4px;"><strong>${params[0].axisValue}</strong></div>`
        params.forEach((param: any) => {
          const value = param.value !== null && param.value !== undefined ? param.value.toFixed(2) : '-'
          const unit = param.seriesName.includes('价差') ? '元/千克' : 
                       param.seriesName.includes('均价') ? '元/千克' : ''
          const yAxisName = yAxisConfig.length > 1 && param.series.yAxisIndex === 1 ? '(右轴)' : ''
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}${yAxisName}: <strong>${value}${unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: assignedSeries.map(s => s.name),
      top: 10,
      type: 'plain', // 不使用滚动
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '15%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: processedData.categories,
      boundaryGap: false,
      // X轴不显示标签（默认时间轴）
      name: '',
      axisLabel: {
        rotate: chartMode.value === 'compare' ? 45 : 0,
        formatter: (value: string) => {
          // 多年对比模式：只显示月-日
          if (chartMode.value === 'compare') {
            const match = value.match(/(\d{2})-(\d{2})/)
            if (match) return `${match[1]}-${match[2]}`
          }
          return value
        }
      }
    },
    yAxis: yAxisConfig,
    series: assignedSeries.map((series, idx) => ({
      name: series.name,
      type: 'line',
      data: series.data.map(([_, value]) => value),
      smooth: true,
      yAxisIndex: series.yAxisIndex || 0,
      // 移除数据点
      symbol: 'none',
      // 处理断点：使用连续曲线
      connectNulls: true,
      lineStyle: {
        width: 2
      },
      // 自动颜色分配
      color: series.color || undefined
    })),
    // 只保留内部缩放，删除日期筛选进度条
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ]
  }
  
  chartInstance.setOption(option, true)
}

const handleModeChange = () => {
  updateChart()
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
  if (!chartInstance || !props.data) {
    ElMessage.warning('图表数据未加载，无法保存')
    return
  }
  
  try {
    // 获取图表数据URL（PNG格式）
    const dataURL = chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2, // 提高清晰度
      backgroundColor: '#fff'
    })
    
    // 创建下载链接
    const link = document.createElement('a')
    const seriesNames = props.data.series.map(s => s.name).join('_')
    const fileName = `图表_${seriesNames}_${new Date().toISOString().slice(0, 10)}.png`.replace(/[^\w\-_\.]/g, '_')
    link.download = fileName
    link.href = dataURL
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('图表已保存为PNG')
  } catch (error) {
    console.error('保存图表失败:', error)
    ElMessage.error('保存图表失败，请稍后重试')
  }
}

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
    
    window.addEventListener('resize', () => {
      chartInstance?.resize()
    })
  }
})

watch(() => props.data, updateChart, { deep: true })
watch(() => props.loading, (loading) => {
  if (!loading) {
    // 数据加载完成后更新图表
    setTimeout(updateChart, 100)
  }
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
  })
})
</script>

<style scoped>
.chart-panel {
  margin-bottom: 8px;
}
</style>
