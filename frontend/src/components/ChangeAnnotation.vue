<template>
  <div class="change-annotation">
    <!-- 第一行：本期涨跌和较去年同期涨跌 -->
    <div v-if="(currentChange != null && typeof currentChange === 'number') || (yoyChange != null && typeof yoyChange === 'number')" class="annotation-row">
      <span v-if="currentChange != null && typeof currentChange === 'number'" class="annotation-item">
        <span class="label">本期涨跌：</span>
        <span :class="['value', currentChange >= 0 ? 'positive' : 'negative']">
          {{ currentChange >= 0 ? '+' : '' }}{{ currentChange.toFixed(2) }}{{ unit }}
        </span>
      </span>
      <span v-if="yoyChange != null && typeof yoyChange === 'number'" class="annotation-item">
        <span class="label">较去年同期涨跌：</span>
        <span :class="['value', yoyChange >= 0 ? 'positive' : 'negative']">
          {{ yoyChange >= 0 ? '+' : '' }}{{ yoyChange.toFixed(2) }}{{ unit }}
        </span>
      </span>
    </div>
    <!-- 第二行：5日、10日、30日涨跌 -->
    <div v-if="(day5Change != null && typeof day5Change === 'number') || (day10Change != null && typeof day10Change === 'number') || (day30Change != null && typeof day30Change === 'number')" class="annotation-row">
      <span v-if="day5Change != null && typeof day5Change === 'number'" class="annotation-item">
        <span class="label">5日涨跌：</span>
        <span :class="['value', day5Change >= 0 ? 'positive' : 'negative']">
          {{ day5Change >= 0 ? '+' : '' }}{{ day5Change.toFixed(2) }}{{ unit }}
        </span>
      </span>
      <span v-if="day10Change != null && typeof day10Change === 'number'" class="annotation-item">
        <span class="label">10日涨跌：</span>
        <span :class="['value', day10Change >= 0 ? 'positive' : 'negative']">
          {{ day10Change >= 0 ? '+' : '' }}{{ day10Change.toFixed(2) }}{{ unit }}
        </span>
      </span>
      <span v-if="day30Change != null && typeof day30Change === 'number'" class="annotation-item">
        <span class="label">30日涨跌：</span>
        <span :class="['value', day30Change >= 0 ? 'positive' : 'negative']">
          {{ day30Change >= 0 ? '+' : '' }}{{ day30Change.toFixed(2) }}{{ unit }}
        </span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  currentChange?: number | null // 本期涨跌
  yoyChange?: number | null // 较去年同期涨跌
  day5Change?: number | null // 5日涨跌
  day10Change?: number | null // 10日涨跌
  day30Change?: number | null // 30日涨跌
  unit?: string // 单位
}>()
</script>

<style scoped>
.change-annotation {
  display: flex;
  flex-direction: column;
  gap: 4px; /* 行距缩小 */
  padding: 8px 0; /* 减少padding */
  /* 移除背景色 */
  background-color: transparent;
  font-size: 14px;
  width: fit-content; /* 宽度缩小 */
}

.annotation-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.annotation-item {
  display: flex;
  align-items: center;
  white-space: nowrap;
}

.label {
  color: #606266;
  margin-right: 4px;
}

.value {
  font-weight: 500;
}

.value.positive {
  color: #f56c6c;
}

.value.negative {
  color: #67c23a;
}
</style>
