<template>
  <div class="cr5-daily-page">
    <el-card>
      <template #header>
        <span>D1. CR5企业日度出栏统计</span>
      </template>

      <!-- 时间筛选按钮 -->
      <div class="filter-buttons">
        <el-button
          :type="selectedMonths === 6 ? 'primary' : 'default'"
          size="small"
          @click="handleMonthsChange(6)"
        >
          近6个月
        </el-button>
        <el-button
          :type="selectedMonths === 0 ? 'primary' : 'default'"
          size="small"
          @click="handleMonthsChange(0)"
        >
          全部日期
        </el-button>
      </div>

      <!-- 图表容器：两两一行 -->
      <div class="charts-container">
        <!-- 第一行 -->
        <div class="chart-row">
          <!-- (1) CR5企业日度出栏 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">CR5企业日度出栏</h3>
              <div v-if="loadingCr5" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!cr5Data || cr5Data.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据" />
              </div>
              <div v-else>
                <div ref="cr5ChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <DataSourceInfo
                :source-name="cr5Data?.data_source || '企业集团出栏跟踪'"
                :update-date="formatUpdateDate(cr5Data?.update_time)"
              />
            </div>
          </div>

          <!-- (2) 四川重点企业日度出栏 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">四川重点企业日度出栏</h3>
              <div v-if="loadingSichuan" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!sichuanData || sichuanData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据" />
              </div>
              <div v-else>
                <div ref="sichuanChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <DataSourceInfo
                :source-name="sichuanData?.data_source || '企业集团出栏跟踪'"
                :update-date="formatUpdateDate(sichuanData?.update_time)"
              />
            </div>
          </div>
        </div>

        <!-- 第二行 -->
        <div class="chart-row">
          <!-- (3) 广西重点企业日度出栏 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">广西重点企业日度出栏</h3>
              <div v-if="loadingGuangxi" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!guangxiData || guangxiData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据" />
              </div>
              <div v-else>
                <div ref="guangxiChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <DataSourceInfo
                :source-name="guangxiData?.data_source || '企业集团出栏跟踪'"
                :update-date="formatUpdateDate(guangxiData?.update_time)"
              />
            </div>
          </div>

          <!-- (4) 西南样本企业日度出栏 -->
          <div class="chart-wrapper">
            <div class="chart-box">
              <h3 class="chart-title">西南样本企业日度出栏</h3>
              <div v-if="loadingSouthwest" class="loading-placeholder">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 10px">加载中...</span>
              </div>
              <div v-else-if="!southwestData || southwestData.series.length === 0" class="no-data-placeholder">
                <el-empty description="暂无数据" />
              </div>
              <div v-else>
                <div ref="southwestChartRef" class="chart-container"></div>
              </div>
            </div>
            <div class="info-box">
              <DataSourceInfo
                :source-name="southwestData?.data_source || '企业集团出栏跟踪'"
                :update-date="formatUpdateDate(southwestData?.update_time)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getCr5Daily, getSichuanDaily, getGuangxiDaily, getSouthwestSampleDaily } from '@/api/enterprise-statistics'
import type { EnterpriseStatisticsResponse } from '@/api/enterprise-statistics'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

// 时间筛选
const selectedMonths = ref<number>(6)

// 加载状态
const loadingCr5 = ref(false)
const loadingSichuan = ref(false)
const loadingGuangxi = ref(false)
const loadingSouthwest = ref(false)

// 数据
const cr5Data = ref<EnterpriseStatisticsResponse | null>(null)
const sichuanData = ref<EnterpriseStatisticsResponse | null>(null)
const guangxiData = ref<EnterpriseStatisticsResponse | null>(null)
const southwestData = ref<EnterpriseStatisticsResponse | null>(null)

// 图表引用
const cr5ChartRef = ref<HTMLDivElement>()
const sichuanChartRef = ref<HTMLDivElement>()
const guangxiChartRef = ref<HTMLDivElement>()
const southwestChartRef = ref<HTMLDivElement>()

