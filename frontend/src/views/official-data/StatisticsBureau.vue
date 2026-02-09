<template>
  <div class="statistics-bureau-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E4. 统计局数据汇总</span>
          <DataSourceInfo
            v-if="latestPeriod || latestMonth"
            source-name="国家统计局、钢联模板"
            :update-date="latestPeriod || latestMonth"
          />
        </div>
      </template>

      <!-- 表1：统计局季度数据汇总 -->
      <div class="table-section">
        <h3>表1：统计局季度数据汇总</h3>
        <div class="table-container">
          <el-table
            :data="quarterlyTableData"
            border
            stripe
            v-loading="loadingTable1"
            style="width: 100%"
            :row-class-name="tableRowClassName"
            max-height="600"
          >
            <el-table-column prop="period" label="季度" width="120" fixed="left">
            </el-table-column>
            <el-table-column
              v-for="(header, idx) in quarterlyHeaders"
              :key="idx"
              :label="header || `列${getColumnLetter(idx + 1)}`"
              width="120"
              align="right"
            >
              <template #default="{ row }">
                {{ formatNumber(row.data[getColumnLetter(idx + 1)]) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 图1：统计局生猪出栏量&屠宰量 -->
      <div class="chart-section">
        <h3>图1：统计局生猪出栏量&屠宰量</h3>
        <div class="filter-section">
          <span class="filter-label">时间周期筛选：</span>
          <el-slider
            v-model="timeRange"
            :min="0"
            :max="100"
            :step="1"
            range
            @change="handleTimeRangeChange"
            style="width: 400px; margin-left: 20px"
          />
          <span style="margin-left: 20px; color: #666">
            {{ timeRangeText }}
          </span>
        </div>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 500px" v-loading="loadingChart1"></div>
        </div>
      </div>

      <!-- 图2：猪肉进口（实际是猪价系数） -->
      <div class="chart-section">
        <h3>图2：猪肉进口（猪价系数）</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 500px" v-loading="loadingChart2"></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getQuarterlyData,
  getOutputSlaughter,
  getImportMeat
} from '@/api/statistics-bureau'
import type {
  QuarterlyDataResponse,
  OutputSlaughterResponse,
  ImportMeatResponse
} from '@/api/statistics-bureau'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const chart1Ref = ref<HTMLDivElement>()
const chart2Ref = ref<HTMLDivElement>()

let chart1Instance: echarts.ECharts | null = null
let chart2Instance: echarts.ECharts | null = null

const loadingTable1 = ref(false)
const loadingChart1 = ref(false)
const loadingChart2 = ref(false)

const quarterlyData = ref<QuarterlyDataResponse | null>(null)
const outputSlaughterData = ref<OutputSlaughterResponse | null>(null)
const importMeatData = ref<ImportMeatResponse | null>(null)

const latestPeriod = ref<string | null>(null)
const latestMonth = ref<string | null>(null)

const timeRange = ref<[number, number]>([0, 100])

// 计算属性
const quarterlyHeaders = computed(() => {
  return quarterlyData.value?.headers || []
})

const quarterlyTableData = computed(() => {
  return quarterlyData.value?.data || []
})

const filteredOutputSlaughterData = computed(() => {
  if (!outputSlaughterData.value) return []
  const data = outputSlaughterData.value.data
  if (data.length === 0) return []
  
  const [startPercent, endPercent] = timeRange.value
  const startIdx = Math.floor((data.length - 1) * startPercent / 100)
  const endIdx = Math.floor((data.length - 1) * endPercent / 100)
  
  return data.slice(startIdx, endIdx + 1)
})

const timeRangeText = computed(() => {
  if (!outputSlaughterData.value || outputSlaughterData.value.data.length === 0) {
    return ''
  }
  const data = outputSlaughterData.value.data
  const [startPercent, endPercent] = timeRange.value
  const startIdx = Math.floor((data.length - 1) * startPercent / 100)
  const endIdx = Math.floor((data.length - 1) * endPercent / 100)
  
  const startPeriod = data[startIdx]?.period || ''
  const endPeriod = data[endIdx]?.period || ''
  
  return `${startPeriod} 至 ${endPeriod}`
})

// 工具函数
const getColumnLetter = (idx: number): string => {
  // B=1, C=2, ..., Y=24
  return String.fromCharCode(65 + idx) // A=65, B=66, etc.
}

const formatNumber = (val: number | null | undefined): string => {
  if (val === null || val === undefined) return '-'
  return val.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  return rowIndex % 2 === 1 ? 'even-row' : ''
}

const handleTimeRangeChange = () => {
  updateChart1()
}

// 加载表1数据
const loadQuarterlyData = async () => {
  loadingTable1.value = true
  try {
    const response = await getQuarterlyData()
    quarterlyData.value = response
  } catch (error: any) {
    console.error('加载季度数据失败:', error)
    ElMessage.error('加载季度数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingTable1.value = false
  }
}

// 加载图1数据
const loadOutputSlaughterData = async () => {
  loadingChart1.value = true
  try {
    const response = await getOutputSlaughter()
    outputSlaughterData.value = response
    if (response.latest_period && !latestPeriod.value) {
      latestPeriod.value = response.latest_period
    }
    updateChart1()
  } catch (error: any) {
    console.error('加载出栏量&屠宰量数据失败:', error)
    ElMessage.error('加载出栏量&屠宰量数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingChart1.value = false
  }
}

// 加载图2数据
const loadImportMeatData = async () => {
  loadingChart2.value = true
  try {
    const response = await getImportMeat()
    importMeatData.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
    }
    updateChart2()
  } catch (error: any) {
    console.error('加载猪肉进口数据失败:', error)
    ElMessage.error('加载猪肉进口数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingChart2.value = false
  }
}

// 更新图表1
const updateChart1 = () => {
  if (!chart1Ref.value || !outputSlaughterData.value) return

  if (!chart1Instance) {
    chart1Instance = echarts.init(chart1Ref.value)
  }

  const data = filteredOutputSlaughterData.value
  if (data.length === 0) {
    chart1Instance.setOption({
      title: {
        text: '统计局生猪出栏量&屠宰量',
        left: 'center'
      },
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '暂无数据',
          fontSize: 16,
          fill: '#999'
        }
      }
    })
    return
  }

  const periods = data.map(d => d.period)
  const outputVolumes = data.map(d => d.output_volume)
  const slaughterVolumes = data.map(d => d.slaughter_volume)
  const scaleRates = data.map(d => d.scale_rate ? d.scale_rate * 100 : null) // 转换为百分比

  const option: echarts.EChartsOption = {
    title: {
      text: '统计局生猪出栏量&屠宰量',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            if (param.seriesName.includes('规模化率')) {
              result += `${param.seriesName}: ${param.value.toFixed(2)}%<br/>`
            } else {
              result += `${param.seriesName}: ${param.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}<br/>`
            }
          }
        })
        return result
      }
    },
    legend: {
      data: ['季度出栏量', '定点屠宰量', '规模化率'],
      top: 30
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
      data: periods
    },
    yAxis: [
      {
        type: 'value',
        name: '出栏量/屠宰量',
        position: 'left',
        axisLabel: {
          formatter: '{value}'
        }
      },
      {
        type: 'value',
        name: '规模化率(%)',
        position: 'right',
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    dataZoom: [
      {
        type: 'slider',
        show: true,
        xAxisIndex: [0],
        start: 0,
        end: 100
      },
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '季度出栏量',
        type: 'line',
        yAxisIndex: 0,
        data: outputVolumes,
        connectNulls: false,
        itemStyle: {
          color: '#5470c6'
        }
      },
      {
        name: '定点屠宰量',
        type: 'line',
        yAxisIndex: 0,
        data: slaughterVolumes,
        connectNulls: false,
        itemStyle: {
          color: '#91cc75'
        }
      },
      {
        name: '规模化率',
        type: 'line',
        yAxisIndex: 1,
        data: scaleRates,
        connectNulls: false,
        itemStyle: {
          color: '#fac858'
        }
      }
    ]
  }

  chart1Instance.setOption(option)
}

