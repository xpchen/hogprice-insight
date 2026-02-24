<template>
  <div class="production-indicators-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>规模场数据汇总</span>
          <DataSourceInfo
            v-if="latestDate"
            source-name="涌益咨询周度数据 - 月度-生产指标"
            :update-date="latestDate"
          />
        </div>
      </template>

      <!-- 图表1：母猪效能 -->
      <div class="chart-section">
        <h3>图表1：母猪效能</h3>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 400px" v-loading="loading1"></div>
        </div>
      </div>

      <!-- 图表2：压栏系数 -->
      <div class="chart-section">
        <h3>图表2：压栏系数</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 400px" v-loading="loading2"></div>
        </div>
      </div>

      <!-- 图表3：涌益生产指标 -->
      <div class="chart-section">
        <h3>图表3：涌益生产指标</h3>
        
        <!-- 图例筛选 -->
        <div class="filter-section">
          <span class="filter-label">图例筛选：</span>
          <el-checkbox-group v-model="selectedIndicators" @change="handleIndicatorChange">
            <el-checkbox
              v-for="indicator in indicatorNames"
              :key="indicator"
              :label="indicator"
            >
              {{ indicator }}
            </el-checkbox>
            <el-checkbox label="全部">全部</el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="chart-container">
          <div ref="chart3Ref" style="width: 100%; height: 400px" v-loading="loading3"></div>
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
  getSowEfficiency,
  getPressureCoefficient,
  getYongyiProductionIndicators
} from '@/api/production-indicators'
import type {
  ProductionIndicatorResponse,
  ProductionIndicatorsResponse
} from '@/api/production-indicators'
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import { yAxisHideMinMaxLabel } from '@/utils/chart-style'

const chart1Ref = ref<HTMLDivElement>()
const chart2Ref = ref<HTMLDivElement>()
const chart3Ref = ref<HTMLDivElement>()

let chart1Instance: echarts.ECharts | null = null
let chart2Instance: echarts.ECharts | null = null
let chart3Instance: echarts.ECharts | null = null

const loading1 = ref(false)
const loading2 = ref(false)
const loading3 = ref(false)

const chart1Data = ref<ProductionIndicatorResponse | null>(null)
const chart2Data = ref<ProductionIndicatorResponse | null>(null)
const chart3Data = ref<ProductionIndicatorsResponse | null>(null)

const latestDate = ref<string | null>(null)

// 图表3的指标筛选
const indicatorNames = ref<string[]>([])
const selectedIndicators = ref<string[]>(['全部'])

// 过滤后的图表3数据
const displayIndicators = computed(() => {
  if (!chart3Data.value) return []
  
  if (selectedIndicators.value.includes('全部')) {
    return indicatorNames.value
  }
  
  return selectedIndicators.value.filter(name => name !== '全部')
})

// 加载图表1数据
const loadChart1Data = async () => {
  loading1.value = true
  try {
    const response = await getSowEfficiency()
    chart1Data.value = response
    if (response.latest_date && !latestDate.value) {
      latestDate.value = response.latest_date
    }
    updateChart1()
  } catch (error: any) {
    console.error('加载图表1数据失败:', error)
    ElMessage.error('加载图表1数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading1.value = false
  }
}

// 加载图表2数据
const loadChart2Data = async () => {
  loading2.value = true
  try {
    const response = await getPressureCoefficient()
    chart2Data.value = response
    if (response.latest_date && !latestDate.value) {
      latestDate.value = response.latest_date
    }
    updateChart2()
  } catch (error: any) {
    console.error('加载图表2数据失败:', error)
    ElMessage.error('加载图表2数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading2.value = false
  }
}

// 加载图表3数据
const loadChart3Data = async () => {
  loading3.value = true
  try {
    const response = await getYongyiProductionIndicators()
    chart3Data.value = response
    indicatorNames.value = response.indicator_names
    // 默认选中全部
    selectedIndicators.value = ['全部']
    if (response.latest_date && !latestDate.value) {
      latestDate.value = response.latest_date
    }
    updateChart3()
  } catch (error: any) {
    console.error('加载图表3数据失败:', error)
    ElMessage.error('加载图表3数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading3.value = false
  }
}

// 更新图表1
const updateChart1 = () => {
  if (!chart1Ref.value || !chart1Data.value) return

  if (!chart1Instance) {
    chart1Instance = echarts.init(chart1Ref.value)
  }

  const option: echarts.EChartsOption = {
    title: {
      text: '母猪效能（分娩窝数）',
      left: 'left'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `${param.axisValue}<br/>${param.seriesName}: ${param.value}`
      }
    },
    legend: {
      data: ['分娩窝数'],
      bottom: 10,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chart1Data.value.data.map(d => d.date)
    },
    yAxis: {
      type: 'value',
      name: '窝数',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      },
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '分娩窝数',
        type: 'line',
        smooth: true,
        data: chart1Data.value.data.map(d => d.value),
        itemStyle: {
          color: '#5470c6'
        }
      }
    ]
  }

  chart1Instance.setOption(option)
}

