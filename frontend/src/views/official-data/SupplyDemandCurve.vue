<template>
  <div class="supply-demand-curve-page">
    <el-card class="chart-page-card">
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
        <h3>图1：长周期生猪供需曲线</h3>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 500px" v-loading="loading1"></div>
        </div>
      </div>

      <!-- 图表2：能繁母猪存栏&猪价（滞后10个月） -->
      <div class="chart-section">
        <h3>图2：能繁母猪存栏&猪价（滞后10个月）</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 500px" v-loading="loading2"></div>
        </div>
      </div>

      <!-- 图表3：新生仔猪&猪价（滞后10个月） -->
      <div class="chart-section">
        <h3>图3：新生仔猪&猪价（滞后10个月）</h3>
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

const chart1Data = ref<SupplyDemandCurveResponse | null>(null)
const chart2Data = ref<InventoryPriceResponse | null>(null)
const chart3Data = ref<InventoryPriceResponse | null>(null)

const latestMonth = ref<string | null>(null)

// 加载图表1数据
const loadChart1Data = async () => {
  loading1.value = true
  try {
    const response = await getSupplyDemandCurve()
    chart1Data.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
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

// 将数据按年份分组，每年一条线：横轴屠宰系数，纵轴价格系数，按月份顺序
function buildSupplyDemandSeries(data: { month: string; slaughter_coefficient?: number | null; price_coefficient?: number | null }[]) {
  const byYear = new Map<number, Array<{ price: number; slaughter: number; month: string }>>()
  for (const d of data) {
    const price = d.price_coefficient
    const slaughter = d.slaughter_coefficient
    if (price == null || slaughter == null || isNaN(price) || isNaN(slaughter)) continue
    const [yStr, mStr] = d.month.split('-')
    const year = parseInt(yStr, 10)
    if (isNaN(year)) continue
    if (!byYear.has(year)) byYear.set(year, [])
    byYear.get(year)!.push({ price, slaughter, month: d.month })
  }
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452']
  const series: echarts.SeriesOption[] = []
  const years = Array.from(byYear.keys()).sort((a, b) => a - b)
  years.forEach((year, i) => {
    const pts = byYear.get(year)!
    pts.sort((a, b) => a.month.localeCompare(b.month))
    const lineData = pts.map(p => [p.slaughter, p.price])  // [x屠宰系数, y价格系数]
    series.push({
      name: `${year}年`,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: lineData,
      itemStyle: { color: colors[i % colors.length] },
      lineStyle: { width: 2 }
    })
  })
  return { series, years }
}

// 更新图表1：供需曲线（横轴价格系数，纵轴屠宰系数，每年一条线）
const updateChart1 = () => {
  if (!chart1Ref.value || !chart1Data.value) return

  if (!chart1Instance) {
    chart1Instance = echarts.init(chart1Ref.value)
  }

  const { series, years } = buildSupplyDemandSeries(chart1Data.value.data)
  if (series.length === 0) {
    chart1Instance.setOption({
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: { text: '暂无有效数据（需同时有价格系数和屠宰系数）', fontSize: 14, fill: '#999' }
      }
    })
    return
  }

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (!params?.data) return ''
        const [slaughter, price] = params.data
        return `${params.seriesName}<br/>屠宰系数: ${Number(slaughter).toFixed(2)}<br/>价格系数: ${Number(price).toFixed(2)}`
      }
    },
    legend: {
      data: years.map(y => `${y}年`),
      top: 8,
      type: 'scroll',
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '12%',
      bottom: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '屠宰系数',
      interval: 0.2,
      minInterval: 0.2,
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
    },
    yAxis: {
      type: 'value',
      name: '价格系数',
      interval: 0.2,
      minInterval: 0.2,
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
    },
    series
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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['能繁母猪存栏指数', '猪价'],
      top: 8,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '12%',
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
        position: 'left',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
      },
      {
        type: 'value',
        name: '猪价',
        position: 'right',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['新生仔猪指数', '猪价'],
      top: 8,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '12%',
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
        position: 'left',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
      },
      {
        type: 'value',
        name: '猪价',
        position: 'right',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
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
  padding: 4px;
  
  :deep(.el-card__body) {
    padding: 4px 6px;
  }
  
  .chart-section {
    margin-bottom: 12px;

    h3 {
      font-size: 14px;
      font-weight: 600;
      margin: 0 0 8px 0;
      color: #303133;
    }
  }

  .chart-container {
    margin-bottom: 20px;
  }
}
</style>
