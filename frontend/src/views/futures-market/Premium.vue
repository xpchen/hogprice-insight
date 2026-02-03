<template>
  <div class="premium-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>C1. 升贴水</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <el-select v-model="selectedContract" size="small" @change="loadData" style="width: 120px">
              <el-option label="全部合约" :value="null" />
              <el-option v-for="month in contractMonths" :key="month" :label="`${month.toString().padStart(2, '0')}合约`" :value="month" />
            </el-select>
            <el-select v-model="chartType" size="small" @change="loadData" style="width: 120px">
              <el-option label="历史连续" value="timeseries" />
              <el-option label="季节性" value="seasonality" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <div v-if="errorMessage" style="padding: 20px; color: red;">
          <el-alert :title="errorMessage" type="error" :closable="false" />
        </div>
        <div v-else-if="premiumData.series.length === 0" style="padding: 20px;">
          <el-empty description="暂无数据">
            <el-button type="primary" @click="loadData">重新加载</el-button>
          </el-empty>
        </div>
        <div v-else>
          <div v-if="chartType === 'timeseries'">
            <div v-for="series in premiumData.series" :key="series.contract_month" style="margin-bottom: 30px">
              <h3>{{ series.contract_name }} - 历史连续图</h3>
              <ChartPanel
                :data="convertToChartData(series, 'timeseries')"
                :loading="false"
                :title="`${series.contract_name}升贴水`"
              />
            </div>
          </div>
          <div v-else>
            <div v-for="series in premiumData.series" :key="series.contract_month" style="margin-bottom: 30px">
              <h3>{{ series.contract_name }} - 季节性图</h3>
              <ChartPanel
                :data="convertToChartData(series, 'seasonality')"
                :loading="false"
                :title="`${series.contract_name}升贴水季节性`"
              />
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ChartPanel, { type ChartData } from '@/components/ChartPanel.vue'
import { futuresApi, type PremiumResponse } from '@/api/futures'

const loading = ref(false)
const selectedContract = ref<number | null>(null)
const chartType = ref<'timeseries' | 'seasonality'>('timeseries')
const contractMonths = [3, 5, 7, 9, 11, 1]
const premiumData = ref<PremiumResponse>({ series: [], update_time: null })
const errorMessage = ref<string>('')

const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await futuresApi.getPremium({
      contract_month: selectedContract.value || undefined
    })
    premiumData.value = result
    if (result.series.length === 0) {
      errorMessage.value = '未找到升贴水数据，请检查：1. 是否有期货数据 2. 是否有全国现货价格数据'
    }
  } catch (error: any) {
    console.error('加载升贴水数据失败:', error)
    errorMessage.value = error?.response?.data?.detail || error?.message || '加载数据失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const convertToChartData = (series: PremiumResponse['series'][0], type: 'timeseries' | 'seasonality'): ChartData => {
  if (type === 'timeseries') {
    // 历史连续图
    const categories = series.data.map(d => d.date)
    return {
      categories,
      series: [
        {
          name: '升贴水',
          data: series.data.map(d => [d.date, d.premium]),
          unit: '元/公斤'
        },
        {
          name: '期货结算价',
          data: series.data.map(d => [d.date, d.futures_settle]),
          unit: '元/公斤'
        },
        {
          name: '现货价格',
          data: series.data.map(d => [d.date, d.spot_price]),
          unit: '元/公斤'
        }
      ]
    }
  } else {
    // 季节性图：按年份分组
    const yearMap = new Map<number, Array<{ date: string; premium: number | null }>>()
    
    series.data.forEach(d => {
      const year = new Date(d.date).getFullYear()
      if (!yearMap.has(year)) {
        yearMap.set(year, [])
      }
      yearMap.get(year)!.push({ date: d.date, premium: d.premium })
    })
    
    const categories: string[] = []
    const seriesData: Array<{ name: string; data: Array<[string, number | null]> }> = []
    
    // 获取所有日期（MM-DD格式）
    const dateSet = new Set<string>()
    series.data.forEach(d => {
      const date = new Date(d.date)
      const monthDay = `${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`
      dateSet.add(monthDay)
    })
    categories.push(...Array.from(dateSet).sort())
    
    // 为每年创建一条线
    Array.from(yearMap.keys()).sort().forEach(year => {
      const yearData = yearMap.get(year)!
      const dataMap = new Map<string, number | null>()
      yearData.forEach(d => {
        const date = new Date(d.date)
        const monthDay = `${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`
        dataMap.set(monthDay, d.premium)
      })
      
      seriesData.push({
        name: `${year}年`,
        data: categories.map(cat => [cat, dataMap.get(cat) || null])
      })
    })
    
    return {
      categories,
      series: seriesData.map(s => ({
        ...s,
        unit: '元/公斤'
      }))
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.premium-page {
  padding: 20px;
}

h3 {
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: 600;
}
</style>
