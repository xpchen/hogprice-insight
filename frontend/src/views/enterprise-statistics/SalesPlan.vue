<template>
  <div class="sales-plan-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D3. 销售计划</span>
          <DataSourceInfo
            v-if="tableData && (tableData.latest_date || tableData.update_time)"
            :source-name="tableData.data_source || '企业集团出栏跟踪、涌益咨询、钢联'"
            :update-date="formatUpdateDate(tableData.latest_date) || tableData.update_time"
          />
        </div>
      </template>

      <!-- 筛选框 -->
      <div class="filters">
        <div class="filter-row">
          <span class="filter-label">指标：</span>
          <el-radio-group v-model="selectedIndicator" @change="handleFilterChange">
            <el-radio-button label="全部">全部</el-radio-button>
            <el-radio-button label="当月环比">当月环比</el-radio-button>
            <el-radio-button label="计划环比">计划环比</el-radio-button>
            <el-radio-button label="计划达成率">计划达成率</el-radio-button>
            <el-radio-button label="当月出栏量">当月出栏量</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-row">
          <span class="filter-label">区域：</span>
          <el-radio-group v-model="selectedRegion" @change="handleFilterChange">
            <el-radio-button label="全部">全部</el-radio-button>
            <el-radio-button label="全国CR20">全国CR20</el-radio-button>
            <el-radio-button label="全国CR5">全国CR5</el-radio-button>
            <el-radio-button label="涌益">涌益</el-radio-button>
            <el-radio-button label="钢联">钢联</el-radio-button>
            <el-radio-button label="广东">广东</el-radio-button>
            <el-radio-button label="四川">四川</el-radio-button>
            <el-radio-button label="贵州">贵州</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 数据表格：根据筛选显示不同布局 -->
      <div class="table-container">
        <!-- 模式A：单指标 + 全部区域 → 按区域透视为列 -->
        <el-table
          v-if="isModeA"
          :data="pivotedByRegion"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          max-height="calc(100vh - 320px)"
        >
          <el-table-column prop="date" label="日期" width="120" fixed="left" align="center">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column
            v-for="r in regionColumns"
            :key="r"
            :prop="r"
            :label="r"
            min-width="90"
            align="right"
          >
            <template #default="{ row }">{{ formatCell(row[r]) }}</template>
          </el-table-column>
        </el-table>

        <!-- 模式B：全部指标 + 全部区域 → 按区域分组，每区域5列 -->
        <el-table
          v-else-if="isModeB"
          :data="pivotedByRegionMetric"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          max-height="calc(100vh - 320px)"
        >
          <el-table-column prop="date" label="日期" width="120" fixed="left" align="center">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column
            v-for="col in regionMetricColumns"
            :key="col.key"
            :prop="col.key"
            :label="col.label"
            min-width="85"
            align="right"
          >
            <template #default="{ row }">{{ formatCellByMetric(row[col.key], col.metric) }}</template>
          </el-table-column>
        </el-table>

        <!-- 模式C：单区域 → 常规列，无区域/数据来源 -->
        <el-table
          v-else
          :data="displayData"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          max-height="calc(100vh - 320px)"
        >
          <el-table-column prop="date" label="日期" width="120" fixed="left" align="center">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column prop="actual_output" label="当月出栏量" min-width="100" align="right">
            <template #default="{ row }">{{ formatValue(row.actual_output) }}</template>
          </el-table-column>
          <el-table-column prop="plan_output" label="当月计划" min-width="100" align="right">
            <template #default="{ row }">{{ formatValue(row.plan_output) }}</template>
          </el-table-column>
          <el-table-column prop="month_on_month" label="当月环比" min-width="90" align="right">
            <template #default="{ row }">{{ formatPercent(row.month_on_month) }}</template>
          </el-table-column>
          <el-table-column prop="plan_on_plan" label="计划环比" min-width="90" align="right">
            <template #default="{ row }">{{ formatPercent(row.plan_on_plan) }}</template>
          </el-table-column>
          <el-table-column prop="plan_completion_rate" label="计划达成率" min-width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.plan_completion_rate) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSalesPlanData } from '@/api/sales-plan'
import type { SalesPlanResponse, SalesPlanDataPoint } from '@/api/sales-plan'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const selectedIndicator = ref('全部')
const selectedRegion = ref('全部')
const loading = ref(false)
const tableData = ref<SalesPlanResponse | null>(null)
const allData = ref<SalesPlanDataPoint[]>([])

