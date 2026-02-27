<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="dashboard-title">生猪重点数据汇总</h1>
        <span class="dashboard-subtitle">核心指标一览</span>
      </div>
      <el-button type="primary" :loading="exportLoading" @click="exportToImage" class="export-btn">
        <el-icon><Download /></el-icon>
        导出图片
      </el-button>
    </header>

    <div ref="exportTargetRef" class="charts-container">
      <!-- 第一行：A1区域 全国猪价、标肥价差 【季节性图】 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">全国猪价</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartPriceRef"
              :data="nationalPriceSeasonalityData"
              :loading="loadingA1"
              bare
              hide-title
            />
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">标肥价差</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartSpreadRef"
              :data="fatStdSpreadSeasonalityData"
              :loading="loadingA1"
              bare
              hide-title
            />
          </div>
        </div>
      </div>

      <!-- 第二行：A3+A2区域 日度屠宰量(农历)、出栏均重 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">日度屠宰量（农历）</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartSlaughterRef"
              :data="slaughterLunarData"
              :loading="loadingA3"
              :lunar-alignment="true"
              bare
              hide-title
            />
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">出栏均重</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartWeightRef"
              :data="outWeightData"
              :loading="loadingA2"
              bare
              hide-title
            />
          </div>
        </div>
      </div>

      <!-- 第三行：A8区域 仔猪价格、淘汰母猪折扣率 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">仔猪价格</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartPigletRef"
              :data="pigletPriceData"
              :loading="loadingA8"
              bare
              hide-title
            />
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">淘汰母猪折扣率</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartCullDiscountRef"
              :data="cullDiscountData"
              :loading="loadingA8"
              bare
              hide-title
            />
          </div>
        </div>
      </div>

      <!-- 第四行：A8区域 屠宰利润、自养利润 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">屠宰利润</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartSlaughterProfitRef"
              :data="slaughterProfitData"
              :loading="loadingA8"
              bare
              hide-title
            />
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">自养利润</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartSelfProfitRef"
              :data="selfProfitData"
              :loading="loadingA8"
              bare
              hide-title
            />
          </div>
        </div>
      </div>

      <!-- 第五行：A5区域 区域价差:广东-贵州、区域价差:广东-河南 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">区域价差：广东-贵州</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartRegionGZRef"
              :data="regionSpreadGZData"
              :loading="loadingA5"
              bare
              hide-title
            />
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header"><h3 class="card-title">区域价差：广东-河南</h3></div>
          <div class="card-body">
            <SeasonalityChart
              ref="chartRegionHNRef"
              :data="regionSpreadHNData"
              :loading="loadingA5"
              bare
              hide-title
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import html2canvas from 'html2canvas'
import { saveAs } from 'file-saver'
import SeasonalityChart from '../components/SeasonalityChart.vue'
import {
  getNationalPriceSeasonality,
  getFatStdSpreadSeasonality,
  getSlaughterLunar,
  getIndustryChainSeasonality,
  getRegionSpreadSeasonality,
  getProvinceIndicatorsSeasonality
} from '../api/price-display'
import type { SeasonalityData } from '../components/SeasonalityChart.vue'
import type { SeasonalityResponse } from '../api/price-display'

const exportTargetRef = ref<HTMLElement | null>(null)
const exportLoading = ref(false)

const chartPriceRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartSpreadRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartSlaughterRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartWeightRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartPigletRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartCullDiscountRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartSlaughterProfitRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartSelfProfitRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartRegionGZRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)
const chartRegionHNRef = ref<InstanceType<typeof SeasonalityChart> | null>(null)

const loadingA1 = ref(false)
const loadingA3 = ref(false)
const loadingA2 = ref(false)
const loadingA8 = ref(false)
const loadingA5 = ref(false)

const nationalPriceSeasonalityData = ref<SeasonalityData | null>(null)
const fatStdSpreadSeasonalityData = ref<SeasonalityData | null>(null)
const slaughterLunarData = ref<SeasonalityData | null>(null)
const outWeightData = ref<SeasonalityData | null>(null)
const pigletPriceData = ref<SeasonalityData | null>(null)
const cullDiscountData = ref<SeasonalityData | null>(null)
const slaughterProfitData = ref<SeasonalityData | null>(null)
const selfProfitData = ref<SeasonalityData | null>(null)
const regionSpreadGZData = ref<SeasonalityData | null>(null)
const regionSpreadHNData = ref<SeasonalityData | null>(null)

