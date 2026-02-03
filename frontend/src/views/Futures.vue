<template>
  <div class="futures-page">
    <el-form :model="filters" inline style="margin-bottom: 20px">
      <el-form-item label="合约">
        <el-input v-model="filters.contract" placeholder="如 lh2603" />
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
      </el-form-item>
    </el-form>
    <ChartPanel :data="chartData" :loading="loading" title="生猪期货" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChartPanel from '../components/ChartPanel.vue'
import { futuresApi } from '../api/futures'

const loading = ref(false)
const chartData = ref(null)
const filters = ref({ contract: 'lh2603' })
const dateRange = ref<[string, string] | null>(null)

const loadData = async () => {
  loading.value = true
  try {
    const result = await futuresApi.getFuturesDaily({
      contract: filters.value.contract,
      from_date: dateRange.value?.[0],
      to_date: dateRange.value?.[1]
    })
    
    chartData.value = {
      series: [{
        name: result.contract_code,
        data: result.series.map(s => [s.date, s.close])
      }],
      categories: result.series.map(s => s.date)
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.futures-page {
  padding: 20px;
}
</style>
