<template>
  <el-card class="seasonality-chart-panel">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>{{ title || '季节性图表' }}</span>
        <div v-if="changeInfo" class="change-info" style="display: flex; gap: 20px; font-size: 14px">
          <span v-if="changeInfo.period_change !== null" class="change-item">
            本期涨跌：
            <span :class="getChangeClass(changeInfo.period_change)">
              {{ formatChange(changeInfo.period_change) }}
            </span>
          </span>
          <span v-if="changeInfo.yoy_change !== null" class="change-item">
            较去年同期涨跌：
            <span :class="getChangeClass(changeInfo.yoy_change)">
              {{ formatChange(changeInfo.yoy_change) }}
            </span>
          </span>
        </div>
      </div>
    </template>
    <div class="chart-content">
      <div ref="chartRef" style="width: 100%; height: 500px;" v-loading="loading"></div>
      <div v-if="sourceName || updateDate" class="data-source-info">
        <span v-if="sourceName">数据来源：{{ sourceName }}</span>
        <span v-if="sourceName && updateDate" class="separator"> </span>
        <span v-if="updateDate">更新日期：{{ updateDate }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getYearColor, axisLabelDecimalFormatter } from '@/utils/chart-style'

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
  lunarAlignment?: boolean  // 是否支持农历对齐
  changeInfo?: {
    period_change: number | null
    yoy_change: number | null
  } | null  // 变化信息（本期涨跌、较去年同期涨跌）
  sourceName?: string | null  // 数据来源名称（标准化：钢联/涌益）
  updateDate?: string | null  // 更新日期（格式：X年X月X日）
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const xMode = ref<'week_of_year' | 'month_day' | 'lunar_day_index'>('week_of_year')

// 图例选中状态（用于控制显示/隐藏）
const legendSelected = ref<Record<string, boolean>>({})


