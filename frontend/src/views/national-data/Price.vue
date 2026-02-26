<template>
  <div class="price-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>A1. 价格（全国）</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <UpdateTimeBadge 
              :update-time="priceUpdateTime || spreadUpdateTime" 
              :last-data-date="priceUpdateTime || spreadUpdateTime" 
            />
          </div>
        </div>
      </template>

      <!-- 图表容器：两两一行 -->
      <div class="charts-container">
        <!-- 第一行 -->
        <div class="chart-row">
          <!-- (1) 全国猪价 -->
          <div class="chart-wrapper">
            <!-- 图表框 -->
            <div class="chart-box">
              <h3 class="chart-title">全国猪价</h3>
              <div v-if="loadingPrice" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!priceSeasonalityData || priceSeasonalityData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据">
                  <el-button type="primary" @click="handleGenerateSQL">生成INSERT SQL</el-button>
                </el-empty>
              </div>
              <div v-else>
                <div ref="priceSeasonalityChartRef" class="chart-container"></div>
              </div>
            </div>
            <!-- 说明框 -->
            <div class="info-box">
              <ChangeAnnotation
                :current-change="priceChanges.day5_change"
                :yoy-change="priceChanges.yoy_change"
                :day5-change="priceChanges.day5_change"
                :day10-change="priceChanges.day10_change"
                :day30-change="priceChanges.day30_change"
                :unit="priceSeasonalityData?.unit"
              />
              <DataSourceInfo
                :source-name="'钢联'"
                :update-date="formatUpdateDate(priceUpdateTime)"
              />
            </div>
          </div>

          <!-- (2) 标肥价差 -->
          <div class="chart-wrapper">
            <!-- 图表框 -->
            <div class="chart-box">
              <h3 class="chart-title">标肥价差</h3>
              <div v-if="loadingSpread" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!spreadSeasonalityData || spreadSeasonalityData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据">
                  <el-button type="primary" @click="handleGenerateSQL">生成INSERT SQL</el-button>
                </el-empty>
              </div>
              <div v-else>
                <div ref="spreadSeasonalityChartRef" class="chart-container"></div>
              </div>
            </div>
            <!-- 说明框 -->
            <div class="info-box">
              <ChangeAnnotation
                :current-change="spreadChanges.day5_change"
                :yoy-change="spreadChanges.yoy_change"
                :day5-change="spreadChanges.day5_change"
                :day10-change="spreadChanges.day10_change"
                :day30-change="spreadChanges.day30_change"
                :unit="spreadSeasonalityData?.unit"
              />
              <DataSourceInfo
                :source-name="'钢联'"
                :update-date="formatUpdateDate(spreadUpdateTime)"
              />
            </div>
          </div>
        </div>

        <!-- 第二行 -->
        <div class="chart-row">
          <!-- (3) 猪价&标肥价差 -->
          <div class="chart-wrapper">
            <!-- 图表框 -->
            <div class="chart-box">
              <div class="chart-title-row">
                <h3 class="chart-title">猪价&标肥价差</h3>
                <el-select v-model="selectedYear" size="small" @change="handleYearFilterChange" style="width: 120px">
                  <el-option
                    v-for="year in availableYears"
                    :key="year"
                    :label="`${year}年`"
                    :value="year"
                  />
                </el-select>
              </div>
              <div v-if="loadingPriceSpread" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!priceSpreadData || (priceSpreadData.price_data.length === 0 && priceSpreadData.spread_data.length === 0)" class="no-data-placeholder">
                <el-empty description="暂无数据">
                  <el-button type="primary" @click="handleGenerateSQL">生成INSERT SQL</el-button>
                </el-empty>
              </div>
              <div v-else>
                <div ref="priceSpreadChartRef" class="chart-container"></div>
              </div>
            </div>
            <!-- 说明框 -->
            <div class="info-box">
              <DataSourceInfo
                :source-name="'钢联'"
                :update-date="formatUpdateDate(priceUpdateTime || spreadUpdateTime)"
              />
            </div>
          </div>

          <!-- (4) 日度屠宰量（农历） -->
          <div class="chart-wrapper">
            <!-- 图表框 -->
            <div class="chart-box">
              <h3 class="chart-title">日度屠宰量（农历）</h3>
              <div v-if="loadingSlaughter" class="loading-placeholder">
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
            <!-- 说明框 -->
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
  getNationalPriceSeasonality,
  getFatStdSpreadSeasonality,
  getPriceAndSpread,
  getSlaughterLunar,
  getPriceChanges,
  type SeasonalityResponse,
  type PriceSpreadResponse,
  type PriceChangesResponse
} from '@/api/price-display'
import { downloadSQL, generateInsertSQL } from '@/utils/sql-generator'
import type { MetricConfig, SQLGenerationOptions } from '@/utils/sql-generator'
import { getYearColor, axisLabelDecimalFormatter, axisLabelHideMinMax } from '@/utils/chart-style'

