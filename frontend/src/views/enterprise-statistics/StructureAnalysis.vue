<template>
  <div class="structure-analysis-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D4. 结构分析</span>
          <DataSourceInfo
            v-if="latestDate"
            source-name="企业集团出栏跟踪、涌益咨询、钢联、农业部、定点企业屠宰"
            :update-date="latestDate"
          />
        </div>
      </template>

      <!-- 数据源筛选 -->
      <div class="filters">
        <div class="filter-row">
          <span class="filter-label">数据源：</span>
          <el-checkbox-group v-model="selectedSources" @change="handleSourceChange">
            <el-checkbox label="CR20">CR20集团出栏环比</el-checkbox>
            <el-checkbox label="涌益">涌益</el-checkbox>
            <el-checkbox label="钢联-全国">钢联-全国</el-checkbox>
            <el-checkbox label="钢联-规模场">钢联-规模场</el-checkbox>
            <el-checkbox label="钢联-中小散户">钢联-中小散户</el-checkbox>
            <el-checkbox label="农业部-全国">农业部-全国</el-checkbox>
            <el-checkbox label="农业部-规模场">农业部-规模场</el-checkbox>
            <el-checkbox label="农业部-中小散户">农业部-中小散户</el-checkbox>
            <el-checkbox label="定点企业屠宰">定点企业屠宰</el-checkbox>
          </el-checkbox-group>
        </div>
      </div>

      <!-- 图表容器 -->
      <div class="chart-container">
        <div ref="chartRef" style="width: 100%; height: 500px" v-loading="loading"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getStructureAnalysisData } from '@/api/structure-analysis'
import type { StructureAnalysisResponse, StructureDataPoint } from '@/api/structure-analysis'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const loading = ref(false)
const tableData = ref<StructureAnalysisResponse | null>(null)
const latestDate = ref<string | null>(null)

// 默认选中的数据源
const selectedSources = ref<string[]>([
  'CR20',
  '涌益',
  '钢联-全国',
  '定点企业屠宰'
])

// 数据源映射（用于显示）
const sourceMap: Record<string, string> = {
  'CR20': 'CR20集团出栏环比',
  '涌益': '涌益',
  '钢联-全国': '钢联-全国',
  '钢联-规模场': '钢联-规模场',
  '钢联-中小散户': '钢联-中小散户',
  '农业部-全国': '农业部-全国',
  '农业部-规模场': '农业部-规模场',
  '农业部-中小散户': '农业部-中小散户',
  '定点企业屠宰': '定点企业屠宰'
}

// 过滤后的数据
const displayData = computed(() => {
  if (!tableData.value) return []
  return tableData.value.data.filter(item => selectedSources.value.includes(item.source))
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const sources = selectedSources.value.join(',')
    const response = await getStructureAnalysisData(sources)
    tableData.value = response
    latestDate.value = response.latest_date || null
    updateChart()
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 更新图表
const updateChart = () => {
  if (!chartInstance || !displayData.value.length) return

  // 按日期分组数据
  const dateMap: Record<string, Record<string, number | null>> = {}
  const allDates = new Set<string>()

  displayData.value.forEach(item => {
    if (!dateMap[item.date]) {
      dateMap[item.date] = {}
      allDates.add(item.date)
    }
    dateMap[item.date][item.source] = item.value
  })

  const sortedDates = Array.from(allDates).sort()

  // 构建series数据
  const sources = Array.from(new Set(displayData.value.map(item => item.source)))
  const series = sources.map(source => {
    const data = sortedDates.map(date => dateMap[date]?.[source] ?? null)
    return {
      name: sourceMap[source] || source,
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      connectNulls: false
    }
  })

  const option: echarts.EChartsOption = {
    title: {
      text: '结构分析 - 出栏环比',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let result = `<div style="margin-bottom: 4px;"><strong>${params[0].axisValue}</strong></div>`
        params.forEach((param: any) => {
          if (param.value !== null && param.value !== undefined) {
            const value = typeof param.value === 'number' ? param.value.toFixed(2) + '%' : param.value
            result += `<div style="margin: 2px 0;">
              <span style="display: inline-block; width: 10px; height: 10px; background-color: ${param.color}; margin-right: 5px;"></span>
              ${param.seriesName}: <strong>${value}</strong>
            </div>`
          }
        })
        return result
      }
    },
    legend: {
      data: sources.map(s => sourceMap[s] || s),
      bottom: 10,
      type: 'scroll'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: sortedDates.map(date => {
        const d = new Date(date)
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      }),
      axisLabel: {
        rotate: 45,
        interval: 0
      }
    },
    yAxis: {
      type: 'value',
      name: '环比 (%)',
      axisLabel: {
        formatter: '{value}%'
      }
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

  chartInstance.setOption(option, true)
}

// 数据源变化处理
const handleSourceChange = () => {
  loadData()
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
}

// 组件挂载
onMounted(() => {
  initChart()
  loadData()
})

// 组件卸载
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
  })
})

// 监听数据变化
watch(displayData, () => {
  updateChart()
}, { deep: true })
</script>

<style scoped lang="scss">
.structure-analysis-page {
  .filters {
    margin-bottom: 20px;
    
    .filter-row {
      display: flex;
      align-items: center;
      margin-bottom: 10px;
      
      .filter-label {
        font-weight: 500;
        margin-right: 10px;
        min-width: 60px;
      }
    }
  }

  .chart-container {
    margin-top: 20px;
  }
}
</style>
