<template>
  <div class="calendar-spread-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>月间价差数据</span>
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
      </div>

      <!-- 图表区域 -->
      <div v-loading="loading">
        <div v-if="errorMessage" style="padding: 20px; color: red;">
          <el-alert :title="errorMessage" type="error" :closable="false" />
        </div>
        <div v-else-if="spreadData.series.length === 0" style="padding: 20px;">
          <el-empty description="暂无数据">
            <el-button type="primary" @click="loadData">重新加载</el-button>
          </el-empty>
        </div>
        <div v-else>
          <!-- 全部格式：左侧全部日期，右侧季节性 -->
          <div v-if="formatType === '全部格式'" class="charts-container">
            <div class="chart-row">
              <div class="chart-item">
                <h3>全部日期</h3>
                <div
                  v-for="series in spreadData.series"
                  :key="`all-${series.spread_name}`"
                  class="chart-wrapper"
                >
                  <div
                    :ref="el => setChartRef(`all-${series.spread_name}`, el)"
                    class="chart"
                  ></div>
                </div>
              </div>
              <div class="chart-item">
                <h3>季节性</h3>
                <div
                  v-for="series in spreadData.series"
                  :key="`seasonal-${series.spread_name}`"
                  class="chart-wrapper"
                >
                  <div
                    :ref="el => setChartRef(`seasonal-${series.spread_name}`, el)"
                    class="chart"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          <!-- 非全部格式：只显示当前视图 -->
          <div v-else>
            <div
              v-for="series in spreadData.series"
              :key="series.spread_name"
              class="chart-wrapper"
            >
              <h3>{{ getChartTitle(series.spread_name) }}合约价差</h3>
              <div
                :ref="el => setChartRef(`${viewType}-${series.spread_name}`, el)"
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
import { futuresApi, type CalendarSpreadResponse } from '@/api/futures'
import { axisLabelDecimalFormatter } from '@/utils/chart-style'

const loading = ref(false)
const viewType = ref<'季节性' | '全部日期'>('全部日期')
const formatType = ref('全部格式')
const spreadData = ref<CalendarSpreadResponse>({ series: [], update_time: null })
const errorMessage = ref<string>('')
const chartInstances = new Map<string, echarts.ECharts>()
const chartRefs = new Map<string, HTMLDivElement>()

// 03-05 -> 3-5
const getChartTitle = (spreadName: string) => {
  return spreadName.replace(/^0(\d)-0(\d)价差$/, '$1-$2').replace(/^0(\d)-(\d+)价差$/, '$1-$2').replace(/^(\d+)-0(\d)价差$/, '$1-$2').replace(/价差$/, '') || spreadName.replace('价差', '')
}

const setChartRef = (key: string, el: HTMLDivElement | null) => {
  if (el) chartRefs.set(key, el)
  else chartRefs.delete(key)
}

const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await futuresApi.getCalendarSpread({})
    spreadData.value = result
    await nextTick()
    renderCharts()
  } catch (error: any) {
    console.error('加载月间价差数据失败:', error)
    errorMessage.value = error?.response?.data?.detail || error?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 获取季节性年份（如 03-05：6月到次年2月 = 2024/2025；11-01：2月到10月 = 2025）
const getSeasonalYear = (dateStr: string, nearMonth: number, farMonth: number): string => {
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const startMonth = farMonth >= 12 ? 1 : farMonth + 1
  const endMonth = nearMonth <= 1 ? 12 : nearMonth - 1
  // 跨年（如03-05：6月-2月）：6-12月=year/year+1，1-2月=year-1/year
  if (startMonth > endMonth) {
    if (month >= startMonth) return `${year}/${year + 1}`
    if (month <= endMonth) return `${year - 1}/${year}`
  }
  // 不跨年（如11-01：2月-10月）：统一用 year
  return `${year}`
}

const renderCharts = () => {
  if (formatType.value === '全部格式') {
    spreadData.value.series.forEach(s => {
      const allEl = chartRefs.get(`all-${s.spread_name}`)
      if (allEl) renderAllDatesChart(allEl, s)
    })
    spreadData.value.series.forEach(s => {
      const seaEl = chartRefs.get(`seasonal-${s.spread_name}`)
      if (seaEl) renderSeasonalChart(seaEl, s)
    })
  } else {
    spreadData.value.series.forEach(s => {
      const el = chartRefs.get(`${viewType.value}-${s.spread_name}`)
      if (el) {
        if (viewType.value === '季节性') renderSeasonalChart(el, s)
        else renderAllDatesChart(el, s)
      }
    })
  }
}

const renderAllDatesChart = (el: HTMLDivElement, series: CalendarSpreadResponse['series'][0]) => {
  const key = `all-${series.spread_name}`
  chartInstances.get(key)?.dispose()
  const chart = echarts.init(el)
  chartInstances.set(key, chart)

  const yearMap = new Map<number, typeof series.data>()
  series.data.forEach(d => {
    const y = new Date(d.date).getFullYear()
    if (!yearMap.has(y)) yearMap.set(y, [])
    yearMap.get(y)!.push(d)
  })
  const years = Array.from(yearMap.keys()).sort()
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']

  const seriesOpt: any[] = years.map((year, i) => ({
    name: `${year}年`,
    type: 'line',
    data: yearMap.get(year)!.map(d => [d.date, d.spread]),
    lineStyle: { color: colors[i % colors.length] },
    symbol: 'circle',
    symbolSize: 4,
    smooth: true,
    connectNulls: true
  }))

  chart.setOption({
    title: { text: `${getChartTitle(series.spread_name)}合约价差`, left: 'left', top: 8 },
    legend: { data: seriesOpt.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.value != null) r += `<div>${x.seriesName}: <strong>${Number(x.value).toFixed(2)}</strong> 元/公斤</div>`
        })
        return r
      }
    },
    xAxis: { type: 'time', boundaryGap: false },
    yAxis: { type: 'value', name: '价差(元/公斤)', axisLabel: { formatter: axisLabelDecimalFormatter } },
    series: seriesOpt,
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }]
  })
  window.addEventListener('resize', () => chart.resize())
}

