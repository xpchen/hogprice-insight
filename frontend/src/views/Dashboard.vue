<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 完成度看板 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>数据更新完成度</span>
              <el-button type="text" @click="loadCompleteness" :loading="completenessLoading">
                刷新
              </el-button>
            </div>
          </template>
          <div v-if="completenessData" style="margin-bottom: 20px">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-statistic title="整体最新日期" :value="completenessData.as_of" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="总指标数" :value="completenessData.summary.total" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="已更新" :value="completenessData.summary.ok">
                  <template #suffix>
                    <el-tag type="success" style="margin-left: 8px">正常</el-tag>
                  </template>
                </el-statistic>
              </el-col>
              <el-col :span="6">
                <el-statistic title="未更新" :value="completenessData.summary.late">
                  <template #suffix>
                    <el-tag type="warning" style="margin-left: 8px">延迟</el-tag>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
          </div>
          
          <!-- 缺口Top10指标 -->
          <div v-if="completenessData && completenessData.items.length > 0">
            <el-divider>缺口Top10指标</el-divider>
            <el-table :data="completenessData.items.slice(0, 10)" style="width: 100%">
              <el-table-column prop="metric_name" label="指标名称" />
              <el-table-column prop="metric_group" label="指标组">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.metric_group }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="latest_date" label="最新日期" />
              <el-table-column prop="missing_days" label="缺失天数">
                <template #default="{ row }">
                  <el-tag :type="row.missing_days === 0 ? 'success' : 'warning'">
                    {{ row.missing_days }}天
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="coverage_ratio" label="覆盖率">
                <template #default="{ row }">
                  {{ (row.coverage_ratio * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    @click="openMetricAnalysis(row.metric_id)"
                  >
                    查看分析
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <el-empty v-if="!completenessLoading && (!completenessData || completenessData.items.length === 0)" description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 常用模板卡片 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>常用模板</span>
              <el-button type="text" @click="$router.push('/templates')">管理模板</el-button>
            </div>
          </template>
          <div v-if="recentTemplates.length > 0">
            <el-list>
              <el-list-item
                v-for="template in recentTemplates"
                :key="template.id"
                @click="openTemplate(template)"
                style="cursor: pointer"
              >
                <template #default>
                  <div style="display: flex; justify-content: space-between; width: 100%">
                    <div>
                      <div style="font-weight: bold">{{ template.name }}</div>
                      <div style="font-size: 12px; color: #909399; margin-top: 4px">
                        {{ template.chart_type === 'seasonality' ? '季节性图' : '区间图' }}
                        · {{ formatDate(template.created_at) }}
                      </div>
                    </div>
                    <el-button type="primary" size="small" @click.stop="openTemplate(template)">
                      打开
                    </el-button>
                  </div>
                </template>
              </el-list-item>
            </el-list>
          </div>
          <el-empty v-else description="暂无模板，去创建一个吧" />
        </el-card>
      </el-col>
      
      <!-- TopN卡片 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>异常检测 Top5</span>
          </template>
          <el-tabs v-model="topnActiveTab">
            <el-tab-pane label="价格涨跌" name="price">
              <topn-list
                :data="topnPriceData"
                :loading="topnLoading"
                metric-name="价格"
              />
            </el-tab-pane>
            <el-tab-pane label="价差变化" name="spread">
              <topn-list
                :data="topnSpreadData"
                :loading="topnLoading"
                metric-name="价差"
              />
            </el-tab-pane>
            <el-tab-pane label="利润转负" name="profit">
              <topn-list
                :data="topnProfitData"
                :loading="topnLoading"
                metric-name="利润"
              />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
      
      <!-- 快捷入口和最近导入批次 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快捷入口</span>
          </template>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <el-button type="primary" @click="$router.push('/import')">数据导入</el-button>
            <el-button type="success" @click="$router.push('/analysis')">多维分析</el-button>
            <el-button type="info" @click="$router.push('/chart-builder')">图表配置</el-button>
          </div>
        </el-card>
        
        <el-card style="margin-top: 20px">
          <template #header>
            <span>最近导入批次</span>
          </template>
          <el-table :data="batches" style="width: 100%">
            <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="success_rows" label="成功行数" width="100" />
            <el-table-column prop="created_at" label="导入时间" width="150">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { importApi, type BatchInfo } from '../api/import'
import { templatesApi, type TemplateInfo } from '../api/templates'
import { completenessApi, type CompletenessResponse } from '../api/completeness'
import { topnApi, type TopNResponse } from '../api/topn'
import TopNList from '../components/TopNList.vue'

const router = useRouter()

const batches = ref<BatchInfo[]>([])
const recentTemplates = ref<TemplateInfo[]>([])
const completenessData = ref<CompletenessResponse | null>(null)
const completenessLoading = ref(false)

const topnActiveTab = ref('price')
const topnLoading = ref(false)
const topnPriceData = ref<TopNResponse | null>(null)
const topnSpreadData = ref<TopNResponse | null>(null)
const topnProfitData = ref<TopNResponse | null>(null)

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadBatches = async () => {
  try {
    batches.value = await importApi.getBatches(0, 10)
  } catch (error) {
    console.error('获取批次列表失败', error)
  }
}

const loadTemplates = async () => {
  try {
    const allTemplates = await templatesApi.getTemplates('all')
    // 取最近5个模板
    recentTemplates.value = allTemplates.slice(0, 5)
  } catch (error) {
    console.error('获取模板列表失败', error)
  }
}

const loadCompleteness = async () => {
  completenessLoading.value = true
  try {
    completenessData.value = await completenessApi.getCompleteness()
  } catch (error) {
    console.error('获取完成度数据失败', error)
  } finally {
    completenessLoading.value = false
  }
}

const loadTopN = async () => {
  topnLoading.value = true
  try {
    // 注意：这里需要根据实际指标ID查询
    // 简化实现：假设有价格、价差、利润指标
    // 实际应该从metadata API获取指标ID
    
    // 示例：查询价格涨跌Top5（需要先获取价格指标ID）
    // const priceMetrics = await metadataApi.getMetrics('province')
    // const priceMetric = priceMetrics.find(m => m.metric_name.includes('价格'))
    // if (priceMetric) {
    //   topnPriceData.value = await topnApi.queryTopN({
    //     metric_id: priceMetric.id,
    //     dimension: 'geo',
    //     window_days: 7,
    //     rank_by: 'delta',
    //     topk: 5
    //   })
    // }
    
    // 暂时留空，等待实际指标数据
  } catch (error) {
    console.error('获取TopN数据失败', error)
  } finally {
    topnLoading.value = false
  }
}

const openTemplate = (template: TemplateInfo) => {
  router.push({
    path: '/chart-builder',
    query: { template_id: template.id.toString() }
  })
}

const openMetricAnalysis = (metricId: number) => {
  router.push({
    path: '/analysis',
    query: { metric_id: metricId.toString() }
  })
}

onMounted(() => {
  loadBatches()
  loadTemplates()
  loadCompleteness()
  loadTopN()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}
</style>
