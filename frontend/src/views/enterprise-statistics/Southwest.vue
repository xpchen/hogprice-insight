<template>
  <div class="southwest-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>重点省份旬度</span>
          <DataSourceInfo
            v-if="tableData && tableData.update_time"
            :source-name="tableData.data_source || '企业集团出栏跟踪'"
            :update-date="tableData.update_time"
          />
        </div>
      </template>

      <!-- 时间范围选择 -->
      <div class="date-range-selector">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="handleDateRangeChange"
        />
        <el-button
          type="primary"
          size="small"
          @click="loadDefaultRange"
          style="margin-left: 10px"
        >
          最近4个月
        </el-button>
      </div>

      <!-- 表格容器：多表头，相同省份合并 -->
      <div class="table-container" ref="tableContainerRef">
        <el-table
          :data="allRows"
          border
          stripe
          v-loading="loading"
          height="500"
          style="width: 100%"
        >
          <el-table-column prop="date" label="日期" width="120" fixed="left" align="center">
            <template #default="{ row }">
              {{ formatDate(row.date) }}
            </template>
          </el-table-column>
          <el-table-column prop="period_type" label="旬度" width="80" fixed="left" align="center">
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
              width="110"
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
      <div v-if="hasMoreData" class="scroll-hint">
        <el-icon><ArrowRight /></el-icon>
        <span>表格共 {{ allRows.length }} 行数据，可滚动查看</span>
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

// 表格容器引用
const tableContainerRef = ref<HTMLDivElement>()


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

// 是否有更多数据（用于滚动提示）
const hasMoreData = computed(() => {
  // 表格高度600px，每行约40px，大约可显示15行，如果数据超过15行，显示提示
  return allRows.value.length > 15
})

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
  padding: 20px;
}

.date-range-selector {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.table-container {
  margin-top: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.scroll-hint {
  margin-top: 10px;
  text-align: center;
  color: #909399;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

:deep(.el-table) {
  font-size: 12px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 8px 0;
}
</style>
