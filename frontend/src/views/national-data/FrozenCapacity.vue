<template>
  <div class="frozen-capacity-page">
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
            :loading="loadingProvinces"
          >
            <el-option
              v-for="province in provinces"
              :key="province.province_name"
              :label="province.province_name"
              :value="province.province_name"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="chart-container" v-loading="loading">
      <div v-if="errorMessage" class="error-message">
        <el-alert
          :title="errorMessage"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
      <template v-else>
        <div v-if="!seasonalityData && !loading && filters.province" class="empty-state">
          <el-empty description="暂无数据" />
        </div>
        <div v-else-if="!filters.province && !loadingProvinces && provinces.length === 0" class="empty-state">
          <el-empty description="正在加载省份列表..." />
        </div>
        <div v-else-if="!filters.province" class="empty-state">
          <el-empty description="请选择省份查看数据" />
        </div>
        <SeasonalityChart
          v-else
          :data="seasonalityData"
          :loading="loading"
          :title="chartTitle"
          :change-info="changeInfo"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import SeasonalityChart from '../../components/SeasonalityChart.vue'
import type { SeasonalityData } from '../../components/SeasonalityChart.vue'
import {
  getFrozenInventoryProvinces,
  getFrozenInventoryProvinceSeasonality,
  type FrozenInventoryProvinceInfo,
  type FrozenInventorySeasonalityResponse
} from '../../api/price-display'

const loading = ref(false)
const loadingProvinces = ref(false)
const provinces = ref<FrozenInventoryProvinceInfo[]>([])
const seasonalityData = ref<SeasonalityData | null>(null)
const changeInfo = ref<{
  period_change: number | null
  yoy_change: number | null
} | null>(null)
const errorMessage = ref<string>('')

const filters = ref({
  province: ''
})

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
  loadingProvinces.value = true
  errorMessage.value = ''
  try {
    const response = await getFrozenInventoryProvinces()
    provinces.value = response.provinces
    
    if (provinces.value.length === 0) {
      errorMessage.value = '暂无省份数据'
      return
    }
    
    // 默认选择第一个省份
    if (!filters.value.province) {
      filters.value.province = provinces.value[0].province_name
      await loadSeasonalityData()
    }
  } catch (error: any) {
    console.error('加载省份列表失败:', error)
    errorMessage.value = `加载省份列表失败: ${error?.message || '未知错误'}`
    ElMessage.error('加载省份列表失败')
  } finally {
    loadingProvinces.value = false
  }
}

// 加载季节性数据
const loadSeasonalityData = async () => {
  if (!filters.value.province) {
    seasonalityData.value = null
    changeInfo.value = null
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    // 加载所有年份的数据
    const response: FrozenInventorySeasonalityResponse = await getFrozenInventoryProvinceSeasonality(
      filters.value.province
    )
    
    if (!response.series || response.series.length === 0) {
      errorMessage.value = '该省份暂无数据'
      return
    }

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

    // 保存涨跌信息
    changeInfo.value = {
      period_change: response.period_change,
      yoy_change: response.yoy_change
    }
  } catch (error: any) {
    console.error('加载季节性数据失败:', error)
    errorMessage.value = `加载数据失败: ${error?.message || '未知错误'}`
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

// 初始化
onMounted(() => {
  console.log('FrozenCapacity页面已挂载，开始加载数据...')
  loadProvinces().catch(err => {
    console.error('初始化失败:', err)
    errorMessage.value = `初始化失败: ${err?.message || '未知错误'}`
  })
})
</script>

<style scoped>
.frozen-capacity-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.chart-container {
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

.error-message {
  margin-bottom: 20px;
}

.empty-state {
  padding: 40px 0;
}
</style>
