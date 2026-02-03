<template>
  <div class="industry-chain-page">
    <ChartPanel :data="chartData" :loading="loading" title="产业链周度汇总" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChartPanel from '../components/ChartPanel.vue'

const loading = ref(false)
const chartData = ref(null)
</script>

<style scoped>
.industry-chain-page {
  padding: 20px;
}
</style>
