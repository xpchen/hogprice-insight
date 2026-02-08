<template>
  <div class="sales-plan-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D3. 销售计划</span>
          <DataSourceInfo
            v-if="tableData && tableData.update_time"
            :source-name="tableData.data_source || '企业集团出栏跟踪、涌益咨询、钢联'"
            :update-date="tableData.update_time"
          />
        </div>
      </template>

      <!-- 筛选框 -->
      <div class="filters">
        <!-- 第一排：指标筛选 -->
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

        <!-- 第二排：区域筛选 -->
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

      <!-- 数据表格 -->
      <div class="table-container">
        <el-table
          :data="displayData"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          height="500"
        >
          <el-table-column prop="date" label="日期" width="120" fixed="left">
            <template #default="{ row }">
              {{ formatDate(row.date) }}
            </template>
          </el-table-column>
          <el-table-column prop="region" label="区域" width="100" fixed="left">
          </el-table-column>
          <el-table-column prop="source" label="数据来源" width="150">
          </el-table-column>
          <el-table-column prop="actual_output" label="当月出栏量" width="120" align="right">
            <template #default="{ row }">
              {{ formatValue(row.actual_output) }}
            </template>
          </el-table-column>
          <el-table-column prop="plan_output" label="当月计划" width="120" align="right">
            <template #default="{ row }">
              {{ formatValue(row.plan_output) }}
            </template>
          </el-table-column>
          <el-table-column prop="month_on_month" label="当月环比" width="120" align="right">
            <template #default="{ row }">
              {{ formatPercent(row.month_on_month) }}
            </template>
          </el-table-column>
          <el-table-column prop="plan_on_plan" label="计划环比" width="120" align="right">
            <template #default="{ row }">
              {{ formatPercent(row.plan_on_plan) }}
            </template>
          </el-table-column>
          <el-table-column prop="plan_completion_rate" label="计划达成率" width="120" align="right">
            <template #default="{ row }">
              {{ formatPercent(row.plan_completion_rate) }}
            </template>
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

// 筛选状态
const selectedIndicator = ref('全部')
const selectedRegion = ref('全部')

// 数据状态
const loading = ref(false)
const tableData = ref<SalesPlanResponse | null>(null)
const allData = ref<SalesPlanDataPoint[]>([])

// 显示的数据（根据筛选条件）
const displayData = computed(() => {
  let filtered = [...allData.value]
  
  // 根据指标筛选
  if (selectedIndicator.value !== '全部') {
    filtered = filtered.filter(item => {
      if (selectedIndicator.value === '当月环比') {
        return item.month_on_month !== null && item.month_on_month !== undefined
      } else if (selectedIndicator.value === '计划环比') {
        return item.plan_on_plan !== null && item.plan_on_plan !== undefined
      } else if (selectedIndicator.value === '计划达成率') {
        return item.plan_completion_rate !== null && item.plan_completion_rate !== undefined
      } else if (selectedIndicator.value === '当月出栏量') {
        return item.actual_output !== null && item.actual_output !== undefined
      }
      return true
    })
  }
  
  // 根据区域筛选
  if (selectedRegion.value !== '全部') {
    filtered = filtered.filter(item => item.region === selectedRegion.value)
  }
  
  return filtered
})

// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 格式化数值
const formatValue = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

// 格式化百分比
const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return (value * 100).toFixed(2) + '%'
}

// 筛选变化处理
const handleFilterChange = () => {
  // 数据已经在computed中自动筛选，这里可以添加其他逻辑
}

// 加载数据
const loadData = async () => {
  loading.value = true
  
  try {
    const data = await getSalesPlanData(selectedIndicator.value, selectedRegion.value)
    tableData.value = data
    allData.value = data.data
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
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
  padding: 20px;
}

.filters {
  margin-bottom: 20px;
}

.filter-row {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.filter-label {
  width: 60px;
  font-weight: 600;
  color: #606266;
}

.table-container {
  margin-top: 20px;
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
}

:deep(.el-table td) {
  padding: 8px 0;
}
</style>
