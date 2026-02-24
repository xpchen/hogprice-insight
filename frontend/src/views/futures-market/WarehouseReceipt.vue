<template>
  <div class="warehouse-receipt-page">
    <el-card class="chart-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>注册仓单统计</span>
          <el-button size="small" @click="loadChartData">刷新</el-button>
        </div>
      </template>
      <div v-loading="chartLoading" style="min-height: 360px">
        <div v-if="chartData.data.length === 0 && !chartLoading" class="empty-tip">
          暂无数据，请先导入钢联模板（仓单数据 sheet）后刷新
        </div>
        <div v-else ref="chartRef" class="chart"></div>
      </div>
      <div v-if="chartData.data.length > 0" class="time-range-tip">
        全部时间周期，可使用下方进度条选择特定时期
      </div>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <div class="table-header-row">
          <span>企业仓单统计</span>
          <div class="filters-row">
            <el-select
              v-model="selectedEnterprise"
              placeholder="选择企业"
              size="small"
              style="width: 120px"
              clearable
            >
              <el-option
                v-for="e in ENTERPRISE_NAMES"
                :key="e"
                :label="e"
                :value="e"
              />
            </el-select>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              size="small"
              style="width: 260px"
              value-format="YYYY-MM-DD"
            />
            <el-button type="primary" size="small" :loading="tableLoading" @click="queryRaw">查询</el-button>
          </div>
        </div>
      </template>
      <div v-if="!selectedEnterprise" class="table-tip">请选择企业并选择日期范围后点击「查询」</div>
      <el-table v-else :data="rawData.rows" stripe border size="small" max-height="480">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column
          v-for="col in rawData.columns.slice(1)"
          :key="col"
          :prop="'values.' + col"
          :label="col"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            {{ row.values[col] != null ? Number(row.values[col]).toLocaleString() : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { futuresApi, type WarehouseReceiptChartResponse, type WarehouseReceiptRawResponse } from '@/api/futures'

const ENTERPRISE_NAMES = ['德康', '中粮', '神农', '富之源', '扬翔', '牧原']

const chartLoading = ref(false)
const tableLoading = ref(false)
const chartRef = ref<HTMLDivElement | null>(null)
const chartData = ref<WarehouseReceiptChartResponse>({
  data: [],
  date_range: { start: null, end: null },
  top2_enterprises: []
})
const selectedEnterprise = ref<string>('德康')
const dateRange = ref<[string, string] | null>(null)
const rawData = ref<WarehouseReceiptRawResponse>({ enterprise: '', columns: [], rows: [] })
let chartInstance: echarts.ECharts | null = null

const loadChartData = async () => {
  chartLoading.value = true
  try {
    const result = await futuresApi.getWarehouseReceiptChart()
    chartData.value = result
    await nextTick()
    renderChart()
  } catch (e) {
    console.error('加载仓单图表失败:', e)
  } finally {
    chartLoading.value = false
  }
}

const queryRaw = async () => {
  if (!selectedEnterprise.value) return
  tableLoading.value = true
  try {
    const [start_date, end_date] = dateRange.value || [undefined, undefined]
    const result = await futuresApi.getWarehouseReceiptRaw({
      enterprise: selectedEnterprise.value,
      start_date: start_date || undefined,
      end_date: end_date || undefined
    })
    rawData.value = result
  } catch (e) {
    console.error('加载企业仓单原始数据失败:', e)
  } finally {
    tableLoading.value = false
  }
}

const renderChart = () => {
  if (!chartRef.value || chartData.value.data.length === 0) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const data = chartData.value.data
  const dates = data.map(d => d.date)
  const totalData = data.map(d => d.total)
  const top2 = chartData.value.top2_enterprises || []

  const series: echarts.SeriesOption[] = [
    {
      name: '注册仓单总量',
      type: 'bar',
      data: totalData,
      itemStyle: { color: '#5470c6' }
    }
  ]

  const colors = ['#91cc75', '#fac858']
  top2.forEach((ent, i) => {
    series.push({
      name: ent,
      type: 'line',
      yAxisIndex: 1,
      data: data.map(d => d.enterprises[ent] ?? null),
      itemStyle: { color: colors[i % colors.length] },
      lineStyle: { color: colors[i % colors.length] },
      symbol: 'circle',
      symbolSize: 4,
      smooth: true,
      connectNulls: true
    })
  })

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['注册仓单总量', ...top2],
      top: 8,
      left: 'left'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '18%',
      top: '18%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45 }
    },
    yAxis: [
      {
        type: 'value',
        name: '总量',
        position: 'left'
      },
      {
        type: 'value',
        name: '企业',
        position: 'right',
        splitLine: { show: false }
      }
    ],
    series,
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 0 }
    ]
  }

  chartInstance.setOption(option, true)
}

const handleResize = () => chartInstance?.resize()

onMounted(() => {
  loadChartData()
  if (selectedEnterprise.value) queryRaw()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped lang="scss">
.warehouse-receipt-page {
  padding: 4px;
}

.chart-card,
.table-card {
  margin-bottom: 12px;

  :deep(.el-card__body) {
    padding: 8px 12px;
  }
}

.table-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filters-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.table-tip {
  color: #909399;
  padding: 24px;
  text-align: center;
  font-size: 14px;
}

.chart {
  width: 100%;
  height: 400px;
}

.empty-tip {
  color: #909399;
  padding: 40px;
  text-align: center;
}

.time-range-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
</style>
