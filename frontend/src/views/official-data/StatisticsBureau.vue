<template>
  <div class="statistics-bureau-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E4. 统计局数据汇总</span>
          <DataSourceInfo
            v-if="latestPeriod || latestMonth"
            source-name="国家统计局、钢联模板"
            :update-date="latestPeriod || latestMonth"
          />
        </div>
      </template>

      <!-- 表1：统计局季度数据汇总（按 Excel 原样：多级表头 + 合并单元格） -->
      <div class="table-section">
        <h3>表1：统计局季度数据汇总</h3>
        <p class="table-desc">数据来源：03.统计局季度数据（国家统计局）</p>
        <div class="table-container raw-table-wrap" v-loading="loadingTable1">
          <table
            v-if="quarterlyTableData && (quarterlyTableData.header_row_0?.length || quarterlyTableData.rows?.length)"
            class="raw-excel-table"
          >
            <thead>
              <tr v-for="(row, r) in quarterlyHeaderGridNoFirstCol" :key="'hr-' + r">
                <template v-for="(cell, c) in row" :key="'h' + r + '-' + c">
                  <th
                    v-if="cell"
                    :colspan="cell.colspan"
                    :rowspan="cell.rowspan"
                    :class="getHeaderCellClass(r, c + 1, cell)"
                  >
                    {{ formatCell(cell.value) }}
                  </th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in quarterlyTableData.rows" :key="'r-' + ri">
                <td
                  v-for="(cell, ci) in row.slice(1)"
                  :key="'c-' + ri + '-' + ci"
                  :class="getDataCellClass(ci + 1, cell)"
                >
                  {{ formatDataCell(ci + 1, cell) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div
          v-if="!loadingTable1 && (!quarterlyTableData || (!quarterlyTableData.rows?.length && !quarterlyTableData.header_row_0?.length)) && !table1Error"
          class="empty-hint"
        >
          <el-empty description="暂无数据，请先导入包含 03.统计局季度数据 的 Excel 文件" />
        </div>
        <div v-if="table1Error" class="error-hint">
          <el-alert :title="table1Error" type="error" show-icon />
        </div>
      </div>

      <!-- 图1：统计局生猪出栏量&屠宰量 -->
      <div class="chart-section">
        <h3>图1：统计局生猪出栏量&屠宰量</h3>
        <div class="chart-container">
          <div ref="chart1Ref" style="width: 100%; height: 420px" v-loading="loadingChart1"></div>
        </div>
        <div class="filter-section filter-section-below">
          <span class="filter-label">特定周期筛选：</span>
          <el-slider
            v-model="timeRange"
            :min="0"
            :max="100"
            :step="1"
            range
            show-stops
            @change="handleTimeRangeChange"
            style="flex: 1; max-width: 500px; margin: 0 12px"
          />
          <span class="filter-range-text">{{ timeRangeText }}</span>
        </div>
      </div>

      <!-- 图2：猪肉进口 -->
      <div class="chart-section">
        <h3>图2：猪肉进口</h3>
        <div class="chart-container">
          <div ref="chart2Ref" style="width: 100%; height: 500px" v-loading="loadingChart2"></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getQuarterlyData,
  getOutputSlaughter,
  getImportMeat
} from '@/api/statistics-bureau'
import type {
  QuarterlyDataRawResponse,
  OutputSlaughterResponse,
  ImportMeatResponse
} from '@/api/statistics-bureau'
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import { yAxisHideMinMaxLabel } from '@/utils/chart-style'

const chart1Ref = ref<HTMLDivElement>()
const chart2Ref = ref<HTMLDivElement>()

let chart1Instance: echarts.ECharts | null = null
let chart2Instance: echarts.ECharts | null = null

const loadingTable1 = ref(false)
const loadingChart1 = ref(false)
const loadingChart2 = ref(false)

const quarterlyData = ref<QuarterlyDataRawResponse | null>(null)
const table1Error = ref('')
const outputSlaughterData = ref<OutputSlaughterResponse | null>(null)
const importMeatData = ref<ImportMeatResponse | null>(null)

const latestPeriod = ref<string | null>(null)
const latestMonth = ref<string | null>(null)

const timeRange = ref<[number, number]>([0, 100])

// 计算属性
const quarterlyTableData = computed(() => quarterlyData.value)

/** 根据 merged_cells 和表头构建带合并信息的表头网格 */
const quarterlyHeaderGrid = computed(() => {
  const td = quarterlyTableData.value
  if (!td?.header_row_0?.length) return []
  const rows: (string[])[] = [td.header_row_0]
  if (td.header_row_1?.length) rows.push(td.header_row_1)
  const maxCol = Math.max(...rows.map((r) => r.length), td.column_count || 0, 1)
  const merged = td.merged_cells_json || []
  type CellInfo = { value: string; rowspan: number; colspan: number }
  const grid: (CellInfo | null)[][] = rows.map((row) =>
    [...row, ...Array(Math.max(0, maxCol - row.length)).fill('')].map((v) => ({
      value: String(v ?? '').trim() || '',
      rowspan: 1,
      colspan: 1
    }))
  )
  for (const m of merged) {
    const r0 = (m.min_row ?? 1) - 1
    const c0 = (m.min_col ?? 1) - 1
    const r1 = (m.max_row ?? 1) - 1
    const c1 = (m.max_col ?? 1) - 1
    if (r0 < 0 || r0 >= grid.length || c0 < 0) continue
    const rowspan = r1 - r0 + 1
    const colspan = c1 - c0 + 1
    if (rowspan <= 0 || colspan <= 0) continue
    const cell = grid[r0][c0] as CellInfo
    if (cell) {
      cell.rowspan = rowspan
      cell.colspan = colspan
    }
    for (let r = r0; r <= r1; r++) {
      for (let c = c0; c <= c1; c++) {
        if (r === r0 && c === c0) continue
        if (r < grid.length && c < (grid[r]?.length ?? 0)) grid[r][c] = null
      }
    }
  }
  return grid
})

/** 去掉第一列（季度）后的表头网格 */
const quarterlyHeaderGridNoFirstCol = computed(() => {
  const grid = quarterlyHeaderGrid.value
  return grid.map((row) => row.slice(1))
})

const filteredOutputSlaughterData = computed(() => {
  if (!outputSlaughterData.value) return []
  const data = outputSlaughterData.value.data
  if (data.length === 0) return []
  
  const [startPercent, endPercent] = timeRange.value
  const startIdx = Math.floor((data.length - 1) * startPercent / 100)
  const endIdx = Math.floor((data.length - 1) * endPercent / 100)
  
  return data.slice(startIdx, endIdx + 1)
})

const timeRangeText = computed(() => {
  if (!outputSlaughterData.value || outputSlaughterData.value.data.length === 0) {
    return ''
  }
  const data = outputSlaughterData.value.data
  const [startPercent, endPercent] = timeRange.value
  const startIdx = Math.floor((data.length - 1) * startPercent / 100)
  const endIdx = Math.floor((data.length - 1) * endPercent / 100)
  
  const startPeriod = data[startIdx]?.period || ''
  const endPeriod = data[endIdx]?.period || ''
  
  return `${startPeriod} 至 ${endPeriod}`
})

// 表1 工具函数
function getHeaderCellClass(_r: number, _c: number, cell: { value: string } | null): string {
  if (!cell?.value) return ''
  const v = String(cell.value)
  if (/能繁母猪/i.test(v)) return 'header-yellow'
  if (/生猪存栏/i.test(v)) return 'header-green'
  if (/生猪出栏/i.test(v)) return 'header-blue'
  if (/定点屠宰|猪肉产量|猪肉进口|猪肉供给/i.test(v)) return 'header-orange'
  return ''
}

function getParentHeader(colIdx: number): string {
  const td = quarterlyTableData.value
  if (!td?.header_row_1) return ''
  for (let c = colIdx; c >= 0; c--) {
    const v = String(td.header_row_1[c] ?? '').trim()
    if (v && !/^环比$|^同比$|^比例$|^占比$|^累计$/.test(v)) return v
  }
  return String(td.header_row_0?.[colIdx] ?? '').trim()
}

function getDataCellClass(colIdx: number, _cell: unknown): string {
  const td = quarterlyTableData.value
  if (!td) return ''
  const cls: string[] = []
  const h1 = td.header_row_1?.[colIdx] ?? ''
  const isMomYoy = /环比|同比/.test(String(h1))
  if (isMomYoy) cls.push('cell-mom-yoy')
  const num = typeof _cell === 'number' ? _cell : parseFloat(String(_cell ?? ''))
  if (Number.isFinite(num) && num < 0) cls.push('cell-negative')
  return cls.join(' ')
}

function formatCell(val: unknown): string {
  if (val === null || val === undefined) return ''
  if (typeof val === 'number')
    return Number.isFinite(val)
      ? val.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
      : ''
  return String(val).trim() || ''
}

function formatDataCell(colIdx: number, val: unknown): string {
  const td = quarterlyTableData.value
  const h1 = td?.header_row_1?.[colIdx] ?? ''
  const isMomYoy = /环比|同比/.test(String(h1))
  if (!isMomYoy) return formatCell(val)
  if (val === null || val === undefined) return ''
  const num = typeof val === 'number' ? val : parseFloat(String(val ?? ''))
  if (!Number.isFinite(num)) return formatCell(val)
  return `(${num})`
}

const handleTimeRangeChange = () => {
  updateChart1()
}

// 加载表1数据
const loadQuarterlyData = async () => {
  loadingTable1.value = true
  table1Error.value = ''
  try {
    const response = await getQuarterlyData()
    quarterlyData.value = response
  } catch (error: any) {
    table1Error.value = '加载季度数据失败: ' + (error.message || '未知错误')
    quarterlyData.value = null
    ElMessage.error(table1Error.value)
  } finally {
    loadingTable1.value = false
  }
}

// 加载图1数据
const loadOutputSlaughterData = async () => {
  loadingChart1.value = true
  try {
    const response = await getOutputSlaughter()
    outputSlaughterData.value = response
    if (response.latest_period && !latestPeriod.value) {
      latestPeriod.value = response.latest_period
    }
    updateChart1()
  } catch (error: any) {
    console.error('加载出栏量&屠宰量数据失败:', error)
    ElMessage.error('加载出栏量&屠宰量数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingChart1.value = false
  }
}

// 加载图2数据
const loadImportMeatData = async () => {
  loadingChart2.value = true
  try {
    const response = await getImportMeat()
    importMeatData.value = response
    if (response.latest_month && !latestMonth.value) {
      latestMonth.value = response.latest_month
    }
    await nextTick()
    updateChart2()
  } catch (error: any) {
    console.error('加载猪肉进口数据失败:', error)
    ElMessage.error('加载猪肉进口数据失败: ' + (error.message || '未知错误'))
  } finally {
    loadingChart2.value = false
    await nextTick()
    chart2Instance?.resize()
  }
}

// 更新图表1
const updateChart1 = () => {
  if (!chart1Ref.value || !outputSlaughterData.value) return

  if (!chart1Instance) {
    chart1Instance = echarts.init(chart1Ref.value)
  }

  const data = filteredOutputSlaughterData.value
  if (data.length === 0) {
    chart1Instance.setOption({
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '暂无数据',
          fontSize: 16,
          fill: '#999'
        }
      }
    })
    return
  }

  const periods = data.map(d => d.period)
  const outputVolumes = data.map(d => d.output_volume)
  const slaughterVolumes = data.map(d => d.slaughter_volume)
  const scaleRates = data.map(d => d.scale_rate ? d.scale_rate * 100 : null) // 转换为百分比

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
            if (param.seriesName.includes('规模化率')) {
              result += `${param.seriesName}: ${param.value.toFixed(2)}%<br/>`
            } else {
              result += `${param.seriesName}: ${param.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}<br/>`
            }
          }
        })
        return result
      }
    },
    legend: {
      data: ['季度出栏量', '定点屠宰量', '规模化率'],
      top: 8,
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 28,
      left: 'left',
      type: 'plain'
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '15%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: periods
    },
    yAxis: [
      {
        type: 'value',
        name: '出栏量/屠宰量',
        position: 'left',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2) }
      },
      {
        type: 'value',
        name: '规模化率(%)',
        position: 'right',
        ...yAxisHideMinMaxLabel,
        axisLabel: { formatter: (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(2)) + '%' }
      }
    ],
    dataZoom: [
      {
        type: 'slider',
        show: true,
        xAxisIndex: [0],
        start: 0,
        end: 100
      },
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '季度出栏量',
        type: 'line',
        yAxisIndex: 0,
        data: outputVolumes,
        connectNulls: false,
        itemStyle: {
          color: '#5470c6'
        }
      },
      {
        name: '定点屠宰量',
        type: 'line',
        yAxisIndex: 0,
        data: slaughterVolumes,
        connectNulls: false,
        itemStyle: {
          color: '#91cc75'
        }
      },
      {
        name: '规模化率',
        type: 'line',
        yAxisIndex: 1,
        data: scaleRates,
        connectNulls: false,
        itemStyle: {
          color: '#fac858'
        }
      }
    ]
  }

  chart1Instance.setOption(option)
}

