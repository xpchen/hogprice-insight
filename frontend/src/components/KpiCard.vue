<template>
  <el-card class="kpi-card">
    <div class="kpi-content">
      <div class="kpi-title">{{ title }}</div>
      <div class="kpi-value" :class="{ 'kpi-value-large': large }">
        {{ formattedValue }}
        <span v-if="unit" class="kpi-unit">{{ unit }}</span>
      </div>
      <div class="kpi-metrics" v-if="showMetrics">
        <div class="kpi-metric" v-if="chg !== null && chg !== undefined">
          <span class="metric-label">较上期：</span>
          <span :class="['metric-value', chg >= 0 ? 'positive' : 'negative']">
            {{ chg >= 0 ? '+' : '' }}{{ formatNumber(chg) }}{{ unit }}
          </span>
        </div>
        <div class="kpi-metric" v-if="yoy !== null && yoy !== undefined">
          <span class="metric-label">同比：</span>
          <span :class="['metric-value', yoy >= 0 ? 'positive' : 'negative']">
            {{ yoy >= 0 ? '+' : '' }}{{ formatNumber(yoy) }}%
          </span>
        </div>
      </div>
      <div class="kpi-update-time" v-if="updateTime">
        更新时间：{{ formatTime(updateTime) }}
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  title: string
  value: number | null | undefined
  unit?: string
  chg?: number | null
  yoy?: number | null
  updateTime?: string
  large?: boolean
  showMetrics?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  unit: '',
  chg: null,
  yoy: null,
  updateTime: '',
  large: false,
  showMetrics: true
})

const formattedValue = computed(() => {
  if (props.value === null || props.value === undefined) {
    return '--'
  }
  return formatNumber(props.value)
})

const formatNumber = (num: number): string => {
  if (num === null || num === undefined) {
    return '--'
  }
  // 保留2位小数
  return num.toFixed(2)
}

const formatTime = (timeStr: string): string => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.kpi-card {
  height: 100%;
}

.kpi-content {
  text-align: center;
  padding: 20px;
}

.kpi-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 16px;
}

.kpi-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 16px;
}

.kpi-value-large {
  font-size: 48px;
}

.kpi-unit {
  font-size: 16px;
  font-weight: normal;
  color: #909399;
  margin-left: 4px;
}

.kpi-metrics {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 12px;
}

.kpi-metric {
  font-size: 14px;
}

.metric-label {
  color: #909399;
  margin-right: 4px;
}

.metric-value {
  font-weight: 500;
}

.metric-value.positive {
  color: #f56c6c;
}

.metric-value.negative {
  color: #67c23a;
}

.kpi-update-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 8px;
}
</style>
