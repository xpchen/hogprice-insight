<template>
  <div class="weight-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>A2. 均重（全国）</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <UpdateTimeBadge 
              :update-time="updateTime" 
              :last-data-date="updateTime" 
            />
          </div>
        </div>
      </template>

      <!-- 图表容器：两两一行 -->
      <div class="charts-container">
        <!-- 第一行 -->
        <div class="chart-row">
          <!-- 图1：宰前均重 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">宰前均重【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!hasPreSlaughterWeight" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="preSlaughterChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="preSlaughterCurrentChange"
                :yoy-change="preSlaughterYoyChange"
                unit="kg"
              />
            </div>
          </div>

          <!-- 图2：出栏均重 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">出栏均重【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!hasOutWeight" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="outWeightChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="outWeightCurrentChange"
                :yoy-change="outWeightYoyChange"
                unit="kg"
              />
            </div>
          </div>
        </div>

        <!-- 第二行 -->
        <div class="chart-row">
          <!-- 图3：规模场 出栏均重 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">规模场 出栏均重【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!hasScaleFarmWeight" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="scaleFarmChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="scaleFarmCurrentChange"
                :yoy-change="scaleFarmYoyChange"
                unit="kg"
              />
            </div>
          </div>

          <!-- 图4：散户 出栏均重 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">散户 出栏均重【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!hasRetailWeight" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="retailChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="retailCurrentChange"
                :yoy-change="retailYoyChange"
                unit="kg"
              />
            </div>
          </div>
        </div>

        <!-- 第三行 -->
        <div class="chart-row">
          <!-- 图5：90Kg出栏占比 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">90Kg出栏占比【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!has90kgRatio" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="ratio90kgChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="ratio90kgCurrentChange"
                :yoy-change="ratio90kgYoyChange"
                unit="%"
              />
            </div>
          </div>

          <!-- 图6：150Kg出栏占重 -->
          <div class="chart-wrapper">
            <h3 class="chart-title">150Kg出栏占重【数据来源：涌益咨询 周度数据】</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!has150kgRatio" class="no-data-placeholder">
              <el-empty description="暂无数据">
                <el-button type="primary" @click="handleImportData">导入数据</el-button>
              </el-empty>
            </div>
            <div v-else>
              <div ref="ratio150kgChartRef" class="chart-container"></div>
              <ChangeAnnotation
                :current-change="ratio150kgCurrentChange"
                :yoy-change="ratio150kgYoyChange"
                unit="%"
              />
            </div>
          </div>
        </div>
      </div>
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
import { getWeightData } from '@/api/national-data'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const updateTime = ref<string | null>(null)

// 数据状态
const hasPreSlaughterWeight = ref(false)
const hasOutWeight = ref(false)
const hasScaleFarmWeight = ref(false)
const hasRetailWeight = ref(false)
const has90kgRatio = ref(false)
const has150kgRatio = ref(false)

// 图表引用
const preSlaughterChartRef = ref<HTMLDivElement>()
const outWeightChartRef = ref<HTMLDivElement>()
const scaleFarmChartRef = ref<HTMLDivElement>()
const retailChartRef = ref<HTMLDivElement>()
const ratio90kgChartRef = ref<HTMLDivElement>()
const ratio150kgChartRef = ref<HTMLDivElement>()

// 涨跌数据
const preSlaughterCurrentChange = ref<number | null>(null)
const preSlaughterYoyChange = ref<number | null>(null)
const outWeightCurrentChange = ref<number | null>(null)
const outWeightYoyChange = ref<number | null>(null)
const scaleFarmCurrentChange = ref<number | null>(null)
const scaleFarmYoyChange = ref<number | null>(null)
const retailCurrentChange = ref<number | null>(null)
const retailYoyChange = ref<number | null>(null)
const ratio90kgCurrentChange = ref<number | null>(null)
const ratio90kgYoyChange = ref<number | null>(null)
const ratio150kgCurrentChange = ref<number | null>(null)
const ratio150kgYoyChange = ref<number | null>(null)