// 加载状态
const loadingPrice = ref(false)
const loadingSpread = ref(false)
const loadingPriceSpread = ref(false)
const loadingSlaughter = ref(false)

// 数据
const priceSeasonalityData = ref<SeasonalityResponse | null>(null)
const spreadSeasonalityData = ref<SeasonalityResponse | null>(null)
const priceSpreadData = ref<PriceSpreadResponse | null>(null)
const slaughterLunarData = ref<SeasonalityResponse | null>(null)

// 涨跌数据
const priceChanges = ref<PriceChangesResponse>({
  current_value: null,
  latest_date: null,
  day5_change: null,
  day10_change: null,
  day30_change: null,
  unit: '元/公斤'
})

const spreadChanges = ref<PriceChangesResponse>({
  current_value: null,
  latest_date: null,
  day5_change: null,
  day10_change: null,
  day30_change: null,
  unit: '元/公斤'
})

// 更新时间
const priceUpdateTime = ref<string | null>(null)
const spreadUpdateTime = ref<string | null>(null)
const slaughterUpdateTime = ref<string | null>(null)

// 年度筛选（单选，默认去年）
const availableYears = ref<number[]>([])
const selectedYear = ref<number | null>(null)

// 图表引用
const priceSeasonalityChartRef = ref<HTMLDivElement>()
const spreadSeasonalityChartRef = ref<HTMLDivElement>()
const priceSpreadChartRef = ref<HTMLDivElement>()
const slaughterLunarChartRef = ref<HTMLDivElement>()

let priceSeasonalityChart: echarts.ECharts | null = null
let spreadSeasonalityChart: echarts.ECharts | null = null
let priceSpreadChart: echarts.ECharts | null = null
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

