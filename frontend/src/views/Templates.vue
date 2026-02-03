<template>
  <div class="templates-page">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>图表模板管理</span>
          <el-button type="primary" @click="handleCreate">新建模板</el-button>
        </div>
      </template>
      
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的模板" name="mine">
          <template-list
            :templates="myTemplates"
            :loading="loading"
            scope="mine"
            @open="handleOpen"
            @edit="handleEdit"
            @delete="handleDelete"
            @copy="handleCopy"
          />
        </el-tab-pane>
        <el-tab-pane label="公共模板" name="public">
          <template-list
            :templates="publicTemplates"
            :loading="loading"
            scope="public"
            @open="handleOpen"
            @edit="handleEdit"
            @delete="handleDelete"
            @copy="handleCopy"
            @publish="handlePublish"
            :is-admin="isAdmin"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 新建/编辑模板对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建模板' : '编辑模板'"
      width="600px"
    >
      <el-form :model="templateForm" label-width="100px">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="图表类型" required>
          <el-select v-model="templateForm.chart_type" placeholder="请选择">
            <el-option label="季节性图" value="seasonality" />
            <el-option label="区间多指标图" value="timeseries" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isAdmin" label="公开模板">
          <el-switch v-model="templateForm.is_public" />
        </el-form-item>
        <el-form-item label="配置JSON">
          <el-input
            v-model="templateForm.spec_json_str"
            type="textarea"
            :rows="10"
            placeholder="ChartSpec JSON配置"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { templatesApi, type TemplateInfo } from '../api/templates'
import { useUserStore } from '../store/user'
import TemplateList from '../components/TemplateList.vue'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('mine')
const loading = ref(false)
const myTemplates = ref<TemplateInfo[]>([])
const publicTemplates = ref<TemplateInfo[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const templateForm = ref({
  id: null as number | null,
  name: '',
  chart_type: '' as 'seasonality' | 'timeseries' | '',
  is_public: false,
  spec_json_str: ''
})

const isAdmin = computed(() => {
  // 从用户信息中获取角色（如果后端返回了roles字段）
  const roles = userStore.user?.roles || []
  return roles.includes('admin') || roles.some((r: any) => r.code === 'admin')
})

const handleTabChange = () => {
  loadTemplates()
}

const loadTemplates = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'mine') {
      myTemplates.value = await templatesApi.getTemplates('mine')
    } else {
      publicTemplates.value = await templatesApi.getTemplates('public')
    }
  } catch (error) {
    ElMessage.error('加载模板失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  templateForm.value = {
    id: null,
    name: '',
    chart_type: '',
    is_public: false,
    spec_json_str: ''
  }
  dialogVisible.value = true
}

const handleEdit = async (template: TemplateInfo) => {
  try {
    const detail = await templatesApi.getTemplate(template.id)
    dialogMode.value = 'edit'
    templateForm.value = {
      id: detail.id,
      name: detail.name,
      chart_type: detail.chart_type || '',
      is_public: detail.is_public,
      spec_json_str: JSON.stringify(detail.spec_json, null, 2)
    }
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载模板详情失败')
  }
}

const handleSave = async () => {
  if (!templateForm.value.name || !templateForm.value.chart_type) {
    ElMessage.warning('请填写模板名称和图表类型')
    return
  }
  
  try {
    // 解析JSON
    let specJson: any
    try {
      specJson = JSON.parse(templateForm.value.spec_json_str || '{}')
    } catch (e) {
      ElMessage.error('JSON格式错误')
      return
    }
    
    if (dialogMode.value === 'create') {
      await templatesApi.createTemplate({
        name: templateForm.value.name,
        chart_type: templateForm.value.chart_type,
        spec_json: specJson,
        is_public: templateForm.value.is_public && isAdmin.value
      })
      ElMessage.success('模板创建成功')
    } else {
      if (!templateForm.value.id) return
      await templatesApi.updateTemplate(templateForm.value.id, {
        name: templateForm.value.name,
        spec_json: specJson,
        is_public: templateForm.value.is_public && isAdmin.value ? true : undefined
      })
      ElMessage.success('模板更新成功')
    }
    
    dialogVisible.value = false
    loadTemplates()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  }
}

const handleOpen = (template: TemplateInfo) => {
  // 跳转到ChartBuilder页面并加载模板
  router.push({
    path: '/chart-builder',
    query: { template_id: template.id.toString() }
  })
}

const handleDelete = async (template: TemplateInfo) => {
  try {
    await ElMessageBox.confirm('确定要删除这个模板吗？', '确认删除', {
      type: 'warning'
    })
    
    await templatesApi.deleteTemplate(template.id)
    ElMessage.success('删除成功')
    loadTemplates()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleCopy = async (template: TemplateInfo) => {
  try {
    const detail = await templatesApi.getTemplate(template.id)
    await templatesApi.createTemplate({
      name: `${detail.name} (副本)`,
      chart_type: detail.chart_type || 'seasonality',
      spec_json: detail.spec_json,
      is_public: false
    })
    ElMessage.success('复制成功')
    loadTemplates()
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handlePublish = async (template: TemplateInfo) => {
  try {
    await templatesApi.updateTemplate(template.id, {
      is_public: !template.is_public
    })
    ElMessage.success(template.is_public ? '已取消公开' : '已发布为公共模板')
    loadTemplates()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.templates-page {
  padding: 20px;
}
</style>
