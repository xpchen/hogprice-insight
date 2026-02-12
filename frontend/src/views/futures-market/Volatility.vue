<template>
  <div class="volatility-page">
    <el-card class="chart-page-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>波动率</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <el-radio-group v-model="windowDays" @change="loadData" size="small">
              <el-radio-button :label="5">5日波动率</el-radio-button>
              <el-radio-button :label="10">10日波动率</el-radio-button>
            </el-radio-group>
            <el-select v-model="selectedContract" size="small" @change="loadData" style="width: 120px">
              <el-option label="全部合约" :value="null" />
              <el-option v-for="month in contractMonths" :key="month" :label="`${month.toString().padStart(2, '0')}合约`" :value="month" />
            </el-select>
            <el-button size="small" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 波动率季节性图 -->
      <div v-loading="loading">
        <div v-for="series in volatilityData.series" :key="series.contract_code" style="margin-bottom: 12px">
          <h3>{{ `${series.contract_month.toString().padStart(2, '0')}合约` }} - 波动率季节性图</h3>
          <div
            :ref="el => setChartRef(series.contract_month, el)"
            class="chart"
          ></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { futuresApi, type VolatilityResponse } from '@/api/futures'
import { axisLabelPercentFormatter } from '@/utils/chart-style'

const loading = ref(false)
const windowDays = ref<number>(10)
const selectedContract = ref<number | null>(null)
const contractMonths = [1, 3, 5, 7, 9, 11]
const volatilityData = ref<VolatilityResponse>({ series: [], update_time: null })
const chartInstances = new Map<number, echarts.ECharts>()
const chartRefs = new Map<number, HTMLDivElement>()

const setChartRef = (key: number, el: HTMLDivElement | null) => {
  if (el) {
    chartRefs.set(key, el)
  } else {
    chartRefs.delete(key)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const result = await futuresApi.getVolatility({
      contract_month: selectedContract.value || undefined,
      window_days: windowDays.value
    })
    volatilityData.value = result
    await nextTick()
    renderCharts()
  } catch (error) {
    console.error('加载波动率数据失败:', error)
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  volatilityData.value.series.forEach(series => {
    const key = series.contract_month
    const el = chartRefs.get(key)
    if (!el) return
    
    // 销毁旧实例
    if (chartInstances.has(key)) {
      chartInstances.get(key)?.dispose()
    }
    
    const chartInstance = echarts.init(el)
    chartInstances.set(key, chartInstance)
    
    // 按年份分组数据
    const yearMap = new Map<number, Array<typeof series.data[0]>>()
    series.data.forEach(point => {
      const year = point.year || new Date(point.date).getFullYear()
      if (!yearMap.has(year)) yearMap.set(year, [])
      yearMap.get(year)!.push(point)
    })
    
    const years = Array.from(yearMap.keys()).sort()
    const colors = [
      '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272',
      '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3'
    ]
    
    // 获取所有日期（MM-DD格式），季节性图日期从4月1日到2月28日
    const dateSet = new Set<string>()
    series.data.forEach(d => {
      const date = new Date(d.date)
      const month = date.getMonth() + 1
      const day = date.getDate()
      // 只包含4月1日到2月28日的数据
      if ((month === 4 && day >= 1) || (month > 4 && month <= 12) || (month >= 1 && month <= 2 && day <= 28)) {
        const monthDay = `${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`
        dateSet.add(monthDay)
      }
    })
    const categories = Array.from(dateSet).sort((a, b) => {
      // 排序：4月1日-12月31日，然后1月1日-2月28日
      const [aMonth, aDay] = a.split('-').map(Number)
      const [bMonth, bDay] = b.split('-').map(Number)
      const aOrder = aMonth >= 4 ? aMonth : aMonth + 12
      const bOrder = bMonth >= 4 ? bMonth : bMonth + 12
      if (aOrder !== bOrder) return aOrder - bOrder
      return aDay - bDay
    })
    
    const tooltipLookup = new Map<string, { settle_price?: number; open_interest?: number }>()
    series.data.forEach(point => {
      const year = point.year ?? new Date(point.date).getFullYear()
      const d = new Date(point.date)
      const mmdd = `${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')}`
      tooltipLookup.set(`${year}-${mmdd}`, {
        settle_price: point.settle_price,
        open_interest: point.open_interest
      })
    })
    
    const seriesData: any[] = []
    
    years.forEach((year, idx) => {
      const yearData = yearMap.get(year)!
      const color = colors[idx % colors.length]
      const dataMap = new Map<string, number | null>()
      
      yearData.forEach(d => {
        const date = new Date(d.date)
        const month = date.getMonth() + 1
        const day = date.getDate()
        const monthDay = `${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`
        dataMap.set(monthDay, d.volatility)
      })
      
      seriesData.push({
        name: `${year}年`,
        type: 'line',
        data: categories.map(cat => dataMap.get(cat) || null),
        lineStyle: { color },
        symbol: 'circle',
        symbolSize: 4,
        smooth: true,
        connectNulls: true
      })
    })
    
    const option: echarts.EChartsOption = {
      title: {
        text: `${series.contract_month.toString().padStart(2, '0')}合约波动率季节性图`,
        left: 'left',
        top: 8
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          if (!Array.isArray(params)) return ''
          const cat = params[0]?.axisValue
          let result = `<div style="margin-bottom: 4px;"><strong>${cat}</strong></div>`
          params.forEach((param: any) => {
            if (param.value !== null && param.value !== undefined) {
              const v = typeof param.value === 'number' ? param.value.toFixed(2) : param.value
              const yearMatch = param.seriesName?.match(/^(\d{4})年?/)
              const year = yearMatch ? yearMatch[1] : ''
              result += `<div style="margin: 2px 0;">
                <span style="display: inline-block; width: 10px; height: 10px; background: ${param.color}; margin-right: 5px;"></span>
                ${param.seriesName}: <strong>${v}%</strong>
              </div>`
              if (year) {
                const extra = tooltipLookup.get(`${year}-${cat}`)
                if (extra) {
                  if (extra.settle_price != null) result += `<div style="margin: 2px 0; color:#666;">主力合约结算价: ${extra.settle_price.toFixed(2)}</div>`
                  if (extra.open_interest != null) result += `<div style="margin: 2px 0; color:#666;">持仓量: ${extra.open_interest.toLocaleString()}</div>`
                }
              }
            }
          })
          return result
        }
      },
      legend: {
        data: seriesData.map(s => s.name),
        top: 36,
        left: 'left',
        type: 'plain',
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 18
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '22%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        boundaryGap: false,
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '波动率（%）',
        axisLabel: { formatter: (v: number) => axisLabelPercentFormatter(v) }
      },
      series: seriesData,
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }
      ]
    }
    
    chartInstance.setOption(option, true)
    window.addEventListener('resize', () => chartInstance.resize())
  })
}

watch(() => volatilityData.value.series, () => {
  nextTick(() => {
    renderCharts()
  })
}, { deep: true })

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.volatility-page {
  padding: 4px;
  
  :deep(.el-card__body) {
    padding: 4px 6px;
  }
  
  h3 {
    margin-bottom: 6px;
    font-size: 16px;
    font-weight: 600;
    text-align: left;
  }
  
  .chart {
    width: 100%;
    height: 400px;
  }
}
</style>
