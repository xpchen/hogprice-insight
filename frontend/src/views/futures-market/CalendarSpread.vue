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
import { axisLabelDecimalFormatter, yAxisHideMinMaxLabel } from '@/utils/chart-style'

const loading = ref(false)
const viewType = ref<'季节性' | '全部日期'>('全部日期')
const formatType = ref('全部格式')
const spreadData = ref<CalendarSpreadResponse>({ series: [], update_time: null })
const errorMessage = ref<string>('')
const chartInstances = new Map<string, echarts.ECharts>()
const chartRefs = new Map<string, HTMLDivElement>()

// 保留两位月份显示，如 03-05、11-01（不要 11-1）
const getChartTitle = (spreadName: string) => {
  return spreadName.replace(/价差$/, '')
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

  const nearMonth = series.near_month
  const farMonth = series.far_month
  // 按季节性周期分组（与季节性图一致），每个周期一条连续线、一个颜色
  const seasonalMap = new Map<string, typeof series.data>()
  series.data.forEach(d => {
    const sy = getSeasonalYear(d.date, nearMonth, farMonth)
    if (!seasonalMap.has(sy)) seasonalMap.set(sy, [])
    seasonalMap.get(sy)!.push(d)
  })
  const seasonalYears = Array.from(seasonalMap.keys()).sort()
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']
  const getColorForSeasonalYear = (sy: string) => {
    const parts = sy.split('/')
    const year = parts.length >= 2 ? parseInt(parts[1], 10) : parseInt(parts[0], 10)
    return colors[Math.max(0, (year - 2019) % colors.length)]
  }

  // 每个周期的数据按日期排序，直接绘制（周期间自然断开）
  const spreadSeriesList: any[] = seasonalYears.map((sy) => {
    const arr = seasonalMap.get(sy)!.slice().sort((a, b) => a.date.localeCompare(b.date))
    const color = getColorForSeasonalYear(sy)
    return {
      name: sy,
      type: 'line',
      yAxisIndex: 0,
      data: arr.map(d => [d.date, d.spread]),
      lineStyle: { color },
      itemStyle: { color },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: false
    }
  })
  // 用结算价数据驱动右侧 Y 轴刻度，系列不显示、不参与图例和 tooltip
  const settleData = series.data.map(d => [d.date, d.near_contract_settle ?? d.far_contract_settle ?? null])
  const hasSettle = settleData.some(([, v]) => v != null && Number.isFinite(v))
  const seriesOpt: any[] = [
    ...spreadSeriesList,
    ...(hasSettle ? [{
      name: '__结算价轴__',
      type: 'line' as const,
      yAxisIndex: 1,
      data: settleData,
      lineStyle: { opacity: 0 },
      symbol: 'none',
      symbolSize: 0,
      connectNulls: true,
      legendHoverLink: false
    }] : [])
  ]

  chart.setOption({
    title: { text: `${getChartTitle(series.spread_name)}合约价差`, left: 'left', top: 8 },
    legend: { data: spreadSeriesList.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.seriesName === '__结算价轴__') return
          const v = x.value
          if (v != null && v !== '' && Number.isFinite(Number(v))) r += `<div>${x.seriesName}: <strong>${Number(v).toFixed(2)}</strong> 元/公斤</div>`
        })
        return r
      }
    },
    xAxis: { type: 'time', boundaryGap: false },
    yAxis: [
      { type: 'value', name: '价差(元/公斤)', position: 'left', ...yAxisHideMinMaxLabel, axisLabel: { formatter: axisLabelDecimalFormatter } },
      { type: 'value', name: '结算价(元/公斤)', position: 'right', ...yAxisHideMinMaxLabel, axisLabel: { formatter: axisLabelDecimalFormatter } }
    ],
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

  // X-Y价差时间轴：(Y+1)月1日～(X-1)月最后日。按价差计算起止月与是否跨年，用于 X 轴排序
  const startMonth = farMonth >= 12 ? 1 : farMonth + 1
  const endMonth = nearMonth <= 1 ? 12 : nearMonth - 1
  const crossYear = startMonth > endMonth
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
    const aOrder = crossYear ? (ma >= startMonth ? ma : ma + 12) : ma
    const bOrder = crossYear ? (mb >= startMonth ? mb : mb + 12) : mb
    if (aOrder !== bOrder) return aOrder - bOrder
    return da - db
  })

  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3']
  const getColorForSeasonalYear = (sy: string) => {
    const parts = sy.split('/')
    const year = parts.length >= 2 ? parseInt(parts[1], 10) : parseInt(parts[0], 10)
    return colors[Math.max(0, (year - 2019) % colors.length)]
  }
  const seasonalYears = Array.from(seasonalMap.keys()).sort()
  const spreadSeriesList: any[] = seasonalYears.map((sy) => {
    const color = getColorForSeasonalYear(sy)
    return {
      name: sy,
      type: 'line',
      yAxisIndex: 0,
      data: categories.map(c => seasonalMap.get(sy)!.get(c) ?? null),
      lineStyle: { color },
      itemStyle: { color },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    }
  })
  // 结算价按 mmdd 汇总以驱动右侧 Y 轴（近月/远月任取有值），系列不显示
  const settleByCat = new Map<string, number[]>()
  categories.forEach(c => { settleByCat.set(c, []) })
  series.data.forEach(d => {
    const date = new Date(d.date)
    const mmdd = `${(date.getMonth() + 1).toString().padStart(2, '0')}${date.getDate().toString().padStart(2, '0')}`
    const v = d.near_contract_settle ?? d.far_contract_settle
    if (v != null && Number.isFinite(v) && settleByCat.has(mmdd)) settleByCat.get(mmdd)!.push(v)
  })
  const settleAvg = categories.map(c => {
    const arr = settleByCat.get(c)!
    return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null
  })
  const hasSettle = settleAvg.some(v => v != null)
  const seriesOpt: any[] = [
    ...spreadSeriesList,
    ...(hasSettle ? [{
      name: '__结算价轴__',
      type: 'line' as const,
      yAxisIndex: 1,
      data: settleAvg,
      lineStyle: { opacity: 0 },
      symbol: 'none',
      symbolSize: 0,
      connectNulls: true,
      legendHoverLink: false
    }] : [])
  ]

  chart.setOption({
    title: { text: `${getChartTitle(series.spread_name)}合约价差`, left: 'left', top: 8 },
    legend: { data: spreadSeriesList.map(s => s.name), top: 36, left: 'left', type: 'plain', icon: 'circle', itemWidth: 10, itemHeight: 10, itemGap: 18 },
    grid: { left: '3%', right: '4%', bottom: '18%', top: '22%', containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (p: any) => {
        if (!Array.isArray(p)) return ''
        let r = `<div><strong>${p[0].axisValue}</strong></div>`
        p.forEach((x: any) => {
          if (x.seriesName === '__结算价轴__') return
          const v = x.value
          if (v != null && v !== '' && Number.isFinite(Number(v))) r += `<div>${x.seriesName}: <strong>${Number(v).toFixed(2)}</strong> 元/公斤</div>`
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
    yAxis: [
      { type: 'value', name: '价差(元/公斤)', position: 'left', ...yAxisHideMinMaxLabel, axisLabel: { formatter: axisLabelDecimalFormatter } },
      { type: 'value', name: '结算价(元/公斤)', position: 'right', ...yAxisHideMinMaxLabel, axisLabel: { formatter: axisLabelDecimalFormatter } }
    ],
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
