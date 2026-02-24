<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="dashboard-title">生猪市场全景监控</h1>
        <span class="dashboard-subtitle">核心指标一览</span>
      </div>
      <el-button type="primary" :loading="exportLoading" @click="exportToWord" class="export-btn">
        <el-icon><Download /></el-icon>
        导出到 Word
      </el-button>
    </header>

    <div class="charts-grid">
      <!-- 1. 全国猪价 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">全国猪价</h3>
        </div>
        <div class="card-body">
          <ChartPanel ref="chart1Ref" :data="cardNationalPriceData" :loading="loadingPriceDisplay" />
        </div>
      </div>

      <!-- 2. 标肥价差 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">标肥价差</h3>
        </div>
        <div class="card-body">
          <ChartPanel ref="chart2Ref" :data="cardStdFatSpreadData" :loading="loadingPriceDisplay" />
        </div>
      </div>

      <!-- 3. 猪价&标肥价差 -->
      <div class="chart-card chart-card-wide">
        <div class="card-header">
          <h3 class="card-title">猪价&标肥价差</h3>
        </div>
        <div class="card-body">
          <DualAxisChart ref="chart3Ref" :data="card1Data" :loading="loadingPriceDisplay" axis1="left" axis2="right" />
        </div>
      </div>

      <!-- 4. 日度屠宰量（农历） -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">日度屠宰量（农历）</h3>
        </div>
        <div class="card-body">
          <SeasonalityChart
            ref="chart4Ref"
            :data="card2Data"
            :loading="loadingPriceDisplay"
            :lunar-alignment="true"
            :show-year-filter="false"
          />
        </div>
      </div>

      <!-- 5. 屠宰量&价格 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">屠宰量&价格</h3>
        </div>
        <div class="card-body">
          <ChartPanel ref="chart5Ref" :data="card3Data" :loading="loadingPriceDisplay" />
        </div>
      </div>

      <!-- 6. 标肥价差（分省区） -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">标肥价差（分省区）</h3>
        </div>
        <div class="card-body">
          <ChartPanel ref="chart6Ref" :data="provinceSpreadChartData" :loading="loadingProvinceSpread" />
        </div>
      </div>

      <!-- 7. 毛白价差比率&生猪价格 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">毛白价差比率&生猪价格</h3>
        </div>
        <div class="card-body">
          <DualAxisChart ref="chart7Ref" :data="liveWhiteLeftData" :loading="loadingLiveWhite" axis1="left" axis2="right" />
        </div>
      </div>

      <!-- 8. 毛白价差&比率 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">毛白价差&比率</h3>
        </div>
        <div class="card-body">
          <DualAxisChart ref="chart8Ref" :data="liveWhiteRightData" :loading="loadingLiveWhite" axis1="left" axis2="right" />
        </div>
      </div>

      <!-- 9. 升贴水 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">升贴水</h3>
        </div>
        <div class="card-body">
          <DashboardLineChart ref="chart9Ref" :data="premiumChartData" :loading="futuresLoading" />
        </div>
      </div>

      <!-- 10. 供求曲线 -->
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">供求曲线</h3>
        </div>
        <div class="card-body">
          <div ref="chart10Ref" class="supply-demand-chart" v-loading="loadingSupplyDemand"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { Document, Packer, Paragraph, ImageRun, TextRun } from 'docx'
import { saveAs } from 'file-saver'
import DualAxisChart from '../components/DualAxisChart.vue'
import SeasonalityChart from '../components/SeasonalityChart.vue'
import ChartPanel from '../components/ChartPanel.vue'
import DashboardLineChart from '../components/DashboardLineChart.vue'
import { futuresApi } from '../api/futures'
import {
  getLiveWhiteSpreadDualAxis,
  getPriceAndSpread,
  getSlaughterLunar,
  getSlaughterPriceTrendSolar
} from '../api/price-display'
import { getFatStdSpreadProvinces, getFatStdSpreadProvinceSeasonality } from '../api/price-display'
import { getSupplyDemandCurve } from '../api/supply-demand'
import * as echarts from 'echarts'
import { yAxisHideMinMaxLabel } from '@/utils/chart-style'
import type { DualAxisData } from '../components/DualAxisChart.vue'
import type { SeasonalityData } from '../components/SeasonalityChart.vue'
import type { ChartData } from '../components/ChartPanel.vue'

const chart1Ref = ref<InstanceType<typeof ChartPanel> | null>(null)
const chart2Ref = ref<InstanceType<typeof ChartPanel> | null>(null)
const chart3Ref = ref<InstanceType<typeof DualAxisChart> | null>(null)
const chart4Ref = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chart5Ref = ref<InstanceType<typeof ChartPanel> | null>(null)
const chart6Ref = ref<InstanceType<typeof ChartPanel> | null>(null)
const chart7Ref = ref<InstanceType<typeof DualAxisChart> | null>(null)
const chart8Ref = ref<InstanceType<typeof DualAxisChart> | null>(null)
const chart9Ref = ref<InstanceType<typeof DashboardLineChart> | null>(null)
const chart10Ref = ref<HTMLDivElement | null>(null)
const exportLoading = ref(false)
let chart10Instance: echarts.ECharts | null = null

