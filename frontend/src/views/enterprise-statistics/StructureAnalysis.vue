<template>
  <div class="structure-analysis-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D4. 结构分析</span>
          <DataSourceInfo
            v-if="latestMonth"
            source-name="企业集团出栏跟踪、涌益咨询、钢联、农业部、定点企业屠宰"
            :update-date="latestMonth"
          />
        </div>
      </template>

      <!-- 表格容器 -->
      <div class="table-container">
        <el-table
          :data="tableData"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          :header-cell-style="{ background: '#f5f7fa', color: '#606266', textAlign: 'center' }"
          default-sort="{ prop: 'month', order: 'descending' }"
        >
          <!-- 月度列 -->
          <el-table-column prop="month" label="月度" width="120" align="center" fixed="left" sortable />
          
          <!-- CR20集团列 -->
          <el-table-column prop="cr20" label="CR20集团" width="120" align="center">
            <template #default="{ row }">
              <span v-if="row.cr20 !== null && row.cr20 !== undefined">
                {{ formatValue(row.cr20) }}%
              </span>
              <span v-else class="empty-cell">-</span>
            </template>
          </el-table-column>
          
          <!-- 出栏环比列组 -->
          <el-table-column label="出栏环比" align="center">
            <!-- 涌益 -->
            <el-table-column prop="yongyi" label="涌益" width="120" align="center">
              <template #default="{ row }">
                <span v-if="row.yongyi !== null && row.yongyi !== undefined">
                  {{ formatValue(row.yongyi) }}%
                </span>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>
            
            <!-- 钢联 -->
            <el-table-column prop="ganglian" label="钢联" width="120" align="center">
              <template #default="{ row }">
                <span v-if="row.ganglian !== null && row.ganglian !== undefined">
                  {{ formatValue(row.ganglian) }}%
                </span>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>
            
            <!-- 农业部规模场 -->
            <el-table-column prop="ministry_scale" label="农业部规模场" width="140" align="center">
              <template #default="{ row }">
                <span v-if="row.ministry_scale !== null && row.ministry_scale !== undefined">
                  {{ formatValue(row.ministry_scale) }}%
                </span>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>
            
            <!-- 农业部散户 -->
            <el-table-column prop="ministry_scattered" label="农业部散户" width="140" align="center">
              <template #default="{ row }">
                <span v-if="row.ministry_scattered !== null && row.ministry_scattered !== undefined">
                  {{ formatValue(row.ministry_scattered) }}%
                </span>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>
          </el-table-column>
          
          <!-- 屠宰环比列组 -->
          <el-table-column label="屠宰环比" align="center">
            <!-- 定点企业 -->
            <el-table-column prop="slaughter" label="定点企业" width="120" align="center">
              <template #default="{ row }">
                <span v-if="row.slaughter !== null && row.slaughter !== undefined">
                  {{ formatValue(row.slaughter) }}%
                </span>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStructureAnalysisTable } from '@/api/structure-analysis'
import type { StructureTableResponse, StructureTableRow } from '@/api/structure-analysis'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const loading = ref(false)
const tableData = ref<StructureTableRow[]>([])
const latestMonth = ref<string | null>(null)

// 格式化数值显示
const formatValue = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const response = await getStructureAnalysisTable()
    // 按月份倒序排列，显示最新的数据在前面
    const sortedData = (response.data || []).sort((a, b) => {
      return b.month.localeCompare(a.month)
    })
    tableData.value = sortedData
    latestMonth.value = response.latest_month || null
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 组件挂载
onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.structure-analysis-page {
  .table-container {
    margin-top: 20px;
    
    .empty-cell {
      color: #c0c4cc;
    }
  }
}
</style>
