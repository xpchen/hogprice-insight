<template>
  <div class="import-page">
    <el-card>
      <template #header>
        <span>数据导入</span>
      </template>
      
      <el-upload
        class="upload-demo"
        drag
        :action="uploadUrl"
        :headers="uploadHeaders"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传xlsx/xls文件
          </div>
        </template>
      </el-upload>
      
      <el-divider />
      
      <el-table :data="batches" style="width: 100%" v-loading="loading">
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_rows" label="总行数" />
        <el-table-column prop="success_rows" label="成功行数" />
        <el-table-column prop="failed_rows" label="失败行数" />
        <el-table-column prop="created_at" label="导入时间" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button type="text" @click="viewBatchDetail(row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-dialog v-model="detailDialogVisible" title="批次详情" width="80%">
        <div v-if="batchDetail">
          <p><strong>文件名:</strong> {{ batchDetail.filename }}</p>
          <p><strong>状态:</strong> {{ batchDetail.status }}</p>
          <p><strong>总行数:</strong> {{ batchDetail.total_rows }}</p>
          <p><strong>成功行数:</strong> {{ batchDetail.success_rows }}</p>
          <p><strong>失败行数:</strong> {{ batchDetail.failed_rows }}</p>
          <el-table :data="batchDetail.error_json" v-if="batchDetail.error_json && batchDetail.error_json.length">
            <el-table-column prop="sheet" label="Sheet" />
            <el-table-column prop="row" label="行" />
            <el-table-column prop="col" label="列" />
            <el-table-column prop="reason" label="错误原因" />
          </el-table>
        </div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { importApi, type BatchInfo } from '../api/import'
import request from '../api/request'

const fileList = ref([])
const batches = ref<BatchInfo[]>([])
const loading = ref(false)
const detailDialogVisible = ref(false)
const batchDetail = ref<any>(null)

const uploadUrl = computed(() => `${request.defaults.baseURL}/data/import-excel`)
const uploadHeaders = computed(() => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const beforeUpload = (file: File) => {
  const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
  if (!isExcel) {
    ElMessage.error('只能上传Excel文件!')
    return false
  }
  return true
}

const handleUploadSuccess = (response: any) => {
  ElMessage.success('导入成功')
  loadBatches()
}

const handleUploadError = () => {
  ElMessage.error('导入失败')
}

const loadBatches = async () => {
  loading.value = true
  try {
    batches.value = await importApi.getBatches()
  } catch (error) {
    ElMessage.error('获取批次列表失败')
  } finally {
    loading.value = false
  }
}

const viewBatchDetail = async (batchId: number) => {
  try {
    batchDetail.value = await importApi.getBatchDetail(batchId)
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取批次详情失败')
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    partial: 'warning'
  }
  return map[status] || 'info'
}

onMounted(() => {
  loadBatches()
})
</script>

<style scoped>
.import-page {
  padding: 20px;
}

.upload-demo {
  margin-bottom: 20px;
}
</style>
