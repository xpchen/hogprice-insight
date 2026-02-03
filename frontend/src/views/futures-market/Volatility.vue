<template>
  <div class="volatility-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>C4. 波动率数据</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <el-select v-model="selectedContract" size="small" @change="loadData" style="width: 120px">
              <el-option label="全部合约" :value="null" />
              <el-option v-for="month in contractMonths" :key="month" :label="`${month.toString().padStart(2, '0')}合约`" :value="month" />
            </el-select>
            <el-button size="small" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-card style="margin-bottom: 20px">
        <template #header>
          <span>筛选条件</span>
        </template>
        <el-form :model="filters" inline>
          <el-form-item label="5日波动率范围">
            <el-input-number v-model="filters.min_volatility_5d" :precision="2" :step="0.1" placeholder="最小值" style="width: 120px" />
            <span style="margin: 0 10px">-</span>
            <el-input-number v-model="filters.max_volatility_5d" :precision="2" :step="0.1" placeholder="最大值" style="width: 120px" />
          </el-form-item>
          <el-form-item label="10日波动率范围">
            <el-input-number v-model="filters.min_volatility_10d" :precision="2" :step="0.1" placeholder="最小值" style="width: 120px" />
            <span style="margin: 0 10px">-</span>
            <el-input-number v-model="filters.max_volatility_10d" :precision="2" :step="0.1" placeholder="最大值" style="width: 120px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadData">应用筛选</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 数据表格 -->
      <div v-loading="loading">
        <div v-for="series in volatilityData.series" :key="series.contract_code" style="margin-bottom: 30px">
          <h3>{{ series.contract_code }} - 波动率数据</h3>
          <el-table :data="series.data" stripe border style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="close_price" label="收盘价" width="120" align="right">
              <template #default="{ row }">
                {{ row.close_price !== null ? row.close_price.toFixed(2) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="volatility_5d" label="5日波动率（年化）" width="180" align="right">
              <template #default="{ row }">
                <span :style="{ color: getVolatilityColor(row.volatility_5d) }">
                  {{ row.volatility_5d !== null ? row.volatility_5d.toFixed(2) + '%' : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="volatility_10d" label="10日波动率（年化）" width="180" align="right">
              <template #default="{ row }">
                <span :style="{ color: getVolatilityColor(row.volatility_10d) }">
                  {{ row.volatility_10d !== null ? row.volatility_10d.toFixed(2) + '%' : '-' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { futuresApi, type VolatilityResponse } from '@/api/futures'

const loading = ref(false)
const selectedContract = ref<number | null>(null)
const contractMonths = [3, 5, 7, 9, 11, 1]
const volatilityData = ref<VolatilityResponse>({ series: [], update_time: null })

const filters = ref({
  min_volatility_5d: null as number | null,
  max_volatility_5d: null as number | null,
  min_volatility_10d: null as number | null,
  max_volatility_10d: null as number | null
})

const loadData = async () => {
  loading.value = true
  try {
    const result = await futuresApi.getVolatility({
      contract_month: selectedContract.value || undefined,
      min_volatility_5d: filters.value.min_volatility_5d || undefined,
      max_volatility_5d: filters.value.max_volatility_5d || undefined,
      min_volatility_10d: filters.value.min_volatility_10d || undefined,
      max_volatility_10d: filters.value.max_volatility_10d || undefined
    })
    volatilityData.value = result
  } catch (error) {
    console.error('加载波动率数据失败:', error)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    min_volatility_5d: null,
    max_volatility_5d: null,
    min_volatility_10d: null,
    max_volatility_10d: null
  }
  loadData()
}

const getVolatilityColor = (volatility: number | null): string => {
  if (volatility === null) return '#666'
  if (volatility < 20) return 'green'
  if (volatility < 30) return 'orange'
  return 'red'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.volatility-page {
  padding: 20px;
}

h3 {
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: 600;
}
</style>