// 更新图表2：猪肉进口柱形图
const updateChart2 = () => {
  if (!chart2Ref.value || !importMeatData.value) return

  if (!chart2Instance) {
    chart2Instance = echarts.init(chart2Ref.value)
  }

  const data = importMeatData.value.data
  if (data.length === 0) {
    chart2Instance.setOption({
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '暂无数据',
          fontSize: 16,
          fill: '#999'
        }
      }
    })
    chart2Instance.resize()
    return
  }

  const months = data.map(d => d.month)
  const hasTopCountries = data.some(d => d.top_countries && d.top_countries.length > 0)

  // 钢联数据单位为吨，图表显示为万吨（÷10000）
  const toWanTon = (v: number | null | undefined) => (v != null ? v / 10000 : 0)

  // 构建堆叠柱形图数据
  const totalData = data.map(d => (d.total != null ? toWanTon(d.total) : null))
  const countryColors = ['#5470c6', '#91cc75']  // 最大、次大国家颜色
  const series: any[] = []

  if (hasTopCountries) {
    const c1Data = data.map(d => toWanTon(d.top_countries?.[0]?.value))
    const c2Data = data.map(d => toWanTon(d.top_countries?.[1]?.value))
    const otherData = data.map((d) => {
      const total = d.total ?? 0
      const c1v = d.top_countries?.[0]?.value ?? 0
      const c2v = d.top_countries?.[1]?.value ?? 0
      const other = Math.max(0, total - c1v - c2v)
      return toWanTon(other)
    })
    // 使用最新月份的前两名国家作为图例（每月前两名可能不同）
    const lastPoint = data[data.length - 1]
    const c1Name = lastPoint?.top_countries?.[0]?.country ?? '进口量第1'
    const c2Name = lastPoint?.top_countries?.[1]?.country ?? '进口量第2'
    series.push(
      { name: '其他', type: 'bar', stack: 'total', data: otherData, itemStyle: { color: '#e0e0e0' } },
      { name: c1Name, type: 'bar', stack: 'total', data: c1Data, itemStyle: { color: countryColors[0] } },
      { name: c2Name, type: 'bar', stack: 'total', data: c2Data, itemStyle: { color: countryColors[1] } }
    )
  } else {
    series.push({
      name: '进口总量',
      type: 'bar',
      data: totalData,
      itemStyle: { color: '#5470c6' }
    })
  }

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const month = params[0].axisValue
        const idx = params[0].dataIndex
        const point = data[idx]
        const fmt = (v: number) => v.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
        const totalWanTon = (point.total ?? 0) / 10000
        let result = `<strong>${month}</strong><br/>`
        result += `进口总量: ${fmt(totalWanTon)} 万吨<br/>`
        if (point.top_countries?.length) {
          point.top_countries.forEach((c: { country: string; value?: number | null }) => {
            result += `${c.country}进口量: ${fmt((c.value ?? 0) / 10000)} 万吨<br/>`
          })
        }
        return result
      }
    },
    legend: hasTopCountries ? { top: 4, left: 'center', type: 'plain' } : { show: false },
    grid: {
      left: '3%',
      right: '4%',
      top: '10%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '万吨',
      ...yAxisHideMinMaxLabel,
      axisLabel: { formatter: (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(1) }
    },
    dataZoom: [
      { type: 'slider', show: true, xAxisIndex: [0], start: 0, end: 100, height: 20, bottom: 0 },
      { type: 'inside', xAxisIndex: [0], start: 0, end: 100 }
    ],
    series
  }

  chart2Instance.setOption(option)
  chart2Instance.resize()
}

