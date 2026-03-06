<template>
  <div class="group-price-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>D5. 集团价格</span>
          <DataSourceInfo
            v-if="table1Data && (table1Data.latest_date || table1Data.date_range?.end)"
            source-name="钢联模板"
            :update-date="formatUpdateDate(table1Data.latest_date || table1Data.date_range?.end)"
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

        <!-- 价格表格：列头与以前一致（日期 + 企业名列 + 牧原白条及下属区域），无升贴水行 -->
        <div class="table-container">
          <el-table
            :data="table1DisplayData"
            border
            stripe
            v-loading="loading1"
            style="width: 100%"
            max-height="calc(100vh - 320px)"
          >
            <el-table-column prop="date" label="日期" min-width="110" fixed="left" align="center">
              <template #default="{ row }">
                <span class="date-cell">{{ formatDate(row.date) }}</span>
              </template>
            </el-table-column>
            <el-table-column
              v-for="company in table1FlatColumns"
              :key="company"
              min-width="68"
              align="right"
              header-align="center"
            >
              <template #header>
                <div class="header-with-pd">
                  <span>{{ getColumnLabel(company) }}</span>
                  <span v-if="getHeaderPremiumDiscount(company) !== null" class="header-pd">{{ formatHeaderPremiumDiscount(getHeaderPremiumDiscount(company)) }}</span>
                </div>
              </template>
              <template #default="{ row }">
                <span v-if="getCompanyPrice(row, company) !== null">{{ formatCompanyPrice(company, getCompanyPrice(row, company)!) }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column
              label="牧原白条"
              align="center"
              header-align="center"
            >
              <el-table-column
                v-for="region in MUYUAN_WHITE_STRIP_REGIONS"
                :key="region"
                :prop="region"
                min-width="62"
                align="right"
                header-align="center"
              >
                <template #header>
                  <div class="header-with-pd">
                    <span>{{ region }}</span>
                    <span v-if="getHeaderPremiumDiscount(region) !== null" class="header-pd">{{ formatHeaderPremiumDiscount(getHeaderPremiumDiscount(region)) }}</span>
                  </div>
                </template>
                <template #default="{ row }">
                  <span v-if="getCompanyPrice(row, region) !== null">{{ formatPrice(getCompanyPrice(row, region), region) }}</span>
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

        <!-- 白条市场表格：市场在行上，列为各日期的到货量/价格（日期正序） -->
        <div class="table-container">
          <el-table
            :data="table2DisplayData"
            border
            stripe
            v-loading="loading2"
            style="width: 100%"
            max-height="calc(100vh - 320px)"
          >
            <el-table-column prop="market" label="市场" min-width="88" fixed="left" align="center" />
            <template v-for="date in table2DateList" :key="date">
              <el-table-column :label="formatDate(date)" align="center">
                <el-table-column
                  :label="'到货量'"
                  :prop="'arrival_'+date"
                  min-width="72"
                  align="right"
                >
                  <template #default="{ row }">
                    {{ row['arrival_'+date] != null ? formatValue(row['arrival_'+date]) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column
                  :label="'价格'"
                  :prop="'price_'+date"
                  min-width="72"
                  align="right"
                >
                  <template #default="{ row }">
                    {{ row['price_'+date] != null ? formatPrice(row['price_'+date]) : '-' }}
                  </template>
                </el-table-column>
              </el-table-column>
            </template>
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
import type { GroupPriceTableResponse, WhiteStripMarketResponse, GroupPriceDataPoint } from '@/api/group-price'
import DataSourceInfo from '@/components/DataSourceInfo.vue'

const loading1 = ref(false)
const loading2 = ref(false)
const table1Data = ref<GroupPriceTableResponse | null>(null)
const table2Data = ref<WhiteStripMarketResponse | null>(null)

const selectedDays = ref(90)
const selectedDays2 = ref(90)
const dateRange = ref<[Date, Date] | null>(null)
const rangeChangeResult = ref<number | null>(null)

// 牧原白条多表头：来源于 3.3、白条市场跟踪.xlsx 华宝和牧原白条 sheet，一级「牧原白条」，二级为以下区域
const MUYUAN_WHITE_STRIP_REGIONS = ['华东', '河南山东', '湖北陕西', '京津冀', '东北']

// 以下列显示整数（无小数点）：华宝白条、牧原白条下属区域
const INTEGER_DISPLAY_COLUMNS = ['华宝白条', ...MUYUAN_WHITE_STRIP_REGIONS]

// 表格1 平铺列（不含牧原白条及下属华东等 5 列，该部分用多表头展示）
const table1FlatColumns = computed(() => {
  const companies = table1Data.value?.companies || []
  return companies.filter(
    (c: string) => c !== '牧原白条' && !MUYUAN_WHITE_STRIP_REGIONS.includes(c)
  )
})

// 表格1显示数据（按日期分组，含价格与升贴水）
const table1DisplayData = computed(() => {
  if (!table1Data.value || !table1Data.value.data.length) return []
  
  const dateMap: Record<string, Record<string, number | null>> = {}
  const dates = new Set<string>()
  
  table1Data.value.data.forEach((item: GroupPriceDataPoint) => {
    if (!dateMap[item.date]) {
      dateMap[item.date] = {}
      dates.add(item.date)
    }
    dateMap[item.date][item.company] = item.price ?? null
    const pdKey = item.company + '_pd'
    dateMap[item.date][pdKey] = item.premium_discount ?? null
  })
  
  return Array.from(dates).sort().map(date => ({
    date,
    ...dateMap[date]
  }))
})

// 表格2：市场在行上，日期正序；每行一个市场，列为各日期的到货量/价格
const table2DateList = computed(() => {
  if (!table2Data.value?.data?.length) return []
  const set = new Set<string>()
  table2Data.value.data.forEach((d: { date: string }) => set.add(d.date))
  return Array.from(set).sort()
})

// 表格2 市场顺序（与后端 WHITE_STRIP_MARKET_SOURCES 一致，参照原表）
const TABLE2_MARKET_ORDER = ['北京石门', '上海西郊', '成都点杀', '山西太原', '杭州五和', '无锡天鹏', '南京众彩', '广西桂林']

const table2DisplayData = computed(() => {
  if (!table2Data.value || !table2Data.value.data.length) return []
  const dates = table2DateList.value
  const marketsOrdered = TABLE2_MARKET_ORDER.filter((m: string) => (table2Data.value?.markets || []).includes(m))
  const byMarketDate: Record<string, Record<string, { arrival_volume?: number; price?: number }>> = {}
  table2Data.value.data.forEach((d: WhiteStripMarketDataPoint) => {
    if (!byMarketDate[d.market]) byMarketDate[d.market] = {}
    if (!byMarketDate[d.market][d.date]) byMarketDate[d.market][d.date] = {}
    if (d.arrival_volume != null) byMarketDate[d.market][d.date].arrival_volume = d.arrival_volume
    if (d.price != null) byMarketDate[d.market][d.date].price = d.price
  })
  return marketsOrdered.map((market: string) => {
    const row: Record<string, string | number | null> = { market }
    dates.forEach((date: string) => {
      const v = byMarketDate[market]?.[date]
      row[`arrival_${date}`] = v?.arrival_volume ?? null
      row[`price_${date}`] = v?.price ?? null
    })
    return row
  })
})

// 获取企业价格
const getCompanyPrice = (row: any, company: string): number | null => {
  return row[company] ?? null
}

// 获取企业升贴水（同行、同列）
const getCompanyPremiumDiscount = (row: any, company: string): number | null => {
  const v = row[company + '_pd']
  return v != null ? v : null
}

// 列标题：仅企业名称
const getColumnLabel = (company: string): string => company

// 表头升贴水：取最新一行的该企业升贴水。API 为 元/公斤，表头按 元/吨 显示：(＋200) / (－300)
const getHeaderPremiumDiscount = (company: string): number | null => {
  const rows = table1DisplayData.value
  if (!rows.length) return null
  const last = rows[rows.length - 1]
  const v = last[company + '_pd']
  return v != null ? v : null
}
const formatHeaderPremiumDiscount = (v: number | null | undefined): string => {
  if (v == null) return ''
  const yuanPerTon = Math.round(v * 1000) // 元/公斤 -> 元/吨
  return yuanPerTon >= 0 ? `(+${yuanPerTon})` : `(${yuanPerTon})`
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

const formatPrice = (price: number | null | undefined, column?: string) => {
  if (price === null || price === undefined) return '-'
  return INTEGER_DISPLAY_COLUMNS.includes(column || '') ? String(Math.round(price)) : price.toFixed(2)
}

const formatCompanyPrice = (company: string, value: number) => {
  return INTEGER_DISPLAY_COLUMNS.includes(company) ? String(Math.round(value)) : value.toFixed(2)
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

const formatUpdateDate = (dateStr: string | null | undefined): string | null => {
  if (!dateStr || String(dateStr).includes('年')) return dateStr || null
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return null
    return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`
  } catch {
    return null
  }
}

// 组件挂载
onMounted(() => {
  loadTable1Data()
  loadTable2Data()
})
</script>

<style scoped lang="scss">
.group-price-page {
  padding: 8px;
  :deep(.el-card__body) { padding: 8px 12px; }

  .table-section {
    margin-bottom: 16px;

    h3 {
      margin-bottom: 8px;
      font-size: 15px;
      font-weight: 600;
    }
  }

  .filter-section {
    margin-bottom: 8px;
    display: flex;
    align-items: center;

    .filter-label {
      font-weight: 500;
      margin-right: 8px;
      min-width: 72px;
    }
  }

  .table-container {
    margin-bottom: 12px;
  }

  .range-section {
    margin-top: 12px;
    padding: 10px;
    background-color: #f5f7fa;
    border-radius: 4px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;

    .filter-label { font-weight: 500; margin-right: 4px; }
    .range-result { font-size: 13px; }
  }

  :deep(.el-table) { font-size: 11px; }
  :deep(.el-table th) { padding: 2px 4px; font-weight: 600; background-color: #f5f7fa; }
  :deep(.el-table td) { padding: 1px 4px; }
  .date-cell { white-space: nowrap; }
  .header-with-pd { display: flex; flex-direction: column; align-items: center; gap: 1px; }
  .header-pd { font-size: 10px; color: #909399; }

  .group-price-table-wrap table.group-price-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    th, td { border: 1px solid #ebeef5; padding: 4px 8px; }
    th { background: #f5f7fa; font-weight: 600; }
    .th-date, .td-date { min-width: 100px; text-align: center; }
    .th-premium { text-align: center; }
    .th-company, .th-muyuan, .th-sub { text-align: center; }
    .td-num { text-align: right; min-width: 64px; }
  }
}
</style>