let cr5Chart: echarts.ECharts | null = null
let sichuanChart: echarts.ECharts | null = null
let guangxiChart: echarts.ECharts | null = null
let southwestChart: echarts.ECharts | null = null

// 格式化更新日期
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

// 生成X轴网格点（月度3个点：10号、20号、30号）
const generateXAxisGrid = (dates: string[]): string[] => {
  if (dates.length === 0) return []
  
  const gridDates: string[] = []
  const processedMonths = new Set<string>()
  
  // 按月份分组
  const monthGroups: Record<string, string[]> = {}
  dates.forEach(dateStr => {
    const date = new Date(dateStr)
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    if (!monthGroups[monthKey]) {
      monthGroups[monthKey] = []
    }
    monthGroups[monthKey].push(dateStr)
  })
  
  // 为每个月生成10号、20号、30号网格点
  Object.keys(monthGroups).sort().forEach(monthKey => {
    const [year, month] = monthKey.split('-').map(Number)
    const monthDates = monthGroups[monthKey].sort()
    
    // 找到最接近10号、20号、30号的日期
    const targetDays = [10, 20, 30]
    targetDays.forEach(targetDay => {
      // 找到最接近目标日期的实际日期
      const targetDate = new Date(year, month - 1, targetDay)
      const targetDateStr = targetDate.toISOString().split('T')[0]
      
      // 如果目标日期在数据范围内，直接使用
      if (monthDates.includes(targetDateStr)) {
        gridDates.push(targetDateStr)
      } else {
        // 否则找最接近的日期
        const closest = monthDates.find(d => d >= targetDateStr) || monthDates[monthDates.length - 1]
        if (closest && !gridDates.includes(closest)) {
          gridDates.push(closest)
        }
      }
    })
  })
  
  return gridDates.sort()
}

// 渲染图表
const renderChart = (
  chartRef: HTMLDivElement | undefined,
  chartInstance: echarts.ECharts | null,
  data: EnterpriseStatisticsResponse,
  chartTitle: string
): echarts.ECharts | null => {
  if (!chartRef) return null
  
  // 销毁旧图表
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  // 创建新图表
  const chart = echarts.init(chartRef)
  
  // 收集所有日期
  const allDates = new Set<string>()
  data.series.forEach(series => {
    series.data.forEach(point => {
      if (point.date) allDates.add(point.date)
    })
  })
  
  const sortedDates = Array.from(allDates).sort()
  
  // 生成X轴网格点（全部日期时使用月度网格）
  const gridDates = selectedMonths.value === 0 ? generateXAxisGrid(sortedDates) : sortedDates
  
  // 构建系列数据
  const series = data.series.map((s, idx) => {
    const seriesData = sortedDates.map(date => {
      const point = s.data.find(p => p.date === date)
      return point?.value ?? null
    })
    
    return {
      name: s.name,
      type: 'line',
      data: seriesData,
      smooth: true,
      symbol: 'none',
      connectNulls: true,
      lineStyle: {
        width: 2
      }
    }
  })
  
  // 计算Y轴范围
  const allValues = data.series.flatMap(s => s.data.map(p => p.value).filter(v => v !== null)) as number[]
  const minValue = Math.min(...allValues)
  const maxValue = Math.max(...allValues)
  const padding = (maxValue - minValue) * 0.1
  
  const option: echarts.EChartsOption = {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        let result = `${params[0].axisValue}<br/>`
        params.forEach((param: any) => {
          result += `${param.seriesName}: ${param.value !== null ? param.value.toFixed(2) : '无数据'}<br/>`
        })
        return result
      }
    },
    legend: {
      data: data.series.map(s => s.name),
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        fontSize: 12
      }
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
      data: sortedDates,
      boundaryGap: false,
      axisLabel: {
        formatter: (value: string) => {
          const date = new Date(value)
          const month = date.getMonth() + 1
          const day = date.getDate()
          // 如果是网格点（10、20、30号），显示完整日期
          if ([10, 20, 30].includes(day)) {
            return `${month}月${day}日`
          }
          return `${month}-${day}`
        },
        rotate: 45,
        interval: selectedMonths.value === 0 ? (idx: number) => {
          // 只显示网格点
          return gridDates.includes(sortedDates[idx])
        } : 'auto'
      },
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      scale: false,
      min: minValue - padding,
      max: maxValue + padding,
      axisLabel: {
        formatter: (value: number) => value.toFixed(0)
      }
    },
    series: series as any
  }
  
  chart.setOption(option)
  return chart
}

