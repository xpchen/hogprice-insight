<template>
  <div class="options-page">
    <el-form :model="filters" inline style="margin-bottom: 20px">
      <el-form-item label="标的合约">
        <el-input v-model="filters.underlying" placeholder="如 lh2603" />
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="filters.type" clearable>
          <el-option label="看涨" value="C" />
          <el-option label="看跌" value="P" />
        </el-select>
      </el-form-item>
      <el-form-item label="行权价">
        <el-input-number v-model="filters.strike" :precision="0" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
      </el-form-item>
    </el-form>
    <ChartPanel :data="chartData" :loading="loading" title="生猪期权" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChartPanel from '../components/ChartPanel.vue'
import { optionsApi } from '../api/options'

const loading = ref(false)
const chartData = ref(null)
const filters = ref({
  underlying: 'lh2603',
  type: undefined as 'C' | 'P' | undefined,
  strike: undefined as number | undefined
})

const loadData = async () => {
  loading.value = true
  try {
    const result = await optionsApi.getOptionsDaily({
      underlying: filters.value.underlying,
      type: filters.value.type,
      strike: filters.value.strike
    })
    
    chartData.value = {
      series: [{
        name: result.option_code,
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
.options-page {
  padding: 20px;
}
</style>
