<template>
  <div class="dashboard">
    <!-- 全局筛选栏 -->
    <FilterBar
      :show-region-filter="true"
      :show-year-filter="true"
      :show-freq-filter="false"
      :available-years="availableYears"
      @change="handleFilterChange"
    />

    <!-- 7个卡片布局 -->
    <el-row :gutter="20">
      <!-- 卡片1：全国出栏均价 + 标肥价差（合并图） -->
      <el-col :span="24">
        <DualAxisChart
          :data="card1Data"
          :loading="loading"
          title="全国出栏均价 + 标肥价差"
          axis1="left"
          axis2="right"
        />
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 卡片2：日度屠宰量季节性（农历对齐） -->
      <el-col :span="12">
        <SeasonalityChart
          :data="card2Data"
          :loading="loading"
          title="日度屠宰量季节性"
          :lunar-alignment="true"
          :show-year-filter="true"
          :available-years="availableYears"
          :selected-years="selectedYears"
        />
      </el-col>

      <!-- 卡片3：价格&屠宰走势（年度筛选） -->
      <el-col :span="12">
        <ChartPanel
          :data="card3Data"
          :loading="loading"
          title="价格&屠宰走势"
        />
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 卡片4：均重专区入口（6图） -->
      <el-col :span="12">
        <el-card class="entrance-card">
          <template #header>
            <span>均重专区</span>
          </template>
          <div class="entrance-grid">
            <div
              v-for="indicator in weightIndicators"
              :key="indicator.code"
              class="entrance-item"
              @click="navigateToIndicator(indicator.code)"
            >
              <div class="entrance-name">{{ indicator.name }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 卡片5：价差专区入口 -->
      <el-col :span="12">
        <el-card class="entrance-card">
          <template #header>
            <span>价差专区</span>
          </template>
          <div class="entrance-grid">
            <div
              v-for="indicator in spreadIndicators"
              :key="indicator.code"
              class="entrance-item"
              @click="navigateToIndicator(indicator.code)"
            >
              <div class="entrance-name">{{ indicator.name }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 卡片6：冻品库容率（分省区季节性） -->
      <el-col :span="12">
        <SeasonalityChart
          :data="card6Data"
          :loading="loading"
          title="冻品库容率（分省区季节性）"
          :show-year-filter="true"
          :available-years="availableYears"
          :selected-years="selectedYears"
        />
      </el-col>

      <!-- 卡片7：产业链周度汇总 -->
      <el-col :span="12">
        <ChartPanel
          :data="card7Data"
          :loading="loading"
          title="产业链周度汇总"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FilterBar from '../components/FilterBar.vue'
import DualAxisChart from '../components/DualAxisChart.vue'
import SeasonalityChart from '../components/SeasonalityChart.vue'
import ChartPanel from '../components/ChartPanel.vue'
import { dashboardApi } from '../api/dashboard'
import type { DualAxisData } from '../components/DualAxisChart.vue'
import type { SeasonalityData } from '../components/SeasonalityChart.vue'

const router = useRouter()

const loading = ref(false)
const dashboardData = ref<any>(null)
const filters = ref({
  dateRange: { start: '', end: '' },
  region: undefined,
  years: [] as number[]
})

// 可用年份
const availableYears = ref<number[]>([2024, 2025, 2026])
const selectedYears = ref<number[]>([2025, 2026])

// 均重指标列表
const weightIndicators = [
  { code: 'hog_weight_pre_slaughter', name: '宰前均重' },
  { code: 'hog_weight_out_week', name: '出栏均重' },
  { code: 'hog_weight_scale', name: '规模场出栏均重' },
  { code: 'hog_weight_retail', name: '散户出栏均重' },
  { code: 'hog_weight_90kg', name: '90kg出栏占比' },
  { code: 'hog_weight_150kg', name: '150kg出栏占比' }
]

// 价差指标列表
const spreadIndicators = [
  { code: 'spread_std_fat', name: '标肥价差' },
  { code: 'spread_region', name: '区域价差' },
  { code: 'spread_hog_carcass', name: '毛白价差' }
]

// 卡片数据
const card1Data = computed<DualAxisData | null>(() => {
  if (!dashboardData.value) return null
  const card = dashboardData.value.cards?.find((c: any) => c.card_id === 'card_1_price_spread')
  if (!card || card.data.error) return null
  return card.data as DualAxisData
})

const card2Data = computed<SeasonalityData | null>(() => {
  if (!dashboardData.value) return null
  const card = dashboardData.value.cards?.find((c: any) => c.card_id === 'card_2_slaughter_seasonality')
  if (!card || card.data.error) return null
  // 转换数据格式
  return {
    x_values: card.data.series?.map((s: any) => s.date) || [],
    series: [], // 需要从后端获取多年数据
    meta: {
      unit: card.data.unit || '',
      freq: 'D',
      metric_name: '日度屠宰量'
    }
  } as SeasonalityData
})

const card3Data = computed(() => {
  if (!dashboardData.value) return null
  const card = dashboardData.value.cards?.find((c: any) => c.card_id === 'card_3_price_slaughter_trend')
  if (!card || card.data.error) return null
  return card.data
})

const card6Data = computed<SeasonalityData | null>(() => {
  if (!dashboardData.value) return null
  const card = dashboardData.value.cards?.find((c: any) => c.card_id === 'card_6_frozen_capacity')
  if (!card || card.data.error) return null
  return {
    x_values: card.data.series?.map((s: any) => s.date) || [],
    series: [],
    meta: {
      unit: card.data.unit || '',
      freq: 'W',
      metric_name: '冻品库容率'
    }
  } as SeasonalityData
})

const card7Data = computed(() => {
  if (!dashboardData.value) return null
  const card = dashboardData.value.cards?.find((c: any) => c.card_id === 'card_7_industry_chain')
  if (!card || card.data.error) return null
  return card.data
})

const handleFilterChange = (newFilters: any) => {
  filters.value = newFilters
  loadDashboard()
}

const navigateToIndicator = (indicatorCode: string) => {
  router.push({
    path: '/analysis',
    query: { indicator: indicatorCode }
  })
}

const loadDashboard = async () => {
  loading.value = true
  try {
    const data = await dashboardApi.getDefaultDashboard()
    dashboardData.value = data
    
    // 更新可用年份
    if (data.global_filters?.years) {
      availableYears.value = data.global_filters.years
      selectedYears.value = data.global_filters.years.slice(-2)
    }
  } catch (error) {
    ElMessage.error('加载看板数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.entrance-card {
  height: 100%;
}

.entrance-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 20px;
}

.entrance-item {
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.entrance-item:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.entrance-name {
  font-size: 14px;
  color: #303133;
}
</style>
