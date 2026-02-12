<template>
  <div class="region-premium-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>重点区域升贴水</span>
        </div>
      </template>

      <!-- 筛选区域 -->
      <div class="filters">
        <div class="filter-group">
          <span class="filter-label">时间筛选：</span>
          <el-radio-group v-model="viewType" @change="loadData" size="small">
            <el-radio-button label="季节性">季节性</el-radio-button>
            <el-radio-button label="全部日期">全部日期</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-group">
          <span class="filter-label">格式筛选：</span>
          <el-radio-group v-model="formatType" @change="loadData" size="small">
            <el-radio-button label="全部格式">全部格式</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-group">
          <span class="filter-label">区域筛选：</span>
          <el-radio-group v-model="selectedRegion" @change="loadData" size="small">
            <el-radio-button label="全国均价">全国均价</el-radio-button>
            <el-radio-button label="贵州">贵州</el-radio-button>
            <el-radio-button label="四川">四川</el-radio-button>
            <el-radio-button label="云南">云南</el-radio-button>
            <el-radio-button label="广东">广东</el-radio-button>
            <el-radio-button label="广西">广西</el-radio-button>
            <el-radio-button label="江苏">江苏</el-radio-button>
            <el-radio-button label="内蒙">内蒙</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 省区升贴水注释（经区域升贴水调整） -->
      <div v-if="regionPremiums && Object.keys(regionPremiums).length > 0" class="region-premiums">
        <div class="region-premiums-title">{{ selectedRegion }}区域升贴水（经区域升贴水调整）：</div>
        <div class="region-premiums-content">
          <span v-for="(value, region) in regionPremiums" :key="region" class="region-item">
            {{ region }}：{{ value }}
          </span>
        </div>
      </div>

      <!-- 图表区域 -->
      <div v-loading="loading">
        <div v-if="errorMessage" style="padding: 20px; color: red;">
          <el-alert :title="errorMessage" type="error" :closable="false" />
        </div>
        <div v-else-if="premiumData.series.length === 0" style="padding: 20px;">
          <el-empty description="暂无数据">
            <el-button type="primary" @click="loadData">重新加载</el-button>
          </el-empty>
        </div>
        <div v-else>
          <div v-if="formatType === '全部格式'" class="charts-container">
            <div class="chart-row">
              <div class="chart-item">
                <h3>全部日期</h3>
                <div
                  v-for="series in premiumDataAllDates.series"
                  :key="`all-${series.contract_month}`"
                  class="chart-wrapper"
                >
                  <div
                    :ref="el => setChartRef(`all-${series.contract_month}`, el)"
                    class="chart"
                  ></div>
                </div>
              </div>
              <div class="chart-item">
                <h3>季节性</h3>
                <div
                  v-for="series in premiumDataSeasonal.series"
                  :key="`seasonal-${series.contract_month}`"
                  class="chart-wrapper"
                >
                  <div
                    :ref="el => setChartRef(`seasonal-${series.contract_month}`, el)"
                    class="chart"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          <div v-else>
            <div
              v-for="series in premiumData.series"
              :key="series.contract_month"
              class="chart-wrapper"
            >
              <h3>{{ series.contract_name }}合约升贴水</h3>
              <div
                :ref="el => setChartRef(`${viewType}-${series.contract_month}`, el)"
                class="chart"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { futuresApi, type PremiumResponseV2 } from '@/api/futures'
import { axisLabelDecimalFormatter, axisLabelPercentFormatter } from '@/utils/chart-style'

const loading = ref(false)
const viewType = ref<'季节性' | '全部日期'>('全部日期')
const formatType = ref('全部格式')
const selectedRegion = ref('贵州')
const premiumData = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const premiumDataAllDates = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const premiumDataSeasonal = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const regionPremiums = ref<Record<string, number>>({})
const errorMessage = ref<string>('')
const chartInstances = new Map<string, echarts.ECharts>()
const chartRefs = new Map<string, HTMLDivElement>()

const setChartRef = (key: string, el: HTMLDivElement | null) => {
  if (el) chartRefs.set(key, el)
  else chartRefs.delete(key)
}

