<template>
  <div class="chart-builder-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>图表配置</span>
          <div>
            <el-button @click="handleLoadTemplate">从模板加载</el-button>
            <el-button @click="handleSaveTemplate">保存为模板</el-button>
          </div>
        </div>
      </template>
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 季节性图配置标签页 -->
        <el-tab-pane label="季节性图（多年叠线）" name="seasonality">
          <el-form :model="seasonalityConfig" label-width="120px" style="margin-top: 20px">
            <el-form-item label="指标组（可选，支持多选）">
              <el-select 
                v-model="seasonalityConfig.metric_groups" 
                placeholder="请选择指标组（不选则显示所有）" 
                multiple
                clearable
                collapse-tags
                collapse-tags-tooltip
                style="width: 100%"
                @change="handleSeasonalityGroupChange"
              >
                <el-option label="分省区" value="province" />
                <el-option label="集团企业" value="group" />
                <el-option label="交割库" value="warehouse" />
                <el-option label="价差" value="spread" />
                <el-option label="利润" value="profit" />
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                提示：选择指标组后，下方指标列表会自动过滤
              </div>
            </el-form-item>
            <el-form-item label="指标" required>
              <el-select
                v-model="seasonalityConfig.metric_id"
                placeholder="请选择指标"
                :loading="metricsLoading"
                style="width: 100%"
              >
                <el-option
                  v-for="metric in filteredSeasonalityMetrics"
                  :key="metric.id"
                  :label="metric.raw_header"
                  :value="metric.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="年份范围" required>
              <el-select
                v-model="seasonalityConfig.years"
                multiple
                placeholder="请选择年份"
                style="width: 100%"
              >
                <el-option
                  v-for="year in availableYears"
                  :key="year"
                  :label="`${year}年度`"
                  :value="year"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="X轴模式">
              <el-radio-group v-model="seasonalityConfig.x_mode">
                <el-radio label="week_of_year">周序号（1-52）</el-radio>
                <el-radio label="month_day">月-日（01-01至12-31）</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <!-- 维度过滤 -->
            <el-divider>维度过滤（可选）</el-divider>
            <el-form-item label="地区">
              <el-select
                v-model="seasonalityConfig.geo_ids"
                multiple
                placeholder="请选择地区"
                :loading="geoLoading"
                style="width: 100%"
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
                v-model="seasonalityConfig.company_ids"
                multiple
                placeholder="请选择企业"
                :loading="companyLoading"
                style="width: 100%"
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
              <el-button type="primary" @click="handleGenerateSeasonality">生成季节性图</el-button>
              <el-button @click="handleResetSeasonality">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 区间多指标图配置标签页 -->
        <el-tab-pane label="区间多指标图" name="timeseries">
          <el-form :model="timeseriesConfig" label-width="120px" style="margin-top: 20px">
            <el-form-item label="时间范围" required>
              <el-date-picker
                v-model="timeseriesDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="指标组（可选，支持多选）">
              <el-select 
                v-model="timeseriesConfig.metric_groups" 
                placeholder="请选择指标组（不选则显示所有）" 
                multiple
                clearable
                collapse-tags
                collapse-tags-tooltip
                style="width: 100%"
                @change="handleTimeseriesGroupChange"
              >
                <el-option label="分省区" value="province" />
                <el-option label="集团企业" value="group" />
                <el-option label="交割库" value="warehouse" />
                <el-option label="价差" value="spread" />
                <el-option label="利润" value="profit" />
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                提示：选择指标组后，下方指标列表会自动过滤
              </div>
            </el-form-item>
            <el-form-item label="指标（1-N个）" required>
              <el-select
                v-model="timeseriesConfig.metric_ids"
                multiple
                placeholder="请选择指标（支持多选）"
                :loading="metricsLoading"
                style="width: 100%"
              >
                <el-option
                  v-for="metric in filteredTimeseriesMetrics"
                  :key="metric.id"
                  :label="metric.raw_header"
                  :value="metric.id"
                />
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                提示：MVP阶段仅支持同频指标（daily和weekly不混画）
              </div>
            </el-form-item>
            <el-form-item label="时间维度">
              <el-select v-model="timeseriesConfig.time_dimension" placeholder="请选择" clearable>
                <el-option label="日度" value="daily" />
                <el-option label="周度" value="weekly" />
                <el-option label="月度" value="monthly" />
                <el-option label="季度" value="quarterly" />
                <el-option label="年度" value="yearly" />
              </el-select>
            </el-form-item>
            
            <!-- 维度过滤 -->
            <el-divider>维度过滤（可选）</el-divider>
            <el-form-item label="地区">
              <el-select
                v-model="timeseriesConfig.geo_ids"
                multiple
                placeholder="请选择地区"
                :loading="geoLoading"
                style="width: 100%"
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
                v-model="timeseriesConfig.company_ids"
                multiple
                placeholder="请选择企业"
                :loading="companyLoading"
                style="width: 100%"
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
              <el-button type="primary" @click="handleGenerateTimeseries">生成区间图</el-button>
              <el-button @click="handleResetTimeseries">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 图表展示区域 -->
    <div style="margin-top: 30px">
      <el-divider>
        <span style="font-size: 16px; font-weight: bold">图表展示区域</span>
      </el-divider>
      
      <!-- 两列布局 -->
      <el-row :gutter="20" v-if="seasonalityData || timeseriesData">
        <!-- 左列：季节性图 -->
        <el-col :span="12">
          <el-card v-if="seasonalityData" shadow="hover" style="height: 100%">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="font-weight: bold; color: #409eff">📊 季节性图表（多年叠线）</span>
                <el-button type="danger" size="small" @click="seasonalityData = null">清除</el-button>
              </div>
            </template>
            <SeasonalityChart
              :data="seasonalityData"
              :loading="seasonalityLoading"
              :title="seasonalityTitle"
            />
          </el-card>
          <el-card v-else shadow="never" style="height: 600px; display: flex; align-items: center; justify-content: center">
            <el-empty description="暂无季节性图表" :image-size="100">
              <template #description>
                <p style="color: #909399; margin: 0">在"季节性图"标签页配置并生成</p>
              </template>
            </el-empty>
          </el-card>
        </el-col>
        
        <!-- 右列：区间多指标图 -->
        <el-col :span="12">
          <el-card v-if="timeseriesData" shadow="hover" style="height: 100%">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="font-weight: bold; color: #67c23a">📈 区间多指标图表</span>
                <el-button type="danger" size="small" @click="timeseriesData = null">清除</el-button>
              </div>
            </template>
            <ChartPanel
              :data="timeseriesData"
              :loading="timeseriesLoading"
            />
          </el-card>
          <el-card v-else shadow="never" style="height: 600px; display: flex; align-items: center; justify-content: center">
            <el-empty description="暂无区间图表" :image-size="100">
              <template #description>
                <p style="color: #909399; margin: 0">在"区间多指标图"标签页配置并生成</p>
              </template>
            </el-empty>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 提示信息：两个图表都没有时 -->
      <el-card v-if="!seasonalityData && !timeseriesData" shadow="never">
        <el-empty description="暂无图表">
          <template #image>
            <el-icon :size="60" color="#909399"><DataAnalysis /></el-icon>
          </template>
          <template #description>
            <div style="text-align: left; max-width: 600px; margin: 0 auto">
              <p style="margin-bottom: 10px; font-weight: bold">请配置并生成图表：</p>
              <ul style="margin: 10px 0; padding-left: 20px; line-height: 2">
                <li><strong>季节性图</strong>：在"季节性图（多年叠线）"标签页选择指标和年份范围，点击"生成季节性图"</li>
                <li><strong>区间多指标图</strong>：在"区间多指标图"标签页选择时间范围和指标，点击"生成区间图"</li>
              </ul>
              <el-alert
                type="info"
                :closable="false"
                style="margin-top: 15px"
              >
                <template #default>
                  <p style="margin: 0">💡 提示：两个图表可以同时显示，互不影响。生成后图表会并排显示在此区域。</p>
                </template>
              </el-alert>
            </div>
          </template>
        </el-empty>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import SeasonalityChart, { type SeasonalityData } from '../components/SeasonalityChart.vue'
