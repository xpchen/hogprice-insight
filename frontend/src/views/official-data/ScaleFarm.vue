<template>
  <div class="scale-farm-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E1. 规模场数据汇总</span>
          <DataSourceInfo
            v-if="chartLatestDate"
            source-name="涌益咨询周度数据 - 月度-生产指标"
            :update-date="chartLatestDate"
          />
        </div>
      </template>

      <!-- 规模场数据汇总表格：按 Excel 原样输出（两行表头 + 数据行） -->
      <div class="table-section">
        <h3 class="table-title">规模场数据汇总</h3>
        <p class="table-desc">数据来源：A1供给预测（2、【生猪产业数据】.xlsx）</p>
        <div class="table-container raw-table-wrap" v-loading="loading">
          <table v-if="tableData && (tableData.header_row_0?.length || tableData.rows?.length)" class="raw-excel-table">
            <thead>
              <tr v-if="tableData.header_row_0?.length">
                <th v-for="(cell, i) in tableData.header_row_0" :key="'h0-' + i">{{ formatCell(cell) }}</th>
              </tr>
              <tr v-if="tableData.header_row_1?.length">
                <th v-for="(cell, i) in tableData.header_row_1" :key="'h1-' + i">{{ formatCell(cell) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in tableData.rows" :key="'r-' + ri">
                <td v-for="(cell, ci) in row" :key="'c-' + ri + '-' + ci">{{ formatCell(cell) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!loading && (!tableData || (!tableData.rows?.length && !tableData.header_row_0?.length)) && !errorMessage" class="empty-hint">
          <el-empty description="暂无数据，请先导入 2、【生猪产业数据】.xlsx 并确保包含 A1供给预测 sheet" />
        </div>
        <div v-if="errorMessage" class="error-hint">
          <el-alert :title="errorMessage" type="error" show-icon />
        </div>
      </div>

      <!-- 图表1：母猪效能 -->
      <div class="chart-section">
        <h3 class="chart-title">图表1：母猪效能</h3>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 400px" v-loading="loading1"></div>
        </div>
      </div>

      <!-- 图表2：压栏系数 -->
      <div class="chart-section">
        <h3 class="chart-title">图表2：压栏系数</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 400px" v-loading="loading2"></div>
        </div>
      </div>

      <!-- 图表3：涌益生产指标 -->
      <div class="chart-section">
        <h3 class="chart-title">图表3：涌益生产指标</h3>
        <div class="filter-section">
          <span class="filter-label">图例筛选：</span>
          <el-checkbox-group v-model="selectedIndicators" @change="handleIndicatorChange">
            <el-checkbox v-for="indicator in indicatorNames" :key="indicator" :label="indicator">
              {{ indicator }}
            </el-checkbox>
            <el-checkbox label="全部">全部</el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="chart-container">
          <div ref="chart3Ref" style="width: 100%; height: 400px" v-loading="loading3"></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getA1SupplyForecastTable,
  getSowEfficiency,
  getPressureCoefficient,
  getYongyiProductionIndicators
} from '@/api/production-indicators'
import type {
  A1SupplyForecastTableResponse,
  ProductionIndicatorResponse,
  ProductionIndicatorsResponse
} from '@/api/production-indicators'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const loading = ref(false)
const tableData = ref<A1SupplyForecastTableResponse | null>(null)
const errorMessage = ref('')

const chart1Ref = ref<HTMLDivElement>()
const chart2Ref = ref<HTMLDivElement>()
const chart3Ref = ref<HTMLDivElement>()
let chart1Instance: echarts.ECharts | null = null
let chart2Instance: echarts.ECharts | null = null
let chart3Instance: echarts.ECharts | null = null
const loading1 = ref(false)
const loading2 = ref(false)
const loading3 = ref(false)
const chart1Data = ref<ProductionIndicatorResponse | null>(null)
const chart2Data = ref<ProductionIndicatorResponse | null>(null)
const chart3Data = ref<ProductionIndicatorsResponse | null>(null)
const chartLatestDate = ref<string | null>(null)
const indicatorNames = ref<string[]>([])
const selectedIndicators = ref<string[]>(['全部'])

const displayIndicators = computed(() => {
  if (!chart3Data.value) return []
  if (selectedIndicators.value.includes('全部')) return indicatorNames.value
  return selectedIndicators.value.filter((name: string) => name !== '全部')
})

function formatCell(val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'number') return Number.isFinite(val) ? String(val) : '-'
  return String(val).trim() || '-'
}

async function loadTable() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await getA1SupplyForecastTable()
    tableData.value = res
  } catch (e: any) {
    errorMessage.value = e?.message || '加载规模场数据汇总表格失败'
    tableData.value = null
  } finally {
    loading.value = false
  }
}

async function loadChart1Data() {
  loading1.value = true
  try {
    const res = await getSowEfficiency()
    chart1Data.value = res
    if (res.latest_date && !chartLatestDate.value) chartLatestDate.value = res.latest_date
    updateChart1()
  } catch (e: any) {
    console.error('加载图表1失败:', e)
    ElMessage.error('加载图表1失败: ' + (e?.message || '未知错误'))
  } finally {
    loading1.value = false
  }
}

