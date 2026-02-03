<template>
  <div class="frozen-page">
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <!-- 省份选择 -->
        <el-form-item label="省份">
          <el-select
            v-model="filters.province"
            placeholder="请选择省份"
            clearable
            @change="handleProvinceChange"
            style="width: 200px"
          >
            <el-option
              v-for="province in provinces"
              :key="province.province_name"
              :label="province.province_name"
              :value="province.province_name"
            />
          </el-select>
        </el-form-item>

        <!-- 年度筛选 -->
        <el-form-item v-if="availableYears.length > 0" label="年度">
          <el-checkbox-group v-model="filters.years" @change="handleYearChange">
            <el-checkbox
              v-for="year in availableYears"
              :key="year"
              :label="year"
            >
              {{ year }}年
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="chart-card" v-loading="loading">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ chartTitle }}</span>
          <div v-if="changeInfo" class="change-info">
            <span v-if="changeInfo.period_change !== null" class="change-item">
              本期涨跌：
              <span :class="getChangeClass(changeInfo.period_change)">
                {{ formatChange(changeInfo.period_change) }}
              </span>
            </span>
            <span v-if="changeInfo.yoy_change !== null" class="change-item">
              较去年同期涨跌：
              <span :class="getChangeClass(changeInfo.yoy_change)">
                {{ formatChange(changeInfo.yoy_change) }}
              </span>
            </span>
          </div>
        </div>
      </template>
      <SeasonalityChart
        :data="seasonalityData"
        :loading="loading"
        :title="chartTitle"
        :show-year-filter="true"
        :available-years="availableYears.length > 0 ? availableYears : undefined"
        :selected-years="filters.years.length > 0 ? filters.years : undefined"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import SeasonalityChart from '../components/SeasonalityChart.vue'
import type { SeasonalityData } from '../components/SeasonalityChart.vue'
import {
  getFrozenInventoryProvinces,
  getFrozenInventoryProvinceSeasonality,
  type FrozenInventoryProvinceInfo,
  type FrozenInventorySeasonalityResponse
} from '../api/price-display'

const loading = ref(false)
const provinces = ref<FrozenInventoryProvinceInfo[]>([])
const seasonalityData = ref<SeasonalityData | null>(null)
const changeInfo = ref<{
  period_change: number | null
  yoy_change: number | null
} | null>(null)

const filters = ref({
  province: '',
  years: [] as number[]
})

const availableYears = ref<number[]>([])

const chartTitle = computed(() => {
  if (filters.value.province) {
    return `冻品库容率：${filters.value.province}`
  }
  return '冻品库容率（分省区季节性）'
})

// 格式化涨跌值
const formatChange = (value: number | null): string => {
  if (value === null) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}`
}

// 获取涨跌样式类
const getChangeClass = (value: number | null): string => {
  if (value === null) return ''
  return value >= 0 ? 'change-positive' : 'change-negative'
}

// 加载省份列表
const loadProvinces = async () => {
  try {
    const response = await getFrozenInventoryProvinces()
    provinces.value = response.provinces
    
    // 默认选择第一个省份
    if (provinces.value.length > 0 && !filters.value.province) {
      filters.value.province = provinces.value[0].province_name
      await loadSeasonalityData()
    }
  } catch (error) {
    console.error('加载省份列表失败:', error)
    ElMessage.error('加载省份列表失败')
  }
}

// 从数据中提取可用年份
const extractAvailableYears = (series: any[]) => {
  const years = new Set<number>()
  series.forEach(s => {
    if (s.year) {
      years.add(s.year)
    }
  })
  return Array.from(years).sort()
}

// 加载季节性数据
const loadSeasonalityData = async () => {
  if (!filters.value.province) {
    seasonalityData.value = null
    changeInfo.value = null
    return
  }

  loading.value = true
  try {
    const minYear = Math.min(...filters.value.years)
    const maxYear = Math.max(...filters.value.years)
    
    const response: FrozenInventorySeasonalityResponse = await getFrozenInventoryProvinceSeasonality(
      filters.value.province,
      minYear,
      maxYear
    )

    // 转换数据格式为SeasonalityChart需要的格式
    // 使用周序号作为x值（1-52）
    const xValues: number[] = []
    for (let i = 1; i <= 52; i++) {
      xValues.push(i)
    }

    // 将数据按周序号组织
    // 后端返回的series中，每个series的data数组已经按周序号排序（1-52周）
    const series = response.series.map(s => {
      const values: Array<number | null> = []
      
      // 后端已经按周序号1-52返回数据，直接提取value
      s.data.forEach(point => {
        values.push(point.value)
      })
      
      // 确保有52个值（如果不足，补齐null）
      while (values.length < 52) {
        values.push(null)
      }
      
      return {
        year: s.year,
        values: values.slice(0, 52)  // 确保只有52个值
      }
    })

    seasonalityData.value = {
      x_values: xValues,
      series: series,
      meta: {
        unit: response.unit || 'ratio',
        freq: 'W',
        metric_name: response.metric_name
      }
    }

    // 更新可用年份列表
    const years = extractAvailableYears(response.series)
    if (years.length > 0) {
      availableYears.value = years
      // 如果当前选中的年份不在可用年份中，或者没有选中年份，则默认选择所有年份
      if (filters.value.years.length === 0 || 
          !filters.value.years.every(y => years.includes(y))) {
        filters.value.years = [...years]
      }
    }

    // 保存涨跌信息
    changeInfo.value = {
      period_change: response.period_change,
      yoy_change: response.yoy_change
    }
  } catch (error) {
    console.error('加载季节性数据失败:', error)
    ElMessage.error('加载数据失败')
    seasonalityData.value = null
    changeInfo.value = null
  } finally {
    loading.value = false
  }
}


// 处理省份变化
const handleProvinceChange = () => {
  loadSeasonalityData()
}

// 处理年度变化
const handleYearChange = () => {
  loadSeasonalityData()
}

// 初始化
onMounted(() => {
  loadProvinces()
})
</script>

<style scoped>
.frozen-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.change-info {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.change-positive {
  color: #f56c6c;
  font-weight: bold;
}

.change-negative {
  color: #67c23a;
  font-weight: bold;
}
</style>
