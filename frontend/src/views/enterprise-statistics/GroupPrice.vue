<template>
  <div class="group-price-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D4. 集团价格</span>
          <DataSourceInfo
            v-if="table1Data && table1Data.latest_date"
            source-name="钢联模板"
            :update-date="table1Data.latest_date"
          />
        </div>
      </template>

      <!-- 表格1：重点集团企业生猪出栏价格和白条价格 -->
      <div class="table-section">
        <h3>表格1：重点集团企业生猪出栏价格和白条价格</h3>
        
        <!-- 日期选择器 -->
        <div class="filter-section">
          <span class="filter-label">显示天数：</span>
          <el-select v-model="selectedDays" @change="handleDaysChange" style="width: 120px">
            <el-option label="最近15日" :value="15" />
            <el-option label="最近30日" :value="30" />
            <el-option label="最近60日" :value="60" />
            <el-option label="最近90日" :value="90" />
          </el-select>
        </div>

        <!-- 价格表格：牧原白条为多表头，下属华东、河南山东、湖北陕西、京津冀、东北 -->
        <div class="table-container">
          <el-table
            :data="table1DisplayData"
            border
            stripe
            v-loading="loading1"
            style="width: 100%"
            height="400"
          >
            <el-table-column prop="date" label="日期" width="120" fixed="left" align="center">
              <template #default="{ row }">
                {{ formatDate(row.date) }}
              </template>
            </el-table-column>
            <el-table-column
              v-for="company in table1FlatColumns"
              :key="company"
              :label="company"
              width="120"
              align="right"
              header-align="center"
            >
              <template #default="{ row }">
                <div v-if="getCompanyPrice(row, company) !== null">
                  <div class="price-value">{{ formatCompanyPrice(company, getCompanyPrice(row, company)) }}</div>
                  <div class="premium-discount" v-if="getPremiumDiscount(company) !== null && getPremiumDiscount(company) !== 0">
                    ({{ formatPremiumDiscount(getPremiumDiscount(company)) }})
                  </div>
                </div>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <!-- 牧原白条 多表头：始终展示，一级「牧原白条」，二级 华东、河南山东、湖北陕西、京津冀、东北（来源：3.3、白条市场跟踪.xlsx） -->
            <el-table-column
              label="牧原白条"
              align="center"
              header-align="center"
            >
              <el-table-column
                v-for="region in MUYUAN_WHITE_STRIP_REGIONS"
                :key="region"
                :label="region"
                :prop="region"
                width="110"
                align="right"
                header-align="center"
              >
                <template #default="{ row }">
                  <span v-if="getCompanyPrice(row, region) !== null">{{ formatPrice(getCompanyPrice(row, region)) }}</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table-column>
          </el-table>
        </div>

        <!-- 区间涨跌幅选择 -->
        <div class="range-section">
          <span class="filter-label">区间涨跌幅：</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="handleDateRangeChange"
            style="width: 300px"
          />
          <el-button type="primary" @click="calculateRangeChange" style="margin-left: 10px">
            计算涨跌幅
          </el-button>
          <div v-if="rangeChangeResult !== null" class="range-result">
            涨跌幅：<strong>{{ formatPercent(rangeChangeResult) }}</strong>
          </div>
        </div>
      </div>

      <!-- 表格2：重点市场白条到货量&价格 -->
      <div class="table-section" style="margin-top: 30px">
        <h3>表格2：重点市场白条到货量&价格</h3>
        
        <!-- 日期选择器 -->
        <div class="filter-section">
          <span class="filter-label">显示天数：</span>
          <el-select v-model="selectedDays2" @change="handleDaysChange2" style="width: 120px">
            <el-option label="最近15日" :value="15" />
            <el-option label="最近30日" :value="30" />
            <el-option label="最近60日" :value="60" />
            <el-option label="最近90日" :value="90" />
          </el-select>
        </div>

        <!-- 白条市场表格 -->
        <div class="table-container">
          <el-table
            :data="table2DisplayData"
            border
            stripe
            v-loading="loading2"
            style="width: 100%"
            height="400"
          >
            <el-table-column prop="date" label="日期" width="120" fixed="left">
              <template #default="{ row }">
                {{ formatDate(row.date) }}
              </template>
            </el-table-column>
            <el-table-column prop="market" label="市场" width="150" fixed="left">
            </el-table-column>
            <el-table-column prop="arrival_volume" label="到货量" width="120" align="right">
              <template #default="{ row }">
                {{ formatValue(row.arrival_volume) }}
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="120" align="right">
              <template #default="{ row }">
                {{ formatPrice(row.price) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getGroupEnterprisePrice, getWhiteStripMarket } from '@/api/group-price'
import type { GroupPriceTableResponse, WhiteStripMarketResponse } from '@/api/group-price'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const loading1 = ref(false)
const loading2 = ref(false)
const table1Data = ref<GroupPriceTableResponse | null>(null)
const table2Data = ref<WhiteStripMarketResponse | null>(null)

const selectedDays = ref(15)
const selectedDays2 = ref(15)
const dateRange = ref<[Date, Date] | null>(null)
const rangeChangeResult = ref<number | null>(null)

// 牧原白条多表头：来源于 3.3、白条市场跟踪.xlsx 华宝和牧原白条 sheet，一级「牧原白条」，二级为以下区域
const MUYUAN_WHITE_STRIP_REGIONS = ['华东', '河南山东', '湖北陕西', '京津冀', '东北']

// 表格1 平铺列（不含牧原白条及下属华东等 5 列，该部分用多表头展示）
const table1FlatColumns = computed(() => {
  const companies = table1Data.value?.companies || []
  return companies.filter(
    (c: string) => c !== '牧原白条' && !MUYUAN_WHITE_STRIP_REGIONS.includes(c)
  )
})

// 表格1显示数据（按日期分组）
const table1DisplayData = computed(() => {
  if (!table1Data.value || !table1Data.value.data.length) return []
  
  // 按日期分组
  const dateMap: Record<string, Record<string, number | null>> = {}
  const dates = new Set<string>()
  
  table1Data.value.data.forEach(item => {
    if (!dateMap[item.date]) {
      dateMap[item.date] = {}
      dates.add(item.date)
    }
    dateMap[item.date][item.company] = item.price
  })
  
  return Array.from(dates).sort().reverse().map(date => ({
    date,
    ...dateMap[date]
  }))
})

// 表格2显示数据
const table2DisplayData = computed(() => {
  if (!table2Data.value || !table2Data.value.data) {
    console.log('table2DisplayData: 无数据')
    return []
  }
  const sorted = [...table2Data.value.data].sort((a, b) => b.date.localeCompare(a.date))
  console.log('table2DisplayData: 排序后数据条数:', sorted.length)
  return sorted
})

// 获取企业价格
const getCompanyPrice = (row: any, company: string): number | null => {
  return row[company] ?? null
}

// 获取升贴水（从API返回的数据中获取）
const getPremiumDiscount = (company: string): number | null => {
  if (!table1Data.value) return null
  
  // 从API返回的数据中查找该企业的升贴水
  const dataPoint = table1Data.value.data.find(d => d.company === company)
  return dataPoint?.premium_discount ?? null
}

// 加载表格1数据
const loadTable1Data = async () => {
  loading1.value = true
  try {
    const response = await getGroupEnterprisePrice(selectedDays.value)
    table1Data.value = response
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading1.value = false
  }
}

// 加载表格2数据
const loadTable2Data = async () => {
  loading2.value = true
  try {
    const response = await getWhiteStripMarket(selectedDays2.value)
    console.log('表格2数据加载成功:', response)
    table2Data.value = response
    console.log('table2Data.value:', table2Data.value)
    console.log('table2DisplayData:', table2DisplayData.value)
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading2.value = false
  }
}

// 天数变化处理
const handleDaysChange = () => {
  loadTable1Data()
}

const handleDaysChange2 = () => {
  loadTable2Data()
}

// 日期范围变化处理
const handleDateRangeChange = () => {
  rangeChangeResult.value = null
}

// 计算区间涨跌幅
const calculateRangeChange = () => {
  if (!dateRange.value || !table1Data.value) {
    ElMessage.warning('请选择日期范围')
    return
  }
  
  const [startDate, endDate] = dateRange.value
  const startStr = startDate.toISOString().split('T')[0]
  const endStr = endDate.toISOString().split('T')[0]
  
  // 计算所有企业的平均涨跌幅
  const companies = table1Data.value.companies
  const changes: number[] = []
  
  companies.forEach(company => {
    const startData = table1Data.value!.data.find(
      d => d.company === company && d.date === startStr
    )
    const endData = table1Data.value!.data.find(
      d => d.company === company && d.date === endStr
    )
    
    if (startData?.price && endData?.price && startData.price > 0) {
      const change = (endData.price - startData.price) / startData.price * 100
      changes.push(change)
    }
  })
  
  if (changes.length > 0) {
    const avgChange = changes.reduce((a, b) => a + b, 0) / changes.length
    rangeChangeResult.value = avgChange
  } else {
    ElMessage.warning('所选日期范围内没有数据')
  }
}

// 格式化函数
const formatDate = (dateStr: string) => {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const formatPrice = (price: number | null | undefined) => {
  if (price === null || price === undefined) return '-'
  return price.toFixed(2)
}

// 华宝白条列当前数据源为升贴水（元），非价格（元/公斤），展示时注明
const formatCompanyPrice = (company: string, value: number) => {
  const s = value.toFixed(2)
  if (company === '华宝白条') return `${s} (升贴水)`
  return s
}

const formatValue = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

const formatPremiumDiscount = (value: number | null | undefined) => {
  if (value === null || value === undefined) return ''
  return `${value >= 0 ? '+' : ''}${value}`
}

// 组件挂载
onMounted(() => {
  loadTable1Data()
  loadTable2Data()
})
</script>

<style scoped lang="scss">
.group-price-page {
  .table-section {
    margin-bottom: 30px;
    
    h3 {
      margin-bottom: 15px;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .filter-section {
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    
    .filter-label {
      font-weight: 500;
      margin-right: 10px;
      min-width: 80px;
    }
  }

  .table-container {
    margin-bottom: 20px;
  }

  .range-section {
    margin-top: 20px;
    padding: 15px;
    background-color: #f5f7fa;
    border-radius: 4px;
    display: flex;
    align-items: center;
    
    .filter-label {
      font-weight: 500;
      margin-right: 10px;
    }
    
    .range-result {
      margin-left: 20px;
      font-size: 14px;
    }
  }

  .price-value {
    font-weight: 500;
  }

  .premium-discount {
    font-size: 12px;
    color: #909399;
    margin-top: 2px;
  }
}
</style>
