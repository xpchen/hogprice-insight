<template>
  <div class="province-range-page">
    <!-- 省份选择区域 -->
    <el-card class="province-selector-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>省区范围</span>
          <!-- 年份筛选 -->
          <div v-if="availableYears.length > 0" style="display: flex; align-items: center; gap: 10px">
            <span style="font-size: 14px">年份筛选：</span>
            <el-checkbox-group v-model="selectedYears" @change="handleYearChange" size="small">
              <el-checkbox
                v-for="year in availableYears"
                :key="year"
                :label="year"
              >
                {{ year }}年
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </template>
      
      <!-- 18个省份单选按钮 -->
      <div class="provinces-grid">
        <el-radio-group v-model="selectedProvince" @change="handleProvinceChange" size="large">
          <div class="province-row" v-for="(row, rowIndex) in provinceRows" :key="rowIndex">
            <el-radio-button
              v-for="province in row"
              :key="province"
              :label="province"
              class="province-radio"
            >
              {{ province }}
            </el-radio-button>
          </div>
        </el-radio-group>
      </div>
    </el-card>

    <!-- 6个季节性图表 -->
    <div v-if="selectedProvince" class="charts-container">
      <div v-loading="loading" class="charts-grid">
        <div
          v-for="(indicatorName, index) in indicatorNames"
          :key="indicatorName"
          class="chart-wrapper"
        >
          <SeasonalityChart
            :data="getChartData(indicatorName)"
            :loading="loading"
            :title="`${selectedProvince} - ${indicatorName}`"
          />
        </div>
      </div>
      
      <div v-if="!loading && Object.keys(indicatorsData).length === 0" class="empty-state">
        <el-empty description="暂无数据" />
      </div>
    </div>
    
    <div v-else class="empty-state">
      <el-empty description="请选择省份查看数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SeasonalityChart from '../../components/SeasonalityChart.vue'
import type { SeasonalityData } from '../../components/SeasonalityChart.vue'
import {
  getProvinceIndicatorsSeasonality,
  type ProvinceIndicatorsResponse,
  type SeasonalityResponse
} from '../../api/price-display'

// 18个省份列表
const provinces = [
  '河南', '山东', '河北', '山西', '湖北', '陕西',
  '黑龙江', '吉林', '辽宁', '湖南', '安徽', '江西',
  '广东', '广西', '四川', '贵州', '重庆', '云南'
]

// 将省份分成3行，每行6个
const provinceRows = computed(() => {
  const rows: string[][] = []
  for (let i = 0; i < provinces.length; i += 6) {
    rows.push(provinces.slice(i, i + 6))
  }
  return rows
})

// 6个指标名称
const indicatorNames = [
  '日度 均价',
  '日度 散户标肥价差',
  '周度 出栏均重',
  '周度 宰后均重',
  '周度 90KG占比',
  '周度 冻品库容'
]

const selectedProvince = ref<string>('')
const selectedYears = ref<number[]>([])
const loading = ref(false)
const indicatorsData = ref<Record<string, SeasonalityResponse>>({})
const availableYears = ref<number[]>([])