// 更新图表2
const updateChart2 = () => {
  if (!chart2Ref.value || !chart2Data.value) return

  if (!chart2Instance) {
    chart2Instance = echarts.init(chart2Ref.value)
  }

  const option: echarts.EChartsOption = {
    title: {
      text: '压栏系数（窝均健仔数-河南）',
      left: 'left'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `${param.axisValue}<br/>${param.seriesName}: ${param.value}`
      }
    },
    legend: {
      data: ['窝均健仔数（河南）'],
      bottom: 10,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chart2Data.value.data.map(d => d.date)
    },
    yAxis: {
      type: 'value',
      name: '窝均健仔数',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      },
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '窝均健仔数（河南）',
        type: 'line',
        smooth: true,
        data: chart2Data.value.data.map(d => d.value),
        itemStyle: {
          color: '#91cc75'
        }
      }
    ]
  }

  chart2Instance.setOption(option)
}

// 更新图表3
const updateChart3 = () => {
  if (!chart3Ref.value || !chart3Data.value) return

  if (!chart3Instance) {
    chart3Instance = echarts.init(chart3Ref.value)
  }

  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272']
  
  const series = displayIndicators.value.map((indicator, idx) => {
    const data = chart3Data.value!.indicators[indicator] || []
    return {
      name: indicator,
      type: 'line',
      smooth: true,
      data: data.map(d => d.value),
      itemStyle: {
        color: colors[idx % colors.length]
      }
    }
  })

  // 获取所有数据的日期（取第一个指标的数据日期）
  const dates = displayIndicators.value.length > 0
    ? (chart3Data.value!.indicators[displayIndicators.value[0]] || []).map(d => d.date)
    : []

  const option: echarts.EChartsOption = {
    title: {
      text: '涌益生产指标（窝均健仔数）',
      left: 'left'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          result += `${param.seriesName}: ${param.value}<br/>`
        })
        return result
      }
    },
    legend: {
      data: displayIndicators.value,
      bottom: 10,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value',
      name: '窝均健仔数',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      },
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ],
    series
  }

  chart3Instance.setOption(option)
}

// 指标筛选变化处理
const handleIndicatorChange = () => {
  updateChart3()
}

// 监听窗口大小变化
const handleResize = () => {
  chart1Instance?.resize()
  chart2Instance?.resize()
  chart3Instance?.resize()
}

// 监听显示指标变化
watch(displayIndicators, () => {
  updateChart3()
})

onMounted(() => {
  loadChart1Data()
  loadChart2Data()
  loadChart3Data()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart1Instance?.dispose()
  chart2Instance?.dispose()
  chart3Instance?.dispose()
})
</script>

<style scoped lang="scss">
.production-indicators-page {
  padding: 4px;
  
  :deep(.el-card__body) {
    padding: 4px 6px;
  }
  
  .chart-section {
    margin-bottom: 12px;
    
    h3 {
      margin-bottom: 6px;
      font-size: 16px;
      font-weight: 600;
      text-align: left;
    }
  }

  .filter-section {
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    
    .filter-label {
      font-weight: 500;
      margin-right: 10px;
      min-width: 80px;
    }
  }

  .chart-container {
    margin-bottom: 12px;
  }
}
</style>