const METRICS = ['当月出栏量', '当月计划', '当月环比', '计划环比', '计划达成率'] as const
const METRIC_KEYS: Record<string, keyof SalesPlanDataPoint> = {
  '当月出栏量': 'actual_output',
  '当月计划': 'plan_output',
  '当月环比': 'month_on_month',
  '计划环比': 'plan_on_plan',
  '计划达成率': 'plan_completion_rate'
}

const isModeA = computed(() => selectedIndicator.value !== '全部' && selectedRegion.value === '全部')
const isModeB = computed(() => selectedIndicator.value === '全部' && selectedRegion.value === '全部')

const displayData = computed(() => {
  let filtered = [...allData.value]
  if (selectedIndicator.value !== '全部') {
    const key = METRIC_KEYS[selectedIndicator.value]
    if (key) filtered = filtered.filter(item => item[key] != null)
  }
  if (selectedRegion.value !== '全部') {
    filtered = filtered.filter(item => item.region === selectedRegion.value)
  }
  return filtered
})

const regionColumns = computed(() => {
  const set = new Set<string>()
  allData.value.forEach(item => set.add(item.region))
  return Array.from(set).sort((a, b) => {
    const order = ['涌益', '钢联', '全国CR20', '全国CR5', '广东', '四川', '贵州']
    const ia = order.indexOf(a)
    const ib = order.indexOf(b)
    if (ia >= 0 && ib >= 0) return ia - ib
    if (ia >= 0) return -1
    if (ib >= 0) return 1
    return a.localeCompare(b)
  })
})

const pivotedByRegion = computed(() => {
  if (!isModeA.value) return []
  const key = METRIC_KEYS[selectedIndicator.value] as keyof SalesPlanDataPoint
  if (!key) return []
  const regions = regionColumns.value
  const byDate = new Map<string, Record<string, any>>()
  displayData.value.forEach(item => {
    if (!byDate.has(item.date)) {
      const row: Record<string, any> = { date: item.date }
      regions.forEach(r => { row[r] = null })
      byDate.set(item.date, row)
    }
    const row = byDate.get(item.date)!
    const v = item[key]
    row[item.region] = typeof v === 'number' ? v : null
  })
  return Array.from(byDate.values()).sort((a, b) => b.date.localeCompare(a.date))
})

const regionMetricColumns = computed(() => {
  const regions = regionColumns.value
  const cols: { key: string; label: string; metric: string }[] = []
  regions.forEach(r => {
    METRICS.forEach(m => {
      cols.push({ key: `${r}-${m}`, label: `${r}-${m}`, metric: m })
    })
  })
  return cols
})

const pivotedByRegionMetric = computed(() => {
  if (!isModeB.value) return []
  const regions = regionColumns.value
  const byDate = new Map<string, Record<string, any>>()
  displayData.value.forEach(item => {
    if (!byDate.has(item.date)) {
      const row: Record<string, any> = { date: item.date }
      regions.forEach(r => METRICS.forEach(m => { row[`${r}-${m}`] = null }))
      byDate.set(item.date, row)
    }
    const row = byDate.get(item.date)!
    METRICS.forEach(m => {
      const k = METRIC_KEYS[m]
      const v = item[k as keyof SalesPlanDataPoint]
      row[`${item.region}-${m}`] = v
    })
  })
  return Array.from(byDate.values()).sort((a, b) => b.date.localeCompare(a.date))
})

const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const formatValue = (v: number | null | undefined): string => {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const formatPercent = (v: number | null | undefined): string => {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}

const formatCell = (v: number | null | undefined): string => {
  if (v == null) return '-'
  if (selectedIndicator.value === '当月出栏量' || selectedIndicator.value === '当月计划') return formatValue(v)
  return formatPercent(v)
}

const formatCellByMetric = (v: number | null | undefined, metric: string): string => {
  if (v == null) return '-'
  if (metric === '当月出栏量' || metric === '当月计划') return formatValue(v)
  return formatPercent(v)
}

const formatUpdateDate = (dateStr: string | null | undefined): string | null => {
  if (!dateStr || dateStr.includes('年')) return dateStr || null
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return null
    return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`
  } catch {
    return null
  }
}

const handleFilterChange = () => {
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await getSalesPlanData(selectedIndicator.value, selectedRegion.value)
    tableData.value = data
    allData.value = data.data || []
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.sales-plan-page {
  padding: 8px;
}

.sales-plan-page :deep(.el-card__body) {
  padding: 8px 12px;
}

.filters {
  margin-bottom: 12px;
}

.filter-row {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-label {
  width: 48px;
  font-weight: 600;
  color: #606266;
  flex-shrink: 0;
}

.table-container {
  margin-top: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.el-table) {
  font-size: 12px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
  padding: 4px 0;
}

:deep(.el-table td) {
  padding: 4px 0;
}
</style>
