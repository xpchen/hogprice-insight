<template>
  <div class="template-center-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>模板中心</span>
          <el-button type="primary" @click="handleInitPreset" v-if="isAdmin" :loading="initLoading">
            初始化预设模板
          </el-button>
        </div>
      </template>
      
      <el-tabs v-model="activeCategory">
        <el-tab-pane
          v-for="category in categories"
          :key="category"
          :label="category"
          :name="category"
        >
          <el-row :gutter="20">
            <el-col
              v-for="template in getTemplatesByCategory(category)"
              :key="template.template_id"
              :span="8"
            >
              <el-card shadow="hover" style="margin-bottom: 20px; cursor: pointer" @click="handleOpenTemplate(template)">
                <template #header>
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span style="font-weight: bold">{{ template.name }}</span>
                    <el-tag :type="getCategoryTagType(category)" size="small">{{ category }}</el-tag>
                  </div>
                </template>
                <div>
                  <p style="color: #909399; font-size: 12px; margin-bottom: 10px">
                    {{ template.description }}
                  </p>
                  <div style="font-size: 12px; color: #606266">
                    <div>图表类型: {{ template.chart_type === 'seasonality' ? '季节性图' : '区间图' }}</div>
                    <div v-if="template.acceptance && template.acceptance.length > 0" style="margin-top: 8px">
                      <strong>验收点:</strong>
                      <ul style="margin: 4px 0; padding-left: 20px">
                        <li v-for="(point, idx) in template.acceptance.slice(0, 2)" :key="idx" style="font-size: 11px">
                          {{ point }}
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
                <template #footer>
                  <el-button type="primary" size="small" @click.stop="handleOpenTemplate(template)">
                    使用模板
                  </el-button>
                </template>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 模板参数配置对话框 -->
    <el-dialog
      v-model="paramDialogVisible"
      :title="selectedTemplate?.name"
      width="600px"
      v-if="selectedTemplate"
    >
      <el-form :model="templateParams" label-width="120px">
        <el-form-item
          v-for="(paramConfig, paramName) in selectedTemplate.params"
          :key="paramName"
          :label="paramConfig.description || paramName"
        >
          <el-select
            v-if="paramConfig.type === 'multi_select'"
            v-model="templateParams[paramName]"
            multiple
            :placeholder="`请选择${paramConfig.description}`"
            style="width: 100%"
          >
            <el-option
              v-if="paramName === 'years'"
              v-for="year in availableYears"
              :key="year"
              :label="`${year}年`"
              :value="year"
            />
            <el-option
              v-else-if="paramName === 'geo_ids'"
              v-for="geo in geos"
              :key="geo.id"
              :label="geo.province"
              :value="geo.id"
            />
          </el-select>
          
          <el-select
            v-else-if="paramConfig.type === 'select'"
            v-model="templateParams[paramName]"
            :placeholder="`请选择${paramConfig.description}`"
            style="width: 100%"
          >
            <el-option
              v-for="option in paramConfig.options"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
          
          <el-date-picker
            v-else-if="paramConfig.type === 'daterange'"
            v-model="templateParams[paramName]"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paramDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleApplyTemplate" :loading="applying">
          应用并生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { templatesApi } from '../api/templates'
import { metadataApi, type GeoInfo } from '../api/metadata'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const presetTemplates = ref<any[]>([])
const geos = ref<GeoInfo[]>([])
const activeCategory = ref('价差')
const initLoading = ref(false)
const paramDialogVisible = ref(false)
const selectedTemplate = ref<any>(null)
const templateParams = ref<any>({})
const applying = ref(false)

const currentYear = new Date().getFullYear()
const availableYears = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i)

const categories = computed(() => {
  const cats = new Set(presetTemplates.value.map(t => t.category))
  return Array.from(cats).sort()
})

const isAdmin = computed(() => {
  const roles = userStore.user?.roles || []
  return roles.includes('admin')
})