import ChartPanel, { type ChartData } from '../components/ChartPanel.vue'
import { queryApi, type SeasonalityResponse } from '../api/query'
import { metadataApi, type MetricInfo, type GeoInfo, type CompanyInfo } from '../api/metadata'
import { templatesApi } from '../api/templates'

const route = useRoute()
const router = useRouter()

const activeTab = ref('seasonality')

// 季节性图配置
const seasonalityConfig = reactive({
  metric_groups: [] as string[],
  metric_id: null as number | null,
  years: [] as number[],
  x_mode: 'week_of_year' as 'week_of_year' | 'month_day',
  geo_ids: [] as number[],
  company_ids: [] as number[]
})

// 区间多指标图配置
const timeseriesConfig = reactive({
  metric_groups: [] as string[],
  metric_ids: [] as number[],
  time_dimension: 'daily' as 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly',
  geo_ids: [] as number[],
  company_ids: [] as number[]
})

const timeseriesDateRange = ref<[Date, Date] | null>(null)

// 图表数据
const seasonalityData = ref<SeasonalityData | null>(null)
const timeseriesData = ref<ChartData | null>(null)
const seasonalityLoading = ref(false)
const timeseriesLoading = ref(false)

const metrics = ref<MetricInfo[]>([])
const geos = ref<GeoInfo[]>([])
const companies = ref<CompanyInfo[]>([])

