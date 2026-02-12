<template>
  <div class="slaughter-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>A3. 日度屠宰量（全国，涌益）</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <UpdateTimeBadge 
              :update-time="slaughterUpdateTime" 
              :last-data-date="lastDataDate" 
            />
          </div>
        </div>
      </template>

      <!-- 图表容器：两两一行 -->
      <div class="charts-container">
        <div class="chart-row">
          <!-- (1) 日度屠宰量（农历） -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">日度屠宰量（农历）</h3>
              <div v-if="loadingSlaughterLunar" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!slaughterLunarData || slaughterLunarData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据">
                  <el-button type="primary" @click="handleGenerateSQL">生成INSERT SQL</el-button>
                </el-empty>
              </div>
              <div v-else>
                <div ref="slaughterLunarChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <ChangeAnnotation
                :current-change="slaughterChanges.month_change"
                :yoy-change="slaughterChanges.yoy_change"
                :unit="slaughterLunarData?.unit"
              />
              <DataSourceInfo
                :source-name="'涌益'"
                :update-date="formatUpdateDate(slaughterUpdateTime)"
              />
            </div>
          </div>

          <!-- (2) 屠宰量&价格：按年筛选，阳历 正月初八～腊月二十八 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <div class="chart-title-row">
                <h3 class="chart-title">屠宰量&价格</h3>
                <el-select
                  v-model="selectedSolarYear"
                  placeholder="选择年份"
                  size="small"
                  style="width: 100px"
                  @change="loadSolarTrendData"
                >
                  <el-option
                    v-for="y in solarTrendAvailableYears"
                    :key="y"
                    :label="`${y}年`"
                    :value="y"
                  />
                </el-select>
              </div>
              <div v-if="loadingSolarTrend" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!solarTrendData || (solarTrendData.slaughter_data.length === 0 && solarTrendData.price_data.length === 0)" class="no-data-placeholder">
                <el-empty description="暂无数据" />
              </div>
              <div v-else>
                <div ref="solarTrendChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <span v-if="solarTrendData?.start_date && solarTrendData?.end_date" class="date-range-hint">
                区间：{{ solarTrendData.start_date }} ～ {{ solarTrendData.end_date }}（农历正月初八～腊月二十八）
              </span>
              <DataSourceInfo
                :source-name="'涌益'"
                :update-date="formatUpdateDate(solarTrendData?.latest_date)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- SQL下载对话框 -->
      <el-dialog v-model="showSQLDialog" title="生成的INSERT SQL语句" width="80%">
        <el-input
          v-model="generatedSQL"
          type="textarea"
          :rows="20"
          readonly
        />
        <template #footer>
          <el-button @click="showSQLDialog = false">关闭</el-button>
          <el-button type="primary" @click="handleDownloadSQL">下载SQL文件</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import UpdateTimeBadge from '@/components/UpdateTimeBadge.vue'
import ChangeAnnotation from '@/components/ChangeAnnotation.vue'
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import {
  getSlaughterLunar,
  getSlaughterPriceTrendSolar,
  type SeasonalityResponse,
  type SlaughterPriceTrendSolarResponse
} from '@/api/price-display'
import { getSlaughterData } from '@/api/national-data'
import { generateInsertSQL, downloadSQL } from '@/utils/sql-generator'
import type { MetricConfig, SQLGenerationOptions } from '@/utils/sql-generator'
import { getYearColor, axisLabelDecimalFormatter } from '@/utils/chart-style'

// 加载状态
const loadingSlaughterLunar = ref(false)

// 数据
const slaughterLunarData = ref<SeasonalityResponse | null>(null)

// 涨跌数据（日度屠宰量农历图）
const slaughterChanges = ref<{
  month_change: number | null
  yoy_change: number | null
}>({
  month_change: null,
  yoy_change: null
})

// 更新时间
const slaughterUpdateTime = ref<string | null>(null)
const lastDataDate = ref<string | null>(null)

