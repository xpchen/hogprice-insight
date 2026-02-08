<template>
  <div class="fat-std-spread-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>A4. 标肥价差（分省区）</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <UpdateTimeBadge 
              v-if="latestUpdateTime"
              :update-time="latestUpdateTime" 
              :last-data-date="latestUpdateTime" 
            />
          </div>
        </div>
      </template>

      <!-- 加载中 -->
      <div v-if="loadingProvinces" class="loading-placeholder">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span style="margin-left: 10px">加载省区列表...</span>
      </div>

      <!-- 省区列表为空 -->
      <el-empty v-else-if="!provinces || provinces.length === 0" description="暂无省区数据" />

      <!-- 图表网格：每行2个图表 -->
      <div v-else class="charts-grid">
        <div 
          v-for="province in provinces" 
          :key="province.province_name"
          class="chart-wrapper"
        >
          <h3 class="chart-title">标肥价差：{{ province.province_name }}</h3>
          <div v-if="loadingCharts[province.province_name]" class="loading-placeholder">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span style="margin-left: 10px">加载中...</span>
          </div>
          <div v-else-if="!chartData[province.province_name] || !chartData[province.province_name].series || chartData[province.province_name].series.length === 0" class="no-data-placeholder">
            <el-empty description="暂无数据" :image-size="80" />
          </div>
          <div v-else>
            <div class="chart-box">
              <div 
                :ref="el => setChartRef(province.province_name, el)"
                class="chart-container"
              ></div>
            </div>
            <div class="info-box">
              <ChangeAnnotation
                :day5-change="changesData[province.province_name]?.day5_change"
                :day10-change="changesData[province.province_name]?.day10_change"
                :unit="chartData[province.province_name]?.unit || '元/公斤'"
              />
              <DataSourceInfo
                :source-name="'钢联'"
                :update-date="formatUpdateDate(latestUpdateTime)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import UpdateTimeBadge from '@/components/UpdateTimeBadge.vue'
import ChangeAnnotation from '@/components/ChangeAnnotation.vue'
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import {
  getFatStdSpreadProvinces,
  getFatStdSpreadProvinceSeasonality,
  getFatStdSpreadProvinceChanges,
  type ProvinceSpreadInfo,
  type SeasonalityResponse,
  type ProvinceChangesResponse
} from '@/api/price-display'

// 省区列表
const provinces = ref<ProvinceSpreadInfo[]>([])
const loadingProvinces = ref(false)

// 图表数据
const chartData = ref<Record<string, SeasonalityResponse>>({})
const changesData = ref<Record<string, ProvinceChangesResponse>>({})
const loadingCharts = ref<Record<string, boolean>>({})

// 图表实例
const chartInstances = ref<Record<string, echarts.ECharts>>({})
const chartRefs = ref<Record<string, HTMLElement | null>>({})

// 最新更新时间
const latestUpdateTime = ref<string | null>(null)

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

// 渲染队列控制
const renderQueue = ref<string[]>([])
const isRendering = ref(false)

// 添加到渲染队列
const addToRenderQueue = (provinceName: string) => {
  // 如果已经在队列中，不重复添加
  if (renderQueue.value.includes(provinceName)) {
    return
  }
  renderQueue.value.push(provinceName)
  // 如果当前没有在渲染，开始处理队列
  if (!isRendering.value) {
    processRenderQueue()
  }
}

// 处理渲染队列，逐个渲染图表
const processRenderQueue = async () => {
  if (isRendering.value || renderQueue.value.length === 0) {
    return
  }
  
  isRendering.value = true
  
  while (renderQueue.value.length > 0) {
    const provinceName = renderQueue.value.shift()!
    
    // 等待DOM准备好
    await nextTick()
    
    // 检查数据是否存在
    const data = chartData.value[provinceName]
    if (!data || !data.series || data.series.length === 0) {
      continue
    }
    
    // 等待图表容器准备好
    let retries = 0
    while (retries < 10) {
      const chartEl = chartRefs.value[provinceName]
      if (chartEl && chartEl.offsetWidth > 0 && chartEl.offsetHeight > 0) {
        // 容器准备好了，渲染图表
        renderChart(provinceName)
        break
      }
      // 等待一段时间后重试
      await new Promise(resolve => setTimeout(resolve, 100))
      retries++
    }
    
    // 每个图表渲染之间延迟200ms，让用户看到逐个出现的效果
    if (renderQueue.value.length > 0) {
      await new Promise(resolve => setTimeout(resolve, 200))
    }
  }
  
  isRendering.value = false
}