// 更新图表2
const updateChart2 = () => {
  if (!chart2Ref.value || !importMeatData.value) return

  if (!chart2Instance) {
    chart2Instance = echarts.init(chart2Ref.value)
  }

  const data = importMeatData.value.data
  if (data.length === 0) {
    chart2Instance.setOption({
      title: {
        text: '猪肉进口（猪价系数）',
        left: 'center'
      },
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '暂无数据',
          fontSize: 16,
          fill: '#999'
        }
      }
    })
    return
  }

  const months = data.map(d => d.month)
  const priceCoefficients = data.map(d => d.price_coefficient)

  const option: echarts.EChartsOption = {
    title: {
      text: '猪肉进口（猪价系数）',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const month = params[0].axisValue
        let result = `${month}<br/>`
        
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            result += `${param.seriesName}: ${param.value.toFixed(4)}<br/>`
          }
        })
        
        return result
      }
    },
    legend: {
      data: ['猪价系数'],
      top: 30
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
      data: months
    },
    yAxis: {
      type: 'value',
      name: '系数',
      axisLabel: {
        formatter: '{value}'
      }
    },
    dataZoom: [
      {
        type: 'slider',
        show: true,
        xAxisIndex: [0],
        start: 0,
        end: 100
      },
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '猪价系数',
        type: 'line',
        smooth: true,
        data: priceCoefficients,
        connectNulls: false,
        itemStyle: {
          color: '#5470c6'
        }
      }
    ]
  }

  chart2Instance.setOption(option)
}

// 监听窗口大小变化
const handleResize = () => {
  chart1Instance?.resize()
  chart2Instance?.resize()
}

onMounted(() => {
  loadQuarterlyData()
  loadOutputSlaughterData()
  loadImportMeatData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart1Instance?.dispose()
  chart2Instance?.dispose()
})
</script>

<style scoped>
.statistics-bureau-page {
  padding: 20px;
}

.table-section,
.chart-section {
  margin-bottom: 40px;
}

.table-section h3,
.chart-section h3 {
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
}

.table-container {
  margin-top: 15px;
}

.chart-container {
  margin-top: 15px;
}

.filter-section {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.filter-label {
  font-weight: 500;
}

:deep(.even-row) {
  background-color: #f5f7fa;
}
</style>
