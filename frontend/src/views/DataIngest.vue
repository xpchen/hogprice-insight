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
        :on-remove="handleFileRemove"
        :file-list="fileList"
        :limit="50"
        multiple
        accept=".xlsx,.xls,.zip"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .xlsx、.xls、.zip（zip 将解压并导入其中的 Excel），可多选
          </div>
        </template>
      </el-upload>

      <!-- 已选文件与执行 -->
      <div v-if="fileList.length > 0" style="margin-top: 20px">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>已选 {{ fileList.length }} 个文件</span>
              <div>
                <el-button type="primary" @click="submitImport" :loading="importing" :disabled="importing">
                  提交导入
                </el-button>
                <el-button @click="handleCancel" :disabled="importing">清空</el-button>
              </div>
            </div>
          </template>
          <el-table :data="fileList" size="small" max-height="200">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column label="文件名">
              <template #default="{ row }">{{ row.name }}</template>
            </el-table-column>
            <el-table-column label="大小" width="100">
              <template #default="{ row }">
                {{ formatSize(row.raw?.size ?? row.size) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 导入进度 -->
      <el-card v-if="progress.visible" style="margin-top: 20px">
        <template #header>
          <span>导入进度</span>
        </template>
        <div>
          <el-progress
            :percentage="progress.percent"
            :status="progress.status"
            :stroke-width="12"
          />
          <div style="margin-top: 12px; color: var(--el-text-color-regular)">
            {{ progress.message }}
          </div>
          <div v-if="progress.currentFile > 0" style="margin-top: 8px; font-size: 12px; color: var(--el-text-color-secondary)">
            第 {{ progress.currentFile }} / {{ progress.totalFiles }} 个文件
          </div>
        </div>
      </el-card>

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
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { ingestApi } from '../api/ingest'

const fileList = ref<any[]>([])
const importing = ref(false)
const batches = ref<any[]>([])
const batchDetail = ref<any>(null)
const detailDialogVisible = ref(false)

const progress = ref({
  visible: false,
  percent: 0,
  message: '',
  currentFile: 0,
  totalFiles: 0,
  status: '' as '' | 'success' | 'exception',
})

const handleFileChange = (_file: any, uploadFiles: any[]) => {
  fileList.value = uploadFiles
}

const handleFileRemove = (_file: any, uploadFiles: any[]) => {
  fileList.value = uploadFiles
}

const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const submitImport = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  importing.value = true
    progress.value = {
      visible: true,
      percent: 0,
      message: '正在提交...',
      currentFile: 0,
      totalFiles: fileList.value.length,
      status: '',
    }

  let eventSource: EventSource | null = null
  const filesToSend = fileList.value.map((f) => f.raw).filter((r): r is File => r instanceof File)

  try {
    const res = await ingestApi.submitImport(filesToSend)
    progress.value.message = '任务已提交，等待处理...'
    progress.value.totalFiles = res.total_files

    eventSource = ingestApi.createSSEStream(res.task_id)
    eventSource.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        const total = data.total_files || 1
        const current = data.current_file || 0
        progress.value = {
          visible: true,
          percent: total > 0 ? Math.round((current / total) * 100) : 0,
          message: data.message || progress.value.message,
          currentFile: current,
          totalFiles: total,
          status: data.status === 'done' ? (data.success ? 'success' : 'exception') : '',
        }
        if (data.status === 'done') {
          eventSource?.close()
          eventSource = null
          importing.value = false
          fileList.value = []
          loadBatches()
          if (data.success) {
            ElMessage.success('导入完成')
          } else {
            ElMessage.error(data.error || '导入失败')
          }
        }
      } catch {
        // ignore parse error
      }
    }
    eventSource.onerror = () => {
      if (importing.value && progress.value.status !== 'success' && progress.value.status !== 'exception') {
        progress.value.message = '连接中断，请刷新批次列表查看结果'
        importing.value = false
      }
      eventSource?.close()
    }
  } catch (error: any) {
    importing.value = false
    progress.value.visible = false
    ElMessage.error(
      error.response?.data?.detail || error.message || '提交失败'
    )
  }
}

const handleCancel = () => {
  fileList.value = []
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

const getStatusType = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
    case 'partial':
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
