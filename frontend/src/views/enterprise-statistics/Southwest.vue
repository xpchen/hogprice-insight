<template>
  <div class="southwest-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D2.重点省份出栏统计</span>
          <DataSourceInfo
            v-if="tableData && (tableData.latest_date || tableData.update_time)"
            :source-name="tableData.data_source || '企业集团出栏跟踪'"
            :update-date="formatUpdateDate(tableData.latest_date) || tableData.update_time"
          />
        </div>
      </template>

      <!-- 时间范围 + 旬度筛选 -->
      <div class="filter-row">
        <div class="date-range-selector">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            size="small"
            @change="handleDateRangeChange"
          />
          <el-button type="primary" size="small" @click="loadDefaultRange">
            最近4个月
          </el-button>
        </div>
        <div class="period-filter">
          <span class="filter-label">旬度筛选：</span>
          <el-checkbox-group v-model="periodTypeFilter" size="small">
            <el-checkbox label="上旬">上旬</el-checkbox>
            <el-checkbox label="中旬">中旬</el-checkbox>
            <el-checkbox label="月度">月度</el-checkbox>
          </el-checkbox-group>
        </div>
      </div>

      <!-- 表格容器：多表头，表头固定 -->
      <div class="table-container" ref="tableContainerRef">
        <el-table
          :data="filteredRows"
          border
          stripe
          v-loading="loading"
          max-height="calc(100vh - 200px)"
          style="width: 100%"
        >
          <el-table-column prop="date" label="日期" width="90" fixed="left" align="center">
            <template #default="{ row }">
              {{ formatDate(row.date) }}
            </template>
          </el-table-column>
          <el-table-column prop="period_type" label="旬度" width="60" fixed="left" align="center">
            <template #default="{ row }">
              {{ row.period_type || '-' }}
            </template>
          </el-table-column>
          <!-- 按省份分组的表头：一级为省份，二级为指标 -->
          <el-table-column
            v-for="prov in provinceHeaderGroups"
            :key="prov.province"
            :label="prov.province"
            align="center"
            header-align="center"
          >
            <el-table-column
              v-for="col in prov.columns"
              :key="col.key"
              :prop="col.key"
              :label="col.label"
              min-width="65"
              align="right"
              header-align="center"
            >
              <template #default="{ row }">
                {{ formatValue(row[col.key], col.key) }}
              </template>
            </el-table-column>
          </el-table-column>
        </el-table>
      </div>

      <!-- 滚动提示 -->
      <div v-if="filteredRows.length > 12" class="scroll-hint">
        <el-icon><ArrowRight /></el-icon>
        <span>表格共 {{ filteredRows.length }} 行数据，表头固定可滚动查看</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { getProvinceSummaryTable } from '@/api/enterprise-statistics'
import type { ProvinceSummaryTableResponse } from '@/api/enterprise-statistics'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

// 加载状态
const loading = ref(false)

// 数据
const tableData = ref<ProvinceSummaryTableResponse | null>(null)
const allRows = ref<any[]>([])

// 日期范围（默认最近4个月）
const dateRange = ref<[string, string] | null>(null)

// 旬度筛选（默认全选）
const periodTypeFilter = ref<string[]>(['上旬', '中旬', '月度'])

// 表格容器引用
const tableContainerRef = ref<HTMLDivElement>()

// 按旬度筛选后的行数据
const filteredRows = computed(() => {
  const sel = periodTypeFilter.value
  if (!sel || sel.length === 0 || sel.length === 3) return allRows.value
  return allRows.value.filter(row => sel.includes(row.period_type || ''))
})


// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}-${day}`
}

