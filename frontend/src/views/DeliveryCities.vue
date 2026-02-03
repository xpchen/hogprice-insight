<template>
  <div class="delivery-cities">
    <FilterPanel @change="handleFilterChange" />
    
    <el-card shadow="never">
      <template #header>
        <span>交割地市出栏价</span>
      </template>
      
      <el-table
        :data="cityData"
        border
        stripe
        v-loading="loading"
      >
        <el-table-column prop="city" label="城市" width="120" />
        <el-table-column prop="province" label="省份" width="120" />
        <el-table-column prop="price" label="价格" width="120" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="obs_date" label="日期" width="120" />
        <el-table-column prop="tags" label="标签">
          <template #default="{ row }">
            <el-tag
              v-for="(value, key) in row.tags"
              :key="key"
              size="small"
              style="margin-right: 4px"
            >
              {{ key }}: {{ value }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import FilterPanel from '../components/FilterPanel.vue'
import { queryObservations } from '../api/observation'

const loading = ref(false)
const cityData = ref<any[]>([])

const handleFilterChange = async (filters: any) => {
  loading.value = true
  try {
    const data = await queryObservations({
      metric_key: 'YY_D_PRICE*',
      tag_key: 'city',
      ...filters
    })
    cityData.value = data
  } catch (error) {
    console.error('查询失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  handleFilterChange({})
})
</script>

<style scoped>
.delivery-cities {
  padding: 20px;
}
</style>