const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    if (formatType.value === '全部格式') {
      const [allDatesResult, seasonalResult] = await Promise.all([
        futuresApi.getPremiumV2({ region: selectedRegion.value, view_type: '全部日期', format_type: formatType.value }),
        futuresApi.getPremiumV2({ region: selectedRegion.value, view_type: '季节性', format_type: formatType.value })
      ])
      premiumDataAllDates.value = allDatesResult
      premiumDataSeasonal.value = seasonalResult
      premiumData.value = allDatesResult
      regionPremiums.value = allDatesResult.region_premiums || {}
      if (allDatesResult.series.length === 0 && seasonalResult.series.length === 0) {
        errorMessage.value = '未找到升贴水数据'
      } else {
        await nextTick()
        renderCharts()
      }
    } else {
      const result = await futuresApi.getPremiumV2({
        region: selectedRegion.value,
        view_type: viewType.value,
        format_type: formatType.value
      })
      premiumData.value = result
      regionPremiums.value = result.region_premiums || {}
      if (result.series.length === 0) {
        errorMessage.value = '未找到升贴水数据'
      } else {
        await nextTick()
        renderCharts()
      }
    }
  } catch (error: any) {
    console.error('加载区域升贴水数据失败:', error)
    errorMessage.value = error?.response?.data?.detail || error?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  if (formatType.value === '全部格式') {
    premiumDataAllDates.value.series.forEach(s => {
      const el = chartRefs.get(`all-${s.contract_month}`)
      if (el) renderAllDatesChart(el, s)
    })
    premiumDataSeasonal.value.series.forEach(s => {
      const el = chartRefs.get(`seasonal-${s.contract_month}`)
      if (el) renderSeasonalChart(el, s)
    })
  } else {
    premiumData.value.series.forEach(s => {
      const el = chartRefs.get(`${viewType.value}-${s.contract_month}`)
      if (el) {
        if (viewType.value === '季节性') renderSeasonalChart(el, s)
        else renderAllDatesChart(el, s)
      }
    })
  }
}

const renderAllDatesChart = (el: HTMLDivElement, series: PremiumResponseV2['series'][0]) => {
  const key = `all-${series.contract_month}`
  chartInstances.get(key)?.dispose()
  const chart = echarts.init(el)
  chartInstances.set(key, chart)

  const yearMap = new Map<number, Array<typeof series.data[0]>>()
  series.data.forEach(p => {
    const y = p.year || new Date(p.date).getFullYear()
    if (!yearMap.has(y)) yearMap.set(y, [])
    yearMap.get(y)!.push(p)
  })
  const years = Array.from(yearMap.keys()).sort()
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']

  const seriesData: any[] = [
    {
      name: '现货价格',
      type: 'line',
      data: series.data.map(d => [d.date, d.spot_price]),
      yAxisIndex: 0,
      lineStyle: { color: '#999', type: 'dashed' },
      symbol: 'none',
      connectNulls: true
    }
  ]
  years.forEach((year, i) => {
    const yearData = yearMap.get(year)!
    const color = colors[i % colors.length]
    seriesData.push(
      {
        name: `${year}年合约价格`,
        type: 'line',
        data: yearData.map(d => [d.date, d.futures_settle]),
        yAxisIndex: 0,
        lineStyle: { color },
        symbol: 'circle',
        symbolSize: 4,
        smooth: true,
        connectNulls: true
      },
      {
        name: `${year}年升贴水`,
        type: 'line',
        data: yearData.map(d => [d.date, d.premium]),
        yAxisIndex: 0,
        lineStyle: { color, type: 'dashed' },
        symbol: 'circle',
        symbolSize: 4,
        smooth: true,
        connectNulls: true
      }
    )
  })

  chart.setOption({
    title: { text: `${series.contract_name}合约升贴水`, left: 'left', top: 8 },
    legend: { data: seriesData.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.value != null) r += `<div><span style="display:inline-block;width:10px;height:10px;background:${x.color};margin-right:5px"></span>${x.seriesName}: <strong>${Number(x.value).toFixed(2)}</strong> 元/公斤</div>`
        })
        return r
      }
    },
    xAxis: { type: 'time', boundaryGap: false },
    yAxis: [{ type: 'value', name: '价格', position: 'left', axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) } }],
    series: seriesData,
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }]
  })
  window.addEventListener('resize', () => chart.resize())
}

