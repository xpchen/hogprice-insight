<template>
  <div class="template-list">
    <el-table :data="templates" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="模板名称" />
      <el-table-column prop="chart_type" label="图表类型">
        <template #default="{ row }">
          <el-tag :type="row.chart_type === 'seasonality' ? 'primary' : 'success'">
            {{ row.chart_type === 'seasonality' ? '季节性图' : '区间图' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column v-if="scope === 'public'" prop="is_public" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_public ? 'success' : 'info'">
            {{ row.is_public ? '公开' : '私有' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="$emit('open', row)">打开</el-button>
          <el-button type="success" size="small" @click="$emit('copy', row)">复制</el-button>
          <el-button type="warning" size="small" @click="$emit('edit', row)">编辑</el-button>
          <el-button
            v-if="isAdmin && scope === 'public'"
            type="info"
            size="small"
            @click="$emit('publish', row)"
          >
            {{ row.is_public ? '取消公开' : '发布' }}
          </el-button>
          <el-button type="danger" size="small" @click="$emit('delete', row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-empty v-if="!loading && templates.length === 0" description="暂无模板" />
  </div>
</template>

<script setup lang="ts">
// defineProps 和 defineEmits 是编译器宏，不需要导入
import type { TemplateInfo } from '../api/templates'

defineProps<{
  templates: TemplateInfo[]
  loading: boolean
  scope: 'mine' | 'public'
  isAdmin?: boolean
}>()

defineEmits<{
  (e: 'open', template: TemplateInfo): void
  (e: 'edit', template: TemplateInfo): void
  (e: 'delete', template: TemplateInfo): void
  (e: 'copy', template: TemplateInfo): void
  (e: 'publish', template: TemplateInfo): void
}>()
</script>

<style scoped>
.template-list {
  margin-top: 20px;
}
</style>
