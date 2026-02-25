<template>
  <div class="premium-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>升贴水数据</span>
        </div>
      </template>

      <!-- 筛选区域 -->
      <div class="filters">
        <!-- 时间筛选 -->
        <div class="filter-group">
          <span class="filter-label">时间筛选：</span>
          <el-radio-group v-model="viewType" @change="loadData" size="small">
            <el-radio-button label="季节性">季节性</el-radio-button>
            <el-radio-button label="全部日期">全部日期</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 格式筛选 -->
        <div class="filter-group">
          <span class="filter-label">格式筛选：</span>
          <el-radio-group v-model="formatType" @change="loadData" size="small">
            <el-radio-button label="全部格式">全部格式</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 区域筛选 -->
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

      <!-- 省区升贴水注释 -->
      <div v-if="regionPremiums && Object.keys(regionPremiums).length > 0" class="region-premiums">
        <div class="region-premiums-title">{{ selectedRegion }}区域升贴水：</div>
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
          <!-- 如果格式选全部，则左侧是全部日期；右侧是季节性 -->
          <div v-if="formatType === '全部格式'" class="charts-container">
            <div class="chart-row">
              <div class="chart-item">
                <div class="chart-item-header">
                  <h3>全部日期</h3>
                  <div class="year-filter">
                    <span class="filter-label">年份：</span>
                    <el-select
                      v-model="selectedAllDatesYear"
                      placeholder="选择年份"
                      size="small"
                      style="width: 100px"
                      @change="renderCharts"
                    >
                      <el-option
                        v-for="y in allDatesYearOptions"
                        :key="y"
                        :label="`${y}年`"
                        :value="y"
                      />
                    </el-select>
                  </div>
                </div>
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
          <!-- 如果格式不是全部，只显示当前选择的视图类型 -->
          <div v-else>
            <div
              v-for="series in premiumData.series"
              :key="series.contract_month"
              class="chart-wrapper"
            >
              <h3>{{ series.contract_name }}升贴水</h3>
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
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { futuresApi, type PremiumResponseV2 } from '@/api/futures'
import { axisLabelDecimalFormatter, axisLabelPercentFormatter, yAxisHideMinMaxLabel } from '@/utils/chart-style'

const loading = ref(false)
const viewType = ref<'季节性' | '全部日期'>('全部日期')
const formatType = ref('全部格式')
const selectedRegion = ref('全国均价')
const premiumData = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const premiumDataAllDates = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const premiumDataSeasonal = ref<PremiumResponseV2>({ series: [], region_premiums: {}, update_time: null })
const regionPremiums = ref<Record<string, number>>({})
const errorMessage = ref<string>('')
const chartInstances = new Map<string, echarts.ECharts>()
const chartRefs = new Map<string, HTMLDivElement>()

/** 左侧全部日期图：按年过滤，只显示选中年的现货价格、合约价格、升贴水 */
const selectedAllDatesYear = ref<number | null>(null)
/** 左侧图可选年份（从全部日期数据中汇总各合约年） */
const allDatesYearOptions = computed(() => {
  const set = new Set<number>()
  premiumDataAllDates.value.series.forEach(s => {
    s.data.forEach(p => {
      const y = getContractYear(p.date, s.contract_month)
      set.add(y)
    })
  })
  const list = Array.from(set).sort((a, b) => a - b)
  return list
})

const contractMonths = [3, 5, 7, 9, 11, 1]