// 加载全国猪价季节性数据
const loadPriceSeasonality = async () => {
  loadingPrice.value = true
  try {
    const data = await getNationalPriceSeasonality()
    console.log('全国猪价季节性数据:', data)
    priceSeasonalityData.value = data
    priceUpdateTime.value = data.update_time
    
    // 加载涨跌数据
    const changes = await getPriceChanges('price')
    priceChanges.value = changes
    
    await nextTick()
    // 延迟渲染，确保DOM完全准备好
    setTimeout(() => {
      if (data.series && data.series.length > 0) {
        renderPriceSeasonalityChart()
      } else {
        console.warn('全国猪价数据为空')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载全国猪价季节性数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingPrice.value = false
  }
}

// 加载标肥价差季节性数据
const loadSpreadSeasonality = async () => {
  loadingSpread.value = true
  try {
    const data = await getFatStdSpreadSeasonality()
    console.log('标肥价差季节性数据:', data)
    spreadSeasonalityData.value = data
    spreadUpdateTime.value = data.update_time
    
    // 加载涨跌数据
    const changes = await getPriceChanges('spread')
    spreadChanges.value = changes
    
    await nextTick()
    // 延迟渲染，确保DOM完全准备好
    setTimeout(() => {
      if (data.series && data.series.length > 0) {
        renderSpreadSeasonalityChart()
      } else {
        console.warn('标肥价差数据为空')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载标肥价差季节性数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingSpread.value = false
  }
}

// 加载猪价和标肥价差数据
const loadPriceAndSpread = async () => {
  loadingPriceSpread.value = true
  try {
    // 加载所有年份的数据
    const data = await getPriceAndSpread(undefined)
    priceSpreadData.value = data
    availableYears.value = data.available_years
    
    // 初始化选中年份：默认选择去年（当前年份-1）
    if (selectedYear.value === null && availableYears.value.length > 0) {
      const currentYear = new Date().getFullYear()
      const lastYear = currentYear - 1
      // 如果去年在可用年份列表中，选择去年；否则选择最新的年份
      if (availableYears.value.includes(lastYear)) {
        selectedYear.value = lastYear
      } else {
        selectedYear.value = Math.max(...availableYears.value)
      }
    }
    
    await nextTick()
    // 延迟渲染，确保DOM完全准备好
    setTimeout(() => {
      renderPriceSpreadChart()
    }, 200)
  } catch (error: any) {
    console.error('加载猪价和标肥价差数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingPriceSpread.value = false
  }
}

// 加载日度屠宰量（农历）数据
const loadSlaughterLunar = async () => {
  loadingSlaughter.value = true
  try {
    const data = await getSlaughterLunar()
    console.log('日度屠宰量（农历）数据:', data)
    slaughterLunarData.value = data
    slaughterUpdateTime.value = data.update_time || data.latest_date
    
    await nextTick()
    // 延迟渲染，确保DOM完全准备好
    setTimeout(() => {
      if (data.series && data.series.length > 0) {
        renderSlaughterLunarChart()
      } else {
        console.warn('日度屠宰量（农历）数据为空，series数量:', data.series?.length || 0)
      }
    }, 200)
  } catch (error: any) {
    console.error('加载日度屠宰量数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingSlaughter.value = false
  }
}


// 渲染全国猪价季节性图表
const renderPriceSeasonalityChart = () => {
  if (!priceSeasonalityChartRef.value || !priceSeasonalityData.value || priceSeasonalityData.value.series.length === 0) {
    console.warn('渲染条件不满足:', {
      hasRef: !!priceSeasonalityChartRef.value,
      hasData: !!priceSeasonalityData.value,
      seriesLength: priceSeasonalityData.value?.series?.length || 0
    })
    return
  }
  
  if (priceSeasonalityChart) {
    priceSeasonalityChart.dispose()
    priceSeasonalityChart = null
  }
  
  // 确保容器有尺寸
  if (priceSeasonalityChartRef.value.offsetWidth === 0 || priceSeasonalityChartRef.value.offsetHeight === 0) {
    console.warn('图表容器尺寸为0，延迟渲染')
    setTimeout(() => renderPriceSeasonalityChart(), 100)
    return
  }
  
  priceSeasonalityChart = echarts.init(priceSeasonalityChartRef.value)
  
  // 收集所有唯一的month_day作为X轴
  const allMonthDays = new Set<string>()
  priceSeasonalityData.value.series.forEach(s => {
    s.data.forEach(d => {
      if (d.month_day) allMonthDays.add(d.month_day)
    })
  })
  const xAxisData = Array.from(allMonthDays).sort()
  
  // 为每个年份构建数据，对齐到X轴
  const series = priceSeasonalityData.value.series.map(s => {
    // 创建month_day到value的映射
    const valueMap = new Map<string, number | null>()
    s.data.forEach(d => {
      if (d.month_day) {
        valueMap.set(d.month_day, d.value)
      }
    })
    
    // 按照X轴顺序提取值
    const values = xAxisData.map(md => valueMap.get(md) ?? null)
    
    return {
      name: `${s.year}年`,
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: getYearColor(s.year) },
      connectNulls: true
    }
  })
  
  // 按数据范围设置 Y 轴，避免 0-10 空白（与屠宰量&价格一致）
  const allPriceValues = series.flatMap(s => s.data).filter(v => v !== null && v !== undefined) as number[]
  const pMin = allPriceValues.length > 0 ? Math.min(...allPriceValues) : 0
  const pMax = allPriceValues.length > 0 ? Math.max(...allPriceValues) : 30
  const pPadding = Math.max((pMax - pMin) * 0.08, 0.5)
  const yMinPrice = pMin - pPadding
  const yMaxPrice = pMax + pPadding

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
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}: <strong>${value}${priceSeasonalityData.value.unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: priceSeasonalityData.value.series.map(s => `${s.year}年`),
      top: 10,
      type: 'plain',
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
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
    },
    yAxis: {
      type: 'value',
      name: '价格',
      min: yMinPrice,
      max: yMaxPrice,
      axisLabel: { ...axisLabelHideMinMax, formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    series: series,
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }

  priceSeasonalityChart.setOption(option)

  // 图例切换年份时重新计算 Y 轴范围，使坐标轴自适应可见数据
  const updateYAxisFromVisibleSeries = (selected: Record<string, boolean>) => {
    if (!priceSeasonalityChart) return
    const visibleData: number[] = []
    series.forEach(s => {
      const isVisible = selected[s.name] !== false
      if (isVisible) {
        s.data.forEach(v => {
          if (v != null && typeof v === 'number') visibleData.push(v)
        })
      }
    })
    const pMin = visibleData.length > 0 ? Math.min(...visibleData) : 0
    const pMax = visibleData.length > 0 ? Math.max(...visibleData) : 30
    const pPadding = Math.max((pMax - pMin) * 0.08, 0.5)
    const newMin = pMin - pPadding
    const newMax = pMax + pPadding
    priceSeasonalityChart.setOption({ yAxis: { min: newMin, max: newMax } })
  }

  priceSeasonalityChart.off('legendselectchanged')
  priceSeasonalityChart.on('legendselectchanged', (params: { selected?: Record<string, boolean> }) => {
    updateYAxisFromVisibleSeries(params.selected || {})
  })

  // 确保图表正确渲染
  setTimeout(() => {
    priceSeasonalityChart?.resize()
  }, 100)
}

// 渲染标肥价差季节性图表
const renderSpreadSeasonalityChart = () => {
  if (!spreadSeasonalityChartRef.value || !spreadSeasonalityData.value || spreadSeasonalityData.value.series.length === 0) {
    console.warn('渲染条件不满足:', {
      hasRef: !!spreadSeasonalityChartRef.value,
      hasData: !!spreadSeasonalityData.value,
      seriesLength: spreadSeasonalityData.value?.series?.length || 0
    })
    return
  }
  
  if (spreadSeasonalityChart) {
    spreadSeasonalityChart.dispose()
    spreadSeasonalityChart = null
  }
  
  // 确保容器有尺寸
  if (spreadSeasonalityChartRef.value.offsetWidth === 0 || spreadSeasonalityChartRef.value.offsetHeight === 0) {
    console.warn('图表容器尺寸为0，延迟渲染')
    setTimeout(() => renderSpreadSeasonalityChart(), 100)
    return
  }
  
  spreadSeasonalityChart = echarts.init(spreadSeasonalityChartRef.value)
  
  // 收集所有唯一的month_day作为X轴
  const allMonthDays = new Set<string>()
  spreadSeasonalityData.value.series.forEach(s => {
    s.data.forEach(d => {
      if (d.month_day) allMonthDays.add(d.month_day)
    })
  })
  const xAxisData = Array.from(allMonthDays).sort()
  
  // 为每个年份构建数据，对齐到X轴
  const series = spreadSeasonalityData.value.series.map(s => {
    // 创建month_day到value的映射
    const valueMap = new Map<string, number | null>()
    s.data.forEach(d => {
      if (d.month_day) {
        valueMap.set(d.month_day, d.value)
      }
    })
    
    // 按照X轴顺序提取值
    const values = xAxisData.map(md => valueMap.get(md) ?? null)
    
    return {
      name: `${s.year}年`,
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: getYearColor(s.year) },
      connectNulls: true
    }
  })
  
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
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}: <strong>${value}${spreadSeasonalityData.value.unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: spreadSeasonalityData.value.series.map(s => `${s.year}年`),
      top: 10,
      type: 'plain',
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
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
    },
    yAxis: {
      type: 'value',
      name: '价差',
      axisLabel: { ...axisLabelHideMinMax, formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    series: series,
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
  
  spreadSeasonalityChart.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    spreadSeasonalityChart?.resize()
  }, 100)
}

// 渲染猪价和标肥价差图表
const renderPriceSpreadChart = () => {
  if (!priceSpreadChartRef.value || !priceSpreadData.value) {
    console.warn('渲染条件不满足:', {
      hasRef: !!priceSpreadChartRef.value,
      hasData: !!priceSpreadData.value
    })
    return
  }
  
  if (priceSpreadChart) {
    priceSpreadChart.dispose()
    priceSpreadChart = null
  }
  
  // 确保容器有尺寸
  if (priceSpreadChartRef.value.offsetWidth === 0 || priceSpreadChartRef.value.offsetHeight === 0) {
    console.warn('图表容器尺寸为0，延迟渲染')
    setTimeout(() => renderPriceSpreadChart(), 100)
    return
  }
  
  priceSpreadChart = echarts.init(priceSpreadChartRef.value)
  
  // 统一日期为 YYYY-MM-DD，避免 API 返回带时间或时区时与价格日期不一致导致价差断联
  const normDate = (s: string) => s.slice(0, 10)

  // 根据选中的年份过滤数据（如果已选择年份）
  const filteredPriceData = selectedYear.value !== null
    ? priceSpreadData.value.price_data.filter(item => item.year === selectedYear.value)
    : [...priceSpreadData.value.price_data]
  const filteredSpreadData = selectedYear.value !== null
    ? priceSpreadData.value.spread_data.filter(item => item.year === selectedYear.value)
    : [...priceSpreadData.value.spread_data]
  
  // 按日期排序
  filteredPriceData.sort((a, b) => a.date.localeCompare(b.date))
  filteredSpreadData.sort((a, b) => a.date.localeCompare(b.date))
  
  // 构建X轴：合并所有日期并排序（用统一格式，避免同一天因格式不同被拆成两点）
  const allDates = new Set<string>()
  filteredPriceData.forEach(item => allDates.add(normDate(item.date)))
  filteredSpreadData.forEach(item => allDates.add(normDate(item.date)))
  const sortedDates = Array.from(allDates).sort()
  
  // 格式化X轴标签（MM-DD格式）
  const xAxisData = sortedDates.map(dateStr => {
    const date = new Date(dateStr)
    return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  })
  
  // 创建日期到值的映射（键统一为 YYYY-MM-DD）
  const priceMap = new Map<string, number | null>()
  filteredPriceData.forEach(item => {
    priceMap.set(normDate(item.date), item.value)
  })
  const spreadMap = new Map<string, number | null>()
  filteredSpreadData.forEach(item => {
    spreadMap.set(normDate(item.date), item.value)
  })
  
  // 构建两个指标系列（缺数用 null，connectNulls 使曲线连续）
  const series: any[] = []
  const toNull = (v: number | null | undefined) => (v === undefined || v === null ? null : v)

  // 价格指标（左Y轴）
  const priceValues = sortedDates.map(date => toNull(priceMap.get(date)))
  if (priceValues.some(v => v !== null)) {
    series.push({
      name: '价格',
      type: 'line',
      data: priceValues,
      yAxisIndex: 0,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: '#409EFF' },
      connectNulls: true  // 缺数时连线不断开
    })
  }

  // 价差指标（右Y轴）
  const spreadValues = sortedDates.map(date => toNull(spreadMap.get(date)))
  if (spreadValues.some(v => v !== null)) {
    series.push({
      name: '标肥价差',
      type: 'line',
      data: spreadValues,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2, type: 'dashed' },
      itemStyle: { color: '#67C23A' },
      connectNulls: true  // 缺数时连线不断开
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
          if (!param.seriesName) return
          const value = param.value !== null && param.value !== undefined 
            ? param.value.toFixed(2) 
            : '-'
          const unit = param.seriesName === '价格' ? '元/公斤' : '元/公斤'
          const yAxisName = param.series?.yAxisIndex === 1 ? '（右轴）' : '（左轴）'
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
      type: 'plain',
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
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '价格',
        position: 'left',
        axisLabel: { ...axisLabelHideMinMax, formatter: (v: number) => axisLabelDecimalFormatter(v) }
      },
      {
        type: 'value',
        name: '价差',
        position: 'right',
        axisLabel: { ...axisLabelHideMinMax, formatter: (v: number) => axisLabelDecimalFormatter(v) }
      }
    ],
    series: series,
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
  
  // notMerge: true 确保 connectNulls 等配置完整生效，避免被合并覆盖导致价差断联
  priceSpreadChart.setOption(option, { notMerge: true })
  
  // 确保图表正确渲染
  setTimeout(() => {
    priceSpreadChart?.resize()
  }, 100)
}

// 渲染日度屠宰量（农历）图表
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
      data: series.map(s => s.name),
      top: 10,
      type: 'plain',
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
      axisLabel: { ...axisLabelHideMinMax, formatter: (v: number) => axisLabelDecimalFormatter(v) }
    },
    series: series,
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
  
  slaughterLunarChart.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    slaughterLunarChart?.resize()
  }, 100)
}

