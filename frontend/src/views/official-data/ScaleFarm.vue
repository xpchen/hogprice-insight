<template>
  <div class="scale-farm-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E1. 规模场数据汇总</span>
          <DataSourceInfo
            v-if="chartLatestDate"
            source-name="A1供给预测（2、【生猪产业数据】.xlsx）"
            :update-date="chartLatestDate"
          />
        </div>
      </template>

      <!-- 规模场数据汇总表格：按 Excel 原样输出（多行表头 + 合并单元格 + 数据行） -->
      <div class="table-section">
        <h3 class="table-title">规模场数据汇总</h3>
        <p class="table-desc">数据来源：A1供给预测（2、【生猪产业数据】.xlsx）</p>
        <div class="table-container raw-table-wrap" v-loading="loading">
          <table v-if="tableData && (tableData.header_row_0?.length || tableData.rows?.length)" class="raw-excel-table">
            <thead>
              <tr v-for="(row, r) in headerGrid" :key="'hr-' + r">
                <template v-for="(cell, c) in row" :key="'h' + r + '-' + c">
                  <th
                    v-if="cell"
                    :colspan="cell.colspan"
                    :rowspan="cell.rowspan"
                    :class="getHeaderCellClass(r, c, cell)"
                  >
                    {{ formatCell(cell.value) }}
                  </th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in tableData.rows" :key="'r-' + ri">
                <td
                  v-for="(cell, ci) in row"
                  :key="'c-' + ri + '-' + ci"
                  :class="getDataCellClass(ci, cell)"
                >
                  {{ formatDataCell(ci, cell) }}
                </td>
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

      <!-- 母猪效能、压栏系数 并列显示（季节性，数据源：A1 表 F 列、N 列） -->
      <div class="chart-section charts-row">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <SeasonalityChart
              :data="sowEfficiencySeasonality"
              :loading="loadingSeasonality"
              title="母猪效能"
              source-name="A1供给预测（2、【生猪产业数据】.xlsx）"
            />
          </el-col>
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <SeasonalityChart
              :data="pressureCoefficientSeasonality"
              :loading="loadingSeasonality"
              title="压栏系数"
              source-name="A1供给预测（2、【生猪产业数据】.xlsx）"
            />
          </el-col>
        </el-row>
      </div>

      <!-- 涌益生产指标：五指标筛选 + 季节性图表（数据源：月度-生产指标2 F:J 列） -->
      <div class="chart-section">
        <div class="filter-section">
          <span class="filter-label">图例筛选：</span>
          <el-radio-group v-model="selectedProductionIndicator" @change="handleProductionIndicatorChange">
            <el-radio-button v-for="ind in yongyiIndicatorNames" :key="ind" :label="ind" />
            <el-radio-button label="全部">全部</el-radio-button>
          </el-radio-group>
        </div>
        <SeasonalityChart
          :data="yongyiProductionSeasonalityData"
          :loading="loadingProductionSeasonality"
          :title="yongyiChartTitle"
          source-name="涌益咨询周度数据 - 月度-生产指标2（F:J列）"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getA1SupplyForecastTable,
  getA1SowEfficiencyPressureSeasonality,
  getYongyiProductionSeasonality
} from '@/api/production-indicators'
import type { A1SupplyForecastTableResponse } from '@/api/production-indicators'
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import SeasonalityChart, { type SeasonalityData } from '@/components/SeasonalityChart.vue'

const loading = ref(false)
const tableData = ref<A1SupplyForecastTableResponse | null>(null)
const errorMessage = ref('')

const loadingSeasonality = ref(false)
const loadingProductionSeasonality = ref(false)
const sowEfficiencySeasonality = ref<SeasonalityData | null>(null)
const pressureCoefficientSeasonality = ref<SeasonalityData | null>(null)
const chartLatestDate = ref<string | null>(null)

const yongyiProductionSeasonalityRaw = ref<Record<string, SeasonalityData> | null>(null)
const yongyiIndicatorNames = ref<string[]>(['窝均健仔数', '产房存活率', '配种分娩率', '断奶成活率', '育肥出栏成活率'])
const selectedProductionIndicator = ref<string>('窝均健仔数')

const yongyiProductionSeasonalityData = computed((): SeasonalityData | null => {
  const raw = yongyiProductionSeasonalityRaw.value
  if (!raw) return null
  const ind = selectedProductionIndicator.value === '全部' ? '窝均健仔数' : selectedProductionIndicator.value
  return raw[ind] ?? null
})

const yongyiChartTitle = computed(() => {
  const ind = selectedProductionIndicator.value === '全部' ? '窝均健仔数' : selectedProductionIndicator.value
  return ind
})