// 计算涨跌
const calculateChanges = (data: any[]) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return { currentChange: null, yoyChange: null }
  }
  
  // 按period_end排序，获取最新数据
  const sortedData = [...data].sort((a, b) => {
    const dateA = new Date(a.period_end || a.obs_date || 0).getTime()
    const dateB = new Date(b.period_end || b.obs_date || 0).getTime()
    return dateB - dateA
  })
  
  const latest = sortedData[0]
  const latestDate = new Date(latest.period_end || latest.obs_date)
  const latestYear = latestDate.getFullYear()
  const latestWeek = getWeekOfYear(latest.period_end || latest.obs_date)
  
  // 本期涨跌：与上一期比较
  let currentChange: number | null = null
  if (sortedData.length > 1) {
    const prev = sortedData[1]
    if (latest.value !== null && prev.value !== null) {
      currentChange = latest.value - prev.value
    }
  }
  
  // 较去年同期涨跌：找到去年同一周的数据
  let yoyChange: number | null = null
  const lastYearSameWeek = sortedData.find(item => {
    const itemDate = new Date(item.period_end || item.obs_date)
    const itemYear = itemDate.getFullYear()
    const itemWeek = getWeekOfYear(item.period_end || item.obs_date)
    return itemYear === latestYear - 1 && itemWeek === latestWeek
  })
  
  if (lastYearSameWeek && latest.value !== null && lastYearSameWeek.value !== null) {
    yoyChange = latest.value - lastYearSameWeek.value
  }
  
  return { currentChange, yoyChange }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 查询最近3年的数据
    const endDate = new Date()
    const startDate = new Date()
    startDate.setFullYear(endDate.getFullYear() - 3)
    
    const result = await getWeightData(
      startDate.toISOString().split('T')[0],
      endDate.toISOString().split('T')[0]
    )
    
    hasPreSlaughterWeight.value = result.preSlaughterWeight.length > 0
    hasOutWeight.value = result.outWeight.length > 0
    hasScaleFarmWeight.value = result.scaleFarmWeight.length > 0
    hasRetailWeight.value = result.retailWeight.length > 0
    has90kgRatio.value = result.weight90kgRatio.length > 0
    has150kgRatio.value = result.weight150kgRatio.length > 0
    
    // 计算涨跌
    const preSlaughterChanges = calculateChanges(result.preSlaughterWeight)
    preSlaughterCurrentChange.value = preSlaughterChanges.currentChange
    preSlaughterYoyChange.value = preSlaughterChanges.yoyChange
    
    const outWeightChanges = calculateChanges(result.outWeight)
    outWeightCurrentChange.value = outWeightChanges.currentChange
    outWeightYoyChange.value = outWeightChanges.yoyChange
    
    const scaleFarmChanges = calculateChanges(result.scaleFarmWeight)
    scaleFarmCurrentChange.value = scaleFarmChanges.currentChange
    scaleFarmYoyChange.value = scaleFarmChanges.yoyChange
    
    const retailChanges = calculateChanges(result.retailWeight)
    retailCurrentChange.value = retailChanges.currentChange
    retailYoyChange.value = retailChanges.yoyChange
    
    const ratio90kgChanges = calculateChanges(result.weight90kgRatio)
    ratio90kgCurrentChange.value = ratio90kgChanges.currentChange
    ratio90kgYoyChange.value = ratio90kgChanges.yoyChange
    
    const ratio150kgChanges = calculateChanges(result.weight150kgRatio)
    ratio150kgCurrentChange.value = ratio150kgChanges.currentChange
    ratio150kgYoyChange.value = ratio150kgChanges.yoyChange
    
    // 更新更新时间（以图表时间为准）
    let latestUpdateTime: string | null = null
    const allData = [
      ...result.preSlaughterWeight,
      ...result.outWeight,
      ...result.scaleFarmWeight,
      ...result.retailWeight,
      ...result.weight90kgRatio,
      ...result.weight150kgRatio
    ]
    if (allData.length > 0) {
      const sortedAll = [...allData].sort((a, b) => {
        const dateA = new Date(a.period_end || a.obs_date || 0).getTime()
        const dateB = new Date(b.period_end || b.obs_date || 0).getTime()
        return dateB - dateA
      })
      const latest = sortedAll[0]
      const latestDate = new Date(latest.period_end || latest.obs_date)
      latestUpdateTime = `${latestDate.getFullYear()}-${String(latestDate.getMonth() + 1).padStart(2, '0')}-${String(latestDate.getDate()).padStart(2, '0')}`
    }
    updateTime.value = latestUpdateTime
    
    // 渲染图表
    await nextTick()
    setTimeout(() => {
      if (hasPreSlaughterWeight.value && preSlaughterChartRef.value) {
        renderChart(preSlaughterChartRef.value, result.preSlaughterWeight, '宰前均重', 'kg', { value: preSlaughterChart })
      }
      if (hasOutWeight.value && outWeightChartRef.value) {
        renderChart(outWeightChartRef.value, result.outWeight, '出栏均重', 'kg', { value: outWeightChart })
      }
      if (hasScaleFarmWeight.value && scaleFarmChartRef.value) {
        renderChart(scaleFarmChartRef.value, result.scaleFarmWeight, '规模场出栏均重', 'kg', { value: scaleFarmChart })
      }
      if (hasRetailWeight.value && retailChartRef.value) {
        renderChart(retailChartRef.value, result.retailWeight, '散户出栏均重', 'kg', { value: retailChart })
      }
      if (has90kgRatio.value && ratio90kgChartRef.value) {
        renderChart(ratio90kgChartRef.value, result.weight90kgRatio, '90Kg出栏占比', '%', { value: ratio90kgChart })
      }
      if (has150kgRatio.value && ratio150kgChartRef.value) {
        renderChart(ratio150kgChartRef.value, result.weight150kgRatio, '150Kg出栏占重', '%', { value: ratio150kgChart })
      }
    }, 200)
    
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 图表实例
let preSlaughterChart: echarts.ECharts | null = null
let outWeightChart: echarts.ECharts | null = null
let scaleFarmChart: echarts.ECharts | null = null
let retailChart: echarts.ECharts | null = null
let ratio90kgChart: echarts.ECharts | null = null
let ratio150kgChart: echarts.ECharts | null = null

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

