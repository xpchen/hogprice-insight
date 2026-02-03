<template>
  <div class="filter-panel">
    <el-card shadow="never" class="filter-card">
      <template #header>
        <div class="filter-header">
          <span>筛选条件</span>
          <el-button type="text" size="small" @click="resetFilters">重置</el-button>
        </div>
      </template>
      
      <el-form :model="filters" label-width="100px" size="default">
        <!-- 数据源筛选 -->
        <el-form-item label="数据源">
          <el-select
            v-model="filters.sourceCodes"
            multiple
            placeholder="请选择数据源"
            style="width: 100%"
            @change="handleFilterChange"
          >
            <el-option label="涌益" value="YONGYI" />
            <el-option label="钢联" value="GANGLIAN" />
            <el-option label="DCE" value="DCE" />
          </el-select>
        </el-form-item>

        <!-- 时间粒度 + 范围 -->
        <el-form-item label="时间粒度">
          <el-radio-group v-model="filters.freq" @change="handleFilterChange">
            <el-radio label="day">日</el-radio>
            <el-radio label="week">周</el-radio>
            <el-radio label="month">月</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
            @change="handleFilterChange"
          />
        </el-form-item>

        <!-- 地域筛选 -->
        <el-form-item label="地域">
          <el-cascader
            v-model="filters.geo"
            :options="geoOptions"
            placeholder="请选择地域"
            style="width: 100%"
            @change="handleFilterChange"
          />
        </el-form-item>

        <!-- 维度tags筛选（动态加载） -->
        <el-form-item v-for="tag in availableTags" :key="tag.tag_key" :label="tag.tag_key">
          <el-select
            v-model="filters.tags[tag.tag_key]"
            multiple
            :placeholder="`请选择${tag.tag_key}`"
            style="width: 100%"
            @change="handleFilterChange"
          >
            <el-option
              v-for="value in tag.values"
              :key="value.tag_value"
              :label="value.tag_value"
              :value="value.tag_value"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAvailableTags } from '../api/observation'

interface TagValue {
  tag_value: string
  count: number
}

interface TagInfo {
  tag_key: string
  values: TagValue[]
}

const props = defineProps<{
  sourceCodes?: string[]
  freq?: 'day' | 'week' | 'month'
  dateRange?: [Date, Date]
  geo?: string[]
  tags?: Record<string, string[]>
}>()

const emit = defineEmits<{
  (e: 'change', filters: any): void
}>()

const filters = reactive({
  sourceCodes: props.sourceCodes || [],
  freq: props.freq || 'day',
  dateRange: props.dateRange || null,
  geo: props.geo || [],
  tags: props.tags || {} as Record<string, string[]>
})

const availableTags = ref<TagInfo[]>([])
const geoOptions = ref([
  {
    value: 'nation',
    label: '全国',
    children: [
      { value: 'northeast', label: '东北' },
      { value: 'north', label: '华北' },
      { value: 'east', label: '华东' },
      { value: 'south', label: '华南' },
      { value: 'west', label: '西南' },
      { value: 'northwest', label: '西北' }
    ]
  }
])

// 加载可用的tags
const loadAvailableTags = async () => {
  try {
    const tagKeys = await getAvailableTags()
    const tagValuesPromises = tagKeys.map(async (tag) => {
      const values = await getAvailableTags(tag.tag_key)
      return {
        tag_key: tag.tag_key,
        values: values.map(v => ({ tag_value: v.tag_value, count: v.count }))
      }
    })
    availableTags.value = await Promise.all(tagValuesPromises)
  } catch (error) {
    console.error('加载tags失败:', error)
  }
}

const handleFilterChange = () => {
  emit('change', {
    sourceCodes: filters.sourceCodes,
    freq: filters.freq,
    dateRange: filters.dateRange,
    geo: filters.geo,
    tags: filters.tags
  })
}

const resetFilters = () => {
  filters.sourceCodes = []
  filters.freq = 'day'
  filters.dateRange = null
  filters.geo = []
  filters.tags = {}
  handleFilterChange()
}

onMounted(() => {
  loadAvailableTags()
})
</script>

<style scoped>
.filter-panel {
  margin-bottom: 20px;
}

.filter-card {
  border-radius: 8px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