// 设置图表引用
const setChartRef = (provinceName: string, el: HTMLElement | null) => {
  if (el) {
    chartRefs.value[provinceName] = el
    // 如果数据已经加载完成且不在队列中，添加到渲染队列
    const data = chartData.value[provinceName]
    if (data && data.series && data.series.length > 0 && !chartInstances.value[provinceName]) {
      addToRenderQueue(provinceName)
    }
  }
}

// 加载省区列表
const loadProvinces = async () => {
  try {
    loadingProvinces.value = true
    const response = await getFatStdSpreadProvinces()
    provinces.value = response.provinces
    latestUpdateTime.value = response.provinces
      .map(p => p.latest_date)
      .filter(d => d)
      .sort()
      .reverse()[0] || null
    
    // 并行加载所有省区的数据，不等待完成
    response.provinces.forEach(province => {
      loadProvinceData(province.province_name)
    })
  } catch (error: any) {
    console.error('加载省区列表失败:', error)
    ElMessage.error('加载省区列表失败: ' + (error.message || '未知错误'))
  } finally {
    loadingProvinces.value = false
  }
}

// 加载单个省区的数据
const loadProvinceData = async (provinceName: string) => {
  try {
    loadingCharts.value[provinceName] = true
    
    // 并行加载季节性数据和涨跌数据
    const [seasonalityData, changesResponse] = await Promise.all([
      getFatStdSpreadProvinceSeasonality(provinceName),
      getFatStdSpreadProvinceChanges(provinceName)
    ])
    
    chartData.value[provinceName] = seasonalityData
    changesData.value[provinceName] = changesResponse
    
    // 调试日志
    console.log(`[${provinceName}] 数据加载完成:`, {
      seriesCount: seasonalityData.series?.length || 0,
      hasData: seasonalityData.series && seasonalityData.series.length > 0,
      unit: seasonalityData.unit
    })
    
    // 如果有数据，添加到渲染队列
    if (seasonalityData.series && seasonalityData.series.length > 0) {
      addToRenderQueue(provinceName)
    }
  } catch (error: any) {
    console.error(`加载${provinceName}数据失败:`, error)
    console.error(`错误详情:`, {
      provinceName,
      error: error.message,
      response: error.response?.data,
      status: error.response?.status
    })
    // 不显示错误消息，让用户看到"暂无数据"提示
    // ElMessage.error(`加载${provinceName}数据失败: ` + (error.message || '未知错误'))
  } finally {
    loadingCharts.value[provinceName] = false
  }
}