/** 根据 merged_cells 和表头构建带合并信息的表头网格，用于渲染 */
const headerGrid = computed(() => {
  const td = tableData.value
  if (!td?.header_row_0?.length) return []
  const rows: (string[])[] = [td.header_row_0]
  if (td.header_row_1?.length) rows.push(td.header_row_1)
  if (td.header_row_2?.length) rows.push(td.header_row_2)
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

/** 表头列背景：母猪效能/新生仔猪=黄，5月大猪=绿，残差率/定点屠宰环比=橙 */
function getHeaderCellClass(_r: number, _c: number, cell: { value: string } | null): string {
  if (!cell?.value) return ''
  const v = String(cell.value)
  if (/母猪效能|新生仔猪/i.test(v)) return 'header-yellow'
  if (/5月大猪/i.test(v)) return 'header-green'
  if ((/残差率|定点屠宰/i.test(v) && /环比/i.test(v)) || v === '环比') return 'header-orange'
  return ''
}

/** 查找列的父级表头（合并时 row1 可能为空，向左查找） */
function getParentHeader(colIdx: number): string {
  const td = tableData.value
  if (!td?.header_row_1) return ''
  for (let c = colIdx; c >= 0; c--) {
    const v = String(td.header_row_1[c] ?? '').trim()
    if (v && !/^环比$|^同比$/.test(v)) return v
  }
  return String(td.header_row_0?.[colIdx] ?? '').trim()
}

/** 数据单元格：负值红色、环比/同比列、残差率/定点屠宰环比列橙色 */
function getDataCellClass(colIdx: number, _cell: unknown): string {
  const td = tableData.value
  if (!td) return ''
  const cls: string[] = []
  const h1 = td.header_row_1?.[colIdx] ?? ''
  const h2 = td.header_row_2?.[colIdx] ?? ''
  const isMomYoy = /环比|同比/.test(String(h1)) || /环比|同比/.test(String(h2))
  if (isMomYoy) cls.push('cell-mom-yoy')
  const parent = getParentHeader(colIdx)
  if ((/残差率|定点屠宰/.test(parent)) && /环比/.test(String(h2))) cls.push('cell-orange')
  const num = typeof _cell === 'number' ? _cell : parseFloat(String(_cell ?? ''))
  if (Number.isFinite(num) && num < 0) cls.push('cell-negative')
  return cls.join(' ')
}

function formatCell(val: unknown): string {
  if (val === null || val === undefined) return ''
  if (typeof val === 'number') return Number.isFinite(val) ? String(val) : ''
  return String(val).trim() || ''
}

/** 环比/同比列显示括号格式如 (0.3) */
function formatDataCell(colIdx: number, val: unknown): string {
  const s = formatCell(val)
  if (!s || s === '-') return s
  const td = tableData.value
  const h1 = td?.header_row_1?.[colIdx] ?? ''
  const h2 = td?.header_row_2?.[colIdx] ?? ''
  const isMomYoy = /环比|同比/.test(String(h1)) || /环比|同比/.test(String(h2))
  if (!isMomYoy) return s
  const num = parseFloat(s)
  if (!Number.isFinite(num)) return s
  return `(${num})`
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

async function loadSeasonalityData() {
  loadingSeasonality.value = true
  try {
    const res = await getA1SowEfficiencyPressureSeasonality()
    sowEfficiencySeasonality.value = res.sow_efficiency as SeasonalityData
    pressureCoefficientSeasonality.value = res.pressure_coefficient as SeasonalityData
    if (!chartLatestDate.value && (res.sow_efficiency.series?.length || res.pressure_coefficient.series?.length)) {
      const years = [
        ...(res.sow_efficiency.series?.map((s) => s.year) ?? []),
        ...(res.pressure_coefficient.series?.map((s) => s.year) ?? [])
      ]
      chartLatestDate.value = years.length ? `${Math.max(...years)}年` : null
    }
  } catch (e: any) {
    console.error('加载母猪效能/压栏系数季节性数据失败:', e)
    ElMessage.error('加载季节性数据失败: ' + (e?.message || '未知错误'))
    sowEfficiencySeasonality.value = null
    pressureCoefficientSeasonality.value = null
  } finally {
    loadingSeasonality.value = false
  }
}

async function loadProductionSeasonalityData() {
  loadingProductionSeasonality.value = true
  try {
    const res = await getYongyiProductionSeasonality()
    yongyiProductionSeasonalityRaw.value = res.indicators as Record<string, SeasonalityData>
    yongyiIndicatorNames.value = res.indicator_names
    if (!selectedProductionIndicator.value || !res.indicator_names.includes(selectedProductionIndicator.value)) {
      selectedProductionIndicator.value = res.indicator_names[0] ?? '窝均健仔数'
    }
  } catch (e: any) {
    console.error('加载涌益生产指标季节性失败:', e)
    ElMessage.error('加载涌益生产指标季节性失败: ' + (e?.message || '未知错误'))
    yongyiProductionSeasonalityRaw.value = null
  } finally {
    loadingProductionSeasonality.value = false
  }
}

function handleProductionIndicatorChange() {
  // computed 会自动更新，无需额外逻辑
}

onMounted(() => {
  loadTable()
  loadSeasonalityData()
  loadProductionSeasonalityData()
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
/* Excel 条件格式：表头列背景 */
.raw-excel-table thead th.header-yellow {
  background-color: #fff9e6;
}
.raw-excel-table thead th.header-green {
  background-color: #e8f5e9;
}
.raw-excel-table thead th.header-orange {
  background-color: #fff3e0;
}
.raw-excel-table tbody td {
  text-align: right;
}
.raw-excel-table tbody tr:nth-child(even) td {
  background-color: #fafafa;
}
/* 负值红色、环比同比列、残差率/定点屠宰环比橙色 */
.raw-excel-table tbody td.cell-negative {
  color: #f56c6c;
}
.raw-excel-table tbody td.cell-orange {
  background-color: #fff3e0 !important;
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