// 渲染图表（周度季节性，1-52周）
const renderChart = (chartRef: HTMLDivElement, data: any[], title: string, unit: string = '', chartInstanceRef: { value: echarts.ECharts | null }) => {
  if (!chartRef) return
  
  // 如果已有实例，先销毁
  if (chartInstanceRef.value) {
    chartInstanceRef.value.dispose()
    chartInstanceRef.value = null
  }
  
  // 确保容器有尺寸
  if (chartRef.offsetWidth === 0 || chartRef.offsetHeight === 0) {
    setTimeout(() => renderChart(chartRef, data, title, unit, chartInstanceRef), 100)
    return
  }
  
  const chartInstance = echarts.init(chartRef)
  chartInstanceRef.value = chartInstance
  
  // 处理周度数据，按1-52周对齐
  const weekData = data.map(item => ({
    week: getWeekOfYear(item.period_end || item.obs_date),
    value: item.value,
    year: new Date(item.period_end || item.obs_date).getFullYear()
  }))
  
  // 按年份分组
  const years = [...new Set(weekData.map(d => d.year))].sort((a, b) => b - a) // 降序排列
  
  const series = years.map(year => {
    const yearData = weekData.filter(d => d.year === year)
    const values = Array(52).fill(null)
    yearData.forEach(d => {
      if (d.week >= 1 && d.week <= 52) {
        values[d.week - 1] = d.value
      }
    })
    return {
      name: `${year}年`,
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: getYearColor(year) },
      connectNulls: false
    }
  })
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `<div style="margin-bottom: 4px;"><strong>第${params[0].axisValue}周</strong></div>`
        params.forEach((param: any) => {
          const value = param.value !== null && param.value !== undefined 
            ? param.value.toFixed(2) 
            : '-'
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;width:10px;height:10px;background-color:${param.color};border-radius:50%;margin-right:5px;"></span>
            ${param.seriesName}: <strong>${value}${unit}</strong>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: years.map(y => `${y}年`),
      top: 10,
      type: 'scroll',
      orient: 'horizontal'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 52 }, (_, i) => i + 1),
      name: '周序号（1-52周）',
      nameLocation: 'middle',
      nameGap: 30,
      axisLabel: {
        formatter: (value: number) => {
          // 只显示部分标签，避免过于拥挤
          if (value % 4 === 0 || value === 1 || value === 52) {
            return value.toString()
          }
          return ''
        }
      }
    },
    yAxis: {
      type: 'value',
      name: unit ? `${title}(${unit})` : title,
      nameLocation: 'end',
      nameGap: 20
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
  
  chartInstance.setOption(option)
  
  // 确保图表正确渲染
  setTimeout(() => {
    chartInstance.resize()
  }, 100)
}

// 导入数据
const handleImportData = () => {
  router.push('/data-ingest')
}

// 窗口大小变化时调整图表
const handleResize = () => {
  preSlaughterChart?.resize()
  outWeightChart?.resize()
  scaleFarmChart?.resize()
  retailChart?.resize()
  ratio90kgChart?.resize()
  ratio150kgChart?.resize()
}

// 获取一年中的第几周
const getWeekOfYear = (dateStr: string): number => {
  const date = new Date(dateStr)
  const start = new Date(date.getFullYear(), 0, 1)
  const days = Math.floor((date.getTime() - start.getTime()) / (24 * 60 * 60 * 1000))
  return Math.ceil((days + start.getDay() + 1) / 7)
}

// 生命周期
onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  preSlaughterChart?.dispose()
  outWeightChart?.dispose()
  scaleFarmChart?.dispose()
  retailChart?.dispose()
  ratio90kgChart?.dispose()
  ratio150kgChart?.dispose()
})
</script>

<style scoped>
.weight-page {
  padding: 20px;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
}

.chart-wrapper {
  background: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-title {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  line-height: 1.5;
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
}
</style>
