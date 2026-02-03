<template>
  <div class="time-range-selector">
    <el-radio-group v-model="selectedRange" @change="handleRangeChange" size="small">
      <el-radio-button label="1m">近1月</el-radio-button>
      <el-radio-button label="3m">近3月</el-radio-button>
      <el-radio-button label="6m">近6月</el-radio-button>
      <el-radio-button label="1y">近1年</el-radio-button>
      <el-radio-button label="custom">自定义</el-radio-button>
    </el-radio-group>
    <el-date-picker
      v-if="selectedRange === 'custom'"
      v-model="customRange"
      type="daterange"
      range-separator="至"
      start-placeholder="开始日期"
      end-placeholder="结束日期"
      size="small"
      style="margin-left: 10px"
      @change="handleCustomRangeChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, withDefaults } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: [string, string]
}>(), {
  modelValue: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: [string, string]]
  'change': [value: [string, string]]
}>()

const selectedRange = ref<string>('1y')
const customRange = ref<[Date, Date] | null>(null)

// 计算日期范围
const getDateRange = (range: string): [string, string] => {
  const end = new Date()
  const start = new Date()
  
  switch (range) {
    case '1m':
      start.setMonth(start.getMonth() - 1)
      break
    case '3m':
      start.setMonth(start.getMonth() - 3)
      break
    case '6m':
      start.setMonth(start.getMonth() - 6)
      break
    case '1y':
      start.setFullYear(start.getFullYear() - 1)
      break
    case 'custom':
      if (customRange.value) {
        return [
          customRange.value[0].toISOString().split('T')[0],
          customRange.value[1].toISOString().split('T')[0]
        ]
      }
      break
  }
  
  return [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0]
  ]
}

const handleRangeChange = () => {
  if (selectedRange.value !== 'custom') {
    const range = getDateRange(selectedRange.value)
    emit('update:modelValue', range)
    emit('change', range)
  }
}

const handleCustomRangeChange = () => {
  if (customRange.value) {
    const range = getDateRange('custom')
    emit('update:modelValue', range)
    emit('change', range)
  }
}

// 初始化
onMounted(() => {
  const range = getDateRange(selectedRange.value)
  emit('update:modelValue', range)
  emit('change', range)
})

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  if (newVal && selectedRange.value === 'custom') {
    customRange.value = [
      new Date(newVal[0]),
      new Date(newVal[1])
    ]
  }
})
</script>

<style scoped>
.time-range-selector {
  display: flex;
  align-items: center;
}
</style>