async function loadChart2Data() {
  loading2.value = true
  try {
    const res = await getPressureCoefficient()
    chart2Data.value = res
    if (res.latest_date && !chartLatestDate.value) chartLatestDate.value = res.latest_date
    updateChart2()
  } catch (e: any) {
    console.error('加载图表2失败:', e)
    ElMessage.error('加载图表2失败: ' + (e?.message || '未知错误'))
  } finally {
    loading2.value = false
  }
}

async function loadChart3Data() {
  loading3.value = true
  try {
    const res = await getYongyiProductionIndicators()
    chart3Data.value = res
    indicatorNames.value = res.indicator_names
    selectedIndicators.value = ['全部']
    if (res.latest_date && !chartLatestDate.value) chartLatestDate.value = res.latest_date
    updateChart3()
  } catch (e: any) {
    console.error('加载图表3失败:', e)
    ElMessage.error('加载图表3失败: ' + (e?.message || '未知错误'))
  } finally {
    loading3.value = false
  }
}

function updateChart1() {
  if (!chart1Ref.value || !chart1Data.value) return
  if (!chart1Instance) chart1Instance = echarts.init(chart1Ref.value)
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['分娩窝数'], bottom: 10, icon: 'circle', itemWidth: 10, itemHeight: 10, left: 'left' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: chart1Data.value.data.map((d) => d.date) },
    yAxis: { type: 'value', name: '窝数' },
    dataZoom: [{ type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }, { type: 'inside', start: 0, end: 100 }],
    series: [{ name: '分娩窝数', type: 'line', smooth: true, data: chart1Data.value.data.map((d) => d.value), itemStyle: { color: '#5470c6' } }]
  }
  chart1Instance.setOption(option)
}

function updateChart2() {
  if (!chart2Ref.value || !chart2Data.value) return
  if (!chart2Instance) chart2Instance = echarts.init(chart2Ref.value)
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['窝均健仔数（河南）'], bottom: 10, icon: 'circle', itemWidth: 10, itemHeight: 10, left: 'left' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: chart2Data.value.data.map((d) => d.date) },
    yAxis: { type: 'value', name: '窝均健仔数' },
    dataZoom: [{ type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }, { type: 'inside', start: 0, end: 100 }],
    series: [{ name: '窝均健仔数（河南）', type: 'line', smooth: true, data: chart2Data.value.data.map((d) => d.value), itemStyle: { color: '#91cc75' } }]
  }
  chart2Instance.setOption(option)
}

function updateChart3() {
  if (!chart3Ref.value || !chart3Data.value) return
  if (!chart3Instance) chart3Instance = echarts.init(chart3Ref.value)
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272']
  const series = displayIndicators.value.map((indicator: string, idx: number) => {
    const data = chart3Data.value!.indicators[indicator] || []
    return { name: indicator, type: 'line', smooth: true, data: data.map((d) => d.value), itemStyle: { color: colors[idx % colors.length] } }
  })
  const dates = displayIndicators.value.length > 0 ? (chart3Data.value!.indicators[displayIndicators.value[0]] || []).map((d) => d.date) : []
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: displayIndicators.value, bottom: 10, icon: 'circle', itemWidth: 10, itemHeight: 10, left: 'left' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: dates },
    yAxis: { type: 'value', name: '窝均健仔数' },
    dataZoom: [{ type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }, { type: 'inside', start: 0, end: 100 }],
    series
  }
  chart3Instance.setOption(option)
}

function handleIndicatorChange() {
  updateChart3()
}

function handleResize() {
  chart1Instance?.resize()
  chart2Instance?.resize()
  chart3Instance?.resize()
}

watch(displayIndicators, () => {
  updateChart3()
})

onMounted(() => {
  loadTable()
  loadChart1Data()
  loadChart2Data()
  loadChart3Data()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart1Instance?.dispose()
  chart2Instance?.dispose()
  chart3Instance?.dispose()
})
</script>

<style scoped>
.scale-farm-page {
  padding: 20px;
}

.table-section {
  margin-bottom: 20px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 6px 0;
}

.table-desc {
  font-size: 12px;
  color: #909399;
  margin: 0 0 12px 0;
}

.table-container {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.raw-table-wrap {
  overflow-x: auto;
  max-height: 520px;
  overflow-y: auto;
}

.raw-excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.raw-excel-table th,
.raw-excel-table td {
  border: 1px solid #e4e7ed;
  padding: 6px 10px;
  text-align: center;
}
.raw-excel-table thead th {
  background-color: #f5f7fa;
  font-weight: 600;
  white-space: nowrap;
}
.raw-excel-table tbody td {
  text-align: right;
}
.raw-excel-table tbody tr:nth-child(even) {
  background-color: #fafafa;
}

.empty-hint,
.error-hint {
  margin-top: 16px;
}

:deep(.el-table) {
  font-size: 12px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
}

.chart-section {
  margin-bottom: 24px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px 0;
  text-align: left;
}

.filter-section {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.filter-label {
  font-weight: 500;
  margin-right: 10px;
  min-width: 80px;
}

.chart-container {
  margin-bottom: 8px;
}
</style>
