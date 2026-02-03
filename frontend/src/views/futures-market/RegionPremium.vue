<template>
  <div class="region-premium-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>C3. 重点区域升贴水</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <el-select v-model="selectedContract" size="small" @change="loadData" style="width: 120px">
              <el-option v-for="month in contractMonths" :key="month" :label="`${month.toString().padStart(2, '0')}合约`" :value="month" />
            </el-select>
            <el-date-picker
              v-model="selectedDate"
              type="date"
              size="small"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadData"
              style="width: 150px"
            />
            <el-button size="small" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <el-table :data="regionPremiumData.data" stripe border style="width: 100%">
          <el-table-column prop="region" label="区域" width="120" fixed="left" />
          <el-table-column prop="contract_name" label="合约" width="100" />
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column prop="spot_price" label="区域现货价格" width="140" align="right">
            <template #default="{ row }">
              {{ row.spot_price !== null ? row.spot_price.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="futures_settle" label="期货结算价" width="140" align="right">
            <template #default="{ row }">
              {{ row.futures_settle !== null ? row.futures_settle.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="premium" label="升贴水" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: row.premium !== null && row.premium < 0 ? 'red' : 'green' }">
                {{ row.premium !== null ? row.premium.toFixed(2) : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="单位" width="80">
            <template #default>元/公斤</template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { futuresApi, type RegionPremiumResponse } from '@/api/futures'

const loading = ref(false)
const selectedContract = ref<number>(3)
const selectedDate = ref<string | null>(null)
const contractMonths = [3, 5, 7, 9, 11, 1]
const regionPremiumData = ref<RegionPremiumResponse>({ data: [], update_time: null })

const loadData = async () => {
  loading.value = true
  try {
    const result = await futuresApi.getRegionPremium({
      contract_month: selectedContract.value,
      trade_date: selectedDate.value || undefined
    })
    regionPremiumData.value = result
  } catch (error) {
    console.error('加载区域升贴水数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.region-premium-page {
  padding: 20px;
}
</style>
