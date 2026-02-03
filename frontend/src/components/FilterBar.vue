<template>
  <el-card class="filter-bar">
    <el-form :model="filters" inline>
      <!-- 时间范围 -->
      <el-form-item label="时间范围">
        <el-radio-group v-model="timeRangeType" @change="handleTimeRangeChange">
          <el-radio-button label="1m">近1月</el-radio-button>
          <el-radio-button label="3m">近3月</el-radio-button>
          <el-radio-button label="6m">近6月</el-radio-button>
          <el-radio-button label="1y">近1年</el-radio-button>
          <el-radio-button label="custom">自定义</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-if="timeRangeType === 'custom'"
          v-model="customDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="handleCustomDateRangeChange"
          style="margin-left: 10px"
        />
      </el-form-item>

      <!-- 区域筛选 -->
      <el-form-item v-if="showRegionFilter" label="区域">
        <el-select
          v-model="filters.region"
          placeholder="请选择区域"
          clearable
          @change="handleFilterChange"
        >
          <el-option label="全国" value="NATION" />
          <el-option label="东北" value="NORTHEAST" />
          <el-option label="华北" value="NORTH" />
          <el-option label="华东" value="EAST" />
          <el-option label="华中" value="CENTRAL" />
          <el-option label="华南" value="SOUTH" />
          <el-option label="西南" value="SOUTHWEST" />
          <el-option label="西北" value="NORTHWEST" />
        </el-select>
      </el-form-item>

      <!-- 年度筛选（季节性图） -->
      <el-form-item v-if="showYearFilter" label="年度">
        <el-checkbox-group v-model="filters.years" @change="handleFilterChange">
          <el-checkbox
            v-for="year in availableYears"
            :key="year"
            :label="year"
          >
            {{ year }}年
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <!-- 频率筛选 -->
      <el-form-item v-if="showFreqFilter" label="频率">
        <el-radio-group v-model="filters.freq" @change="handleFilterChange">
          <el-radio-button label="D">日频</el-radio-button>
          <el-radio-button label="W">周频</el-radio-button>
        </el-radio-group>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Props {
  showRegionFilter?: boolean
  showYearFilter?: boolean
  showFreqFilter?: boolean
  availableYears?: number[]
  defaultTimeRange?: '1m' | '3m' | '6m' | '1y' | 'custom'
}

const props = withDefaults(defineProps<Props>(), {
  showRegionFilter: true,
  showYearFilter: false,
  showFreqFilter: false,
  availableYears: () => [2024, 2025, 2026],
  defaultTimeRange: '6m'
})

const emit = defineEmits<{
  (e: 'change', filters: FilterValues): void
}>()

interface FilterValues {
  dateRange: {
    start: string
    end: string
  }
  region?: string
  years?: number[]
  freq?: 'D' | 'W'
}

const filters = ref<FilterValues>({
  dateRange: {
    start: '',
    end: ''
  },
  region: undefined,
  years: props.availableYears.slice(-2), // 默认选择最近2年
  freq: 'D'
})

const timeRangeType = ref<string>(props.defaultTimeRange)
const customDateRange = ref<[string, string] | null>(null)

// 计算日期范围
const calculateDateRange = (type: string) => {
  const end = new Date()
  const start = new Date()

  switch (type) {
    case '1m':
      start.setMonth(end.getMonth() - 1)
      break
    case '3m':
      start.setMonth(end.getMonth() - 3)
      break
    case '6m':
      start.setMonth(end.getMonth() - 6)
      break
    case '1y':
      start.setFullYear(end.getFullYear() - 1)
      break
  }

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0]
  }
}

const handleTimeRangeChange = (type: string) => {
  if (type !== 'custom') {
    const range = calculateDateRange(type)
    filters.value.dateRange = range
    emit('change', filters.value)
  }
}

const handleCustomDateRangeChange = (range: [string, string] | null) => {
  if (range) {
    filters.value.dateRange = {
      start: range[0],
      end: range[1]
    }
    emit('change', filters.value)
  }
}

const handleFilterChange = () => {
  emit('change', filters.value)
}

// 初始化日期范围
const initDateRange = () => {
  if (timeRangeType.value !== 'custom') {
    const range = calculateDateRange(timeRangeType.value)
    filters.value.dateRange = range
  }
}

initDateRange()

// 暴露方法供父组件调用
defineExpose({
  getFilters: () => filters.value,
  setFilters: (newFilters: Partial<FilterValues>) => {
    Object.assign(filters.value, newFilters)
    emit('change', filters.value)
  }
})
</script>

<style scoped>
.filter-bar {
  margin-bottom: 20px;
}

.filter-bar :deep(.el-form-item) {
  margin-bottom: 0;
}
</style>
