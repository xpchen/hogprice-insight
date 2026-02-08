<template>
  <div class="supply-demand-curve-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E3. 供需曲线 - 长周期猪价推演</span>
          <DataSourceInfo
            v-if="latestMonth"
            source-name="定点屠宰、钢联全国猪价、NYB"
            :update-date="latestMonth"
          />
        </div>
      </template>

      <!-- 图表1：长周期生猪供需曲线 -->
      <div class="chart-section">
        <h3>图表1：长周期生猪供需曲线</h3>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 500px" v-loading="loading1"></div>
        </div>
      </div>

      <!-- 图表2：能繁母猪存栏&猪价（滞后10个月） -->
      <div class="chart-section">
        <h3>图表2：能繁母猪存栏&猪价（滞后10个月）</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 500px" v-loading="loading2"></div>
        </div>
      </div>

      <!-- 图表3：新生仔猪&猪价（滞后10个月） -->
      <div class="chart-section">
        <h3>图表3：新生仔猪&猪价（滞后10个月）</h3>
        <div class="chart-container">
          <div ref="chart3Ref" style="width: 100%; height: 500px" v-loading="loading3"></div>
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
  getSupplyDemandCurve,
  getBreedingInventoryPrice,
  getPigletPrice
} from '@/api/supply-demand'
import type {
  SupplyDemandCurveResponse,
  InventoryPriceResponse
} from '@/api/supply-demand'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const chart1Ref = ref<HTMLDivElement>()
const chart2Ref = ref<HTMLDivElement>()
const chart3Ref = ref<HTMLDivElement>()

let chart1Instance: echarts.ECharts | null = null
let chart2Instance: echarts.ECharts | null = null
let chart3Instance: echarts.ECharts | null = null

const loading1 = ref(false)
const loading2 = ref(false)
const loading3 = ref(false)

const chart1Data = ref<SupplyDemandCurveResponse | null>(null)
const chart2Data = ref<InventoryPriceResponse | null>(null)
const chart3Data = ref<InventoryPriceResponse | null>(null)

const latestMonth = ref<string | null>(null)

// 加载图表1数据
const loadChart1Data = async () => {
  loading1.value = true
  try {
    const response = await getSupplyDemandCurve()
    console.log('图表1数据加载成功:', response)
    chart1Data.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
    }
    console.log('chart1Data.value:', chart1Data.value)
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
    const response = await getBreedingInventoryPrice()
    chart2Data.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
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
    const response = await getPigletPrice()
    chart3Data.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
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
  if (!chart1Ref.value || !chart1Data.value) {
    console.log('updateChart1: 缺少数据或ref')
    return
  }

  if (!chart1Instance) {
    chart1Instance = echarts.init(chart1Ref.value)
  }

  console.log('updateChart1: 数据条数:', chart1Data.value.data.length)
  console.log('updateChart1: 前5条数据:', chart1Data.value.data.slice(0, 5))

  const option: echarts.EChartsOption = {
    title: {
      text: '长周期生猪供需曲线',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['定点屠宰系数', '猪价系数'],
      bottom: 10
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
      data: chart1Data.value.data.map(d => d.month)
    },
    yAxis: {
      type: 'value',
      name: '系数'
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
        name: '定点屠宰系数',
        type: 'line',
        smooth: true,
        data: chart1Data.value.data.map(d => d.slaughter_coefficient ?? null),
        itemStyle: { color: '#5470c6' },
        connectNulls: false  // 不连接null值
      },
      {
        name: '猪价系数',
        type: 'line',
        smooth: true,
        data: chart1Data.value.data.map(d => d.price_coefficient ?? null),
        itemStyle: { color: '#91cc75' },
        connectNulls: false  // 不连接null值
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

  // 双Y轴：左轴存栏指数，右轴猪价
  const option: echarts.EChartsOption = {
    title: {
      text: '能繁母猪存栏&猪价（滞后10个月）',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['能繁母猪存栏指数', '猪价'],
      bottom: 10
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
      data: chart2Data.value.data.map(d => d.month)
    },
    yAxis: [
      {
        type: 'value',
        name: '存栏指数',
        position: 'left'
      },
      {
        type: 'value',
        name: '猪价（元/公斤）',
        position: 'right'
      }
    ],
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
        name: '能繁母猪存栏指数',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: chart2Data.value.data.map(d => d.inventory_index),
        itemStyle: { color: '#5470c6' }
      },
      {
        name: '猪价',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: chart2Data.value.data.map(d => d.price),
        itemStyle: { color: '#91cc75' }
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

  const option: echarts.EChartsOption = {
    title: {
      text: '新生仔猪&猪价（滞后10个月）',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['新生仔猪指数', '猪价'],
      bottom: 10
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
      data: chart3Data.value.data.map(d => d.month)
    },
    yAxis: [
      {
        type: 'value',
        name: '存栏指数',
        position: 'left'
      },
      {
        type: 'value',
        name: '猪价（元/公斤）',
        position: 'right'
      }
    ],
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
        name: '新生仔猪指数',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: chart3Data.value.data.map(d => d.inventory_index),
        itemStyle: { color: '#5470c6' }
      },
      {
        name: '猪价',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: chart3Data.value.data.map(d => d.price),
        itemStyle: { color: '#91cc75' }
      }
    ]
  }

  chart3Instance.setOption(option)
}

// 监听窗口大小变化
const handleResize = () => {
  chart1Instance?.resize()
  chart2Instance?.resize()
  chart3Instance?.resize()
}

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
.supply-demand-curve-page {
  .chart-section {
    margin-bottom: 40px;
    
    h3 {
      margin-bottom: 15px;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .chart-container {
    margin-bottom: 20px;
  }
}
</style>
