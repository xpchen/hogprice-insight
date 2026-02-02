<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '200px'" class="sidebar">
      <div class="logo">
        <img src="@/assets/logo.png" alt="HOGPRICE" class="logo-img" />
        <span v-if="!isCollapse" class="logo-text">猪价智盘</span>
        <span v-else class="logo-text-collapsed">智盘</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        :collapse="isCollapse"
        :collapse-transition="false"
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/import">
          <el-icon><Upload /></el-icon>
          <template #title>数据导入</template>
        </el-menu-item>
        <el-menu-item index="/analysis">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>多维分析</template>
        </el-menu-item>
        <el-menu-item index="/template-center">
          <el-icon><Document /></el-icon>
          <template #title>模板中心</template>
        </el-menu-item>
        <el-menu-item index="/chart-builder">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>图表配置</template>
        </el-menu-item>
        <el-menu-item index="/templates">
          <el-icon><Document /></el-icon>
          <template #title>模板管理</template>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <template #title>报告生成</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapse ? Expand : Fold"
            circle
            @click="toggleCollapse"
            style="margin-right: 10px"
          />
        </div>
        <div class="header-right">
          <el-tooltip :content="isFullscreen ? '退出全屏 (Esc)' : '全屏 (F11)'" placement="bottom">
            <el-button
              :icon="FullScreen"
              circle
              @click="toggleFullscreen"
              :type="isFullscreen ? 'warning' : 'default'"
              style="margin-right: 10px"
            />
          </el-tooltip>
          <span>{{ userStore.user?.username }}</span>
          <el-button type="text" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { House, Upload, DataAnalysis, Fold, Expand, FullScreen, Document } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const isCollapse = ref(false)
const isFullscreen = ref(false)

// 切换侧边栏折叠
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 切换全屏
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    // 进入全屏
    document.documentElement.requestFullscreen().then(() => {
      isFullscreen.value = true
      ElMessage.success('已进入全屏模式')
    }).catch((err) => {
      console.error('无法进入全屏:', err)
      ElMessage.error('无法进入全屏模式')
    })
  } else {
    // 退出全屏
    document.exitFullscreen().then(() => {
      isFullscreen.value = false
      ElMessage.success('已退出全屏模式')
    }).catch((err) => {
      console.error('无法退出全屏:', err)
    })
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  // 检查当前是否全屏
  isFullscreen.value = !!document.fullscreenElement
  // 监听全屏状态变化
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})

const handleLogout = () => {
  userStore.clearToken()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  color: #fff;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
  background-color: #2b3a4a;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 10px;
  overflow: hidden;
}

.logo-img {
  height: 36px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  white-space: nowrap;
  flex-shrink: 0;
}

.logo-text-collapsed {
  font-size: 14px;
  white-space: nowrap;
  flex-shrink: 0;
}

.sidebar-menu {
  border: none;
  background-color: #304156;
}

.sidebar-menu .el-menu-item {
  color: #bfcbd9;
}

.sidebar-menu .el-menu-item:hover {
  background-color: #263445;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #409eff;
  color: #fff;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}
</style>