const metricsLoading = ref(false)
const geoLoading = ref(false)
const companyLoading = ref(false)

// 根据指标组过滤后的指标列表
const filteredSeasonalityMetrics = computed(() => {
  if (seasonalityConfig.metric_groups.length === 0) {
    return metrics.value
  }
  return metrics.value.filter(m => seasonalityConfig.metric_groups.includes(m.metric_group))
})

const filteredTimeseriesMetrics = computed(() => {
  if (timeseriesConfig.metric_groups.length === 0) {
    return metrics.value
  }
  return metrics.value.filter(m => timeseriesConfig.metric_groups.includes(m.metric_group))
})

// 生成可用年份列表（当前年份前后5年）
const currentYear = new Date().getFullYear()
const availableYears = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i)

// 季节性图标题
const seasonalityTitle = computed(() => {
  if (seasonalityConfig.metric_id) {
    const metric = metrics.value.find(m => m.id === seasonalityConfig.metric_id)
    return metric ? `${metric.raw_header} - 季节性分析` : '季节性图表'
  }
  return '季节性图表'
})

// 生成季节性图
const handleGenerateSeasonality = async () => {
  if (!seasonalityConfig.metric_id || seasonalityConfig.years.length === 0) {
    ElMessage.warning('请选择指标和年份范围')
    return
  }
  
  seasonalityLoading.value = true
  try {
    const result = await queryApi.seasonality({
      metric_id: seasonalityConfig.metric_id,
      years: seasonalityConfig.years,
      geo_ids: seasonalityConfig.geo_ids.length > 0 ? seasonalityConfig.geo_ids : undefined,
      company_ids: seasonalityConfig.company_ids.length > 0 ? seasonalityConfig.company_ids : undefined,
      x_mode: seasonalityConfig.x_mode,
      agg: 'mean'
    })
    seasonalityData.value = result
    console.log('季节性图数据:', result)
    ElMessage.success('季节性图生成成功！图表已显示在下方。')
  } catch (error) {
    ElMessage.error('查询失败')
    console.error(error)
  } finally {
    seasonalityLoading.value = false
  }
}

