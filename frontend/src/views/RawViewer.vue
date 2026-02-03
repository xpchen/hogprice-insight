<template>
  <div class="raw-viewer">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <span>原表查看器</span>
          <el-button type="primary" @click="loadBatches">刷新</el-button>
        </div>
      </template>

      <!-- 批次选择 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="批次">
          <el-select
            v-model="selectedBatchId"
            placeholder="请选择批次"
            style="width: 200px"
            @change="loadRawFiles"
          >
            <el-option
              v-for="batch in batches"
              :key="batch.id"
              :label="`${batch.filename} (${batch.created_at})`"
              :value="batch.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="文件">
          <el-select
            v-model="selectedRawFileId"
            placeholder="请选择文件"
            style="width: 200px"
            @change="loadRawSheets"
            :disabled="!selectedBatchId"
          >
            <el-option
              v-for="file in rawFiles"
              :key="file.id"
              :label="file.filename"
              :value="file.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Sheet">
          <el-select
            v-model="selectedSheetId"
            placeholder="请选择Sheet"
            style="width: 200px"
            @change="loadRawTable"
            :disabled="!selectedRawFileId"
          >
            <el-option
              v-for="sheet in rawSheets"
              :key="sheet.id"
              :label="`${sheet.sheet_name} (${sheet.parse_status})`"
              :value="sheet.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 表格展示 -->
      <div v-if="tableData.length > 0" class="table-container">
        <el-table
          :data="tableData"
          border
          stripe
          height="600"
          style="width: 100%"
          v-loading="loading"
        >
          <el-table-column
            v-for="(col, idx) in tableColumns"
            :key="idx"
            :prop="`col_${idx}`"
            :label="col"
            min-width="120"
          />
        </el-table>
      </div>

      <el-empty v-else description="请选择批次、文件和Sheet" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRawSheets, getRawTable } from '../api/observation'
import { ingestApi } from '../api/ingest'

const batches = ref<any[]>([])
const rawFiles = ref<any[]>([])
const rawSheets = ref<any[]>([])
const tableData = ref<any[]>([])
const tableColumns = ref<string[]>([])
const loading = ref(false)

const selectedBatchId = ref<number | null>(null)
const selectedRawFileId = ref<number | null>(null)
const selectedSheetId = ref<number | null>(null)

const loadBatches = async () => {
  try {
    const data = await ingestApi.getBatches(0, 100)
    batches.value = data
  } catch (error) {
    ElMessage.error('加载批次失败')
  }
}

const loadRawFiles = async () => {
  if (!selectedBatchId.value) return
  // TODO: 实现从batch获取raw_files的API
  rawFiles.value = []
  selectedRawFileId.value = null
  selectedSheetId.value = null
}

const loadRawSheets = async () => {
  if (!selectedRawFileId.value) return
  try {
    const sheets = await getRawSheets({ raw_file_id: selectedRawFileId.value })
    rawSheets.value = sheets
  } catch (error) {
    ElMessage.error('加载Sheet列表失败')
  }
}

const loadRawTable = async () => {
  if (!selectedSheetId.value) return
  loading.value = true
  try {
    const table = await getRawTable(selectedSheetId.value)
    // 转换table_json为表格数据
    const jsonData = table.table_json
    if (jsonData && jsonData.length > 0) {
      // 第一行作为表头
      tableColumns.value = jsonData[0].map((_, idx) => `列${idx + 1}`)
      // 剩余行作为数据
      tableData.value = jsonData.slice(1).map((row, rowIdx) => {
        const rowData: any = {}
        row.forEach((cell, colIdx) => {
          rowData[`col_${colIdx}`] = cell
        })
        return rowData
      })
    }
  } catch (error) {
    ElMessage.error('加载表格数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBatches()
})
</script>

<style scoped>
.raw-viewer {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
}

.table-container {
  margin-top: 20px;
}
</style>
