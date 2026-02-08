<template>
  <div class="industry-chain-page">
    <el-card>
      <template #header>
        <span>A8. 产业链数据汇总（全国）</span>
      </template>

      <div v-loading="loading" class="charts-container">
        <div
          v-for="(metric, index) in metrics"
          :key="metric.name"
          class="chart-item"
        >
          <SeasonalityChart
            :data="chartData[metric.name]"
            :loading="chartLoading[metric.name]"
            :title="metric.displayName"
            :change-info="changeInfo[metric.name]"
            :source-name="getSourceName(metric.name)"
            :update-date="formatUpdateDate(updateTimes[metric.name])"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import SeasonalityChart, { type SeasonalityData } from '../../components/SeasonalityChart.vue'
import { getIndustryChainSeasonality, type IndustryChainSeasonalityResponse } from '../../api/price-display'

// 15个指标配置
const metrics = [
  { name: '二元母猪价格', displayName: '二元母猪价格' },
  { name: '仔猪价格', displayName: '仔猪价格' },
  { name: '淘汰母猪价格', displayName: '淘汰母猪价格' },
  { name: '淘汰母猪折扣率', displayName: '淘汰母猪折扣率' },
  { name: '猪料比', displayName: '猪料比' },
  { name: '屠宰利润', displayName: '屠宰利润' },
  { name: '自养利润', displayName: '自养利润' },
  { name: '代养利润', displayName: '代养利润' },
  { name: '白条价格', displayName: '白条价格' },
  { name: '1#鲜肉价格', displayName: '1#鲜肉价格' },
  { name: '2#冻肉价格', displayName: '2#冻肉价格' },
  { name: '4#冻肉价格', displayName: '4#冻肉价格' },
  { name: '2号冻肉/1#鲜肉', displayName: '2号冻肉/1#鲜肉' },
  { name: '4#冻肉/白条', displayName: '4#冻肉/白条' },
  { name: '冻品库容率', displayName: '冻品库容率' }
]

const loading = ref(false)
const chartLoading = ref<Record<string, boolean>>({})
const chartData = ref<Record<string, SeasonalityData | null>>({})
const changeInfo = ref<Record<string, { period_change: number | null; yoy_change: number | null }>>({})
const updateTimes = ref<Record<string, string | null>>({})
const availableYears = ref<number[]>([])

// 初始化chartData和changeInfo
metrics.forEach(metric => {
  chartData.value[metric.name] = null
  changeInfo.value[metric.name] = { period_change: null, yoy_change: null }
  updateTimes.value[metric.name] = null
  chartLoading.value[metric.name] = false
})

// 获取数据来源名称（根据指标名称判断）
const getSourceName = (metricName: string): string => {
  // 产业链数据主要来自涌益，部分可能来自钢联
  // 这里可以根据实际数据源配置，暂时默认使用涌益
  return '涌益'
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

// 加载单个图表数据
const loadChartData = async (metricName: string) => {
  chartLoading.value[metricName] = true
  try {
    // 不传年份参数，加载所有年份数据，通过图例控制显示/隐藏
    const response: IndustryChainSeasonalityResponse = await getIndustryChainSeasonality(
      metricName
    )

    // 转换数据格式为SeasonalityChart需要的格式
    const xValues: number[] = []
    for (let i = 1; i <= 52; i++) {
      xValues.push(i)
    }

    // 将数据按周序号组织
    const series = response.series.map(s => {
      const values: Array<number | null> = []
      
      // 后端已经按周序号1-52返回数据，直接提取value
      s.data.forEach(point => {
        values.push(point.value)
      })
      
      // 确保有52个值（如果不足，补齐null）
      while (values.length < 52) {
        values.push(null)
      }
      
      return {
        year: s.year,
        values: values.slice(0, 52)  // 确保只有52个值
      }
    })

    chartData.value[metricName] = {
      x_values: xValues,
      series: series,
      meta: {
        unit: response.unit || '',
        freq: 'W',
        metric_name: response.metric_name
      }
    }

    // 保存涨跌信息
    changeInfo.value[metricName] = {
      period_change: response.period_change,
      yoy_change: response.yoy_change
    }

    // 更新可用年份列表（用于后续可能的用途）
    const years = extractAvailableYears(response.series)
    if (years.length > 0 && availableYears.value.length === 0) {
      availableYears.value = years
    }
  } catch (error: any) {
    console.error(`加载${metricName}数据失败:`, error)
    ElMessage.error(`加载${metricName}数据失败: ${error?.message || '未知错误'}`)
    chartData.value[metricName] = null
    changeInfo.value[metricName] = { period_change: null, yoy_change: null }
  } finally {
    chartLoading.value[metricName] = false
  }
}

// 提取可用年份
const extractAvailableYears = (series: Array<{ year: number; data: any[] }>): number[] => {
  const years = series.map(s => s.year)
  return [...new Set(years)].sort((a, b) => b - a)
}

// 加载所有图表
const loadAllCharts = async () => {
  loading.value = true
  try {
    // 并行加载所有图表数据
    await Promise.all(metrics.map(metric => loadChartData(metric.name)))
  } catch (error) {
    console.error('加载图表数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 初始化：加载所有图表
onMounted(async () => {
  await loadAllCharts()
})
</script>

<style scoped>
.industry-chain-page {
  padding: 20px;
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px; /* 缩小间距，横向两个图表共用边框 */
  margin-top: 20px;
  border: 1px solid #e4e7ed; /* 共用边框 */
  border-radius: 4px;
  padding: 16px;
  background: #fff;
}

.chart-item {
  min-height: 500px;
}

@media (max-width: 1400px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
}
</style>