// 生成区间多指标图
const handleGenerateTimeseries = async () => {
  if (!timeseriesDateRange.value || timeseriesConfig.metric_ids.length === 0) {
    ElMessage.warning('请选择时间范围和至少一个指标')
    return
  }
  
  // MVP：检查指标频率是否一致
  const selectedMetrics = metrics.value.filter(m => timeseriesConfig.metric_ids.includes(m.id))
  const freqs = new Set(selectedMetrics.map(m => m.freq))
  if (freqs.size > 1) {
    ElMessage.warning('MVP阶段不支持混频指标，请选择相同频率的指标')
    return
  }
  
  timeseriesLoading.value = true
  try {
    const formatDate = (date: Date): string => {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }
    
    const result = await queryApi.timeseries({
      date_range: {
        start: formatDate(timeseriesDateRange.value[0]),
        end: formatDate(timeseriesDateRange.value[1])
      },
      time_dimension: timeseriesConfig.time_dimension || 'daily',
      metric_ids: timeseriesConfig.metric_ids,
      geo_ids: timeseriesConfig.geo_ids.length > 0 ? timeseriesConfig.geo_ids : undefined,
      company_ids: timeseriesConfig.company_ids.length > 0 ? timeseriesConfig.company_ids : undefined
    })
    
    // 转换数据格式
    timeseriesData.value = {
      series: result.series.map(series => ({
        ...series,
        unit: detectUnit(series.name)
      })),
      categories: result.categories
    }
    console.log('区间图数据:', timeseriesData.value)
    ElMessage.success('区间图生成成功！图表已显示在下方。')
  } catch (error) {
    ElMessage.error('查询失败')
    console.error(error)
  } finally {
    timeseriesLoading.value = false
  }
}

// 指标组变化时重新加载指标列表
const handleSeasonalityGroupChange = async () => {
  // 清空当前选择的指标
  seasonalityConfig.metric_id = null
  // 重新加载指标（根据指标组过滤）
  await loadMetrics()
}

const handleTimeseriesGroupChange = async () => {
  // 清空当前选择的指标
  timeseriesConfig.metric_ids = []
  // 重新加载指标（根据指标组过滤）
  await loadMetrics()
}

const handleResetSeasonality = () => {
  seasonalityConfig.metric_groups = []
  seasonalityConfig.metric_id = null
  seasonalityConfig.years = []
  seasonalityConfig.x_mode = 'week_of_year'
  seasonalityConfig.geo_ids = []
  seasonalityConfig.company_ids = []
  seasonalityData.value = null
  loadMetrics() // 重置后重新加载所有指标
}

const handleResetTimeseries = () => {
  timeseriesConfig.metric_groups = []
  timeseriesConfig.metric_ids = []
  timeseriesConfig.time_dimension = 'daily'
  timeseriesConfig.geo_ids = []
  timeseriesConfig.company_ids = []
  timeseriesDateRange.value = null
  timeseriesData.value = null
  loadMetrics() // 重置后重新加载所有指标
}

const detectUnit = (name: string): string => {
  if (name.includes('价差') || name.includes('价')) {
    return '元/千克'
  }
  if (name.includes('利润')) {
    return '元'
  }
  return ''
}