// 屠宰量&价格：按年筛选，阳历 正月初八～腊月二十八
const loadingSolarTrend = ref(false)
const solarTrendData = ref<SlaughterPriceTrendSolarResponse | null>(null)
const solarTrendAvailableYears = ref<number[]>([])
const selectedSolarYear = ref<number | null>(null)
const solarTrendChartRef = ref<HTMLDivElement>()
let solarTrendChart: echarts.ECharts | null = null

// 图表引用
const slaughterLunarChartRef = ref<HTMLDivElement>()
let slaughterLunarChart: echarts.ECharts | null = null

// SQL生成
const showSQLDialog = ref(false)
const generatedSQL = ref('')

// 格式化更新日期（只显示年月日）
const formatUpdateDate = (dateStr: string | null | undefined): string | null => {
  if (!dateStr) return null
  try {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}年${month}月${day}日`
  } catch {
    return null
  }
}

// 加载农历日度屠宰量数据
const loadSlaughterLunar = async () => {
  loadingSlaughterLunar.value = true
  try {
    const data = await getSlaughterLunar()
    slaughterLunarData.value = data
    slaughterUpdateTime.value = data.update_time
    lastDataDate.value = data.latest_date
    
    // 计算涨跌数据
    await calculateSlaughterChanges()
    
    await nextTick()
    setTimeout(() => {
      if (data.series && data.series.length > 0) {
        renderSlaughterLunarChart()
      }
    }, 200)
  } catch (error: any) {
    console.error('加载日度屠宰量数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingSlaughterLunar.value = false
  }
}

// 计算屠宰量涨跌数据
const calculateSlaughterChanges = async () => {
  try {
    // 获取最近的数据用于计算涨跌
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    
    const result = await getSlaughterData(startDate, endDate)
    
    if (result.slaughterData.length > 0) {
      const sortedData = result.slaughterData.sort((a, b) => 
        new Date(a.obs_date || '').getTime() - new Date(b.obs_date || '').getTime()
      )
      
      // 计算月均值和同比
      const currentMonth = new Date()
      const lastMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1)
      const lastYear = new Date(currentMonth.getFullYear() - 1, currentMonth.getMonth(), 1)
      
      const currentMonthData = sortedData.filter(d => {
        const date = new Date(d.obs_date || '')
        return date.getMonth() === currentMonth.getMonth() && 
               date.getFullYear() === currentMonth.getFullYear()
      })
      
      const lastMonthData = sortedData.filter(d => {
        const date = new Date(d.obs_date || '')
        return date.getMonth() === lastMonth.getMonth() && 
               date.getFullYear() === lastMonth.getFullYear()
      })
      
      const lastYearData = sortedData.filter(d => {
        const date = new Date(d.obs_date || '')
        return date.getMonth() === currentMonth.getMonth() && 
               date.getFullYear() === lastYear.getFullYear()
      })
      
      // 计算月日均
      const currentMonthAvg = currentMonthData.length > 0
        ? currentMonthData.reduce((sum, d) => sum + (d.value || 0), 0) / currentMonthData.length
        : null
      
      const lastMonthAvg = lastMonthData.length > 0
        ? lastMonthData.reduce((sum, d) => sum + (d.value || 0), 0) / lastMonthData.length
        : null
      
      const lastYearAvg = lastYearData.length > 0
        ? lastYearData.reduce((sum, d) => sum + (d.value || 0), 0) / lastYearData.length
        : null
      
      // 计算涨跌
      if (currentMonthAvg !== null && lastMonthAvg !== null) {
        slaughterChanges.value.month_change = currentMonthAvg - lastMonthAvg
      }
      
      if (currentMonthAvg !== null && lastYearAvg !== null) {
        slaughterChanges.value.yoy_change = currentMonthAvg - lastYearAvg
      }
    }
  } catch (error) {
    console.error('计算涨跌数据失败:', error)
  }
}

// 渲染农历日度屠宰量图表
const renderSlaughterLunarChart = () => {
  if (!slaughterLunarChartRef.value || !slaughterLunarData.value || slaughterLunarData.value.series.length === 0) {
    console.warn('渲染条件不满足:', {
      hasRef: !!slaughterLunarChartRef.value,
      hasData: !!slaughterLunarData.value,
      seriesLength: slaughterLunarData.value?.series?.length || 0
    })
    return
  }
  
  if (slaughterLunarChart) {
    slaughterLunarChart.dispose()
    slaughterLunarChart = null
  }
  
  // 确保容器有尺寸
  if (slaughterLunarChartRef.value.offsetWidth === 0 || slaughterLunarChartRef.value.offsetHeight === 0) {
    console.warn('图表容器尺寸为0，延迟渲染')
    setTimeout(() => renderSlaughterLunarChart(), 100)
    return
  }
  
  slaughterLunarChart = echarts.init(slaughterLunarChartRef.value)
  
  // 收集所有唯一的month_day作为X轴（农历日期索引）
  const allMonthDays = new Set<string>()
  slaughterLunarData.value.series.forEach(s => {
    s.data.forEach(d => {
      if (d.month_day) allMonthDays.add(d.month_day)
    })
  })
  const xAxisData = Array.from(allMonthDays).sort((a, b) => {
    // 按数字排序（month_day是农历日期索引字符串）
    const numA = parseInt(a) || 0
    const numB = parseInt(b) || 0
    return numA - numB
  })
  
  // 为每个年份构建数据，对齐到X轴
  const series = slaughterLunarData.value.series.map(s => {
    // 创建month_day到value的映射
    const valueMap = new Map<string, number | null>()
    s.data.forEach(d => {
      if (d.month_day) {
        valueMap.set(d.month_day, d.value)
      }
    })
    
    // 按照X轴顺序提取值
    const values = xAxisData.map(md => valueMap.get(md) ?? null)
    
    // 判断是否为闰月系列
    const isLeapMonth = s.is_leap_month === true
    const leapMonth = s.leap_month
    
    const lineColor = getYearColor(s.year)
    
    // 图例名称：如果是闰月，显示"2025年闰6月"；否则显示"2025年"
    const seriesName = isLeapMonth && leapMonth 
      ? `${s.year}年闰${leapMonth}月`
      : `${s.year}年`
    
    return {
      name: seriesName,
      type: 'line',
      data: values,
      smooth: true,
      // 移除数据点
      symbol: 'none',
      // 处理断点：使用连续曲线
      connectNulls: true,
      lineStyle: { 
        width: 2,
        color: lineColor
      },
      itemStyle: { color: lineColor }
    }
  })
  
  // 计算Y轴范围（自动调整）
  const allValues = series.flatMap(s => s.data).filter(v => v !== null && v !== undefined) as number[]
  const yMin = allValues.length > 0 ? Math.min(...allValues) : 0
  const yMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const yPadding = (yMax - yMin) * 0.1 // 10% padding
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        // 获取X轴值（索引），转换为农历日期标签（MM-dd格式）
        const index = parseInt(params[0].axisValue) || 0
        let axisLabel = params[0].axisValue
        if (slaughterLunarData.value.x_axis_labels && slaughterLunarData.value.x_axis_labels[index]) {
          axisLabel = slaughterLunarData.value.x_axis_labels[index]
        }
        
        let result = `<div style="margin-bottom: 4px;"><strong>${axisLabel}</strong></div>`
        params.forEach((param: any) => {
          const value = param.value !== null && param.value !== undefined 
            ? param.value.toFixed(0) 
            : '-'
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}: <strong>${value}${slaughterLunarData.value.unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: series.map(s => s.name),  // 使用series中的name（已经处理了闰月）
      top: 10,
      type: 'plain', // 不使用滚动
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      orient: 'horizontal',
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '15%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      name: '',
      axisLabel: {
        rotate: 45,
        interval: 'auto',
        formatter: (value: string) => {
          const index = parseInt(value)
          if (slaughterLunarData.value.x_axis_labels && slaughterLunarData.value.x_axis_labels[index]) {
            return slaughterLunarData.value.x_axis_labels[index]
          }
          return value
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '',
      min: yMin - yPadding,
      max: yMax + yPadding,
      scale: false,
      axisLabel: { formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    series: series,
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ]
  }
  
  slaughterLunarChart.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    slaughterLunarChart?.resize()
  }, 100)
}

// 生成SQL
const handleGenerateSQL = async () => {
  try {
    const configs: MetricConfig[] = [
      {
        metric_key: 'YY_D_SLAUGHTER_TOTAL_1',
        metric_name: '日度屠宰量',
        source_code: 'YONGYI',
        sheet_name: '价格+宰量',
        unit: '头',
        tags: { scope: 'nation' }
      },
      {
        metric_key: 'YY_D_PRICE_NATION_AVG',
        metric_name: '全国出栏均价',
        source_code: 'YONGYI',
        sheet_name: '价格+宰量',
        unit: '元/公斤',
        tags: { scope: 'nation' }
      }
    ]
    
    const options: SQLGenerationOptions = {
      start_date: '2025-01-01',
      end_date: '2026-02-02',
      sample_count: 30,
      batch_id: 1
    }
    
    const sqls = configs.map(config => generateInsertSQL(config, options))
    generatedSQL.value = sqls.join('\n\n')
    showSQLDialog.value = true
  } catch (error: any) {
    ElMessage.error('生成SQL失败: ' + error.message)
  }
}

// 下载SQL
const handleDownloadSQL = () => {
  downloadSQL(generatedSQL.value, `slaughter_data_${new Date().toISOString().split('T')[0]}.sql`)
  ElMessage.success('SQL文件已下载')
}

// 窗口大小变化时调整图表
const handleResize = () => {
  slaughterLunarChart?.resize()
  solarTrendChart?.resize()
}

// 监听数据变化，自动重新渲染图表
watch(() => slaughterLunarData.value, (newVal) => {
  if (newVal && newVal.series && newVal.series.length > 0) {
    nextTick(() => {
      setTimeout(() => renderSlaughterLunarChart(), 200)
    })
  }
}, { deep: true })

// 加载屠宰量&价格（按年，阳历 正月初八～腊月二十八）（按年，阳历 正月初八～腊月二十八）
const loadSolarTrendData = async () => {
  loadingSolarTrend.value = true
  try {
    const res = await getSlaughterPriceTrendSolar(selectedSolarYear.value ?? undefined)
    solarTrendData.value = res
    solarTrendAvailableYears.value = res.available_years || []
    if (selectedSolarYear.value == null && res.available_years?.length) {
      selectedSolarYear.value = res.available_years[0]
    }
    await nextTick()
    setTimeout(() => {
      if (res.slaughter_data?.length || res.price_data?.length) {
        renderSolarTrendChart()
      }
    }, 200)
  } catch (e: any) {
    console.error('加载屠宰&价格相关走势失败:', e)
    ElMessage.error('加载失败: ' + (e.message || '未知错误'))
  } finally {
    loadingSolarTrend.value = false
  }
}

// 渲染屠宰&价格 相关走势图（阳历日期，双 Y 轴）
const renderSolarTrendChart = () => {
  if (!solarTrendChartRef.value || !solarTrendData.value) return
  const data = solarTrendData.value
  if (solarTrendChart) {
    solarTrendChart.dispose()
    solarTrendChart = null
  }
  if (solarTrendChartRef.value.offsetWidth === 0) {
    setTimeout(renderSolarTrendChart, 100)
    return
  }
  solarTrendChart = echarts.init(solarTrendChartRef.value)

  const allDates = new Set<string>()
  data.slaughter_data?.forEach(d => allDates.add(d.date))
  data.price_data?.forEach(d => allDates.add(d.date))
  const sortedDates = Array.from(allDates).sort()
  const slaughterMap = new Map(data.slaughter_data?.map(d => [d.date, d.value]) ?? [])
  const priceMap = new Map(data.price_data?.map(d => [d.date, d.value]) ?? [])

  const slaughterValues = sortedDates.map(d => slaughterMap.get(d) ?? null)
  const priceValues = sortedDates.map(d => priceMap.get(d) ?? null)
  // X 轴用完整阳历日期，轴标签显示为 MM-DD
  const xAxisData = sortedDates
  const xAxisLabelFormatter = (value: string) => {
    const [, m, day] = (value || '').slice(0, 10).split('-')
    return m && day ? `${m}-${day}` : value
  }

  const series: any[] = []
  if (slaughterValues.some(v => v != null)) {
    series.push({
      name: '屠宰量',
      type: 'line',
      data: slaughterValues,
      yAxisIndex: 0,
      smooth: true,
      symbol: 'none',
      connectNulls: true,
      lineStyle: { width: 2 },
      itemStyle: { color: '#409EFF' }
    })
  }
  if (priceValues.some(v => v != null)) {
    series.push({
      name: '价格',
      type: 'line',
      data: priceValues,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'none',
      connectNulls: true,
      lineStyle: { width: 2, type: 'dashed' },
      itemStyle: { color: '#67C23A' }
    })
  }

  if (series.length === 0 || xAxisData.length === 0) return

  solarTrendChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const dateStr = params[0].axisValue
        let s = `<div style="margin-bottom:4px"><strong>${dateStr}</strong></div>`
        params.forEach((p: any) => {
          const v = p.value != null ? Number(p.value).toFixed(2) : '-'
          const u = p.seriesName === '价格' ? '元/公斤' : '头'
          s += `<div style="margin:2px 0"><span style="display:inline-block;width:10px;height:10px;background:${p.color};border-radius:50%;margin-right:5px"></span>${p.seriesName}: <strong>${v} ${u}</strong></div>`
        })
        return s
      }
    },
    legend: { data: series.map(s => s.name), top: 8, type: 'plain', left: 'left' },
    grid: { left: '3%', right: '4%', top: '15%', bottom: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLabel: { rotate: 45, interval: 'auto', formatter: xAxisLabelFormatter }
    },
    yAxis: [
      { type: 'value', position: 'left', name: '', axisLabel: { formatter: (v: number) => (v == null ? '' : String(v)) } },
      { type: 'value', position: 'right', name: '', axisLabel: { formatter: (v: number) => (v == null ? '' : String(v)) } }
    ],
    series,
    dataZoom: [{ type: 'inside', start: 0, end: 100 }]
  })
  setTimeout(() => solarTrendChart?.resize(), 100)
}

// 生命周期
onMounted(() => {
  loadSlaughterLunar()
  loadSolarTrendData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (slaughterLunarChart) {
    slaughterLunarChart.dispose()
    slaughterLunarChart = null
  }
  if (solarTrendChart) {
    solarTrendChart.dispose()
    solarTrendChart = null
  }
})
</script>

<style scoped>
.slaughter-page {
  padding: 4px;
}

.slaughter-page :deep(.el-card__body) {
  padding: 4px 6px;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 4px;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-wrapper {
  padding: 0;
}

.chart-row-full {
  grid-template-columns: 1fr;
}

.chart-wrapper-full {
  grid-column: 1;
}

.date-range-hint {
  font-size: 12px;
  color: #909399;
}

.chart-box {
  margin-bottom: 6px;
}

.info-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 6px;
  background-color: transparent;
}

.chart-title {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  line-height: 1.5;
  text-align: left;
}

.chart-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap;
  gap: 10px;
}

.chart-title-row .chart-title {
  margin: 0;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.loading-placeholder {
  text-align: center;
  padding: 40px;
}

.no-data-placeholder {
  padding: 40px;
  text-align: center;
}

/* 响应式布局：小屏幕时单列显示 */
@media (max-width: 1200px) {
  .chart-row {
    grid-template-columns: 1fr;
  }
  
  .chart-title-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
