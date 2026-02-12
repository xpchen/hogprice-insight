<template>
  <div class="calendar-spread-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>C2. 月间价差</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <el-select v-model="selectedSpread" size="small" @change="loadData" style="width: 150px">
              <el-option label="全部价差" :value="null" />
              <el-option v-for="spread in spreadPairs" :key="spread" :label="spread" :value="spread" />
            </el-select>
            <el-select v-model="chartType" size="small" @change="loadData" style="width: 120px">
              <el-option label="历史连续" value="timeseries" />
              <el-option label="季节性" value="seasonality" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <div v-if="chartType === 'timeseries'">
          <div v-for="series in spreadData.series" :key="series.spread_name" style="margin-bottom: 12px">
            <h3 style="text-align: left">{{ series.spread_name }} - 历史连续图</h3>
            <ChartPanel
              :data="convertToChartData(series, 'timeseries')"
              :loading="false"
              :title="series.spread_name"
            />
          </div>
        </div>
        <div v-else>
          <div v-for="series in spreadData.series" :key="series.spread_name" style="margin-bottom: 12px">
            <h3 style="text-align: left">{{ series.spread_name }} - 季节性图</h3>
            <ChartPanel
              :data="convertToChartData(series, 'seasonality')"
              :loading="false"
              :title="`${series.spread_name}季节性`"
            />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ChartPanel, { type ChartData } from '@/components/ChartPanel.vue'
import { futuresApi, type CalendarSpreadResponse } from '@/api/futures'

const loading = ref(false)
const selectedSpread = ref<string | null>(null)
const chartType = ref<'timeseries' | 'seasonality'>('timeseries')
const spreadPairs = ['03-05', '05-07', '07-09', '09-11', '11-01', '01-03']
const spreadData = ref<CalendarSpreadResponse>({ series: [], update_time: null })

const loadData = async () => {
  loading.value = true
  try {
    const result = await futuresApi.getCalendarSpread({
      spread_pair: selectedSpread.value || undefined
    })
    spreadData.value = result
  } catch (error) {
    console.error('加载月间价差数据失败:', error)
  } finally {
    loading.value = false
  }
}

const convertToChartData = (series: CalendarSpreadResponse['series'][0], type: 'timeseries' | 'seasonality'): ChartData => {
  if (type === 'timeseries') {
    // 历史连续图
    const categories = series.data.map(d => d.date)
    return {
      categories,
      series: [
        {
          name: '价差',
          data: series.data.map(d => [d.date, d.spread]),
          unit: '元/公斤'
        },
        {
          name: '近月合约结算价',
          data: series.data.map(d => [d.date, d.near_contract_settle]),
          unit: '元/公斤'
        },
        {
          name: '远月合约结算价',
          data: series.data.map(d => [d.date, d.far_contract_settle]),
          unit: '元/公斤'
        }
      ]
    }
  } else {
    // 季节性图：按年份分组
    const yearMap = new Map<number, Array<{ date: string; spread: number | null }>>()
    
    series.data.forEach(d => {
      const year = new Date(d.date).getFullYear()
      if (!yearMap.has(year)) {
        yearMap.set(year, [])
      }
      yearMap.get(year)!.push({ date: d.date, spread: d.spread })
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
        dataMap.set(monthDay, d.spread)
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
.calendar-spread-page {
  padding: 4px;
}

.calendar-spread-page :deep(.el-card__body) {
  padding: 4px 6px;
}

h3 {
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: 600;
}
</style>