const loadingPriceDisplay = ref(false)
const futuresLoading = ref(false)
const loadingLiveWhite = ref(false)
const loadingProvinceSpread = ref(false)
const loadingSupplyDemand = ref(false)
const priceSpreadData = ref<any>(null)
const slaughterLunarData = ref<any>(null)
const slaughterPriceTrendData = ref<any>(null)
const premiumData = ref<any>(null)
const liveWhiteData = ref<{
  spread_data?: Array<{ date: string; value: number | null }>
  ratio_data?: Array<{ date: string; value: number | null }>
  spread_unit?: string
  ratio_unit?: string
} | null>(null)
const provinceSpreadData = ref<ChartData | null>(null)
const supplyDemandData = ref<any>(null)

// 图表 1：全国猪价（来自 price-display）
const cardNationalPriceData = computed<ChartData | null>(() => {
  const pd = priceSpreadData.value?.price_data
  if (!pd?.length) return null
  const categories = pd.map((d: any) => d.date).filter(Boolean)
  return {
    categories,
    series: [{ name: '全国猪价', data: pd.map((d: any) => [d.date, d.value]), unit: '元/公斤' }]
  }
})

// 图表 2：标肥价差（来自 price-display）
const cardStdFatSpreadData = computed<ChartData | null>(() => {
  const sd = priceSpreadData.value?.spread_data
  if (!sd?.length) return null
  const categories = sd.map((d: any) => d.date).filter(Boolean)
  return {
    categories,
    series: [{ name: '标肥价差', data: sd.map((d: any) => [d.date, d.value]), unit: '元/公斤' }]
  }
})

// 图表 3：猪价&标肥价差 双轴
const card1Data = computed<DualAxisData | null>(() => {
  const pd = priceSpreadData.value?.price_data || []
  const sd = priceSpreadData.value?.spread_data || []
  if (!pd.length && !sd.length) return null
  return {
    series1: { name: '全国猪价', data: pd.map((d: any) => ({ date: d.date, value: d.value })), unit: '元/公斤' },
    series2: { name: '标肥价差', data: sd.map((d: any) => ({ date: d.date, value: d.value })), unit: '元/公斤' }
  }
})

// 图表 4：日度屠宰量（农历）（来自 price-display）
const card2Data = computed<SeasonalityData | null>(() => {
  const raw = slaughterLunarData.value?.series
  if (!raw?.length) return null
  const allMonthDays = new Set<string>()
  raw.forEach((s: any) => {
    (s.data || []).forEach((d: any) => { if (d.month_day) allMonthDays.add(d.month_day) })
  })
  const x_values = Array.from(allMonthDays).sort((a, b) => (parseInt(a) || 0) - (parseInt(b) || 0))
  const series = raw.map((s: any) => {
    const valueMap = new Map<string, number | null>()
    ;(s.data || []).forEach((d: any) => { if (d.month_day) valueMap.set(d.month_day, d.value ?? null) })
    return { year: s.year, values: x_values.map(md => valueMap.get(md) ?? null) }
  })
  return {
    x_values,
    series,
    meta: { unit: slaughterLunarData.value?.unit || '头', freq: 'D', metric_name: '日度屠宰量' }
  } as SeasonalityData
})

// 图表 5：屠宰量&价格（来自 price-display）
const card3Data = computed<ChartData | null>(() => {
  const slaughter = slaughterPriceTrendData.value?.slaughter_data || []
  const price = slaughterPriceTrendData.value?.price_data || []
  if (!slaughter.length && !price.length) return null
  const allDates = new Set<string>()
  slaughter.forEach((d: any) => allDates.add(d.date))
  price.forEach((d: any) => allDates.add(d.date))
  const categories = Array.from(allDates).sort()
  const slaughterMap = new Map(slaughter.map((d: any) => [d.date, d.value]))
  const priceMap = new Map(price.map((d: any) => [d.date, d.value]))
  const series: any[] = []
  if (slaughter.some((d: any) => d.value != null)) {
    series.push({ name: '屠宰量', data: categories.map(d => [d, slaughterMap.get(d) ?? null]), unit: '头' })
  }
  if (price.some((d: any) => d.value != null)) {
    series.push({ name: '价格', data: categories.map(d => [d, priceMap.get(d) ?? null]), unit: '元/公斤' })
  }
  if (!series.length) return null
  return { categories, series }
})

