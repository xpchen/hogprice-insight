<template>
  <div class="slaughter-page">
    <el-card>
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

          <!-- (2) 屠宰量&价格 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">屠宰量&价格</h3>
              <div v-if="loadingTrend" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!trendData || (trendData.slaughter_data.length === 0 && trendData.price_data.length === 0)" class="no-data-placeholder">
                <el-empty description="暂无数据">
                  <el-button type="primary" @click="handleGenerateSQL">生成INSERT SQL</el-button>
                </el-empty>
              </div>
              <div v-else>
                <div ref="trendChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <DataSourceInfo
                :source-name="'涌益'"
                :update-date="formatUpdateDate(slaughterUpdateTime)"
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
  type SeasonalityResponse
} from '@/api/price-display'
import { getSlaughterData } from '@/api/national-data'
import { generateInsertSQL, downloadSQL } from '@/utils/sql-generator'
import type { MetricConfig, SQLGenerationOptions } from '@/utils/sql-generator'

// 加载状态
const loadingSlaughterLunar = ref(false)
const loadingTrend = ref(false)

// 数据
const slaughterLunarData = ref<SeasonalityResponse | null>(null)
const trendData = ref<{
  slaughter_data: Array<{ date: string; year: number; value: number | null }>
  price_data: Array<{ date: string; year: number; value: number | null }>
  available_years: number[]
} | null>(null)

// 涨跌数据
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

// 年度筛选（单选）
const availableYears = ref<number[]>([])
const selectedYear = ref<number | null>(null)

// 图表引用
const slaughterLunarChartRef = ref<HTMLDivElement>()
const trendChartRef = ref<HTMLDivElement>()

let slaughterLunarChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

// SQL生成
const showSQLDialog = ref(false)
const generatedSQL = ref('')

// 年份颜色映射
const yearColors: Record<number, string> = {
  2021: '#FFB6C1',
  2022: '#FF69B4',
  2023: '#4169E1',
  2024: '#D3D3D3',
  2025: '#1E90FF',
  2026: '#FF0000',
  2027: '#32CD32',
  2028: '#FFA500',
}

const getYearColor = (year: number): string => {
  return yearColors[year] || '#888888'
}

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