const renderSeasonalChart = (el: HTMLDivElement, series: CalendarSpreadResponse['series'][0]) => {
  const key = `seasonal-${series.spread_name}`
  chartInstances.get(key)?.dispose()
  const chart = echarts.init(el)

  const nearMonth = series.near_month
  const farMonth = series.far_month
  const seasonalMap = new Map<string, Map<string, number | null>>()

  series.data.forEach(d => {
    const sy = getSeasonalYear(d.date, nearMonth, farMonth)
    if (!seasonalMap.has(sy)) seasonalMap.set(sy, new Map())
    const date = new Date(d.date)
    const mmdd = `${(date.getMonth() + 1).toString().padStart(2, '0')}${date.getDate().toString().padStart(2, '0')}`
    seasonalMap.get(sy)!.set(mmdd, d.spread)
  })

  const mmddSet = new Set<string>()
  series.data.forEach(d => {
    const date = new Date(d.date)
    mmddSet.add(`${(date.getMonth() + 1).toString().padStart(2, '0')}${date.getDate().toString().padStart(2, '0')}`)
  })
  const categories = Array.from(mmddSet).sort((a, b) => {
    const ma = parseInt(a.slice(0, 2), 10)
    const mb = parseInt(b.slice(0, 2), 10)
    const da = parseInt(a.slice(2), 10)
    const db = parseInt(b.slice(2), 10)
    if (ma !== mb) return ma - mb
    return da - db
  })

  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']
  const seriesOpt: any[] = Array.from(seasonalMap.keys()).sort().map((sy, i) => ({
    name: sy,
    type: 'line',
    data: categories.map(c => seasonalMap.get(sy)!.get(c) ?? null),
    lineStyle: { color: colors[i % colors.length] },
    symbol: 'circle',
    symbolSize: 4,
    smooth: true,
    connectNulls: true  // 跨空值连线，避免断连
  }))

  chart.setOption({
    title: { text: `${getChartTitle(series.spread_name)}合约价差`, left: 'left', top: 8 },
    legend: { data: seriesOpt.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '18%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.value != null) r += `<div>${x.seriesName}: <strong>${Number(x.value).toFixed(2)}</strong> 元/公斤</div>`
        })
        return r
      }
    },
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: false,
      axisLabel: { rotate: 45, formatter: (v: string) => v.length >= 4 ? `${v.slice(0, 2)}/${v.slice(2)}` : v }
    },
    yAxis: { type: 'value', name: '价差(元/公斤)', axisLabel: { formatter: axisLabelDecimalFormatter } },
    series: seriesOpt,
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }]
  })
  chartInstances.set(key, chart)
  window.addEventListener('resize', () => chart.resize())
}

watch(() => spreadData.value.series, () => nextTick(() => renderCharts()), { deep: true })

onMounted(() => loadData())

onBeforeUnmount(() => {
  chartInstances.forEach(c => c.dispose())
  chartInstances.clear()
  chartRefs.clear()
})
</script>

<style scoped lang="scss">
.calendar-spread-page {
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
