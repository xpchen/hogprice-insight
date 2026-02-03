<template>
  <div class="weight-page">
    <el-row :gutter="20">
      <el-col :span="12" v-for="indicator in weightIndicators" :key="indicator.code">
        <ChartPanel :data="getChartData(indicator.code)" :loading="loading" :title="indicator.name" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChartPanel from '../components/ChartPanel.vue'

const loading = ref(false)
const weightIndicators = [
  { code: 'hog_weight_pre_slaughter', name: '宰前均重' },
  { code: 'hog_weight_out_week', name: '出栏均重' },
  { code: 'hog_weight_scale', name: '规模场出栏均重' },
  { code: 'hog_weight_retail', name: '散户出栏均重' },
  { code: 'hog_weight_90kg', name: '90kg出栏占比' },
  { code: 'hog_weight_150kg', name: '150kg出栏占比' }
]

const getChartData = (code: string) => {
  // 加载对应指标的数据
  return null
}
</script>

<style scoped>
.weight-page {
  padding: 20px;
}
</style>
