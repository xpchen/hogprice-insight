<template>
  <div class="frozen-capacity-page">
    <el-card class="filter-card">
      <!-- 筛选按钮：近3月、近6月、近2年、近3年、全部日期 -->
      <div style="margin-bottom: 16px">
        <el-radio-group v-model="selectedRange" @change="handleRangeChange" size="small">
          <el-radio-button label="3m">近3月</el-radio-button>
          <el-radio-button label="6m">近6月</el-radio-button>
          <el-radio-button label="2y">近2年</el-radio-button>
          <el-radio-button label="3y">近3年</el-radio-button>
          <el-radio-button label="all">全部日期</el-radio-button>
        </el-radio-group>
      </div>
      
      <!-- 省份筛选：2行布局，间距缩小，无边框 -->
      <div class="province-filter">
        <span class="province-label">省份筛选：</span>
        <el-radio-group v-model="filters.province" @change="handleProvinceChange" size="small">
          <div class="province-row" v-for="(row, rowIndex) in provinceRows" :key="rowIndex">
            <el-radio-button
              v-for="province in row"
              :key="province.province_name"
              :label="province.province_name"
              class="province-radio"
            >
              {{ province.province_name }}
            </el-radio-button>
          </div>
        </el-radio-group>
      </div>
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
          :source-name="'涌益'"
          :update-date="formatUpdateDate(updateTime)"
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
const updateTime = ref<string | null>(null)

const filters = ref({
  province: ''
})

// 筛选按钮状态
const selectedRange = ref<string>('all') // 默认全部日期

// 将省份分成2行
const provinceRows = computed(() => {
  const rows: FrozenInventoryProvinceInfo[][] = []
  const perRow = Math.ceil(provinces.value.length / 2)
  for (let i = 0; i < provinces.value.length; i += perRow) {
    rows.push(provinces.value.slice(i, i + perRow))
  }
  return rows
})

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
    case '2y':
      start.setFullYear(start.getFullYear() - 2)
      break
    case '3y':
      start.setFullYear(start.getFullYear() - 3)
      break
    case 'all':
      // 全部日期：返回一个很大的日期范围
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
  // 筛选按钮变化时，重新加载数据（如果需要按日期筛选）
  // 注意：当前API可能不支持日期范围筛选，这里先保留接口
  if (filters.value.province) {
    loadSeasonalityData()
  }
}

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
    
    // 保存更新时间
    updateTime.value = response.update_time
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

.province-filter {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.province-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
  padding-top: 4px;
}

.province-row {
  display: flex;
  gap: 6px; /* 间距缩小 */
  margin-bottom: 6px; /* 间距缩小 */
  flex-wrap: wrap;
}

.province-radio {
  flex: 1;
  min-width: 80px;
  text-align: center;
}

/* 移除el-radio-button的边框 */
.province-radio :deep(.el-radio-button__inner) {
  border: none;
  box-shadow: none;
  background-color: #f5f7fa;
}

.province-radio :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #409eff;
  color: #fff;
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
