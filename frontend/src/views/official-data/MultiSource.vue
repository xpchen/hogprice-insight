<template>
  <div class="multi-source-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>E2. 多渠道汇总</span>
          <DataSourceInfo
            v-if="latestMonth"
            source-name="涌益咨询、钢联、协会、NYB"
            :update-date="latestMonth"
          />
        </div>
      </template>

      <!-- 筛选框 -->
      <div class="filter-section">
        <div class="filter-row">
          <span class="filter-label">时间筛选：</span>
          <el-radio-group v-model="timeFilter" @change="handleTimeFilterChange">
            <el-radio label="all">全部</el-radio>
            <el-radio label="specific">特定时间周期</el-radio>
          </el-radio-group>
          <el-date-picker
            v-if="timeFilter === 'specific'"
            v-model="dateRange"
            type="monthrange"
            range-separator="至"
            start-placeholder="开始月份"
            end-placeholder="结束月份"
            @change="handleDateRangeChange"
            style="margin-left: 20px; width: 300px"
          />
        </div>
        <div class="filter-row" style="margin-top: 15px">
          <span class="filter-label">筛选框：</span>
          <el-checkbox-group v-model="selectedCategories" @change="handleCategoryChange">
            <el-checkbox label="能繁母猪">能繁母猪</el-checkbox>
            <el-checkbox label="新生仔猪">新生仔猪</el-checkbox>
            <el-checkbox label="中大猪存栏">中大猪存栏</el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="filter-row" style="margin-top: 15px">
          <span class="filter-label">显示月数：</span>
          <el-select v-model="selectedMonths" @change="handleMonthsChange" style="width: 120px">
            <el-option label="最近10个月" :value="10" />
            <el-option label="最近12个月" :value="12" />
            <el-option label="最近24个月" :value="24" />
            <el-option label="全部" :value="999" />
          </el-select>
          <span class="filter-hint" style="margin-left: 12px; color: #909399; font-size: 12px">淘汰母猪屠宰等若为「-」可试选「全部」查看历史月份</span>
        </div>
      </div>

      <!-- 表格1：淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比 -->
      <div class="table-section" v-if="showTable1">
        <h3>表格1：淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比</h3>
        <div class="table-container">
          <el-table
            :data="table1Data"
            border
            stripe
            v-loading="loading1"
            style="width: 100%"
            :row-class-name="tableRowClassName"
          >
            <el-table-column prop="month" label="月度" width="120" fixed="left">
            </el-table-column>
            <el-table-column label="淘汰母猪屠宰环比" align="center">
              <el-table-column prop="cull_slaughter_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.cull_slaughter_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column prop="cull_slaughter_ganglian" label="钢联" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.cull_slaughter_ganglian) }}
                </template>
              </el-table-column>
            </el-table-column>
            <el-table-column label="能繁母猪存栏环比" align="center">
              <el-table-column prop="breeding_inventory_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.breeding_inventory_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column label="钢联" align="center">
                <el-table-column prop="breeding_inventory_ganglian_nation" label="全国" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_ganglian_nation) }}
                  </template>
                </el-table-column>
                <el-table-column prop="breeding_inventory_ganglian_scale" label="规模场" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_ganglian_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="breeding_inventory_ganglian_small" label="中小散户" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_ganglian_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
              <el-table-column label="NYB" align="center">
                <el-table-column prop="breeding_inventory_nyb_nation" label="全国" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_nyb_nation ?? row.breeding_inventory_nyb) }}
                  </template>
                </el-table-column>
                <el-table-column prop="breeding_inventory_nyb_scale" label="规模场" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_nyb_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="breeding_inventory_nyb_small" label="散户" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.breeding_inventory_nyb_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table-column>
            <el-table-column label="能繁母猪饲料环比" align="center">
              <el-table-column prop="breeding_feed_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.breeding_feed_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column prop="breeding_feed_ganglian" label="钢联" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.breeding_feed_ganglian) }}
                </template>
              </el-table-column>
              <el-table-column prop="breeding_feed_association" label="协会" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.breeding_feed_association) }}
                </template>
              </el-table-column>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 表格2：新生仔猪存栏环比、仔猪饲料环比 -->
      <div class="table-section" v-if="showTable2" style="margin-top: 30px">
        <h3>表格2：新生仔猪存栏环比、仔猪饲料环比</h3>
        <div class="table-container">
          <el-table
            :data="table2Data"
            border
            stripe
            v-loading="loading2"
            style="width: 100%"
            :row-class-name="tableRowClassName"
          >
            <el-table-column prop="month" label="月度" width="120" fixed="left">
            </el-table-column>
            <el-table-column label="新生仔猪存栏环比" align="center">
              <el-table-column prop="piglet_inventory_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.piglet_inventory_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column label="钢联" align="center">
                <el-table-column prop="piglet_inventory_ganglian_nation" label="全国" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_ganglian_nation) }}
                  </template>
                </el-table-column>
                <el-table-column prop="piglet_inventory_ganglian_scale" label="规模场" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_ganglian_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="piglet_inventory_ganglian_small" label="中小散户" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_ganglian_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
              <el-table-column label="NYB" align="center">
                <el-table-column prop="piglet_inventory_nyb_nation" label="全国" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_nyb_nation ?? row.piglet_inventory_nyb) }}
                  </template>
                </el-table-column>
                <el-table-column prop="piglet_inventory_nyb_scale" label="规模场" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_nyb_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="piglet_inventory_nyb_small" label="散户" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.piglet_inventory_nyb_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table-column>
            <el-table-column label="仔猪饲料环比" align="center">
              <el-table-column prop="piglet_feed_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.piglet_feed_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column prop="piglet_feed_ganglian" label="钢联" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.piglet_feed_ganglian) }}
                </template>
              </el-table-column>
              <el-table-column prop="piglet_feed_association" label="协会" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.piglet_feed_association) }}
                </template>
              </el-table-column>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 表格3：生猪存栏环比、育肥猪饲料环比 -->
      <div class="table-section" v-if="showTable3" style="margin-top: 30px">
        <h3>表格3：生猪存栏环比、育肥猪饲料环比</h3>
        <div class="table-container">
          <el-table
            :data="table3Data"
            border
            stripe
            v-loading="loading3"
            style="width: 100%"
            :row-class-name="tableRowClassName"
          >
            <el-table-column prop="month" label="月度" width="120" fixed="left">
            </el-table-column>
            <el-table-column label="生猪存栏环比" align="center">
              <el-table-column prop="hog_inventory_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.hog_inventory_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column label="钢联" align="center">
                <el-table-column prop="hog_inventory_ganglian_nation" label="全国" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_ganglian_nation) }}
                  </template>
                </el-table-column>
                <el-table-column prop="hog_inventory_ganglian_scale" label="规模场" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_ganglian_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="hog_inventory_ganglian_small" label="中小散户" width="100" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_ganglian_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
              <el-table-column label="NYB" align="center">
                <el-table-column prop="hog_inventory_nyb_nation" label="全国" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_nyb_nation ?? row.hog_inventory_nyb) }}
                  </template>
                </el-table-column>
                <el-table-column prop="hog_inventory_nyb_scale" label="规模场" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_nyb_scale) }}
                  </template>
                </el-table-column>
                <el-table-column prop="hog_inventory_nyb_small" label="散户" width="90" align="right">
                  <template #default="{ row }">
                    {{ formatPercent(row.hog_inventory_nyb_small) }}
                  </template>
                </el-table-column>
              </el-table-column>
            </el-table-column>
            <el-table-column label="育肥猪饲料环比" align="center">
              <el-table-column prop="hog_feed_yongyi" label="涌益" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.hog_feed_yongyi) }}
                </template>
              </el-table-column>
              <el-table-column prop="hog_feed_ganglian" label="钢联" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.hog_feed_ganglian) }}
                </template>
              </el-table-column>
              <el-table-column prop="hog_feed_association" label="协会" width="100" align="right">
                <template #default="{ row }">
                  {{ formatPercent(row.hog_feed_association) }}
                </template>
              </el-table-column>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMultiSourceData } from '@/api/multi-source'