const getTemplatesByCategory = (category: string) => {
  return presetTemplates.value.filter(t => t.category === category)
}

const getCategoryTagType = (category: string): string => {
  const map: Record<string, string> = {
    '价差': 'success',
    '价格': 'primary',
    '利润': 'warning',
    '区域': 'info',
    '企业': 'danger',
    '管理看板': ''
  }
  return map[category] || ''
}

const loadPresetTemplates = async () => {
  try {
    presetTemplates.value = await templatesApi.getPresetTemplates()
  } catch (error) {
    ElMessage.error('加载预设模板失败')
    console.error(error)
  }
}

const loadGeos = async () => {
  try {
    geos.value = await metadataApi.getGeo()
  } catch (error) {
    console.error('加载地区失败', error)
  }
}

const handleInitPreset = async () => {
  initLoading.value = true
  try {
    await templatesApi.initPresetTemplates()
    ElMessage.success('预设模板初始化成功')
    // 重新加载模板列表
    await loadPresetTemplates()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '初始化失败')
  } finally {
    initLoading.value = false
  }
}

const handleOpenTemplate = (template: any) => {
  selectedTemplate.value = template
  
  // 初始化参数默认值
  const params: any = {}
  for (const [paramName, paramConfig] of Object.entries(template.params || {})) {
    const config = paramConfig as any
    if (config.default === 'YTD') {
      // 本年迄今
      const today = new Date()
      params[paramName] = [
        new Date(today.getFullYear(), 0, 1),
        today
      ]
    } else if (config.default === 'last_90_days') {
      const end = new Date()
      const start = new Date(end.getTime() - 90 * 24 * 60 * 60 * 1000)
      params[paramName] = [start, end]
    } else if (config.default === 'last_180_days') {
      const end = new Date()
      const start = new Date(end.getTime() - 180 * 24 * 60 * 60 * 1000)
      params[paramName] = [start, end]
    } else if (paramName === 'years' && !config.default) {
      // 默认最近6年
      params[paramName] = availableYears.slice(-6)
    } else {
      params[paramName] = config.default || (config.type === 'multi_select' ? [] : '')
    }
  }
  
  templateParams.value = params
  paramDialogVisible.value = true
}

const handleApplyTemplate = async () => {
  if (!selectedTemplate.value) return
  
  applying.value = true
  try {
    // 格式化参数
    const formattedParams: any = {}
    
    for (const [key, value] of Object.entries(templateParams.value)) {
      if (key === 'date_range' && Array.isArray(value)) {
        // 日期范围转换为字符串格式
        const formatDate = (date: Date): string => {
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        }
        formattedParams.date_range = JSON.stringify({
          start: formatDate(value[0]),
          end: formatDate(value[1])
        })
      } else if (key === 'years' && Array.isArray(value)) {
        // 年份数组转换为逗号分隔的字符串或JSON
        formattedParams.years = value.join(',')
      } else if (value !== null && value !== undefined && value !== '') {
        formattedParams[key] = value
      }
    }
    
    // 跳转到ChartBuilder页面，传递预设模板ID和参数
    router.push({
      path: '/chart-builder',
      query: {
        preset_template_id: selectedTemplate.value.template_id,
        ...formattedParams
      }
    })
    paramDialogVisible.value = false
  } catch (error) {
    ElMessage.error('应用模板失败')
  } finally {
    applying.value = false
  }
}

onMounted(async () => {
  await loadPresetTemplates()
  await loadGeos()
  
  // 检查URL参数中是否有template_id（从ChartBuilder跳转过来）
  const templateId = route.query.template_id
  if (templateId) {
    const template = presetTemplates.value.find((t: any) => t.template_id === templateId)
    if (template) {
      // 切换到对应类别
      activeCategory.value = template.category
      // 打开模板配置对话框
      handleOpenTemplate(template)
    }
  }
})
</script>

<style scoped>
.template-center-page {
  padding: 20px;
}
</style>