/** 周度数据（week 1-52，后端按周序返回）→ SeasonalityData */
function toSeasonalityDataWeek(res: SeasonalityResponse | null): SeasonalityData | null {
  if (!res?.series?.length) return null
  const xValues: number[] = []
  for (let i = 1; i <= 52; i++) xValues.push(i)
  const series = res.series.map((s: any) => {
    const arr = s.data || []
    const values = xValues.map((_, i) => (arr[i]?.value != null ? arr[i].value : null))
    return { year: s.year, values }
  })
  return { x_values: xValues, series, meta: { unit: res.unit || '', freq: 'W', metric_name: res.metric_name || '' } }
}

/** 日度数据（month_day 如 01-15）→ SeasonalityData */
function toSeasonalityDataMonthDay(res: SeasonalityResponse | null): SeasonalityData | null {
  if (!res?.series?.length) return null
  const allMonthDays = new Set<string>()
  res.series.forEach((s: any) => {
    (s.data || []).forEach((d: any) => { if (d.month_day) allMonthDays.add(d.month_day) })
  })
  const x_values = Array.from(allMonthDays).sort((a, b) => {
    const [am, ad] = a.split('-').map(Number)
    const [bm, bd] = b.split('-').map(Number)
    return am !== bm ? am - bm : ad - bd
  })
  const series = res.series.map((s: any) => {
    const valueMap = new Map<string, number | null>()
    ;(s.data || []).forEach((d: any) => { if (d.month_day) valueMap.set(d.month_day, d.value ?? null) })
    return { year: s.year, values: x_values.map(md => valueMap.get(md) ?? null) }
  })
  return { x_values, series, meta: { unit: res.unit || '', freq: 'D', metric_name: res.metric_name || '' } }
}

/** 日度屠宰量（农历，lunar_day_index 或 month_day）→ SeasonalityData */
function toSeasonalityDataLunar(res: SeasonalityResponse | null): SeasonalityData | null {
  if (!res?.series?.length) return null
  const allKeys = new Set<string>()
  res.series.forEach((s: any) => {
    (s.data || []).forEach((d: any) => {
      const k = d.month_day ?? (d.lunar_day_index != null ? String(d.lunar_day_index) : '')
      if (k) allKeys.add(k)
    })
  })
  const x_values = Array.from(allKeys).sort((a, b) => (parseInt(a, 10) || 0) - (parseInt(b, 10) || 0))
  const series = res.series.map((s: any) => {
    const valueMap = new Map<string, number | null>()
    ;(s.data || []).forEach((d: any) => {
      const k = d.month_day ?? (d.lunar_day_index != null ? String(d.lunar_day_index) : '')
      if (k) valueMap.set(k, d.value ?? null)
    })
    return { year: s.year, values: x_values.map(k => valueMap.get(k) ?? null) }
  })
  return {
    x_values,
    series,
    meta: { unit: res.unit || '头', freq: 'D', metric_name: res.metric_name || '日度屠宰量' }
  }
}

function toSeasonalityDataRegion(res: SeasonalityResponse | null): SeasonalityData | null {
  if (!res?.series?.length) return null
  const allMonthDays = new Set<string>()
  res.series.forEach((s: any) => {
    (s.data || []).forEach((d: any) => { if (d.month_day) allMonthDays.add(d.month_day) })
  })
  const x_values = Array.from(allMonthDays).sort((a, b) => {
    const [am, ad] = a.split('-').map(Number)
    const [bm, bd] = b.split('-').map(Number)
    return am !== bm ? am - bm : ad - bd
  })
  const series = res.series.map((s: any) => {
    const valueMap = new Map<string, number | null>()
    ;(s.data || []).forEach((d: any) => { if (d.month_day) valueMap.set(d.month_day, d.value ?? null) })
    return { year: s.year, values: x_values.map(md => valueMap.get(md) ?? null) }
  })
  return { x_values, series, meta: { unit: res.unit || '元/公斤', freq: 'D', metric_name: res.metric_name || '' } }
}