const loadMetrics = async () => {
  metricsLoading.value = true
  try {
    // 根据当前选择的指标组加载指标
    let groups: string[] | undefined = undefined
    if (activeTab.value === 'seasonality' && seasonalityConfig.metric_groups.length > 0) {
      groups = seasonalityConfig.metric_groups
    } else if (activeTab.value === 'timeseries' && timeseriesConfig.metric_groups.length > 0) {
      groups = timeseriesConfig.metric_groups
    }
    
    metrics.value = await metadataApi.getMetrics(groups)
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

// 监听标签页切换，重新加载指标
watch(() => activeTab.value, () => {
  loadMetrics()
})

// 模板保存和加载
const handleSaveTemplate = async () => {
  try {
    // 确定当前配置类型
    let chartType: 'seasonality' | 'timeseries'
    let specJson: any
    
    if (activeTab.value === 'seasonality') {
      if (!seasonalityConfig.metric_id || seasonalityConfig.years.length === 0) {
        ElMessage.warning('请先配置季节性图')
        return
      }
      chartType = 'seasonality'
      specJson = {
        chart_type: 'seasonality',
        metrics: [{ metric_id: seasonalityConfig.metric_id }],
        filters: {
          geo_ids: seasonalityConfig.geo_ids || [],
          company_ids: seasonalityConfig.company_ids || []
        },
        seasonality: {
          years: seasonalityConfig.years,
          x_mode: seasonalityConfig.x_mode,
          agg: 'mean'
        }
      }
    } else {
      if (!timeseriesDateRange.value || timeseriesConfig.metric_ids.length === 0) {
        ElMessage.warning('请先配置区间图')
        return
      }
      chartType = 'timeseries'
      const formatDate = (date: Date): string => {
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }
      specJson = {
        chart_type: 'timeseries',
        metrics: timeseriesConfig.metric_ids.map(id => ({ metric_id: id })),
        filters: {
          geo_ids: timeseriesConfig.geo_ids || [],
          company_ids: timeseriesConfig.company_ids || []
        },
        time: {
          dimension: timeseriesConfig.time_dimension || 'daily',
          date_range: timeseriesDateRange.value ? {
            start: formatDate(timeseriesDateRange.value[0]),
            end: formatDate(timeseriesDateRange.value[1])
          } : undefined
        }
      }
    }
    
    const { value: name } = await ElMessageBox.prompt('请输入模板名称', '保存模板', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '模板名称不能为空'
    })
    
    await templatesApi.createTemplate({
      name,
      chart_type: chartType,
      spec_json: specJson
    })
    
    ElMessage.success('模板保存成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '保存失败')
    }
  }
}

const handleLoadTemplate = async () => {
  try {
    const templates = await templatesApi.getTemplates('all')
    
    if (templates.length === 0) {
      ElMessage.warning('暂无可用模板')
      return
    }
    
    const { value: selectedId } = await ElMessageBox.prompt(
      '请选择要加载的模板',
      '加载模板',
      {
        confirmButtonText: '加载',
        cancelButtonText: '取消',
        inputType: 'select',
        inputOptions: templates.reduce((acc, t) => {
          acc[t.id] = `${t.name} (${t.chart_type === 'seasonality' ? '季节性图' : '区间图'})`
          return acc
        }, {} as Record<number, string>)
      }
    )
    
    if (!selectedId) return
    
    const template = await templatesApi.getTemplate(Number(selectedId))
    const spec = template.spec_json
    
    // 检查是否是预设模板（有template_id字段）
    if (spec.template_id) {
      // 预设模板：跳转到模板中心页面
      router.push({
        path: '/template-center',
        query: { template_id: spec.template_id }
      })
      return
    }
    
    // 根据模板类型切换到对应标签页并应用配置
    if (spec.chart_type === 'seasonality') {
      activeTab.value = 'seasonality'
      if (spec.metrics && spec.metrics.length > 0) {
        seasonalityConfig.metric_id = spec.metrics[0].metric_id
      }
      if (spec.seasonality) {
        seasonalityConfig.years = spec.seasonality.years || []
        seasonalityConfig.x_mode = spec.seasonality.x_mode || 'week_of_year'
      }
      if (spec.filters) {
        seasonalityConfig.geo_ids = spec.filters.geo_ids || []
        seasonalityConfig.company_ids = spec.filters.company_ids || []
      }
      ElMessage.success('模板已加载，请点击"生成季节性图"查看结果')
    } else if (spec.chart_type === 'timeseries') {
      activeTab.value = 'timeseries'
      if (spec.metrics && spec.metrics.length > 0) {
        timeseriesConfig.metric_ids = spec.metrics.map((m: any) => m.metric_id)
      }
      if (spec.time) {
        timeseriesConfig.time_dimension = spec.time.dimension || 'daily'
        if (spec.time.date_range) {
          timeseriesDateRange.value = [
            new Date(spec.time.date_range.start),
            new Date(spec.time.date_range.end)
          ]
        }
      }
      if (spec.filters) {
        timeseriesConfig.geo_ids = spec.filters.geo_ids || []
        timeseriesConfig.company_ids = spec.filters.company_ids || []
      }
      ElMessage.success('模板已加载，请点击"生成区间图"查看结果')
    } else {
      ElMessage.warning('不支持的模板类型')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('加载模板失败')
    }
  }
}

onMounted(async () => {
  await loadMetrics()
  await loadGeos()
  await loadCompanies()
  
  // 检查URL参数中是否有preset_template_id（预设模板）
  const presetTemplateId = route.query.preset_template_id
  if (presetTemplateId) {
    try {
      // 获取预设模板配置
      const template = await templatesApi.getPresetTemplate(presetTemplateId as string)
      
      // 从URL参数获取用户参数
      const userParams: any = {}
      if (route.query.years) {
        const yearsParam = route.query.years
        if (Array.isArray(yearsParam)) {
          userParams.years = yearsParam.map(y => Number(y))
        } else if (typeof yearsParam === 'string') {
          // 尝试解析JSON数组或逗号分隔的字符串
          try {
            userParams.years = JSON.parse(yearsParam)
          } catch {
            userParams.years = yearsParam.split(',').map(y => Number(y.trim()))
          }
        }
      }
      if (route.query.x_mode) {
        userParams.x_mode = route.query.x_mode as string
      }
      if (route.query.agg) {
        userParams.agg = route.query.agg as string
      }
      if (route.query.date_range) {
        // 日期范围需要特殊处理
        const dr = route.query.date_range as any
        if (typeof dr === 'string') {
          try {
            const parsed = JSON.parse(dr)
            userParams.date_range = parsed
          } catch {
            // 忽略解析错误
          }
        } else if (typeof dr === 'object') {
          userParams.date_range = dr
        }
      }
      
      // 应用预设模板配置
      if (template.chart_type === 'seasonality') {
        activeTab.value = 'seasonality'
        
        // 从blocks中获取第一个seasonality block的配置
        const seasonalityBlock = template.blocks?.find((b: any) => b.type === 'seasonality')
        if (seasonalityBlock) {
          const query = seasonalityBlock.query
          
          // 尝试解析metric_code为metric_id
          // 通过调用后端执行API来获取metric_id
          try {
            const executeResult = await templatesApi.executePresetTemplate(
              presetTemplateId as string,
              userParams
            )
            
            // 从执行结果中获取metric_id
            const blockResult = executeResult.blocks?.[seasonalityBlock.block_id]
            if (blockResult && blockResult.data) {
              // 执行成功，直接使用数据
              seasonalityData.value = blockResult.data
              ElMessage.success(`模板已执行：${template.name}`)
              return
            }
          } catch (error) {
            console.warn('执行模板失败，尝试手动解析:', error)
          }
          
          // 如果执行失败，尝试手动解析metric_code
          // 根据metric_code确定指标组
          const metricCode = query.metric_code
          let targetGroup = 'spread' // 默认
          if (metricCode === 'SPREAD_STANDARD_FATTY' || metricCode === 'SPREAD_MAO_BAI') {
            targetGroup = 'spread'
          } else if (metricCode === 'HOG_PRICE_NATIONAL' || metricCode === 'PRICE_BY_PROVINCE') {
            targetGroup = 'province'
          } else if (metricCode === 'PRICE_BY_GROUP') {
            targetGroup = 'group'
          }
          
          // 加载对应指标组的指标
          seasonalityConfig.metric_groups = [targetGroup]
          await loadMetrics()
          
          // 尝试自动选择指标（根据metric_code的关键词）
          const keywords: Record<string, string[]> = {
            'SPREAD_STANDARD_FATTY': ['标肥', '价差'],
            'SPREAD_MAO_BAI': ['毛白', '价差'],
            'HOG_PRICE_NATIONAL': ['商品猪', '出栏均价', '中国'],
            'PRICE_BY_PROVINCE': ['商品猪', '出栏均价'],
            'PRICE_BY_GROUP': ['外三元', '出栏价']
          }
          
          if (keywords[metricCode]) {
            const matchedMetric = metrics.value.find(m => 
              keywords[metricCode].some(kw => m.raw_header.includes(kw))
            )
            if (matchedMetric) {
              seasonalityConfig.metric_id = matchedMetric.id
            }
          }
          
          // 应用用户参数
          if (userParams.years && userParams.years.length > 0) {
            seasonalityConfig.years = userParams.years
          } else {
            // 默认最近6年
            const currentYear = new Date().getFullYear()
            seasonalityConfig.years = Array.from({ length: 6 }, (_, i) => currentYear - 5 + i)
          }
          if (userParams.x_mode) {
            seasonalityConfig.x_mode = userParams.x_mode as any
          } else {
            const xModeValue = query.x_mode
            if (xModeValue && !xModeValue.startsWith('{{')) {
              seasonalityConfig.x_mode = xModeValue as any
            } else {
              seasonalityConfig.x_mode = 'week_of_year'
            }
          }
          
          ElMessage.success(`模板已加载：${template.name}，请点击"生成季节性图"查看结果`)
        }
      } else if (template.chart_type === 'timeseries') {
        activeTab.value = 'timeseries'
        
        // 从blocks中获取第一个timeseries block的配置
        const timeseriesBlock = template.blocks?.find((b: any) => 
          b.type === 'timeseries' || b.type === 'timeseries_dual_axis' || b.type === 'timeseries_multi_line'
        )
        
        if (timeseriesBlock) {
          const query = timeseriesBlock.query
          
          // 尝试执行模板
          try {
            const executeResult = await templatesApi.executePresetTemplate(
              presetTemplateId as string,
              userParams
            )
            
            const blockResult = executeResult.blocks?.[timeseriesBlock.block_id]
            if (blockResult && blockResult.data) {
              // 执行成功，直接使用数据
              timeseriesData.value = {
                series: blockResult.data.series.map((s: any) => ({
                  ...s,
                  unit: detectUnit(s.name)
                })),
                categories: blockResult.data.categories
              }
              ElMessage.success(`模板已执行：${template.name}`)
              return
            }
          } catch (error) {
            console.warn('执行模板失败，尝试手动解析:', error)
          }
          
          // 如果执行失败，手动解析
          if (query.metrics && Array.isArray(query.metrics)) {
            // 双轴或多指标
            const metricCodes = query.metrics.map((m: any) => m.metric_code).filter(Boolean)
            const targetGroups = new Set<string>()
            
            metricCodes.forEach((code: string) => {
              if (code.includes('SPREAD')) targetGroups.add('spread')
              else if (code.includes('PRICE')) targetGroups.add('province')
              else if (code.includes('GROUP')) targetGroups.add('group')
            })
            
            timeseriesConfig.metric_groups = Array.from(targetGroups)
            await loadMetrics()
            
            // 尝试自动选择指标
            const selectedMetricIds: number[] = []
            metricCodes.forEach((code: string) => {
              const keywords: Record<string, string[]> = {
                'SPREAD_STANDARD_FATTY': ['标肥', '价差'],
                'SPREAD_MAO_BAI': ['毛白', '价差'],
                'HOG_PRICE_NATIONAL': ['商品猪', '出栏均价', '中国'],
                'PRICE_BY_PROVINCE': ['商品猪', '出栏均价']
              }
              
              if (keywords[code]) {
                const matchedMetric = metrics.value.find(m => 
                  keywords[code].some(kw => m.raw_header.includes(kw))
                )
                if (matchedMetric && !selectedMetricIds.includes(matchedMetric.id)) {
                  selectedMetricIds.push(matchedMetric.id)
                }
              }
            })
            
            if (selectedMetricIds.length > 0) {
              timeseriesConfig.metric_ids = selectedMetricIds
            }
          }
        }
        
        // 应用用户参数
        if (userParams.date_range) {
          timeseriesDateRange.value = [
            new Date(userParams.date_range.start),
            new Date(userParams.date_range.end)
          ]
        } else {
          // 默认本年迄今
          const today = new Date()
          timeseriesDateRange.value = [
            new Date(today.getFullYear(), 0, 1),
            today
          ]
        }
        
        if (userParams.time_dimension) {
          timeseriesConfig.time_dimension = userParams.time_dimension as any
        }
        
        ElMessage.success(`模板已加载：${template.name}，请点击"生成区间图"查看结果`)
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '加载预设模板失败'
      ElMessage.error(`加载预设模板失败: ${errorMessage}`)
      console.error('加载预设模板失败:', error)
    }
  }
  
  // 检查URL参数中是否有template_id（用户保存的模板）
  const templateId = route.query.template_id
  if (templateId && !presetTemplateId) {
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:958',message:'Loading user template from URL',data:{templateId,presetTemplateId,queryParams:route.query},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H5'})}).catch(()=>{});
    // #endregion
    try {
      const numericId = Number(templateId)
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:962',message:'Before API call',data:{numericId,isNaN:isNaN(numericId)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H5'})}).catch(()=>{});
      // #endregion
      
      const template = await templatesApi.getTemplate(numericId)
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:966',message:'API call succeeded',data:{templateId:template.id,templateName:template.name,chartType:template.chart_type,hasSpecJson:!!template.spec_json},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H1'})}).catch(()=>{});
      // #endregion
      
      const spec = template.spec_json
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:969',message:'Parsed spec_json',data:{chartType:spec?.chart_type,hasMetrics:!!spec?.metrics,metricsLength:spec?.metrics?.length,hasSeasonality:!!spec?.seasonality,hasTime:!!spec?.time,hasFilters:!!spec?.filters,hasTemplateId:!!spec?.template_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H2'})}).catch(()=>{});
      // #endregion
      
      // 检查是否是预设模板（有template_id字段）
      if (spec.template_id) {
        // 预设模板：跳转到模板中心页面
        router.push({
          path: '/template-center',
          query: { template_id: spec.template_id }
        })
        return
      }
      
      if (spec.chart_type === 'seasonality') {
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:978',message:'Applying seasonality config',data:{metricId:spec.metrics?.[0]?.metric_id,years:spec.seasonality?.years,xMode:spec.seasonality?.x_mode},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
        activeTab.value = 'seasonality'
        if (spec.metrics && spec.metrics.length > 0) {
          seasonalityConfig.metric_id = spec.metrics[0].metric_id
        }
        if (spec.seasonality) {
          seasonalityConfig.years = spec.seasonality.years || []
          seasonalityConfig.x_mode = spec.seasonality.x_mode || 'week_of_year'
        }
        if (spec.filters) {
          seasonalityConfig.geo_ids = spec.filters.geo_ids || []
          seasonalityConfig.company_ids = spec.filters.company_ids || []
        }
        // 自动生成图表
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:988',message:'Before calling handleGenerateSeasonality',data:{metricId:seasonalityConfig.metric_id,years:seasonalityConfig.years},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
        await handleGenerateSeasonality()
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:990',message:'After calling handleGenerateSeasonality',data:{hasData:!!seasonalityData.value},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
      } else if (spec.chart_type === 'timeseries') {
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:992',message:'Applying timeseries config',data:{metricIds:spec.metrics?.map((m:any)=>m.metric_id),timeDimension:spec.time?.dimension},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
        activeTab.value = 'timeseries'
        if (spec.metrics && spec.metrics.length > 0) {
          timeseriesConfig.metric_ids = spec.metrics.map((m: any) => m.metric_id)
        }
        if (spec.time) {
          timeseriesConfig.time_dimension = spec.time.dimension || 'daily'
          if (spec.time.date_range) {
            timeseriesDateRange.value = [
              new Date(spec.time.date_range.start),
              new Date(spec.time.date_range.end)
            ]
          }
        }
        if (spec.filters) {
          timeseriesConfig.geo_ids = spec.filters.geo_ids || []
          timeseriesConfig.company_ids = spec.filters.company_ids || []
        }
        // 自动生成图表
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:1008',message:'Before calling handleGenerateTimeseries',data:{metricIds:timeseriesConfig.metric_ids,dateRange:timeseriesDateRange.value},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
        await handleGenerateTimeseries()
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:1010',message:'After calling handleGenerateTimeseries',data:{hasData:!!timeseriesData.value},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H3'})}).catch(()=>{});
        // #endregion
      }
    } catch (error: any) {
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChartBuilder.vue:1012',message:'Error loading template',data:{errorMessage:error?.message,errorResponse:error?.response?.data,statusCode:error?.response?.status,stack:error?.stack},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H1,H4'})}).catch(()=>{});
      // #endregion
      ElMessage.error(`加载模板失败: ${error?.response?.data?.detail || error?.message || '未知错误'}`)
    }
  }
})
</script>

<style scoped>
.chart-builder-page {
  padding: 20px;
}
</style>
