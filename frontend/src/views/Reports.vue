<template>
  <div class="reports-page">
    <el-card>
      <template #header>
        <span>报告生成</span>
      </template>
      
      <!-- 报告模板列表 -->
      <el-divider>报告模板</el-divider>
      <el-table :data="templates" style="width: 100%" v-loading="templatesLoading">
        <el-table-column prop="name" label="模板名称" />
        <el-table-column prop="created_at" label="创建时间">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleGenerate(row)">生成报告</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 生成记录 -->
      <el-divider style="margin-top: 30px">生成记录</el-divider>
      <el-table :data="runs" style="width: 100%" v-loading="runsLoading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="template_id" label="模板ID" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="finished_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.finished_at ? formatDate(row.finished_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'success'"
              type="primary"
              size="small"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              type="info"
              size="small"
              @click="handleCheckStatus(row)"
            >
              刷新状态
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 生成报告对话框 -->
    <el-dialog
      v-model="generateDialogVisible"
      title="生成报告"
      width="500px"
      v-if="selectedTemplate"
    >
      <el-form :model="generateParams" label-width="120px">
        <el-form-item label="模板名称">
          <el-input :value="selectedTemplate.name" disabled />
        </el-form-item>
        <el-form-item label="年份（可选）">
          <el-select
            v-model="generateParams.years"
            multiple
            placeholder="选择年份"
            style="width: 100%"
          >
            <el-option
              v-for="year in availableYears"
              :key="year"
              :label="`${year}年`"
              :value="year"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围（可选）">
          <el-date-picker
            v-model="generateParams.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="地区（可选）">
          <el-select
            v-model="generateParams.geo_ids"
            multiple
            placeholder="选择地区"
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
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmGenerate" :loading="generating">
          生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { reportsApi, type ReportTemplateInfo, type ReportRunInfo } from '../api/reports'
import { metadataApi, type GeoInfo } from '../api/metadata'

const templates = ref<ReportTemplateInfo[]>([])
const runs = ref<ReportRunInfo[]>([])
const templatesLoading = ref(false)
const runsLoading = ref(false)
const geos = ref<GeoInfo[]>([])

const generateDialogVisible = ref(false)
const selectedTemplate = ref<ReportTemplateInfo | null>(null)
const generating = ref(false)

const currentYear = new Date().getFullYear()
const availableYears = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i)

const generateParams = ref({
  years: [] as number[],
  date_range: null as [Date, Date] | null,
  geo_ids: [] as number[]
})

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const getStatusType = (status: string): string => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '生成中',
    success: '成功',
    failed: '失败'
  }
  return map[status] || status
}

const loadTemplates = async () => {
  templatesLoading.value = true
  try {
    templates.value = await reportsApi.getTemplates()
  } catch (error) {
    ElMessage.error('加载模板失败')
  } finally {
    templatesLoading.value = false
  }
}

const loadRuns = async () => {
  runsLoading.value = true
  try {
    // 注意：这里需要后端提供获取运行记录的API
    // 暂时使用空数组，实际应该调用类似 reportsApi.getRuns() 的接口
    runs.value = []
  } catch (error) {
    ElMessage.error('加载运行记录失败')
  } finally {
    runsLoading.value = false
  }
}

const loadGeos = async () => {
  try {
    geos.value = await metadataApi.getGeo()
  } catch (error) {
    console.error('加载地区失败', error)
  }
}

const handleGenerate = (template: ReportTemplateInfo) => {
  selectedTemplate.value = template
  generateParams.value = {
    years: [],
    date_range: null,
    geo_ids: []
  }
  generateDialogVisible.value = true
}

const handleConfirmGenerate = async () => {
  if (!selectedTemplate.value) return
  
  generating.value = true
  try {
    const formatDate = (date: Date): string => {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }
    
    const params: Record<string, any> = {}
    
    if (generateParams.value.years.length > 0) {
      params.years = generateParams.value.years
    }
    
    if (generateParams.value.date_range) {
      params.date_range = {
        start: formatDate(generateParams.value.date_range[0]),
        end: formatDate(generateParams.value.date_range[1])
      }
    }
    
    if (generateParams.value.geo_ids.length > 0) {
      params.geo_ids = generateParams.value.geo_ids
    }
    
    const run = await reportsApi.createRun({
      template_id: selectedTemplate.value.id,
      params
    })
    
    ElMessage.success('报告生成任务已提交')
    generateDialogVisible.value = false
    
    // 刷新运行记录
    await loadRuns()
    
    // 如果状态是success，自动下载
    if (run.status === 'success') {
      setTimeout(() => {
        handleDownload(run)
      }, 1000)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成报告失败')
  } finally {
    generating.value = false
  }
}

const handleDownload = async (run: ReportRunInfo) => {
  try {
    await reportsApi.downloadReport(run.id)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleCheckStatus = async (run: ReportRunInfo) => {
  try {
    const updated = await reportsApi.getRun(run.id)
    // 更新本地记录
    const index = runs.value.findIndex(r => r.id === run.id)
    if (index >= 0) {
      runs.value[index] = updated
    }
    
    if (updated.status === 'success') {
      ElMessage.success('报告生成完成')
    } else if (updated.status === 'failed') {
      ElMessage.error('报告生成失败')
    }
  } catch (error) {
    ElMessage.error('查询状态失败')
  }
}

onMounted(() => {
  loadTemplates()
  loadRuns()
  loadGeos()
})
</script>

<style scoped>
.reports-page {
  padding: 20px;
}
</style>