// 年度筛选变化
const handleYearFilterChange = () => {
  // 重新渲染图表，根据选中的年份过滤数据
  if (priceSpreadData.value) {
    nextTick(() => {
      setTimeout(() => renderPriceSpreadChart(), 100)
    })
  }
}

// 生成SQL
const handleGenerateSQL = async () => {
  try {
    const configs: MetricConfig[] = [
      {
        metric_key: 'GL_D_PRICE_NATION',
        metric_name: '全国出栏均价',
        source_code: 'GANGLIAN',
        sheet_name: '分省区猪价',
        unit: '元/公斤',
        tags: { scope: 'nation' }
      },
      {
        metric_key: 'GL_D_FAT_STD_SPREAD',
        metric_name: '标肥价差',
        source_code: 'GANGLIAN',
        sheet_name: '肥标价差',
        unit: '元/公斤'
      },
      {
        metric_key: 'YY_D_SLAUGHTER_TOTAL',
        metric_name: '日度屠宰量',
        source_code: 'YONGYI',
        sheet_name: '价格+宰量',
        unit: '头',
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
  downloadSQL(generatedSQL.value, `price_data_${new Date().toISOString().split('T')[0]}.sql`)
  ElMessage.success('SQL文件已下载')
}


// 窗口大小变化时调整图表
const handleResize = () => {
  priceSeasonalityChart?.resize()
  spreadSeasonalityChart?.resize()
  priceSpreadChart?.resize()
  slaughterLunarChart?.resize()
}

// 监听数据变化，自动重新渲染图表
watch(() => priceSeasonalityData.value, (newVal) => {
  if (newVal && newVal.series && newVal.series.length > 0) {
    nextTick(() => {
      setTimeout(() => renderPriceSeasonalityChart(), 200)
    })
  }
}, { deep: true })

watch(() => spreadSeasonalityData.value, (newVal) => {
  if (newVal && newVal.series && newVal.series.length > 0) {
    nextTick(() => {
      setTimeout(() => renderSpreadSeasonalityChart(), 200)
    })
  }
}, { deep: true })

watch(() => [priceSpreadData.value, selectedYear.value], () => {
  if (priceSpreadData.value) {
    nextTick(() => {
      setTimeout(() => renderPriceSpreadChart(), 200)
    })
  }
}, { deep: true })

watch(() => slaughterLunarData.value, (newVal) => {
  if (newVal && newVal.series && newVal.series.length > 0) {
    nextTick(() => {
      setTimeout(() => renderSlaughterLunarChart(), 200)
    })
  }
}, { deep: true })

onMounted(() => {
  loadPriceSeasonality()
  loadSpreadSeasonality()
  loadPriceAndSpread()
  loadSlaughterLunar()
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (priceSeasonalityChart) {
    priceSeasonalityChart.dispose()
    priceSeasonalityChart = null
  }
  if (spreadSeasonalityChart) {
    spreadSeasonalityChart.dispose()
    spreadSeasonalityChart = null
  }
  if (priceSpreadChart) {
    priceSpreadChart.dispose()
    priceSpreadChart = null
  }
  if (slaughterLunarChart) {
    slaughterLunarChart.dispose()
    slaughterLunarChart = null
  }
})
</script>

<style scoped>
.price-page {
  padding: 4px;
}

.price-page :deep(.el-card__body) {
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