// 图表 6：标肥价差（分省区）— 使用 provinceSpreadData
const provinceSpreadChartData = computed<ChartData | null>(() => provinceSpreadData.value)

// 图表 7-8：毛白价差
const liveWhiteLeftData = computed<DualAxisData | null>(() => {
  if (!liveWhiteData.value) return null
  return {
    series1: {
      name: '价差比率',
      data: liveWhiteData.value.ratio_data?.map((item: any) => ({ date: item.date, value: item.value })) || [],
      unit: liveWhiteData.value.ratio_unit || ''
    },
    series2: {
      name: '生猪价格',
      data: [],
      unit: '元/公斤'
    }
  }
})
const liveWhiteRightData = computed<DualAxisData | null>(() => {
  if (!liveWhiteData.value) return null
  return {
    series1: {
      name: '毛白价差',
      data: liveWhiteData.value.spread_data?.map((item: any) => ({ date: item.date, value: item.value })) || [],
      unit: liveWhiteData.value.spread_unit || ''
    },
    series2: {
      name: '价差比率',
      data: liveWhiteData.value.ratio_data?.map((item: any) => ({ date: item.date, value: item.value })) || [],
      unit: liveWhiteData.value.ratio_unit || ''
    }
  }
})

// 图表 9：升贴水（03合约）
const premiumChartData = computed(() => {
  const s = premiumData.value?.series?.find((x: any) => x.contract_month === 3)
  if (!s?.data?.length) return null
  const categories = s.data.map((d: any) => d.date)
  const premium = s.data.map((d: any) => d.premium_ratio ?? d.premium)
  return {
    categories,
    series: [{ name: '升贴水比率(%)', data: premium }]
  }
})

const chartItems = [
  { ref: () => chart1Ref.value, title: '全国猪价' },
  { ref: () => chart2Ref.value, title: '标肥价差' },
  { ref: () => chart3Ref.value, title: '猪价&标肥价差' },
  { ref: () => chart4Ref.value, title: '日度屠宰量（农历）' },
  { ref: () => chart5Ref.value, title: '屠宰量&价格' },
  { ref: () => chart6Ref.value, title: '标肥价差（分省区）' },
  { ref: () => chart7Ref.value, title: '毛白价差比率&生猪价格' },
  { ref: () => chart8Ref.value, title: '毛白价差&比率' },
  { ref: () => chart9Ref.value, title: '升贴水' },
  { ref: () => ({ getChartImage: () => chart10Instance?.getDataURL('png') }), title: '供求曲线' }
]

