<template>
  <div class="topn-list">
    <el-table :data="items" v-loading="loading" style="width: 100%" size="small">
      <el-table-column prop="rank" label="排名" width="60" />
      <el-table-column prop="dimension_name" label="维度" />
      <el-table-column prop="latest_value" label="最新值">
        <template #default="{ row }">
          {{ formatValue(row.latest_value) }}
        </template>
      </el-table-column>
      <el-table-column prop="delta" label="变化">
        <template #default="{ row }">
          <span :style="{ color: getDeltaColor(row.delta) }">
            {{ formatDelta(row.delta, row.pct_change) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && items.length === 0" description="暂无数据" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TopNItem } from '../api/topn'

const props = defineProps<{
  data: any | null
  loading: boolean
  metricName?: string
}>()

const items = computed(() => {
  return props.data?.items || []
})

const formatValue = (value: number | null): string => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

const formatDelta = (delta: number | null | undefined, pctChange: number | null | undefined): string => {
  if (delta === null || delta === undefined) return '-'
  const sign = delta >= 0 ? '+' : ''
  if (pctChange !== null && pctChange !== undefined) {
    return `${sign}${delta.toFixed(2)} (${(pctChange * 100).toFixed(1)}%)`
  }
  return `${sign}${delta.toFixed(2)}`
}

const getDeltaColor = (delta: number | null | undefined): string => {
  if (delta === null || delta === undefined) return '#909399'
  return delta >= 0 ? '#f56c6c' : '#67c23a'
}
</script>

<style scoped>
.topn-list {
  min-height: 200px;
}
</style>
