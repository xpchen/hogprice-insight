<template>
  <div class="data-reconciliation">
    <el-card>
      <template #header>
        <span>数据对账</span>
      </template>

      <!-- 筛选条件 -->
      <el-form :model="filters" inline style="margin-bottom: 20px">
        <el-form-item label="指标代码">
          <el-input v-model="filters.indicator_code" placeholder="请输入指标代码" clearable />
        </el-form-item>
        <el-form-item label="区域代码">
          <el-input v-model="filters.region_code" placeholder="请输入区域代码" clearable />
        </el-form-item>
        <el-form-item label="频率">
          <el-select v-model="filters.freq" clearable>
            <el-option label="日频" value="D" />
            <el-option label="周频" value="W" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadReconciliation">查询</el-button>
          <el-button @click="exportResults">导出</el-button>
        </el-form-item>
      </el-form>

      <!-- Tab切换 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 缺失日期 -->
        <el-tab-pane label="缺失日期" name="missing">
          <el-table :data="missingDates" style="width: 100%">
            <el-table-column prop="indicator_code" label="指标代码" />
            <el-table-column prop="region_code" label="区域代码" />
            <el-table-column prop="freq" label="频率" />
            <el-table-column prop="total_missing" label="缺失数量" />
            <el-table-column label="缺失日期">
              <template #default="{ row }">
                <el-tag
                  v-for="date in row.missing_dates.slice(0, 10)"
                  :key="date"
                  size="small"
                  style="margin-right: 4px; margin-bottom: 4px"
                >
                  {{ date }}
                </el-tag>
                <span v-if="row.missing_dates.length > 10">
                  ... 共{{ row.missing_dates.length }}个
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 重复记录 -->
        <el-tab-pane label="重复记录" name="duplicates">
          <el-table :data="duplicates" style="width: 100%">
            <el-table-column prop="indicator_code" label="指标代码" />
            <el-table-column prop="region_code" label="区域代码" />
            <el-table-column prop="date" label="日期" />
            <el-table-column prop="count" label="重复次数" />
          </el-table>
        </el-tab-pane>

        <!-- 异常值 -->
        <el-tab-pane label="异常值" name="anomalies">
          <el-form :model="anomalyFilters" inline style="margin-bottom: 20px">
            <el-form-item label="最小值阈值">
              <el-input-number v-model="anomalyFilters.min" :precision="2" />
            </el-form-item>
            <el-form-item label="最大值阈值">
              <el-input-number v-model="anomalyFilters.max" :precision="2" />
            </el-form-item>
            <el-form-item label="标准差倍数">
              <el-input-number v-model="anomalyFilters.std_multiplier" :precision="1" :min="1" :max="10" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadAnomalies">查询异常值</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="anomalies" style="width: 100%">
            <el-table-column prop="indicator_code" label="指标代码" />
            <el-table-column prop="region_code" label="区域代码" />
            <el-table-column prop="date" label="日期" />
            <el-table-column prop="value" label="值" />
            <el-table-column prop="mean" label="均值" />
            <el-table-column prop="std" label="标准差" />
            <el-table-column prop="deviation" label="偏差倍数">
              <template #default="{ row }">
                <el-tag :type="Math.abs(row.deviation) > 3 ? 'danger' : 'warning'">
                  {{ row.deviation.toFixed(2) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { reconciliationApi } from '../api/reconciliation'

const filters = ref({
  indicator_code: '',
  region_code: '',
  freq: 'D'
})

const activeTab = ref('missing')
const missingDates = ref<any[]>([])
const duplicates = ref<any[]>([])
const anomalies = ref<any[]>([])

const anomalyFilters = ref({
  min: undefined as number | undefined,
  max: undefined as number | undefined,
  std_multiplier: 3.0
})

const loadReconciliation = async () => {
  if (activeTab.value === 'missing') {
    await loadMissingDates()
  } else if (activeTab.value === 'duplicates') {
    await loadDuplicates()
  } else if (activeTab.value === 'anomalies') {
    await loadAnomalies()
  }
}

const loadMissingDates = async () => {
  if (!filters.value.indicator_code) {
    ElMessage.warning('请输入指标代码')
    return
  }

  try {
    const result = await reconciliationApi.getMissingDates({
      indicator_code: filters.value.indicator_code,
      region_code: filters.value.region_code || undefined,
      freq: filters.value.freq
    })
    
    missingDates.value = [{
      indicator_code: result.indicator_code,
      region_code: result.region_code,
      freq: result.freq,
      total_missing: result.total_missing,
      missing_dates: result.missing_dates
    }]
  } catch (error) {
    ElMessage.error('加载缺失日期失败')
    console.error(error)
  }
}

const loadDuplicates = async () => {
  if (!filters.value.indicator_code) {
    ElMessage.warning('请输入指标代码')
    return
  }

  try {
    const result = await reconciliationApi.getDuplicates({
      indicator_code: filters.value.indicator_code,
      region_code: filters.value.region_code || undefined,
      freq: filters.value.freq
    })
    
    duplicates.value = result.duplicates
  } catch (error) {
    ElMessage.error('加载重复记录失败')
    console.error(error)
  }
}

const loadAnomalies = async () => {
  if (!filters.value.indicator_code) {
    ElMessage.warning('请输入指标代码')
    return
  }

  try {
    const result = await reconciliationApi.getAnomalies({
      indicator_code: filters.value.indicator_code,
      region_code: filters.value.region_code || undefined,
      min_value: anomalyFilters.value.min,
      max_value: anomalyFilters.value.max,
      std_multiplier: anomalyFilters.value.std_multiplier
    })
    
    anomalies.value = result.anomalies.map((a: any) => ({
      ...a,
      date: a.date
    }))
  } catch (error) {
    ElMessage.error('加载异常值失败')
    console.error(error)
  }
}

const handleTabChange = (tab: string) => {
  if (tab === 'missing') {
    loadMissingDates()
  } else if (tab === 'duplicates') {
    loadDuplicates()
  } else if (tab === 'anomalies') {
    loadAnomalies()
  }
}

const exportResults = () => {
  // 导出对账结果（简化实现）
  ElMessage.info('导出功能开发中')
}

onMounted(() => {
  // 默认加载缺失日期
  // loadMissingDates()
})
</script>

<style scoped>
.data-reconciliation {
  padding: 20px;
}
</style>