// 加载数据
const loadCr5Data = async () => {
  loadingCr5.value = true
  try {
    const data = await getCr5Daily(selectedMonths.value)
    cr5Data.value = data
    await nextTick()
    setTimeout(() => {
      if (cr5ChartRef.value) {
        cr5Chart = renderChart(cr5ChartRef.value, cr5Chart, data, 'CR5企业日度出栏')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载CR5数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingCr5.value = false
  }
}

const loadSichuanData = async () => {
  loadingSichuan.value = true
  try {
    const data = await getSichuanDaily(selectedMonths.value)
    sichuanData.value = data
    await nextTick()
    setTimeout(() => {
      if (sichuanChartRef.value) {
        sichuanChart = renderChart(sichuanChartRef.value, sichuanChart, data, '四川重点企业日度出栏')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载四川数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingSichuan.value = false
  }
}

const loadGuangxiData = async () => {
  loadingGuangxi.value = true
  try {
    const data = await getGuangxiDaily(selectedMonths.value)
    guangxiData.value = data
    await nextTick()
    setTimeout(() => {
      if (guangxiChartRef.value) {
        guangxiChart = renderChart(guangxiChartRef.value, guangxiChart, data, '广西重点企业日度出栏')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载广西数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingGuangxi.value = false
  }
}

const loadSouthwestData = async () => {
  loadingSouthwest.value = true
  try {
    const data = await getSouthwestSampleDaily(selectedMonths.value)
    southwestData.value = data
    await nextTick()
    setTimeout(() => {
      if (southwestChartRef.value) {
        southwestChart = renderChart(southwestChartRef.value, southwestChart, data, '西南样本企业日度出栏')
      }
    }, 200)
  } catch (error: any) {
    console.error('加载西南数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingSouthwest.value = false
  }
}

// 时间筛选变化
const handleMonthsChange = (months: number) => {
  selectedMonths.value = months
  loadAllData()
}

// 加载所有数据
const loadAllData = () => {
  loadCr5Data()
  loadSichuanData()
  loadGuangxiData()
  loadSouthwestData()
}

// 监听窗口大小变化
const handleResize = () => {
  if (cr5Chart) cr5Chart.resize()
  if (sichuanChart) sichuanChart.resize()
  if (guangxiChart) guangxiChart.resize()
  if (southwestChart) southwestChart.resize()
}

onMounted(() => {
  loadAllData()
  window.addEventListener('resize', handleResize)
})

// 清理
import { onUnmounted } from 'vue'
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (cr5Chart) cr5Chart.dispose()
  if (sichuanChart) sichuanChart.dispose()
  if (guangxiChart) guangxiChart.dispose()
  if (southwestChart) southwestChart.dispose()
})
</script>

<style scoped>
.cr5-daily-page {
  padding: 20px;
}

.filter-buttons {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-row {
  display: flex;
  gap: 20px;
}

.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-box {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 20px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.chart-title {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.loading-placeholder,
.no-data-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #909399;
}

.info-box {
  margin-top: 10px;
  padding: 10px;
  font-size: 12px;
  color: #909399;
}

@media (max-width: 1200px) {
  .chart-row {
    flex-direction: column;
  }
}
</style>
