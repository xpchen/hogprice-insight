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
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>企业仓单统计</span>
          <el-select
            v-model="selectedEnterprises"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="筛选企业"
            size="small"
            style="width: 280px"
            @change="loadTableData"
          >
            <el-option
              v-for="e in ENTERPRISE_NAMES"
              :key="e"
              :label="e"
              :value="e"
            />
          </el-select>
        </div>
      </template>
      <el-table :data="tableData.data" stripe border size="small">
        <el-table-column prop="enterprise" label="企业" width="120" />
        <el-table-column prop="total" label="企业总量" width="120" align="right">
          <template #default="{ row }">
            {{ row.total != null ? row.total.toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="warehouses" label="交割库及数量">
          <template #default="{ row }">
            <template v-if="row.warehouses && row.warehouses.length">
              <span v-for="(w, i) in row.warehouses" :key="i">
                {{ w.name }}{{ w.quantity != null ? `: ${w.quantity}` : '' }}{{ i < row.warehouses.length - 1 ? '；' : '' }}
              </span>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { futuresApi, type WarehouseReceiptChartResponse, type WarehouseReceiptTableResponse } from '@/api/futures'

const ENTERPRISE_NAMES = ['德康', '牧原', '中粮', '神农', '富之源', '扬翔']

const chartLoading = ref(false)
const tableLoading = ref(false)
const chartRef = ref<HTMLDivElement | null>(null)
const chartData = ref<WarehouseReceiptChartResponse>({
  data: [],
  date_range: { start: null, end: null },
  top2_enterprises: []
})
const tableData = ref<WarehouseReceiptTableResponse>({ data: [], enterprises: ENTERPRISE_NAMES })
const selectedEnterprises = ref<string[]>(ENTERPRISE_NAMES)
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

const loadTableData = async () => {
  tableLoading.value = true
  try {
    const result = await futuresApi.getWarehouseReceiptTable({
      enterprises: selectedEnterprises.value.length ? selectedEnterprises.value.join(',') : undefined
    })
    tableData.value = result
  } catch (e) {
    console.error('加载企业仓单表格失败:', e)
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
  loadTableData()
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