// 监听窗口大小变化
const handleResize = () => {
  chart1Instance?.resize()
  chart2Instance?.resize()
}

onMounted(() => {
  loadQuarterlyData()
  loadOutputSlaughterData()
  loadImportMeatData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart1Instance?.dispose()
  chart2Instance?.dispose()
})
</script>

<style scoped>
.statistics-bureau-page {
  padding: 4px;
}

.statistics-bureau-page :deep(.el-card__body) {
  padding: 4px 6px;
}

.table-section,
.chart-section {
  margin-bottom: 12px;
}

.table-section h3 {
  margin-bottom: 6px;
  font-size: 18px;
  font-weight: 600;
}

.table-desc {
  font-size: 12px;
  color: #909399;
  margin: 0 0 12px 0;
}

/* 表格容器：固定高度约 16 行数据 + 表头，超出部分内部滚动 */
.raw-table-wrap {
  overflow-x: auto;
  overflow-y: auto;
  max-height: 560px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
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

/* 表头固定：滚动时表头不随内容消失 */
.raw-excel-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.raw-excel-table thead th {
  background-color: #f5f7fa;
  font-weight: 600;
  white-space: nowrap;
  box-shadow: 0 1px 0 #e4e7ed;
}

.raw-excel-table thead th.header-yellow {
  background-color: #fff9e6;
}
.raw-excel-table thead th.header-green {
  background-color: #e8f5e9;
}
.raw-excel-table thead th.header-blue {
  background-color: #e3f2fd;
}
.raw-excel-table thead th.header-orange {
  background-color: #fff3e0;
}

.raw-excel-table tbody td {
  text-align: right;
}

.raw-excel-table tbody td.col-period {
  text-align: center;
}

.raw-excel-table tbody tr:nth-child(even) td {
  background-color: #fafafa;
}

.raw-excel-table tbody td.cell-negative {
  color: #f56c6c;
}

.empty-hint,
.error-hint {
  margin-top: 16px;
}

.chart-section h3 {
  margin-bottom: 4px;
  font-size: 18px;
  font-weight: 600;
}

.table-container {
  margin-top: 15px;
}

.chart-container {
  margin-top: 8px;
}

.filter-section {
  display: flex;
  align-items: center;
}

.filter-section-below {
  margin-top: 12px;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
}

.filter-section .filter-label {
  font-weight: 500;
  font-size: 13px;
  white-space: nowrap;
}

.filter-range-text {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

</style>