const updateChart = () => {
  if (!chartRef.value || !chartInstance || !props.data) {
    // 如果chartRef还没有挂载，尝试初始化
    if (chartRef.value && !chartInstance) {
      chartInstance = echarts.init(chartRef.value)
    } else {
      return
    }
  }
  
  const { x_values, series, meta } = props.data
  
  // 初始化图例选中状态（默认全部显示）
  if (Object.keys(legendSelected.value).length === 0) {
    series.forEach(s => {
      const seriesName = `${s.year}年`
      legendSelected.value[seriesName] = true
    })
  }
  
  // 计算Y轴范围（自动调整）
  const allValues = series.flatMap(s => s.values).filter(v => v !== null && v !== undefined) as number[]
  const yMin = allValues.length > 0 ? Math.min(...allValues) : 0
  const yMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const yPadding = (yMax - yMin) * 0.1 // 10% padding
  
  // 根据xMode过滤x_values（如果数据包含两种模式）
  let displayXValues = x_values
  
  // 是否为月-日格式的日度数据（用于 X 轴显示与稀疏化）
  const isMonthDayData = Array.isArray(x_values) && x_values.length > 0 && typeof x_values[0] === 'string' && /^\d{1,2}-\d{1,2}$/.test(String(x_values[0]))
  
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
      data: series.map(s => `${s.year}年`),
      top: 10,
      type: 'plain', // 不使用滚动，使用plain类型
      selected: legendSelected.value,
      selectedMode: true,
      // 自定义图例图标：只显示圆点，不显示直线
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      orient: 'horizontal',
      left: 'left',
      // 计算每行显示的数量（假设总共显示所有年份）
      formatter: (name: string) => name
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '15%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: displayXValues.map(formatXLabel),
      boundaryGap: false,
      name: '',
      axisLabel: {
        rotate: isMonthDayData ? 45 : 0,
        interval: isMonthDayData ? 'auto' : 0,
        formatter: (value: string) => {
          // 月-日格式（如 01-16）：直接显示，避免 parseInt 误判导致空白
          if (/^\d{1,2}-\d{1,2}$/.test(value)) {
            return value
          }
          // 周序号格式（如 第1周）：只显示部分标签
          const weekNum = parseInt(value.replace('第', '').replace('周', ''), 10)
          if (!isNaN(weekNum)) {
            if (weekNum % 4 === 0 || weekNum === 1 || weekNum === 52) return value
            return ''
          }
          return value
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '',
      nameLocation: 'end',
      nameGap: 20,
      min: yMin - yPadding,
      max: yMax + yPadding,
      scale: false,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    series: series.map(s => {
      const isLeap = (s as any).is_leap_month
      const seriesName = `${s.year}年${isLeap ? '(闰月)' : ''}`
      const lineColor = getYearColor(s.year)
      
      return {
        name: seriesName,
        type: 'line',
        data: s.values,
        smooth: true,
        // 移除数据点
        symbol: 'none',
        lineStyle: {
          width: 2,
          type: isLeap ? 'dashed' : 'solid',  // 闰月用虚线
          color: lineColor
        },
        color: lineColor,
        // 处理断点：使用连续曲线
        connectNulls: true
      }
    }),
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
  
  // 监听图例点击事件
  chartInstance.off('legendselectchanged')
  chartInstance.on('legendselectchanged', (params: any) => {
    // 更新图例选中状态
    legendSelected.value = { ...params.selected }
    // 重新设置option以应用选中状态
    chartInstance?.setOption({
      legend: {
        selected: legendSelected.value
      }
    })
    // 重新计算Y轴范围（根据当前显示的数据）
    const visibleSeries = series.filter(s => {
      const seriesName = `${s.year}年`
      return legendSelected.value[seriesName] !== false
    })
    const visibleValues = visibleSeries.flatMap(s => s.values).filter(v => v !== null && v !== undefined) as number[]
    if (visibleValues.length > 0) {
      const newYMin = Math.min(...visibleValues)
      const newYMax = Math.max(...visibleValues)
      const newYPadding = (newYMax - newYMin) * 0.1
      chartInstance?.setOption({
        yAxis: {
          min: newYMin - newYPadding,
          max: newYMax + newYPadding
        }
      })
    }
  })
}

onMounted(() => {
  // 使用nextTick确保DOM已完全渲染
  nextTick(() => {
    if (chartRef.value) {
      try {
        chartInstance = echarts.init(chartRef.value)
        updateChart()
        
        const handleResize = () => {
          if (chartInstance) {
            chartInstance.resize()
          }
        }
        window.addEventListener('resize', handleResize)
        
        // 保存resize handler以便清理
        ;(window as any).__seasonalityChartResizeHandler = handleResize
      } catch (error) {
        console.error('初始化图表失败:', error)
      }
    }
  })
})

watch(() => props.data, () => {
  // 重置图例选中状态
  legendSelected.value = {}
  // 使用nextTick确保DOM已更新
  if (chartRef.value) {
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value)
    }
    updateChart()
  }
}, { deep: true })

watch(() => props.loading, (loading) => {
  if (!loading && chartRef.value) {
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value)
    }
    setTimeout(updateChart, 100)
  }
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  const resizeHandler = (window as any).__seasonalityChartResizeHandler
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    delete (window as any).__seasonalityChartResizeHandler
  }
})

// 格式化涨跌值
const formatChange = (value: number | null): string => {
  if (value === null) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}`
}

// 获取涨跌样式类
const getChangeClass = (value: number | null): string => {
  if (value === null) return ''
  return value >= 0 ? 'change-positive' : 'change-negative'
}
</script>

<style scoped>
.seasonality-chart-panel {
  margin-bottom: 8px;
}

.change-info {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.change-positive {
  color: #f56c6c;
  font-weight: bold;
}

.change-negative {
  color: #67c23a;
  font-weight: bold;
}

.chart-content {
  position: relative;
}

.data-source-info {
  font-size: 12px;
  color: #909399;
  text-align: right;
  margin-top: 6px;
  padding-right: 8px;
}

.separator {
  margin: 0 8px;
}
</style>
