<template>
  <el-card class="filter-panel">
    <template #header>
      <span>筛选条件</span>
    </template>
    <el-form :model="filters" label-width="100px">
      <el-form-item label="时间维度">
        <el-select v-model="filters.time_dimension" placeholder="请选择" clearable>
          <el-option label="日度" value="daily" />
          <el-option label="周度" value="weekly" />
          <el-option label="月度" value="monthly" />
          <el-option label="季度" value="quarterly" />
          <el-option label="年度" value="yearly" />
        </el-select>
      </el-form-item>
      <el-form-item label="时间范围（可选）">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          :clearable="true"
          @change="handleDateChange"
        />
      </el-form-item>
      <el-form-item label="指标组（可选，支持多选）">
        <el-select 
          v-model="filters.metric_groups" 
          placeholder="请选择指标组（不选则显示所有）" 
          multiple
          clearable
          collapse-tags
          collapse-tags-tooltip
        >
          <el-option label="分省区" value="province" />
          <el-option label="集团企业" value="group" />
          <el-option label="交割库" value="warehouse" />
          <el-option label="价差" value="spread" />
          <el-option label="利润" value="profit" />
        </el-select>
        <div style="font-size: 12px; color: #909399; margin-top: 4px;">
          提示：不选择指标组或选择多个指标组，可进行跨组对比分析
        </div>
      </el-form-item>
      <!-- 频率已移除：根据指标组自动确定（profit=weekly，其他=daily） -->
      <el-form-item label="指标">
        <el-select
          v-model="filters.metric_ids"
          multiple
          placeholder="请选择指标"
          :loading="metricsLoading"
        >
          <el-option
            v-for="metric in metrics"
            :key="metric.id"
            :label="metric.raw_header"
            :value="metric.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="地区">
        <el-select
          v-model="filters.geo_ids"
          multiple
          placeholder="请选择地区"
          :loading="geoLoading"
        >
          <el-option
            v-for="geo in geos"
            :key="geo.id"
            :label="geo.province"
            :value="geo.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="企业">
        <el-select
          v-model="filters.company_ids"
          multiple
          placeholder="请选择企业"
          :loading="companyLoading"
        >
          <el-option
            v-for="company in companies"
            :key="company.id"
            :label="company.company_name"
            :value="company.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleQuery">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { metadataApi, type MetricInfo, type GeoInfo, type CompanyInfo } from '../api/metadata'

const emit = defineEmits<{
  (e: 'query', filters: any): void
}>()

const dateRange = ref<[Date, Date] | null>(null)
const filters = reactive({
  time_dimension: 'daily' as 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly',
  metric_groups: [] as string[],  // 改为多选
  metric_ids: [] as number[],
  geo_ids: [] as number[],
  company_ids: [] as number[]
})

const metrics = ref<MetricInfo[]>([])
const geos = ref<GeoInfo[]>([])
const companies = ref<CompanyInfo[]>([])

const metricsLoading = ref(false)
const geoLoading = ref(false)
const companyLoading = ref(false)

// 根据指标组自动推断频率：profit=weekly，其他=daily
// 多指标组时，如果包含profit且其他组都是daily，则返回undefined（不筛选频率）
const getFreqByGroups = (groups: string[]): string | undefined => {
  if (!groups || groups.length === 0) return undefined
  
  const hasProfit = groups.includes('profit')
  const hasDaily = groups.some(g => g !== 'profit')
  
  // 如果同时包含profit和其他组，不筛选频率（显示所有频率）
  if (hasProfit && hasDaily) return undefined
  
  // 如果只有profit，返回weekly
  if (hasProfit) return 'weekly'
  
  // 如果只有其他组，返回daily
  return 'daily'
}

const handleDateChange = () => {
  // 日期变化时触发查询
}

const handleQuery = () => {
  // 格式化日期为 YYYY-MM-DD 格式
  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  const queryFilters = {
    date_range: dateRange.value && dateRange.value.length === 2
      ? {
          start: formatDate(dateRange.value[0]),
          end: formatDate(dateRange.value[1])
        }
      : undefined,
    time_dimension: filters.time_dimension || 'daily',
    metric_groups: filters.metric_groups.length > 0 ? filters.metric_groups : undefined,
    metric_ids: filters.metric_ids,
    geo_ids: filters.geo_ids,
    company_ids: filters.company_ids
  }
  emit('query', queryFilters)
}

const handleReset = () => {
  dateRange.value = null
  filters.time_dimension = 'daily'
  filters.metric_groups = []
  filters.metric_ids = []
  filters.geo_ids = []
  filters.company_ids = []
}

const loadMetrics = async () => {
  metricsLoading.value = true
  try {
    // 根据指标组自动推断频率
    const freq = getFreqByGroups(filters.metric_groups)
    // 支持多指标组筛选
    metrics.value = await metadataApi.getMetrics(
      filters.metric_groups.length > 0 ? filters.metric_groups : undefined, 
      freq
    )
  } catch (error) {
    console.error('加载指标失败', error)
  } finally {
    metricsLoading.value = false
  }
}

const loadGeos = async () => {
  geoLoading.value = true
  try {
    geos.value = await metadataApi.getGeo()
  } catch (error) {
    console.error('加载地区失败', error)
  } finally {
    geoLoading.value = false
  }
}

const loadCompanies = async () => {
  companyLoading.value = true
  try {
    companies.value = await metadataApi.getCompany()
  } catch (error) {
    console.error('加载企业失败', error)
  } finally {
    companyLoading.value = false
  }
}

// 当指标组变化时，自动加载对应频率的指标列表
watch(() => filters.metric_groups, () => {
  // 清空已选择的指标，因为指标组变了
  filters.metric_ids = []
  loadMetrics()
}, { deep: true })

onMounted(() => {
  loadMetrics()
  loadGeos()
  loadCompanies()
})
</script>

<style scoped>
.filter-panel {
  margin-bottom: 20px;
}
</style>