// 加载量价走势数据
const loadTrendData = async () => {
  loadingTrend.value = true
  try {
    // 获取最近3年的数据
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 3 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    
    const result = await getSlaughterData(startDate, endDate)
    
    // 按年份分组数据
    const slaughterByYear: Record<number, Array<{ date: string; value: number | null }>> = {}
    const priceByYear: Record<number, Array<{ date: string; value: number | null }>> = {}
    
    result.slaughterData.forEach(d => {
      const year = new Date(d.obs_date || '').getFullYear()
      if (!slaughterByYear[year]) {
        slaughterByYear[year] = []
      }
      slaughterByYear[year].push({
        date: d.obs_date || '',
        value: d.value
      })
    })
    
    result.priceData.forEach(d => {
      const year = new Date(d.obs_date || '').getFullYear()
      if (!priceByYear[year]) {
        priceByYear[year] = []
      }
      priceByYear[year].push({
        date: d.obs_date || '',
        value: d.value
      })
    })
    
    // 构建响应数据
    const years = [...new Set([...Object.keys(slaughterByYear), ...Object.keys(priceByYear)].map(Number))].sort()
    availableYears.value = years
    
    // 初始化选中年份：默认选择去年
    if (selectedYear.value === null && years.length > 0) {
      const currentYear = new Date().getFullYear()
      const lastYear = currentYear - 1
      if (years.includes(lastYear)) {
        selectedYear.value = lastYear
      } else {
        selectedYear.value = Math.max(...years)
      }
    }
    
    const slaughterData: Array<{ date: string; year: number; value: number | null }> = []
    const priceData: Array<{ date: string; year: number; value: number | null }> = []
    
    years.forEach(year => {
      if (slaughterByYear[year]) {
        slaughterByYear[year].forEach(d => {
          slaughterData.push({ ...d, year })
        })
      }
      if (priceByYear[year]) {
        priceByYear[year].forEach(d => {
          priceData.push({ ...d, year })
        })
      }
    })
    
    trendData.value = {
      slaughter_data: slaughterData,
      price_data: priceData,
      available_years: years
    }
    
    await nextTick()
    setTimeout(() => {
      renderTrendChart()
    }, 200)
  } catch (error: any) {
    console.error('加载量价走势数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingTrend.value = false
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
  
  // 计算最近三年（用于颜色规则）
  const sortedYears = [...slaughterLunarData.value.series.map(s => s.year)].sort((a, b) => b - a)
  const recentThreeYears = new Set(sortedYears.slice(0, 3))
  
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
    
    // 最近三年有颜色，其他年份灰色（闰月也遵循这个规则）
    const isRecentYear = recentThreeYears.has(s.year)
    const lineColor = isRecentYear ? getYearColor(s.year) : '#D3D3D3'
    
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
      left: 'center'
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
      // X轴不显示标签（默认时间轴）
      name: '',
      axisLabel: {
        rotate: 45,
        interval: 'auto',
        // 如果有x_axis_labels，使用农历日期标签（MM-dd格式）；否则使用索引
        formatter: (value: string) => {
          const index = parseInt(value)
          if (slaughterLunarData.value.x_axis_labels && slaughterLunarData.value.x_axis_labels[index]) {
            return slaughterLunarData.value.x_axis_labels[index]
          }
          // 如果没有标签，显示索引（作为后备）
          return value
        }
      }
    },
    yAxis: {
      type: 'value',
      // Y轴不显示单位
      name: '',
      // 自动调整范围
      min: yMin - yPadding,
      max: yMax + yPadding,
      scale: false
    },
    series: series,
    // 只保留内部缩放，删除日期筛选进度条
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

// 渲染量价走势图（年度筛选，阳历日期对齐）
const renderTrendChart = () => {
  if (!trendChartRef.value || !trendData.value) {
    console.warn('渲染条件不满足:', {
      hasRef: !!trendChartRef.value,
      hasData: !!trendData.value
    })
    return
  }
  
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
  
  // 确保容器有尺寸
  if (trendChartRef.value.offsetWidth === 0 || trendChartRef.value.offsetHeight === 0) {
    console.warn('图表容器尺寸为0，延迟渲染')
    setTimeout(() => renderTrendChart(), 100)
    return
  }
  
  trendChart = echarts.init(trendChartRef.value)
  
  // 根据选中的年份过滤数据
  const filteredSlaughterData = selectedYear.value !== null
    ? trendData.value.slaughter_data.filter(item => item.year === selectedYear.value)
    : [...trendData.value.slaughter_data]
  
  const filteredPriceData = selectedYear.value !== null
    ? trendData.value.price_data.filter(item => item.year === selectedYear.value)
    : [...trendData.value.price_data]
  
  // 按日期排序
  filteredSlaughterData.sort((a, b) => a.date.localeCompare(b.date))
  filteredPriceData.sort((a, b) => a.date.localeCompare(b.date))
  
  // 构建X轴：合并所有日期并排序（阳历日期）
  const allDates = new Set<string>()
  filteredSlaughterData.forEach(item => allDates.add(item.date))
  filteredPriceData.forEach(item => allDates.add(item.date))
  const sortedDates = Array.from(allDates).sort()
  
  // 格式化X轴标签（MM-DD格式）
  const xAxisData = sortedDates.map(dateStr => {
    const date = new Date(dateStr)
    return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  })
  
  // 创建日期到值的映射
  const slaughterMap = new Map<string, number | null>()
  filteredSlaughterData.forEach(item => {
    slaughterMap.set(item.date, item.value)
  })
  
  const priceMap = new Map<string, number | null>()
  filteredPriceData.forEach(item => {
    priceMap.set(item.date, item.value)
  })
  
  // 构建两个指标系列
  const series: any[] = []
  
  // 屠宰量指标（左Y轴）
  const slaughterValues = sortedDates.map(date => slaughterMap.get(date) ?? null)
  if (slaughterValues.some(v => v !== null)) {
    // 计算Y轴范围（自动调整）
    const slaughterNumbers = slaughterValues.filter(v => v !== null) as number[]
    const slaughterMin = slaughterNumbers.length > 0 ? Math.min(...slaughterNumbers) : 0
    const slaughterMax = slaughterNumbers.length > 0 ? Math.max(...slaughterNumbers) : 100
    const slaughterPadding = (slaughterMax - slaughterMin) * 0.1
    
    series.push({
      name: '屠宰量',
      type: 'line',
      data: slaughterValues,
      yAxisIndex: 0,
      smooth: true,
      // 移除数据点
      symbol: 'none',
      // 处理断点：使用连续曲线
      connectNulls: true,
      lineStyle: { width: 2 },
      itemStyle: { color: '#409EFF' }
    })
  }
  
  // 价格指标（右Y轴）
  const priceValues = sortedDates.map(date => priceMap.get(date) ?? null)
  if (priceValues.some(v => v !== null)) {
    // 计算Y轴范围（自动调整）
    const priceNumbers = priceValues.filter(v => v !== null) as number[]
    const priceMin = priceNumbers.length > 0 ? Math.min(...priceNumbers) : 0
    const priceMax = priceNumbers.length > 0 ? Math.max(...priceNumbers) : 100
    const pricePadding = (priceMax - priceMin) * 0.1
    
    series.push({
      name: '价格',
      type: 'line',
      data: priceValues,
      yAxisIndex: 1,
      smooth: true,
      // 移除数据点
      symbol: 'none',
      // 处理断点：使用连续曲线
      connectNulls: true,
      lineStyle: { width: 2, type: 'dashed' },
      itemStyle: { color: '#67C23A' }
    })
  }
  
  if (series.length === 0 || xAxisData.length === 0) {
    console.warn('没有数据系列或X轴数据为空，不渲染图表')
    return
  }
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `<div style="margin-bottom: 4px;"><strong>${params[0].axisValue}</strong></div>`
        params.forEach((param: any) => {
          const value = param.value !== null && param.value !== undefined 
            ? param.value.toFixed(2) 
            : '-'
          const unit = param.seriesName === '价格' ? '元/公斤' : '头'
          const yAxisName = param.series.yAxisIndex === 1 ? '（右轴）' : '（左轴）'
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}${yAxisName}: <strong>${value}${unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: series.map(s => s.name),
      top: 10,
      type: 'plain', // 不使用滚动
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 15,
      orient: 'horizontal',
      left: 'center'
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
      // X轴不显示标签（默认时间轴）
      name: '',
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
    },
    yAxis: [
      {
        type: 'value',
        // Y轴不显示单位
        name: '',
        position: 'left',
        // 自动调整范围
        scale: false
      },
      {
        type: 'value',
        // Y轴不显示单位
        name: '',
        position: 'right',
        // 自动调整范围
        scale: false
      }
    ],
    series: series,
    // 只保留内部缩放，删除日期筛选进度条
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ]
  }
  
  trendChart.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    trendChart?.resize()
  }, 100)
}

