<template>
  <div class="data-ingest">
    <el-card>
      <template #header>
        <span>原始数据导入</span>
      </template>

      <!-- 上传区域 -->
      <el-upload
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="fileList"
        accept=".xlsx,.xls"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .xlsx, .xls 格式的Excel文件
          </div>
        </template>
      </el-upload>

      <!-- 预览区域 -->
      <div v-if="previewData" style="margin-top: 20px">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>导入预览</span>
              <div>
                <el-button type="primary" @click="executeImport" :loading="importing" :disabled="!currentFile">
                  执行导入
                </el-button>
                <el-button @click="handleCancel">取消</el-button>
              </div>
            </div>
          </template>

          <div>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="模板类型">
                <el-tag>{{ previewData.template_type }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="日期范围">
                {{ previewData.date_range?.start }} 至 {{ previewData.date_range?.end }}
              </el-descriptions-item>
            </el-descriptions>

            <el-divider>Sheet列表</el-divider>
            <el-table :data="previewData.sheets" style="width: 100%">
              <el-table-column prop="name" label="Sheet名称" />
              <el-table-column prop="rows" label="行数" />
              <el-table-column prop="columns" label="列数">
                <template #default="{ row }">
                  {{ row.columns?.length || 0 }}
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="{ row }">
                  <el-button size="small" @click="viewSheetSample(row)">
                    查看样本
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </div>

      <!-- 批次列表 -->
      <el-card style="margin-top: 20px">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>导入批次</span>
            <el-button @click="loadBatches">刷新</el-button>
          </div>
        </template>

        <el-table :data="batches" style="width: 100%">
          <el-table-column prop="id" label="批次ID" width="100" />
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="source_code" label="数据源">
            <template #default="{ row }">
              <el-tag size="small">{{ row.source_code }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="success_rows" label="成功行数" />
          <el-table-column prop="failed_rows" label="失败行数" />
          <el-table-column prop="created_at" label="创建时间" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="viewBatchDetail(row.id)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 批次详情对话框 -->
      <el-dialog v-model="detailDialogVisible" title="批次详情" width="80%">
        <div v-if="batchDetail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="批次ID">{{ batchDetail.id }}</el-descriptions-item>
            <el-descriptions-item label="文件名">{{ batchDetail.filename }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(batchDetail.status)">{{ batchDetail.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据源">
              <el-tag>{{ batchDetail.source_code }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="成功行数">{{ batchDetail.success_rows }}</el-descriptions-item>
            <el-descriptions-item label="失败行数">{{ batchDetail.failed_rows }}</el-descriptions-item>
            <el-descriptions-item label="日期范围" :span="2">
              {{ batchDetail.date_range?.start }} 至 {{ batchDetail.date_range?.end }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider>错误列表</el-divider>
          <el-table :data="batchDetail.errors" style="width: 100%">
            <el-table-column prop="sheet" label="Sheet" />
            <el-table-column prop="row" label="行号" />
            <el-table-column prop="col" label="列名" />
            <el-table-column prop="error_type" label="错误类型" />
            <el-table-column prop="message" label="错误消息" />
          </el-table>
        </div>
      </el-dialog>

      <!-- Sheet样本对话框 -->
      <el-dialog v-model="sampleDialogVisible" title="Sheet样本数据" width="80%">
        <el-table :data="sampleData" style="width: 100%">
          <el-table-column
            v-for="col in sampleColumns"
            :key="col"
            :prop="col"
            :label="col"
          />
        </el-table>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { ingestApi } from '../api/ingest'

const fileList = ref<any[]>([])
const previewData = ref<any>(null)
const currentFile = ref<File | null>(null) // 保存当前选择的文件对象
const importing = ref(false)
const batches = ref<any[]>([])
const batchDetail = ref<any>(null)
const detailDialogVisible = ref(false)
const sampleDialogVisible = ref(false)
const sampleData = ref<any[]>([])
const sampleColumns = ref<string[]>([])

const handleFileChange = async (file: any) => {
  try {
    // 保存文件对象
    currentFile.value = file.raw
    
    const formData = new FormData()
    formData.append('file', file.raw)
    
    const preview = await ingestApi.previewImport(formData)
    previewData.value = preview
    ElMessage.success('预览成功')
  } catch (error) {
    ElMessage.error('预览失败')
    console.error(error)
    currentFile.value = null
  }
}

const executeImport = async () => {
  if (!previewData.value) {
    ElMessage.warning('请先预览文件')
    return
  }
  
  if (!currentFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  importing.value = true
  
  // 显示长时间导入提示
  const loadingMessage = ElMessage({
    message: '正在导入数据，大文件可能需要几分钟时间，请耐心等待...',
    type: 'info',
    duration: 0, // 不自动关闭
    showClose: false
  })
  
  try {
    const formData = new FormData()
    formData.append('file', currentFile.value)
    
    // 直接执行导入（上传+导入一步完成）
    await ingestApi.executeImport(formData, previewData.value.template_type)
    
    loadingMessage.close()
    ElMessage.success('导入成功')
    previewData.value = null
    currentFile.value = null
    fileList.value = []
    loadBatches()
  } catch (error: any) {
    loadingMessage.close()
    
    // 处理超时错误
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      ElMessage.error('导入超时，文件可能过大。请检查导入批次状态或稍后重试。')
    } else {
      ElMessage.error(`导入失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
    }
    console.error(error)
  } finally {
    importing.value = false
  }
}

const loadBatches = async () => {
  try {
    batches.value = await ingestApi.getBatches()
  } catch (error) {
    ElMessage.error('加载批次列表失败')
    console.error(error)
  }
}

const viewBatchDetail = async (batchId: number) => {
  try {
    batchDetail.value = await ingestApi.getBatchDetail(batchId)
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载批次详情失败')
    console.error(error)
  }
}

const viewSheetSample = (sheet: any) => {
  if (sheet.sample_data && sheet.sample_data.length > 0) {
    sampleData.value = sheet.sample_data
    sampleColumns.value = Object.keys(sheet.sample_data[0] || {})
    sampleDialogVisible.value = true
  } else {
    ElMessage.warning('该Sheet没有样本数据')
  }
}

const handleCancel = () => {
  previewData.value = null
  currentFile.value = null
  fileList.value = []
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'danger'
    case 'processing':
      return 'warning'
    default:
      return 'info'
  }
}

onMounted(() => {
  loadBatches()
})
</script>

<style scoped>
.data-ingest {
  padding: 20px;
}

.upload-area {
  width: 100%;
}
</style>