// 设置图表引用
const setChartRef = (key: string, el: HTMLDivElement | null) => {
  if (el) {
    chartRefs.set(key, el)
  } else {
    chartRefs.delete(key)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    if (formatType.value === '全部格式') {
      // 需要同时获取全部日期和季节性数据
      const [allDatesResult, seasonalResult] = await Promise.all([
        futuresApi.getPremiumV2({
          region: selectedRegion.value,
          view_type: '全部日期',
          format_type: formatType.value
        }),
        futuresApi.getPremiumV2({
          region: selectedRegion.value,
          view_type: '季节性',
          format_type: formatType.value
        })
      ])
      premiumDataAllDates.value = allDatesResult
      premiumDataSeasonal.value = seasonalResult
      premiumData.value = allDatesResult // 用于显示region_premiums
      regionPremiums.value = allDatesResult.region_premiums || {}
      
      if (allDatesResult.series.length === 0 && seasonalResult.series.length === 0) {
        errorMessage.value = '未找到升贴水数据'
      } else {
        if (allDatesResult.series.length > 0) {
          const years = new Set<number>()
          allDatesResult.series.forEach(s => {
            s.data.forEach(p => { years.add(getContractYear(p.date, s.contract_month)) })
          })
          const currentYear = new Date().getFullYear()
          const defaultYear = years.has(currentYear) ? currentYear : Math.max(...years)
          if (selectedAllDatesYear.value == null || !years.has(selectedAllDatesYear.value)) {
            selectedAllDatesYear.value = defaultYear
          }
        }
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
    console.error('加载升贴水数据失败:', error)
    errorMessage.value = error?.response?.data?.detail || error?.message || '加载数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 渲染图表
const renderCharts = () => {
  if (formatType.value === '全部格式') {
    // 左侧：全部日期，右侧：季节性
    premiumDataAllDates.value.series.forEach(series => {
      // 全部日期图
      const allKey = `all-${series.contract_month}`
      const allEl = chartRefs.get(allKey)
      if (allEl) {
        renderAllDatesChart(allEl, series)
      }
    })
    
    premiumDataSeasonal.value.series.forEach(series => {
      // 季节性图
      const seasonalKey = `seasonal-${series.contract_month}`
      const seasonalEl = chartRefs.get(seasonalKey)
      if (seasonalEl) {
        renderSeasonalChart(seasonalEl, series)
      }
    })
  } else {
    // 只显示当前选择的视图类型
    premiumData.value.series.forEach(series => {
      const key = `${viewType.value}-${series.contract_month}`
      const el = chartRefs.get(key)
      if (el) {
        if (viewType.value === '季节性') {
          renderSeasonalChart(el, series)
        } else {
          renderAllDatesChart(el, series)
        }
      }
    })
  }
}

// X月合约季节性区间：(X+1)月1日至(X-1)月最后日。03合约为4月1日～次年2月29日，2203即21年4月1日～22年2月29日；图例显示合约年+1
function getContractYear(dateStr: string, contractMonth: number): number {
  const d = new Date(dateStr)
  const month = d.getMonth() + 1
  const year = d.getFullYear()
  const startMonth = contractMonth === 1 ? 2 : (contractMonth + 1) > 12 ? 1 : contractMonth + 1
  const endMonth = contractMonth - 1 <= 0 ? 12 : contractMonth - 1
  if (startMonth > endMonth) {
    if (month >= startMonth && month <= 12) return year + 1
    if (month >= 1 && month <= endMonth) return year
    return year + 1
  }
  if (month >= startMonth && month <= endMonth) return contractMonth === 1 ? year + 1 : year
  return year
}
function getDisplayYear(contractYear: number): number {
  return contractYear + 1
}

// 左侧全部日期图固定三色：现货价格、合约价格、升贴水
const COLOR_SPOT = '#409EFF'
const COLOR_CONTRACT = '#67C23A'
const COLOR_PREMIUM = '#E6A23C'

// 渲染全部日期图（仅显示选中年，三条线：现货价格、合约价格、升贴水）
const renderAllDatesChart = (el: HTMLDivElement, series: PremiumResponseV2['series'][0]) => {
  const key = `all-${series.contract_month}`
  if (chartInstances.has(key)) chartInstances.get(key)?.dispose()
  const chartInstance = echarts.init(el)
  chartInstances.set(key, chartInstance)

  const contractMonth = series.contract_month
  const yearMap = new Map<number, Array<typeof series.data[0]>>()
  series.data.forEach(point => {
    const contractYear = getContractYear(point.date, contractMonth)
    if (!yearMap.has(contractYear)) yearMap.set(contractYear, [])
    yearMap.get(contractYear)!.push(point)
  })
  const selectedYear = selectedAllDatesYear.value
  const yearData = selectedYear != null ? yearMap.get(selectedYear) : null

  const seriesData: any[] = []
  if (yearData && yearData.length > 0) {
    seriesData.push({
      name: '现货价格',
      type: 'line',
      data: yearData.map(d => [d.date, d.spot_price]),
      yAxisIndex: 0,
      lineStyle: { color: COLOR_SPOT },
      itemStyle: { color: COLOR_SPOT },
      symbol: 'circle',
      symbolSize: 4,
      connectNulls: true
    })
    seriesData.push({
      name: '合约价格',
      type: 'line',
      data: yearData.map(d => [d.date, d.futures_settle]),
      yAxisIndex: 0,
      lineStyle: { color: COLOR_CONTRACT },
      itemStyle: { color: COLOR_CONTRACT },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    })
    seriesData.push({
      name: '升贴水',
      type: 'line',
      data: yearData.map(d => [d.date, d.premium]),
      yAxisIndex: 1,
      lineStyle: { color: COLOR_PREMIUM },
      itemStyle: { color: COLOR_PREMIUM },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    })
  }

  const option: echarts.EChartsOption = {
    title: { text: `${series.contract_name}的升贴水`, left: 'left', top: 8 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `<div style="margin-bottom: 4px;"><strong>${params[0].axisValue}</strong></div>`
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            const value = typeof param.value === 'number' ? param.value.toFixed(2) : param.value
            const unit = param.seriesName?.includes('升贴水') ? '元/公斤' : '元/公斤'
            result += `<div style="margin: 2px 0;">
              <span style="display: inline-block; width: 10px; height: 10px; background-color: ${param.color}; margin-right: 5px;"></span>
              ${param.seriesName}: <strong>${value}${unit}</strong>
            </div>`
          }
        })
        return result
      }
    },
    legend: {
      data: seriesData.length ? seriesData.map(s => s.name) : ['现货价格', '合约价格', '升贴水'],
      top: 36,
      left: 'left',
      type: 'plain',
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 18
    },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '22%', containLabel: true },
    xAxis: { type: 'time', boundaryGap: false },
    yAxis: [
      { type: 'value', name: '价格', position: 'left', scale: true, ...yAxisHideMinMaxLabel, axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) } },
      { type: 'value', name: '升贴水', position: 'right', ...yAxisHideMinMaxLabel, axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) } }
    ],
    series: seriesData,
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }
    ]
  }
  chartInstance.setOption(option, true)
  window.addEventListener('resize', () => chartInstance.resize())
}