const base64ToUint8Array = (dataUrl: string): Uint8Array => {
  const base64 = dataUrl.split(',')[1] || dataUrl
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

const exportToWord = async () => {
  exportLoading.value = true
  try {
    const children: Paragraph[] = []
    children.push(
      new Paragraph({
        children: [new TextRun({ text: '生猪市场全景监控', bold: true })],
        spacing: { after: 400 }
      })
    )
    for (const item of chartItems) {
      const comp = item.ref()
      const img = comp?.getChartImage?.()
      if (img) {
        children.push(
          new Paragraph({
            children: [new TextRun({ text: item.title, bold: true })],
            spacing: { before: 300, after: 100 }
          }),
          new Paragraph({
            children: [
              new ImageRun({
                type: 'png',
                data: base64ToUint8Array(img),
                transformation: { width: 500, height: 350 }
              })
            ],
            spacing: { after: 300 }
          })
        )
      }
    }
    if (children.length <= 1) {
      ElMessage.warning('暂无图表可导出，请先加载数据')
      return
    }
    const doc = new Document({ sections: [{ children }] })
    const blob = await Packer.toBlob(doc)
    saveAs(blob, `生猪市场全景监控_${new Date().toISOString().slice(0, 10)}.docx`)
    ElMessage.success('已导出到 Word')
  } catch (e) {
    ElMessage.error('导出失败')
    console.error(e)
  } finally {
    exportLoading.value = false
  }
}

const loadPriceDisplay = async () => {
  loadingPriceDisplay.value = true
  try {
    const [priceSpread, slaughterLunar, slaughterTrend] = await Promise.all([
      getPriceAndSpread(),
      getSlaughterLunar(),
      getSlaughterPriceTrendSolar()
    ])
    priceSpreadData.value = priceSpread
    slaughterLunarData.value = slaughterLunar
    slaughterPriceTrendData.value = slaughterTrend
  } catch (e) {
    console.error('加载价格/屠宰数据失败:', e)
  } finally {
    loadingPriceDisplay.value = false
  }
}

const loadFuturesData = async () => {
  futuresLoading.value = true
  try {
    const p = await futuresApi.getPremiumV2({ contract_month: 3, region: '全国均价', view_type: '季节性' })
    premiumData.value = p
  } catch (e) {
    console.error('加载期货数据失败:', e)
  } finally {
    futuresLoading.value = false
  }
}

const loadLiveWhite = async () => {
  loadingLiveWhite.value = true
  try {
    const res = await getLiveWhiteSpreadDualAxis()
    liveWhiteData.value = res
  } catch (e) {
    console.error('加载毛白价差失败:', e)
  } finally {
    loadingLiveWhite.value = false
  }
}

const loadProvinceSpread = async () => {
  loadingProvinceSpread.value = true
  try {
    const { provinces } = await getFatStdSpreadProvinces()
    const year = new Date().getFullYear()
    const topProvinces = provinces.slice(0, 5).map(p => p.province_name)
    const results = await Promise.all(
      topProvinces.map(name =>
        getFatStdSpreadProvinceSeasonality(name, year, year).catch(() => null)
      )
    )
    const allDates = new Set<string>()
    const seriesList: { name: string; data: Array<[string, number | null]> }[] = []
    results.forEach((res, i) => {
      if (!res?.series?.length) return
      const prov = topProvinces[i]
      const firstSeries = res.series[0]
      const points = (firstSeries.data || []).map((p: any) => {
        const dateStr = p.month_day ? `${year}-${p.month_day}` : ''
        if (dateStr) allDates.add(dateStr)
        return [dateStr, p.value ?? null] as [string, number | null]
      })
      seriesList.push({ name: prov, data: points })
    })
    const categories = Array.from(allDates).sort()
    if (categories.length && seriesList.length) {
      provinceSpreadData.value = {
        categories,
        series: seriesList.map(s => ({
          name: s.name,
          data: categories.map(d => {
            const found = s.data.find(([dt]) => dt === d)
            return [d, found != null ? found[1] : null] as [string, number | null]
          })
        }))
      }
    } else {
      provinceSpreadData.value = null
    }
  } catch (e) {
    console.error('加载标肥价差分省区失败:', e)
    provinceSpreadData.value = null
  } finally {
    loadingProvinceSpread.value = false
  }
}

function updateSupplyDemandChart() {
  if (!chart10Ref.value || !supplyDemandData.value?.data?.length) return
  if (!chart10Instance) {
    chart10Instance = echarts.init(chart10Ref.value)
  }
  const data = supplyDemandData.value.data
  chart10Instance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['定点屠宰系数', '猪价系数'], bottom: 10 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: data.map((d: any) => d.month) },
    yAxis: { type: 'value', name: '系数', ...yAxisHideMinMaxLabel },
    series: [
      { name: '定点屠宰系数', type: 'line', smooth: true, data: data.map((d: any) => d.slaughter_coefficient ?? null), itemStyle: { color: '#5470c6' } },
      { name: '猪价系数', type: 'line', smooth: true, data: data.map((d: any) => d.price_coefficient ?? null), itemStyle: { color: '#91cc75' } }
    ]
  })
}

const loadSupplyDemand = async () => {
  loadingSupplyDemand.value = true
  try {
    const res = await getSupplyDemandCurve()
    supplyDemandData.value = res
  } catch (e) {
    console.error('加载供求曲线失败:', e)
  } finally {
    loadingSupplyDemand.value = false
  }
}

watch(supplyDemandData, () => {
  nextTick(() => updateSupplyDemandChart())
}, { deep: true })

onMounted(() => {
  loadPriceDisplay()
  loadFuturesData()
  loadLiveWhite()
  loadProvinceSpread()
  loadSupplyDemand()
})
</script>

<style scoped lang="scss">
.dashboard {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 24px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.header-left {
  .dashboard-title {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    color: #1e293b;
    letter-spacing: -0.02em;
  }
  .dashboard-subtitle {
    display: block;
    margin-top: 4px;
    font-size: 13px;
    color: #64748b;
  }
}

.export-btn {
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  &.chart-card-wide {
    grid-column: 1 / -1;
  }
}

.card-header {
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);

  .card-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: #334155;
  }
}

.card-body {
  padding: 16px 20px;

  :deep(.el-card) {
    box-shadow: none;
    border: none;
    border-radius: 0;
  }
  :deep(.el-card__header) {
    display: none;
  }
  :deep(.el-card__body) {
    padding: 0;
  }
  :deep(.dual-axis-chart-panel),
  :deep(.seasonality-chart-panel),
  :deep(.chart-panel) {
    margin-bottom: 0;
  }
  :deep(.dual-axis-chart-panel .el-card__body > div),
  :deep(.seasonality-chart-panel .chart-content > div:first-child),
  :deep(.chart-panel .el-card__body > div) {
    height: 320px !important;
    min-height: 280px;
  }
  :deep(.dashboard-line-chart),
  :deep(.dashboard-bar-chart) {
    min-height: 280px;
  }
  .supply-demand-chart {
    width: 100%;
    min-height: 280px;
  }
}

@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
