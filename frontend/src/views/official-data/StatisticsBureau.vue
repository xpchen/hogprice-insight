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

      <!-- 图2：猪肉进口 -->
      <div class="chart-section">
        <h3>图2：猪肉进口</h3>
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
        text: '猪肉进口',
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
  const totalVolumes = data.map(d => d.total_volume)
  const country1Volumes = data.map(d => d.top_country1_volume)
  const country2Volumes = data.map(d => d.top_country2_volume)
  const country1Names = data.map(d => d.top_country1).filter((name, idx) => country1Volumes[idx] !== null)
  const country2Names = data.map(d => d.top_country2).filter((name, idx) => country2Volumes[idx] !== null)

  // 构建系列数据
  const series: any[] = [
    {
      name: '进口总量',
      type: 'bar',
      data: totalVolumes,
      itemStyle: {
        color: '#5470c6'
      }
    }
  ]

  // 如果有国家1数据，添加系列
  if (country1Volumes.some(v => v !== null)) {
    series.push({
      name: country1Names[0] || '最大国家1',
      type: 'bar',
      data: country1Volumes,
      itemStyle: {
        color: '#91cc75'
      }
    })
  }

  // 如果有国家2数据，添加系列
  if (country2Volumes.some(v => v !== null)) {
    series.push({
      name: country2Names[0] || '最大国家2',
      type: 'bar',
      data: country2Volumes,
      itemStyle: {
        color: '#fac858'
      }
    })
  }

  const option: echarts.EChartsOption = {
    title: {
      text: '猪肉进口',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const month = params[0].axisValue
        let result = `${month}<br/>`
        
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            result += `${param.seriesName}: ${param.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}万吨<br/>`
          }
        })
        
        return result
      }
    },
    legend: {
      show: false // 图例不需要注释
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: months
    },
    yAxis: {
      type: 'value',
      name: '进口量(万吨)',
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
    series: series
  }

  chart2Instance.setOption(option)

  // 添加点击事件，显示详细信息
  chart2Instance.off('click')
  chart2Instance.on('click', (params: any) => {
    const month = params.name
    const dataPoint = data.find(d => d.month === month)
    if (dataPoint) {
      let message = `进口总量: ${dataPoint.total_volume?.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) || '-'}万吨`
      if (dataPoint.top_country1 && dataPoint.top_country1_volume) {
        message += `\n${dataPoint.top_country1}进口量: ${dataPoint.top_country1_volume.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}万吨`
      }
      if (dataPoint.top_country2 && dataPoint.top_country2_volume) {
        message += `\n${dataPoint.top_country2}进口量: ${dataPoint.top_country2_volume.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}万吨`
      }
      ElMessage.info(message)
    }
  })
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
