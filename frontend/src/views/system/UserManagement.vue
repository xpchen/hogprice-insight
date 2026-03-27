<template>
  <div class="user-management">
    <el-card>
      <template #header>
        <div class="header-row">
          <span>用户管理</span>
          <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" border>
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="display_name" label="显示名称" min-width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r" class="role-tag">{{ r }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button type="warning" link @click="openResetPasswordDialog(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="userDialogVisible" :title="dialogMode === 'create' ? '新增用户' : '编辑用户'" width="520px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="初始密码" prop="password">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="userForm.display_name" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active" v-if="dialogMode === 'edit'">
          <el-switch v-model="userForm.is_active" />
        </el-form-item>
        <el-form-item label="角色" prop="role_codes">
          <el-select v-model="userForm.role_codes" multiple filterable style="width: 100%">
            <el-option v-for="role in roles" :key="role.code" :label="`${role.name} (${role.code})`" :value="role.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitUserForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="重置密码" width="420px">
      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="90px">
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="resetForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitResetPassword">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { usersApi, type AdminRole, type AdminUser } from '@/api/users'
import { useUserStore } from '@/store/user'
import { useRouter } from 'vue-router'

type DialogMode = 'create' | 'edit'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const users = ref<AdminUser[]>([])
const roles = ref<AdminRole[]>([])

const userDialogVisible = ref(false)
const dialogMode = ref<DialogMode>('create')
const editingUserId = ref<number | null>(null)
const userFormRef = ref<FormInstance>()
const userForm = reactive({
  username: '',
  password: '',
  display_name: '',
  is_active: true,
  role_codes: [] as string[]
})

const resetDialogVisible = ref(false)
const resetFormRef = ref<FormInstance>()
const resetTargetUserId = ref<number | null>(null)
const resetForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

const isAdmin = computed(() => {
  const rolesVal = userStore.user?.roles || []
  return rolesVal.includes('admin')
})

const userRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    {
      validator: (_rule, value, callback) => {
        if (dialogMode.value === 'create' && !value) callback(new Error('请输入初始密码'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  role_codes: [{ type: 'array', required: true, message: '请选择至少一个角色', trigger: 'change' }]
}

const resetRules: FormRules = {
  newPassword: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== resetForm.newPassword) callback(new Error('两次输入密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

const formatDateTime = (iso: string) => {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 19)
}

const loadData = async () => {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([usersApi.getUsers(), usersApi.getRoles()])
    users.value = usersRes
    roles.value = rolesRes
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  editingUserId.value = null
  userForm.username = ''
  userForm.password = ''
  userForm.display_name = ''
  userForm.is_active = true
  userForm.role_codes = []
  userDialogVisible.value = true
}

const openEditDialog = (row: AdminUser) => {
  dialogMode.value = 'edit'
  editingUserId.value = row.id
  userForm.username = row.username
  userForm.password = ''
  userForm.display_name = row.display_name || ''
  userForm.is_active = row.is_active
  userForm.role_codes = [...row.roles]
  userDialogVisible.value = true
}

const submitUserForm = async () => {
  if (!userFormRef.value) return
  await userFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (dialogMode.value === 'create') {
        await usersApi.createUser({
          username: userForm.username.trim(),
          password: userForm.password,
          display_name: userForm.display_name.trim() || undefined,
          role_codes: userForm.role_codes
        })
        ElMessage.success('用户创建成功')
      } else if (editingUserId.value != null) {
        await usersApi.updateUser(editingUserId.value, {
          display_name: userForm.display_name.trim() || undefined,
          is_active: userForm.is_active,
          role_codes: userForm.role_codes
        })
        ElMessage.success('用户更新成功')
      }
      userDialogVisible.value = false
      await loadData()
    } finally {
      saving.value = false
    }
  })
}

const openResetPasswordDialog = (row: AdminUser) => {
  resetTargetUserId.value = row.id
  resetForm.newPassword = ''
  resetForm.confirmPassword = ''
  resetDialogVisible.value = true
}

const submitResetPassword = async () => {
  if (!resetFormRef.value || resetTargetUserId.value == null) return
  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await usersApi.resetPassword(resetTargetUserId.value!, resetForm.newPassword)
      ElMessage.success('密码已重置')
      resetDialogVisible.value = false
    } finally {
      saving.value = false
    }
  })
}

onMounted(async () => {
  if (!isAdmin.value) {
    ElMessage.error('无权限访问用户管理')
    router.replace('/dashboard')
    return
  }
  await loadData()
})
</script>

<style scoped>
.user-management {
  padding: 16px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.role-tag {
  margin-right: 6px;
}
</style>