import type { MultiSourceResponse } from '@/api/multi-source'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const loading1 = ref(false)
const loading2 = ref(false)
const loading3 = ref(false)

const table1Data = ref<any[]>([])
const table2Data = ref<any[]>([])
const table3Data = ref<any[]>([])

const latestMonth = ref<string | null>(null)

// 筛选条件
const timeFilter = ref<'all' | 'specific'>('all')
const dateRange = ref<[Date, Date] | null>(null)
const selectedCategories = ref<string[]>(['能繁母猪', '新生仔猪', '中大猪存栏'])
const selectedMonths = ref(24)

// 计算显示的表格
const showTable1 = computed(() => selectedCategories.value.includes('能繁母猪'))
const showTable2 = computed(() => selectedCategories.value.includes('新生仔猪'))
const showTable3 = computed(() => selectedCategories.value.includes('中大猪存栏'))

// 表格行样式（隔一行灰色）
const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  if (rowIndex % 2 === 1) {
    return 'gray-row'
  }
  return ''
}

// 加载数据
const loadData = async () => {
  loading1.value = true
  loading2.value = true
  loading3.value = true
  
  try {
    const response = await getMultiSourceData(selectedMonths.value)
    
    // 根据时间筛选过滤数据
    let filteredData = response.data
    if (timeFilter.value === 'specific' && dateRange.value) {
      const [start, end] = dateRange.value
      const startStr = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}`
      const endStr = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}`
      filteredData = filteredData.filter(d => d.month >= startStr && d.month <= endStr)
    }
    
    // 按月份排序（最新的在前）
    filteredData.sort((a, b) => b.month.localeCompare(a.month))
    
    // 限制显示月数
    if (selectedMonths.value !== 999) {
      filteredData = filteredData.slice(0, selectedMonths.value)
    }
    
    // 反转顺序（最新的在后，便于查看）
    filteredData.reverse()
    
    table1Data.value = filteredData
    table2Data.value = filteredData
    table3Data.value = filteredData
    
    latestMonth.value = response.latest_month
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading1.value = false
    loading2.value = false
    loading3.value = false
  }
}

// 筛选变化处理
const handleTimeFilterChange = () => {
  loadData()
}

const handleDateRangeChange = () => {
  loadData()
}

const handleCategoryChange = () => {
  // 类别变化不需要重新加载数据，只需要控制表格显示
}

const handleMonthsChange = () => {
  loadData()
}

// 格式化百分比
const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.multi-source-page {
  .filter-section {
    margin-bottom: 30px;
    padding: 15px;
    background-color: #f5f7fa;
    border-radius: 4px;
    
    .filter-row {
      display: flex;
      align-items: center;
      
      .filter-label {
        font-weight: 500;
        margin-right: 10px;
        min-width: 80px;
      }
    }
  }

  .table-section {
    margin-bottom: 30px;
    
    h3 {
      margin-bottom: 15px;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .table-container {
    margin-bottom: 20px;
  }
}

:deep(.gray-row) {
  background-color: #f5f7fa;
}
</style>
