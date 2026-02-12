<template>
  <div v-if="sourceName || updateDate" class="data-source-info">
    <span v-if="sourceName">数据来源：{{ sourceName }}</span>
    <span v-if="sourceName && updateDate" class="separator"> </span>
    <span v-if="updateDate">更新日期：{{ updateDate }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  sourceName?: string | null // 数据来源名称（标准化：钢联/涌益）
  updateDate?: string | null // 更新日期（格式：X年X月X日）
}>()
</script>

<style scoped>
.data-source-info {
  font-size: 12px;
  color: #909399;
  text-align: right;
  margin-top: 6px;
  padding-right: 8px;
}

.separator {
  margin: 0 8px;
}
</style>
