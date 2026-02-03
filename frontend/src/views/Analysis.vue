<template>
  <div class="analysis-page">
    <el-row :gutter="20">
      <el-col :span="18">
        <FilterPanel @query="handleQuery" />
        <ChartPanel :data="chartData" :loading="queryLoading" />
      </el-col>
      <el-col :span="6">
        <el-card v-if="summaryData" style="position: sticky; top: 20px">
          <template #header>
            <span>数据摘要</span>
          </template>
          <div v-if="summaryData.topn">
            <el-divider>异常检测 Top5</el-divider>
            <el-list>
              <el-list-item
                v-for="item in summaryData.topn.items"
                :key="item.dimension_id"
              >
                <div>
                  <div style="font-weight: bold">{{ item.dimension_name }}</div>
                  <div style="font-size: 12px; color: #909399">
                    最新值: {{ item.latest_value?.toFixed(2) }}
                    <span :style="{ color: item.delta && item.delta >= 0 ? '#f56c6c' : '#67c23a' }">
                      {{ item.delta && item.delta >= 0 ? '+' : '' }}{{ item.delta?.toFixed(2) }}
                    </span>
                  </div>
                </div>
              </el-list-item>
            </el-list>
          </div>
          <el-empty v-else description="暂无摘要数据" />
        </el-card>
      </el-col>
    </el-row>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>数据表格</span>
          <div>
            <el-button @click="handleLoadTemplate">从模板加载</el-button>
            <el-button @click="handleSaveTemplate" :disabled="!currentFilters">保存为模板</el-button>
            <el-button type="primary" @click="handleExport">导出Excel</el-button>
          </div>
        </div>
      </template>
      <el-table :data="tableData" v-loading="queryLoading" style="width: 100%">
        <el-table-column prop="date" label="日期" />
        <el-table-column
          v-for="series in chartData?.series"
          :key="series.name"
          :prop="series.name"
          :label="series.name"
        />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FilterPanel from '../components/FilterPanel.vue'
import ChartPanel, { type ChartData } from '../components/ChartPanel.vue'
import { queryApi, type TimeSeriesResponse } from '../api/query'
import { exportApi } from '../api/export'
import { templatesApi } from '../api/templates'
import { topnApi, type TopNResponse } from '../api/topn'

// 自动检测单位
const detectUnit = (name: string): string => {
  if (name.includes('价差') || name.includes('价')) {
    return '元/千克'
  }
  if (name.includes('利润')) {
    return '元'
  }
  if (name.includes('比') || name.includes('比率')) {
    return ''
  }
  return ''
}

const queryLoading = ref(false)
const chartData = ref<ChartData | null>(null)
const tableData = ref<any[]>([])
const currentFilters = ref<any>(null)
const summaryData = ref<{ topn?: TopNResponse } | null>(null)

const handleQuery = async (filters: any) => {
  currentFilters.value = filters
  queryLoading.value = true
  
  try {
    const result = await queryApi.timeseries({
      date_range: filters.date_range,
      time_dimension: filters.time_dimension || 'daily',
      metric_ids: filters.metric_ids?.length > 0 ? filters.metric_ids : undefined,
      geo_ids: filters.geo_ids?.length > 0 ? filters.geo_ids : undefined,
      company_ids: filters.company_ids?.length > 0 ? filters.company_ids : undefined
      // 注意：metric_groups 仅用于前端筛选指标列表，查询时使用 metric_ids
    })
    
    // 转换数据格式，添加单位信息
    chartData.value = {
      series: result.series.map(series => ({
        ...series,
        unit: detectUnit(series.name)  // 自动检测单位
      })),
      categories: result.categories
    }
    
    // 转换为表格数据
    if (result.categories && result.series) {
      tableData.value = result.categories.map(date => {
        const row: any = { date }
        result.series.forEach(series => {
          const point = series.data.find(([d]) => d === date)
          row[series.name] = point ? point[1] : null
        })
        return row
      })
    }
    
    // 自动请求TopN数据（如果选择了指标）
    if (filters.metric_ids && filters.metric_ids.length > 0) {
      await loadTopN(filters.metric_ids[0])
    }
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    queryLoading.value = false
  }
}

const loadTopN = async (metricId: number) => {
  try {
    const topnResult = await topnApi.queryTopN({
      metric_id: metricId,
      dimension: 'geo',
      window_days: 7,
      rank_by: 'delta',
      topk: 5
    })
    summaryData.value = { topn: topnResult }
  } catch (error) {
    console.error('获取TopN数据失败', error)
    summaryData.value = null
  }
}

const handleExport = async () => {
  if (!currentFilters.value) {
    ElMessage.warning('请先查询数据')
    return
  }
  
  try {
    await exportApi.exportExcel({
      date_range: currentFilters.value.date_range,
      time_dimension: currentFilters.value.time_dimension || 'daily',
      metric_ids: currentFilters.value.metric_ids?.length > 0 ? currentFilters.value.metric_ids : undefined,
      geo_ids: currentFilters.value.geo_ids?.length > 0 ? currentFilters.value.geo_ids : undefined,
      company_ids: currentFilters.value.company_ids?.length > 0 ? currentFilters.value.company_ids : undefined
    })
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handleSaveTemplate = async () => {
  if (!currentFilters.value) {
    ElMessage.warning('请先查询数据')
    return
  }
  
  try {
    const { value: name } = await ElMessageBox.prompt('请输入模板名称', '保存模板', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '模板名称不能为空'
    })
    
    // 构建ChartSpec
    const specJson = {
      chart_type: 'timeseries',
      metrics: currentFilters.value.metric_ids?.map(id => ({ metric_id: id })) || [],
      filters: {
        geo_ids: currentFilters.value.geo_ids || [],
        company_ids: currentFilters.value.company_ids || []
      },
      time: {
        dimension: currentFilters.value.time_dimension || 'daily',
        date_range: currentFilters.value.date_range
      }
    }
    
    await templatesApi.createTemplate({
      name,
      chart_type: 'timeseries',
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
    const templates = await templatesApi.getTemplates('all', 'timeseries')
    
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
          acc[t.id] = t.name
          return acc
        }, {} as Record<number, string>)
      }
    )
    
    if (!selectedId) return
    
    const template = await templatesApi.getTemplate(Number(selectedId))
    
    // 应用模板配置到FilterPanel
    // 注意：这里需要触发FilterPanel的更新，可能需要通过ref或事件
    ElMessage.info('模板已加载，请手动应用筛选条件')
    console.log('Template spec:', template.spec_json)
    
    // TODO: 实现自动应用模板配置到FilterPanel的逻辑
    // 这可能需要修改FilterPanel组件以支持外部设置值
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('加载模板失败')
    }
  }
}
</script>

<style scoped>
.analysis-page {
  padding: 20px;
}
</style>
