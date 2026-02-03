<template>
  <div class="update-time-badge">
    <el-tag type="info" size="small">
      <el-icon style="margin-right: 4px"><Clock /></el-icon>
      {{ updateTimeText }}
    </el-tag>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock } from '@element-plus/icons-vue'

const props = defineProps<{
  updateTime?: string | Date | null // 更新时间
  lastDataDate?: string | Date | null // 最后一个数据点日期
}>()

const updateTimeText = computed(() => {
  if (props.updateTime) {
    const date = typeof props.updateTime === 'string' 
      ? new Date(props.updateTime) 
      : props.updateTime
    return `更新时间：${date.toLocaleString('zh-CN')}`
  } else if (props.lastDataDate) {
    const date = typeof props.lastDataDate === 'string' 
      ? new Date(props.lastDataDate) 
      : props.lastDataDate
    return `更新时间：${date.toLocaleDateString('zh-CN')}`
  } else {
    return '更新时间：暂无'
  }
})
</script>

<style scoped>
.update-time-badge {
  display: inline-block;
}
</style>