const loadA1 = async () => {
  loadingA1.value = true
  try {
    const year = new Date().getFullYear()
    const [priceRes, spreadRes] = await Promise.all([
      getNationalPriceSeasonality(year - 4, year),
      getFatStdSpreadSeasonality(year - 4, year)
    ])
    nationalPriceSeasonalityData.value = toSeasonalityDataMonthDay(priceRes as any)
    fatStdSpreadSeasonalityData.value = toSeasonalityDataMonthDay(spreadRes as any)
  } catch (e) {
    console.error('加载A1失败:', e)
  } finally {
    loadingA1.value = false
  }
}

const loadA3 = async () => {
  loadingA3.value = true
  try {
    const year = new Date().getFullYear()
    const res = await getSlaughterLunar(year - 4, year)
    slaughterLunarData.value = toSeasonalityDataLunar(res as any)
  } catch (e) {
    console.error('加载A3失败:', e)
  } finally {
    loadingA3.value = false
  }
}

const loadA2 = async () => {
  loadingA2.value = true
  try {
    const year = new Date().getFullYear()
    const res = await getProvinceIndicatorsSeasonality('广东', year - 4, year)
    const ind = res?.indicators?.['周度 出栏均重']
    outWeightData.value = toSeasonalityDataWeek(ind as any)
  } catch (e) {
    console.error('加载A2失败:', e)
  } finally {
    loadingA2.value = false
  }
}

const loadA8 = async () => {
  loadingA8.value = true
  try {
    const [piglet, cull, slaughter, self] = await Promise.all([
      getIndustryChainSeasonality('仔猪价格'),
      getIndustryChainSeasonality('淘汰母猪折扣率'),
      getIndustryChainSeasonality('屠宰利润'),
      getIndustryChainSeasonality('自养利润')
    ])
    pigletPriceData.value = toSeasonalityDataWeek(piglet as any)
    cullDiscountData.value = toSeasonalityDataWeek(cull as any)
    slaughterProfitData.value = toSeasonalityDataWeek(slaughter as any)
    selfProfitData.value = toSeasonalityDataWeek(self as any)
  } catch (e) {
    console.error('加载A8失败:', e)
  } finally {
    loadingA8.value = false
  }
}

const loadA5 = async () => {
  loadingA5.value = true
  try {
    const year = new Date().getFullYear()
    const [gz, hn] = await Promise.all([
      getRegionSpreadSeasonality('广东-贵州', year - 4, year),
      getRegionSpreadSeasonality('广东-河南', year - 4, year)
    ])
    regionSpreadGZData.value = toSeasonalityDataRegion(gz as any)
    regionSpreadHNData.value = toSeasonalityDataRegion(hn as any)
  } catch (e) {
    console.error('加载A5失败:', e)
  } finally {
    loadingA5.value = false
  }
}

const exportToImage = async () => {
  if (!exportTargetRef.value) {
    ElMessage.warning('暂无内容可导出')
    return
  }
  exportLoading.value = true
  try {
    const canvas = await html2canvas(exportTargetRef.value, {
      useCORS: true,
      allowTaint: true,
      scale: 2,
      backgroundColor: '#f8fafc',
      logging: false
    })
    canvas.toBlob((blob) => {
      if (blob) {
        saveAs(blob, `生猪重点数据汇总_${new Date().toISOString().slice(0, 10)}.png`)
        ElMessage.success('已导出图片')
      } else {
        ElMessage.error('导出失败')
      }
    }, 'image/png')
  } catch (e) {
    console.error(e)
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

onMounted(() => {
  loadA1()
  loadA3()
  loadA2()
  loadA8()
  loadA5()
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

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  overflow: hidden;

  .card-header {
    padding: 14px 20px;
    border-bottom: 1px solid #f1f5f9;
    .card-title {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #334155;
    }
  }

  .card-body {
    padding: 16px 20px;
    :deep(.seasonality-chart-panel .el-card__body > div),
    :deep(.seasonality-chart-bare .chart-content > div:first-child) {
      height: 320px !important;
      min-height: 280px;
    }
  }
}

@media (max-width: 1200px) {
  .chart-row {
    grid-template-columns: 1fr;
  }
}
</style>
