<template>
  <el-radio-group v-model="selectedFreq" @change="handleChange" size="small">
    <el-radio-button label="day">日度</el-radio-button>
    <el-radio-button label="week">周度</el-radio-button>
  </el-radio-group>
</template>

<script setup lang="ts">
import { ref, watch, withDefaults } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: 'day' | 'week'
}>(), {
  modelValue: 'day'
})

const emit = defineEmits<{
  'update:modelValue': [value: 'day' | 'week']
  'change': [value: 'day' | 'week']
}>()

const selectedFreq = ref<'day' | 'week'>(props.modelValue || 'day')

const handleChange = (value: 'day' | 'week') => {
  emit('update:modelValue', value)
  emit('change', value)
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    selectedFreq.value = newVal
  }
})
</script>

<style scoped>
</style>
