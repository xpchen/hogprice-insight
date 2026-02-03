<template>
  <div class="live-white-spread-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>A6. 毛白价差（全国）</span>
          <div style="display: flex; gap: 10px; align-items: center">
            <UpdateTimeBadge 
              v-if="latestUpdateTime"
              :update-time="latestUpdateTime" 
              :last-data-date="latestUpdateTime" 
            />
          </div>
        </div>
      </template>

      <!-- 时间范围选择器 -->
      <div style="margin-bottom: 20px">
        <TimeRangeSelector 
          v-model="dateRange"
          @change="handleDateRangeChange"
        />
      </div>

      <!-- 图表 -->
      <div class="chart-wrapper">
        <h3 class="chart-title">（毛白价差）</h3>
        <div v-if="loading" class="loading-placeholder">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span style="margin-left: 10px">加载中...</span>
        </div>
        <div v-else-if="!chartData" class="no-data-placeholder">
          <el-empty description="暂无数据" :image-size="80" />
        </div>
        <DualAxisChart
          v-else
          :data="chartData"
          :loading="loading"
          title=""
          axis1="left"
          axis2="right"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import UpdateTimeBadge from '@/components/UpdateTimeBadge.vue'
import DualAxisChart, { type DualAxisData } from '@/components/DualAxisChart.vue'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'
import { getLiveWhiteSpreadDualAxis, type LiveWhiteSpreadDualAxisResponse } from '@/api/price-display'

// 数据状态
const loading = ref(false)
const apiData = ref<LiveWhiteSpreadDualAxisResponse | null>(null)
const dateRange = ref<[string, string] | undefined>(undefined)
const latestUpdateTime = ref<string | null>(null)

// 计算图表数据
const chartData = computed<DualAxisData | null>(() => {
  if (!apiData.value) return null

  return {
    series1: {
      name: '毛白价差',
      data: apiData.value.spread_data.map(item => ({
        date: item.date,
        value: item.value
      })),
      unit: apiData.value.spread_unit
    },
    series2: {
      name: '价差比率',
      data: apiData.value.ratio_data.map(item => ({
        date: item.date,
        value: item.value
      })),
      unit: apiData.value.ratio_unit
    }
  }
})

// 加载数据
const loadData = async () => {
  try {
    loading.value = true
    const [startDate, endDate] = dateRange.value || []
    
    const response = await getLiveWhiteSpreadDualAxis(startDate, endDate)
    apiData.value = response
    latestUpdateTime.value = response.latest_date
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 处理时间范围变化
const handleDateRangeChange = (range: [string, string]) => {
  dateRange.value = range
  loadData()
}

// 初始化
onMounted(() => {
  // TimeRangeSelector会在mounted时自动触发change事件，设置默认时间范围
  // 这里先加载一次数据（使用默认时间范围）
  loadData()
})
</script>

<style scoped>
.live-white-spread-page {
  padding: 20px;
}

.chart-wrapper {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 16px;
  min-height: 400px;
}

.chart-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 16px 0;
  color: #303133;
  text-align: center;
}

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 500px;
  color: #909399;
}

.no-data-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 500px;
}
</style>
