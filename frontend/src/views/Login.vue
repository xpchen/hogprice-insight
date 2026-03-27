<template>
  <div class="login-container">
    <div class="bg-decoration bg-decoration-left"></div>
    <div class="bg-decoration bg-decoration-right"></div>

    <el-card class="login-card" shadow="never">
      <div class="brand-block">
        <img src="@/assets/logo.png" alt="logo" class="brand-logo" />
        <div class="brand-title-group">
          <h1 class="brand-title">农产品数据库</h1>
          <p class="brand-subtitle">HogPrice Insight Platform</p>
        </div>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="login-form" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large">
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item class="submit-item">
          <el-button type="primary" :loading="loading" @click="handleLogin" class="login-btn" size="large">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-footer">欢迎使用数据分析与决策支持系统</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api/auth'
import { useUserStore } from '../store/user'
import { debugLog, debugError } from '../utils/debug'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    loading.value = true
    try {
      debugLog('Attempting login', { username: form.username })
      const response = await authApi.login(form.username, form.password)
      debugLog('Login successful', response)
      
      userStore.setToken(response.access_token)
      await userStore.fetchUserInfo()
      
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (error: any) {
      debugError('Login failed', error)
      const errorMessage = error.response?.data?.detail || error.message || '登录失败，请检查用户名和密码'
      ElMessage.error(errorMessage)
      // 不要自动跳转，让用户看到错误信息
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 16%, rgba(59, 130, 246, 0.24), transparent 36%),
    radial-gradient(circle at 86% 82%, rgba(14, 165, 233, 0.2), transparent 34%),
    linear-gradient(135deg, #0b1f3a 0%, #11325f 45%, #1d4f91 100%);
  padding: 24px;
}

.bg-decoration {
  position: absolute;
  border-radius: 999px;
  filter: blur(4px);
  opacity: 0.36;
}

.bg-decoration-left {
  width: 320px;
  height: 320px;
  left: -120px;
  top: -100px;
  background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
}

.bg-decoration-right {
  width: 360px;
  height: 360px;
  right: -140px;
  bottom: -120px;
  background: linear-gradient(135deg, #0ea5e9 0%, #1d4ed8 100%);
}

.login-card {
  position: relative;
  width: 420px;
  border: 1px solid rgba(148, 197, 255, 0.35);
  border-radius: 16px;
  background: rgba(244, 249, 255, 0.93);
  backdrop-filter: blur(6px);
  box-shadow: 0 24px 64px rgba(10, 35, 73, 0.35);
}

.brand-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 20px;
}

.brand-logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  margin-bottom: 10px;
}

.brand-title {
  margin: 0;
  color: #0d2b52;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.brand-subtitle {
  margin: 6px 0 0;
  color: #3b5f8f;
  font-size: 13px;
  letter-spacing: 0.3px;
}

.login-form {
  margin-top: 10px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #c6d8ef inset;
  background-color: #ffffff;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset;
}

.submit-item {
  margin-top: 4px;
  margin-bottom: 4px !important;
}

.login-btn {
  width: 100%;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.8px;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #0ea5e9 100%);
  border: none;
  box-shadow: 0 10px 20px rgba(30, 78, 170, 0.35);
}

.login-btn:hover {
  filter: brightness(1.03);
  transform: translateY(-1px);
}

.login-footer {
  text-align: center;
  margin-top: 10px;
  margin-bottom: 2px;
  color: #4f6d95;
  font-size: 12px;
}
</style>