// 渲染季节性图（升贴水比率）
const renderSeasonalChart = (el: HTMLDivElement, series: PremiumResponseV2['series'][0]) => {
  const key = `seasonal-${series.contract_month}`
  if (chartInstances.has(key)) chartInstances.get(key)?.dispose()
  const chartInstance = echarts.init(el)
  chartInstances.set(key, chartInstance)

  const contractMonth = series.contract_month
  const yearMap = new Map<number, Array<typeof series.data[0]>>()
  series.data.forEach(point => {
    const contractYear = getContractYear(point.date, contractMonth)
    if (!yearMap.has(contractYear)) yearMap.set(contractYear, [])
    yearMap.get(contractYear)!.push(point)
  })
  const years = Array.from(yearMap.keys()).sort()
  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272',
    '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3'
  ]

  // X合约季节性时间轴：(X+1)月1日～(X-1)月最后日。按合约计算起止月与是否跨年，用于 X 轴排序
  const startMonth = contractMonth + 1 > 12 ? 1 : contractMonth + 1
  const endMonth = contractMonth - 1 <= 0 ? 12 : contractMonth - 1
  const crossYear = startMonth > endMonth
  const dateSet = new Set<string>()
  series.data.forEach(d => {
    const date = new Date(d.date)
    const month = date.getMonth() + 1
    const day = date.getDate()
    dateSet.add(`${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`)
  })
  const categories = Array.from(dateSet).sort((a, b) => {
    const [aMonth, aDay] = a.split('-').map(Number)
    const [bMonth, bDay] = b.split('-').map(Number)
    const aOrder = crossYear
      ? (aMonth >= startMonth ? aMonth : aMonth + 12)
      : aMonth
    const bOrder = crossYear
      ? (bMonth >= startMonth ? bMonth : bMonth + 12)
      : bMonth
    if (aOrder !== bOrder) return aOrder - bOrder
    return aDay - bDay
  })

  const seriesData: any[] = []
  years.forEach((contractYear, idx) => {
    const yearData = yearMap.get(contractYear)!
    const displayYear = getDisplayYear(contractYear)
    const color = colors[idx % colors.length]
    const dataMap = new Map<string, number | null>()
    yearData.forEach(d => {
      const date = new Date(d.date)
      const monthDay = `${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`
      dataMap.set(monthDay, d.premium_ratio ?? null)
    })
    seriesData.push({
      name: `${displayYear}年`,
      type: 'line',
      data: categories.map(cat => dataMap.get(cat) ?? null),
      lineStyle: { color },
      itemStyle: { color },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    })
  })
  
  const option: echarts.EChartsOption = {
    title: {
      text: `${series.contract_name}升贴水比率`,
      left: 'left',
      top: 8
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `<div style="margin-bottom: 4px;"><strong>${params[0].axisValue}</strong></div>`
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            const value = typeof param.value === 'number' ? param.value.toFixed(2) : param.value
            result += `<div style="margin: 2px 0;">
              <span style="display: inline-block; width: 10px; height: 10px; background-color: ${param.color}; margin-right: 5px;"></span>
              ${param.seriesName}: <strong>${value}%</strong>
            </div>`
          }
        })
        return result
      }
    },
    legend: {
      data: seriesData.map(s => s.name),
      top: 36,
      left: 'left',
      type: 'plain',
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 18
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '22%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: false,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '升贴水比率（%）',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => axisLabelPercentFormatter(v) }
    },
    series: seriesData,
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }
    ]
  }
  
  chartInstance.setOption(option, true)
  window.addEventListener('resize', () => chartInstance.resize())
}

// 监听数据变化，重新渲染图表
watch([() => premiumData.value.series, () => premiumDataAllDates.value.series, () => premiumDataSeasonal.value.series], () => {
  nextTick(() => {
    renderCharts()
  })
}, { deep: true })

// 组件挂载
onMounted(() => {
  loadData()
})

// 组件卸载
onBeforeUnmount(() => {
  chartInstances.forEach(chart => chart.dispose())
  chartInstances.clear()
  chartRefs.clear()
})
</script>

<style scoped lang="scss">
.premium-page {
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
  
  .charts-container {
    .chart-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      
      .chart-item {
        .chart-item-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 6px;
          .filter-label { font-weight: 500; margin-right: 4px; }
          .year-filter { display: flex; align-items: center; }
        }
        h3 {
          margin: 0;
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
