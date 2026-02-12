<template>
  <div class="live-white-spread-page">
    <el-card class="chart-page-card">
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

      <!-- 时间范围选择器：近3月、近6月、近1年、全部日期、自定义 -->
      <div style="margin-bottom: 20px">
        <el-radio-group v-model="selectedRange" @change="handleRangeChange" size="small">
          <el-radio-button label="3m">近3月</el-radio-button>
          <el-radio-button label="6m">近6月</el-radio-button>
          <el-radio-button label="1y">近1年</el-radio-button>
          <el-radio-button label="all">全部日期</el-radio-button>
          <el-radio-button label="custom">自定义</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-if="selectedRange === 'custom'"
          v-model="customRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          style="margin-left: 10px"
          @change="handleCustomRangeChange"
        />
      </div>

      <!-- 两个图表横向排列，共用边框 -->
      <div class="charts-row">
        <!-- 左图：毛白价差比率&生猪价格 -->
        <div class="chart-wrapper">
          <div class="chart-box">
            <h3 class="chart-title">毛白价差比率&生猪价格</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!leftChartData" class="no-data-placeholder">
              <el-empty description="暂无数据" :image-size="80" />
            </div>
            <DualAxisChart
              v-else
              :data="leftChartData"
              :loading="loading"
              title=""
              axis1="left"
              axis2="right"
            />
          </div>
          <div class="info-box">
            <DataSourceInfo
              :source-name="'钢联'"
              :update-date="formatUpdateDate(latestUpdateTime)"
            />
          </div>
        </div>

        <!-- 右图：毛白价差&比率 -->
        <div class="chart-wrapper">
          <div class="chart-box">
            <h3 class="chart-title">毛白价差&比率</h3>
            <div v-if="loading" class="loading-placeholder">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span style="margin-left: 10px">加载中...</span>
            </div>
            <div v-else-if="!rightChartData" class="no-data-placeholder">
              <el-empty description="暂无数据" :image-size="80" />
            </div>
            <DualAxisChart
              v-else
              :data="rightChartData"
              :loading="loading"
              title=""
              axis1="left"
              axis2="right"
            />
          </div>
          <div class="info-box">
            <DataSourceInfo
              :source-name="'钢联'"
              :update-date="formatUpdateDate(latestUpdateTime)"
            />
          </div>
        </div>
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
import DataSourceInfo from '@/components/DataSourceInfo.vue'
import { getLiveWhiteSpreadDualAxis, type LiveWhiteSpreadDualAxisResponse } from '@/api/price-display'

// 数据状态
const loading = ref(false)
const apiData = ref<LiveWhiteSpreadDualAxisResponse | null>(null)
const priceData = ref<any>(null) // 生猪价格数据
const dateRange = ref<[string, string] | undefined>(undefined)
const latestUpdateTime = ref<string | null>(null)

// 筛选按钮状态
const selectedRange = ref<string>('all') // 默认全部日期
const customRange = ref<[Date, Date] | null>(null)

// 计算日期范围
const getDateRange = (range: string): [string, string] | undefined => {
  const end = new Date()
  const start = new Date()
  
  switch (range) {
    case '3m':
      start.setMonth(start.getMonth() - 3)
      break
    case '6m':
      start.setMonth(start.getMonth() - 6)
      break
    case '1y':
      start.setFullYear(start.getFullYear() - 1)
      break
    case 'all':
      // 全部日期：返回一个很大的日期范围
      return ['2000-01-01', '2099-12-31']
    case 'custom':
      if (customRange.value) {
        return [
          customRange.value[0].toISOString().split('T')[0],
          customRange.value[1].toISOString().split('T')[0]
        ]
      }
      return ['2000-01-01', '2099-12-31']
    default:
      return ['2000-01-01', '2099-12-31']
  }
  
  return [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0]
  ]
}

const handleRangeChange = () => {
  if (selectedRange.value !== 'custom') {
    const range = getDateRange(selectedRange.value)
    if (range) {
      dateRange.value = range
      loadData()
    }
  }
}

const handleCustomRangeChange = () => {
  if (customRange.value) {
    const range = getDateRange('custom')
    if (range) {
      dateRange.value = range
      loadData()
    }
  }
}

// 计算左图数据：毛白价差比率&生猪价格
const leftChartData = computed<DualAxisData | null>(() => {
  if (!apiData.value) return null
  
  // 暂时使用价差比率作为左图的数据，后续需要添加生猪价格
  // TODO: 需要从后端API获取生猪价格数据
  return {
    series1: {
      name: '价差比率',
      data: apiData.value.ratio_data.map(item => ({
        date: item.date,
        value: item.value
      })),
      unit: apiData.value.ratio_unit
    },
    series2: {
      name: '生猪价格',
      data: [], // TODO: 需要从API获取生猪价格数据
      unit: '元/公斤'
    }
  }
})

// 计算右图数据：毛白价差&比率
const rightChartData = computed<DualAxisData | null>(() => {
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

// 格式化更新日期（只显示年月日）
const formatUpdateDate = (dateStr: string | null | undefined): string | null => {
  if (!dateStr) return null
  try {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}年${month}月${day}日`
  } catch {
    return null
  }
}

// 加载数据
const loadData = async () => {
  try {
    loading.value = true
    const [startDate, endDate] = dateRange.value || []
    
    // 加载毛白价差数据
    const response = await getLiveWhiteSpreadDualAxis(startDate, endDate)
    apiData.value = response
    latestUpdateTime.value = response.latest_date
    
    // TODO: 加载生猪价格数据（用于左图）
    // 暂时不加载，等待后端API支持
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 初始化
onMounted(() => {
  // 默认加载全部日期数据
  const range = getDateRange('all')
  if (range) {
    dateRange.value = range
    loadData()
  }
})
</script>

<style scoped>
.live-white-spread-page {
  padding: 4px;
}

.live-white-spread-page :deep(.el-card__body) {
  padding: 4px 6px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 4px;
  background: #fff;
}

.chart-wrapper {
  padding: 0;
}

.chart-box {
  margin-bottom: 6px;
}

.info-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 6px;
  background-color: transparent;
}

.chart-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 6px 0;
  color: #303133;
  text-align: left;
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