// 年度筛选变化
const handleYearFilterChange = () => {
  if (trendData.value) {
    nextTick(() => {
      setTimeout(() => renderTrendChart(), 100)
    })
  }
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
  trendChart?.resize()
}

// 监听数据变化，自动重新渲染图表
watch(() => slaughterLunarData.value, (newVal) => {
  if (newVal && newVal.series && newVal.series.length > 0) {
    nextTick(() => {
      setTimeout(() => renderSlaughterLunarChart(), 200)
    })
  }
}, { deep: true })

watch(() => [trendData.value, selectedYear.value], () => {
  if (trendData.value) {
    nextTick(() => {
      setTimeout(() => renderTrendChart(), 200)
    })
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  loadSlaughterLunar()
  loadTrendData()
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (slaughterLunarChart) {
    slaughterLunarChart.dispose()
    slaughterLunarChart = null
  }
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
})
</script>

<style scoped>
.slaughter-page {
  padding: 20px;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px; /* 缩小间距 */
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px; /* 缩小间距，横向两个图表共用边框 */
  border: 1px solid #e4e7ed; /* 共用边框 */
  border-radius: 4px;
  padding: 16px; /* 减少padding */
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-wrapper {
  /* 移除单独的边框和背景，因为已经在chart-row中设置了 */
  padding: 0;
}

.chart-box {
  /* 图表框：包含标题、图例、图表 */
  margin-bottom: 8px;
}

.info-box {
  /* 说明框：无背景色，位于图表框下方 */
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
  background-color: transparent;
}

.chart-title {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  line-height: 1.5;
}

.chart-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