// 获取图表数据
const getChartData = (indicatorName: string): SeasonalityData | null => {
  const indicator = indicatorsData.value[indicatorName]
  if (!indicator || !indicator.series || indicator.series.length === 0) {
    return null
  }
  
  // 根据选中的年份过滤数据
  let filteredSeries = indicator.series
  if (selectedYears.value.length > 0) {
    filteredSeries = indicator.series.filter(s => selectedYears.value.includes(s.year))
  }
  
  if (filteredSeries.length === 0) {
    return null
  }
  
  // 判断是日度还是周度数据
  // 日度数据：x_values是"MM-DD"格式的字符串数组
  // 周度数据：x_values是1-52的数字数组
  const isWeekly = indicatorName.includes('周度')
  
  let xValues: number[] | string[] = []
  if (isWeekly) {
    // 周度数据：1-52周
    xValues = Array.from({ length: 52 }, (_, i) => i + 1)
  } else {
    // 日度数据：需要从series中提取所有唯一的month_day
    const monthDays = new Set<string>()
    filteredSeries.forEach(s => {
      s.data.forEach(d => {
        if (d.month_day) {
          monthDays.add(d.month_day)
        }
      })
    })
    xValues = Array.from(monthDays).sort()
  }
  
  // 转换series数据
  const series = filteredSeries.map(s => {
    const values: Array<number | null> = []
    
    if (isWeekly) {
      // 周度数据：按周序号组织
      // 后端返回的数据中，每个数据点的month_day是该周第一天的日期
      // 我们需要根据这个日期计算周序号，然后按周序号组织数据
      const weekDataMap = new Map<number, number | null>()
      
      s.data.forEach(d => {
        if (d.month_day) {
          const [month, day] = d.month_day.split('-').map(Number)
          const date = new Date(s.year, month - 1, day)
          const weekOfYear = getWeekOfYear(date)
          // 如果同一周有多个数据点，取平均值（通常只有一个）
          if (weekDataMap.has(weekOfYear)) {
            const existingValue = weekDataMap.get(weekOfYear)
            if (existingValue !== null && d.value !== null) {
              weekDataMap.set(weekOfYear, (existingValue + d.value) / 2)
            } else if (d.value !== null) {
              weekDataMap.set(weekOfYear, d.value)
            }
          } else {
            weekDataMap.set(weekOfYear, d.value ?? null)
          }
        }
      })
      
      // 按周序号1-52填充数据
      for (let week = 1; week <= 52; week++) {
        values.push(weekDataMap.get(week) ?? null)
      }
    } else {
      // 日度数据：按month_day组织
      xValues.forEach(monthDay => {
        const dayData = s.data.find(d => d.month_day === monthDay)
        values.push(dayData?.value ?? null)
      })
    }
    
    return {
      year: s.year,
      values: values
    }
  })
  
  return {
    x_values: xValues,
    series: series,
    meta: {
      unit: indicator.unit || '',
      freq: isWeekly ? 'W' : 'D',
      metric_name: indicator.metric_name
    }
  }
}

// 计算日期所在的周序号（ISO周）
const getWeekOfYear = (date: Date): number => {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
}

// 处理省份变化
const handleProvinceChange = () => {
  loadIndicatorsData()
}

// 处理年份变化
const handleYearChange = () => {
  // 年份变化时不需要重新加载数据，只需要更新图表显示
}

// 加载指标数据
const loadIndicatorsData = async () => {
  if (!selectedProvince.value) {
    indicatorsData.value = {}
    return
  }
  
  loading.value = true
  try {
    const startYear = selectedYears.value.length > 0 ? Math.min(...selectedYears.value) : undefined
    const endYear = selectedYears.value.length > 0 ? Math.max(...selectedYears.value) : undefined
    
    const response: ProvinceIndicatorsResponse = await getProvinceIndicatorsSeasonality(
      selectedProvince.value,
      startYear,
      endYear
    )
    
    indicatorsData.value = response.indicators
    
    // 提取所有可用的年份
    const yearsSet = new Set<number>()
    Object.values(response.indicators).forEach(indicator => {
      indicator.series.forEach(s => {
        yearsSet.add(s.year)
      })
    })
    availableYears.value = Array.from(yearsSet).sort()
    
    // 如果没有选中年份，默认选中所有年份
    if (selectedYears.value.length === 0 && availableYears.value.length > 0) {
      selectedYears.value = [...availableYears.value]
    }
  } catch (error: any) {
    console.error('加载指标数据失败:', error)
    ElMessage.error(`加载数据失败: ${error?.message || '未知错误'}`)
    indicatorsData.value = {}
  } finally {
    loading.value = false
  }
}

// 初始化：默认选择第一个省份
onMounted(() => {
  if (provinces.length > 0) {
    selectedProvince.value = provinces[0]
    loadIndicatorsData()
  }
})
</script>

<style scoped>
.province-range-page {
  padding: 20px;
}

.province-selector-card {
  margin-bottom: 20px;
}

.provinces-grid {
  padding: 10px 0;
}

.province-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.province-radio {
  flex: 1;
  min-width: 120px;
  text-align: center;
}

.charts-container {
  margin-top: 20px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-wrapper {
  min-height: 500px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