const renderSeasonalChart = (el: HTMLDivElement, series: PremiumResponseV2['series'][0]) => {
  const key = `seasonal-${series.contract_month}`
  chartInstances.get(key)?.dispose()
  const chart = echarts.init(el)

  const yearMap = new Map<number, Array<typeof series.data[0]>>()
  series.data.forEach(p => {
    const y = p.year || new Date(p.date).getFullYear()
    if (!yearMap.has(y)) yearMap.set(y, [])
    yearMap.get(y)!.push(p)
  })
  const years = Array.from(yearMap.keys()).sort()
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']

  const dateSet = new Set<string>()
  series.data.forEach(d => {
    const date = new Date(d.date)
    const m = date.getMonth() + 1
    const day = date.getDate()
    if ((m === 4 && day >= 1) || (m > 4 && m <= 12) || (m >= 1 && m <= 2 && day <= 28)) {
      dateSet.add(`${m.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`)
    }
  })
  const categories = Array.from(dateSet).sort((a, b) => {
    const [am, ad] = a.split('-').map(Number)
    const [bm, bd] = b.split('-').map(Number)
    const ao = am >= 4 ? am : am + 12
    const bo = bm >= 4 ? bm : bm + 12
    if (ao !== bo) return ao - bo
    return ad - bd
  })

  const seriesData: any[] = years.map((year, i) => {
    const yearData = yearMap.get(year)!
    const dataMap = new Map<string, number | null>()
    yearData.forEach(d => {
      const date = new Date(d.date)
      dataMap.set(`${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`, d.premium_ratio)
    })
    return {
      name: `${year}年`,
      type: 'line',
      data: categories.map(c => dataMap.get(c) ?? null),
      lineStyle: { color: colors[i % colors.length] },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    }
  })

  chart.setOption({
    title: { text: `${series.contract_name}合约升贴水比率`, left: 'left', top: 8 },
    legend: { data: seriesData.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.value != null) r += `<div><span style="display:inline-block;width:10px;height:10px;background:${x.color};margin-right:5px"></span>${x.seriesName}: <strong>${Number(x.value).toFixed(2)}%</strong></div>`
        })
        return r
      }
    },
    xAxis: { type: 'category', data: categories, boundaryGap: false, axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '升贴水比率（%）', axisLabel: { formatter: (v: number) => axisLabelPercentFormatter(v) } },
    series: seriesData,
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }]
  })
  chartInstances.set(key, chart)
  window.addEventListener('resize', () => chart.resize())
}

watch([() => premiumData.value.series, () => premiumDataAllDates.value.series, () => premiumDataSeasonal.value.series], () => nextTick(() => renderCharts()), { deep: true })

onMounted(() => loadData())

onBeforeUnmount(() => {
  chartInstances.forEach(c => c.dispose())
  chartInstances.clear()
  chartRefs.clear()
})
</script>

<style scoped lang="scss">
.region-premium-page {
  padding: 4px;

  :deep(.el-card__body) {
    padding: 4px 6px;
  }

  .filters {
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
    gap: 15px;

    .filter-group {
      display: flex;
      align-items: center;
      gap: 10px;

      .filter-label {
        font-weight: 500;
        min-width: 80px;
      }
    }
  }

  .region-premiums {
    margin-bottom: 12px;
    padding: 10px;
    background-color: #f5f7fa;
    border-radius: 4px;

    .region-premiums-title {
      font-weight: 500;
      margin-bottom: 5px;
    }

    .region-premiums-content {
      display: flex;
      flex-wrap: wrap;
      gap: 15px;

      .region-item {
        font-size: 14px;
      }
    }
  }

  .charts-container .chart-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;

    .chart-item {
      h3 {
        margin-bottom: 6px;
        font-size: 16px;
        font-weight: 600;
        text-align: left;
      }

      .chart-wrapper {
        margin-bottom: 4px;

        .chart {
          width: 100%;
          height: 400px;
        }
      }
    }
  }

  .chart-wrapper {
    margin-bottom: 4px;

    h3 {
      margin-bottom: 10px;
      font-size: 16px;
      font-weight: 600;
    }

    .chart {
      width: 100%;
      height: 400px;
    }
  }
}
</style>
