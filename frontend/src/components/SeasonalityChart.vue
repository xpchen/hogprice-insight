<template>
  <el-card class="seasonality-chart-panel">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>{{ title || '季节性图表' }}</span>
        <div style="display: flex; gap: 10px; align-items: center">
          <el-radio-group v-model="xMode" size="small" @change="handleModeChange">
            <el-radio-button label="week_of_year">周序号</el-radio-button>
            <el-radio-button label="month_day">月-日</el-radio-button>
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
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

export interface SeasonalityData {
  x_values: number[] | string[]  // 1..52 或 "01-01".."12-31"
  series: Array<{
    year: number
    values: Array<number | null>
  }>
  meta: {
    unit: string
    freq: string
    metric_name: string
  }
}

const props = defineProps<{
  data: SeasonalityData | null
  loading?: boolean
  title?: string
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const xMode = ref<'week_of_year' | 'month_day'>('week_of_year')

// 年份颜色映射（固定颜色，保证一致性）
const yearColors: Record<number, string> = {
  2021: '#FFB6C1',  // 浅粉
  2022: '#FF69B4',  // 粉
  2023: '#4169E1',  // 中蓝
  2024: '#D3D3D3',  // 浅灰
  2025: '#1E90FF',  // 深蓝
  2026: '#FF0000',  // 红
  2027: '#32CD32',  // 绿
  2028: '#FFA500',  // 橙
}

const getYearColor = (year: number): string => {
  return yearColors[year] || `#${Math.floor(Math.random() * 16777215).toString(16)}`
}

const updateChart = () => {
  if (!chartInstance || !props.data) return
  
  const { x_values, series, meta } = props.data
  
  // 根据xMode过滤x_values（如果数据包含两种模式）
  let displayXValues = x_values
  
  // 格式化x轴标签
  const formatXLabel = (value: number | string): string => {
    if (typeof value === 'number') {
      return `第${value}周`
    } else {
      // "MM-DD"格式
      return value
    }
  }
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        
        let result = `<div style="margin-bottom: 4px;"><strong>${formatXLabel(params[0].axisValue)}</strong></div>`
        params.forEach((param: any) => {
          const value = param.value !== null && param.value !== undefined 
            ? param.value.toFixed(2) 
            : '-'
          const unit = meta.unit || ''
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}: <strong>${value}${unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: series.map(s => `${s.year}年度`),
      bottom: 0,
      type: 'scroll'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: displayXValues.map(formatXLabel),
      boundaryGap: false,
      axisLabel: {
        rotate: xMode.value === 'month_day' ? 45 : 0,
        interval: xMode.value === 'month_day' ? 'auto' : 0,
        formatter: (value: string) => {
          // 如果是周序号模式，只显示部分标签
          if (xMode.value === 'week_of_year') {
            const weekNum = parseInt(value.replace('第', '').replace('周', ''))
            if (weekNum % 4 === 0 || weekNum === 1 || weekNum === 52) {
              return value
            }
            return ''
          }
          return value
        }
      }
    },
    yAxis: {
      type: 'value',
      name: meta.unit || '',
      nameLocation: 'end',
      nameGap: 20
    },
    series: series.map(s => ({
      name: `${s.year}年度`,
      type: 'line',
      data: s.values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: {
        width: 2
      },
      color: getYearColor(s.year),
      // 缺失值断线
      connectNulls: false
    })),
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
  
  chartInstance.setOption(option, true)
}

const handleModeChange = () => {
  updateChart()
}

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
    const fileName = `${props.title || '季节性图表'}_${new Date().toISOString().slice(0, 10)}.png`
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
.seasonality-chart-panel {
  margin-bottom: 20px;
}
</style>