// 渲染图表
const renderChart = (provinceName: string) => {
  const chartEl = chartRefs.value[provinceName]
  if (!chartEl) {
    console.warn(`[${provinceName}] 图表容器不存在`)
    return
  }
  
  const data = chartData.value[provinceName]
  if (!data || !data.series || data.series.length === 0) {
    console.warn(`[${provinceName}] 数据不存在或为空`)
    return
  }
  
  // 如果已经渲染过，跳过
  if (chartInstances.value[provinceName]) {
    return
  }
  
  // 确保容器有尺寸
  if (chartEl.offsetWidth === 0 || chartEl.offsetHeight === 0) {
    console.warn(`[${provinceName}] 图表容器尺寸为0`)
    return
  }
  
  // 创建新实例
  const chart = echarts.init(chartEl)
  chartInstances.value[provinceName] = chart
  
  // 准备数据
  const years = data.series.map(s => s.year)
  const allDates = new Set<string>()
  data.series.forEach(series => {
    series.data.forEach(point => {
      allDates.add(point.month_day)
    })
  })
  const sortedDates = Array.from(allDates).sort()
  
  // 计算最近三年（用于颜色规则）
  const sortedYears = [...data.series.map(s => s.year)].sort((a, b) => b - a)
  const recentThreeYears = new Set(sortedYears.slice(0, 3))
  
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
  
  // 计算Y轴范围（自动调整）
  const allValues = data.series.flatMap(s => s.data.map(p => p.value)).filter(v => v !== null && v !== undefined) as number[]
  const yMin = allValues.length > 0 ? Math.min(...allValues) : 0
  const yMax = allValues.length > 0 ? Math.max(...allValues) : 100
  const yPadding = (yMax - yMin) * 0.1 // 10% padding
  
  // 构建series
  const series = data.series.map((s, index) => {
    const yearData = new Map(s.data.map(p => [p.month_day, p.value]))
    const values = sortedDates.map(date => yearData.get(date) ?? null)
    
    // 最近三年有颜色，其他年份灰色
    const isRecentYear = recentThreeYears.has(s.year)
    const lineColor = isRecentYear ? getYearColor(s.year) : '#D3D3D3'
    
    return {
      name: `${s.year}年`,
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
  
  // 配置选项
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            result += `${param.seriesName}: ${param.value.toFixed(2)}${data.unit}<br/>`
          }
        })
        return result
      }
    },
    legend: {
      data: years.map(y => `${y}年`),
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
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: sortedDates,
      // X轴不显示标签（默认时间轴）
      name: '',
      axisLabel: {
        rotate: 45,
        interval: Math.floor(sortedDates.length / 10)
      }
    },
    yAxis: {
      type: 'value',
      // Y轴不显示单位
      name: '',
      // 自动调整范围
      min: yMin - yPadding,
      max: yMax + yPadding,
      scale: false,
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: series as any
  }
  
  chart.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    chart.resize()
  }, 100)
}


// 监听chartData变化，当数据加载完成时，添加到渲染队列
watch(
  () => chartData.value,
  () => {
    // 遍历所有有数据的省份，添加到渲染队列
    for (const province of provinces.value) {
      const provinceName = province.province_name
      const data = chartData.value[provinceName]
      
      // 如果有数据且图表实例不存在，添加到渲染队列
      if (data && data.series && data.series.length > 0 && !chartInstances.value[provinceName]) {
        addToRenderQueue(provinceName)
      }
    }
  },
  { deep: true, immediate: false }
)

// 监听provinces变化，当省份列表加载完成后，检查是否有需要渲染的图表
watch(
  () => provinces.value.length,
  () => {
    if (provinces.value.length > 0) {
      nextTick(() => {
        // 检查所有省份的图表是否需要渲染
        for (const province of provinces.value) {
          const provinceName = province.province_name
          const data = chartData.value[provinceName]
          
          if (data && data.series && data.series.length > 0 && !chartInstances.value[provinceName]) {
            addToRenderQueue(provinceName)
          }
        }
      })
    }
  }
)

// 响应式调整
let resizeHandler: (() => void) | null = null

onMounted(() => {
  loadProvinces()
  
  // 添加窗口resize监听
  resizeHandler = () => {
    Object.values(chartInstances.value).forEach(chart => {
      if (chart) {
        chart.resize()
      }
    })
  }
  window.addEventListener('resize', resizeHandler)
})

// 组件卸载前清理
onBeforeUnmount(() => {
  // 移除resize监听
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  
  // 销毁所有图表实例
  Object.values(chartInstances.value).forEach(chart => {
    if (chart) {
      chart.dispose()
    }
  })
})
</script>

<style scoped>
.fat-std-spread-page {
  padding: 20px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-wrapper {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 16px;
  min-height: 400px;
}

.chart-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 16px 0;
  color: #303133;
  text-align: center;
}

.chart-container {
  width: 100%;
  height: 350px;
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

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 350px;
  color: #909399;
}

.no-data-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 350px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