// 格式化数值
const formatValue = (value: number | null | undefined, columnKey?: string): string => {
  if (value === null || value === undefined) return '-'
  
  // 如果是百分比（计划完成率），显示2位小数
  if (columnKey && (columnKey.includes('完成率') || columnKey.includes('达成率'))) {
    return (value * 100).toFixed(2) + '%'
  }
  
  // 如果是价格或均重，显示2位小数
  if (columnKey && (columnKey.includes('均价') || columnKey.includes('均重'))) {
    return value.toFixed(2)
  }
  
  // 其他数值显示整数
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

// 格式化更新日期
const formatUpdateDate = (dateStr: string | null | undefined): string | null => {
  if (!dateStr) return null
  try {
    // 如果已经是格式化后的字符串（包含"年"），直接返回
    if (dateStr.includes('年')) {
      return dateStr
    }
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) {
      return null
    }
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}年${month}月${day}日`
  } catch {
    return null
  }
}


// 多表头：按省份分组，相同省份合并为一级表头
// 列名格式为 "省份-指标"，如 "广东-出栏计划"、"四川-实际出栏量"
const provinceHeaderGroups = computed(() => {
  if (!tableData.value || !tableData.value.columns) {
    return []
  }
  const dataCols = tableData.value.columns.filter(
    (col: string) => col !== '日期' && col !== '旬度'
  )
  const groupMap = new Map<string, Array<{ key: string; label: string }>>()
  for (const col of dataCols) {
    const idx = col.indexOf('-')
    const province = idx > 0 ? col.slice(0, idx) : '其他'
    const label = idx > 0 ? col.slice(idx + 1) : col
    if (!groupMap.has(province)) {
      groupMap.set(province, [])
    }
    groupMap.get(province)!.push({ key: col, label })
  }
  // 保持列顺序：按首次出现的省份顺序
  const order: string[] = []
  for (const col of dataCols) {
    const idx = col.indexOf('-')
    const province = idx > 0 ? col.slice(0, idx) : '其他'
    if (!order.includes(province)) order.push(province)
  }
  return order.map(province => ({
    province,
    columns: groupMap.get(province) || []
  }))
})

// 加载默认时间范围（最近4个月）
// 不传日期范围，让后端自动使用数据的最新日期
const loadDefaultRange = async () => {
  // 不设置dateRange，让后端自动计算
  dateRange.value = null
  
  await handleDateRangeChange(null)
}

// 日期范围变化
const handleDateRangeChange = async (range: [string, string] | null) => {
  loading.value = true
  
  try {
    // 如果传入了日期范围，使用传入的日期；否则不传参数，让后端自动使用数据的最新日期
    const startDate = range && range.length === 2 ? range[0] : undefined
    const endDate = range && range.length === 2 ? range[1] : undefined
    
    const data = await getProvinceSummaryTable(startDate, endDate)
    tableData.value = data
    // 确保rows中包含period_type字段
    allRows.value = (data.rows || []).map(row => ({
      ...row,
      period_type: row.period_type || '月度'  // 如果没有旬度信息，默认为月度
    }))
    
    // 如果后端返回了latest_date，更新dateRange显示
    if (data.latest_date && !range) {
      // 从latest_date往前推4个月
      const latestDate = new Date(data.latest_date)
      const startDate = new Date(latestDate)
      startDate.setMonth(startDate.getMonth() - 4)
      
      dateRange.value = [
        startDate.toISOString().split('T')[0],
        latestDate.toISOString().split('T')[0]
      ]
    }
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 默认加载最近4个月的数据
  loadDefaultRange()
})
</script>

<style scoped>
.southwest-page {
  padding: 4px;
}

.southwest-page :deep(.el-card__body) {
  padding: 4px 8px;
}

.southwest-page :deep(.el-card__header) {
  padding: 6px 12px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.date-range-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.period-filter {
  display: flex;
  align-items: center;
  gap: 6px;
}

.period-filter .filter-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
}

.table-container {
  margin-top: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.scroll-hint {
  margin-top: 4px;
  text-align: center;
  color: #909399;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

:deep(.el-table) {
  font-size: 11px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
  padding: 2px 4px;
}

:deep(.el-table td) {
  padding: 1px 4px;
}

:deep(.el-table .cell) {
  padding: 2px 4px;
}
</style>
