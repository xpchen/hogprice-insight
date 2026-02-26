<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
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
        <!-- 1. 总览Dashboard（默认首页） -->
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <template #title>总览</template>
        </el-menu-item>

        <!-- A. 全国重点数据 -->
        <el-sub-menu index="national-data-group">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>全国重点数据</span>
          </template>
          <el-menu-item index="/national-data/price">
            <el-icon><TrendCharts /></el-icon>
            <template #title>A1. 价格（全国）</template>
          </el-menu-item>
          <el-menu-item index="/national-data/weight">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>A2. 均重（全国）</template>
          </el-menu-item>
          <el-menu-item index="/national-data/slaughter">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>A3. 日度屠宰量</template>
          </el-menu-item>
          <el-menu-item index="/national-data/fat-std-spread">
            <el-icon><TrendCharts /></el-icon>
            <template #title>A4. 标肥价差（分省区）</template>
          </el-menu-item>
          <el-menu-item index="/national-data/region-spread">
            <el-icon><TrendCharts /></el-icon>
            <template #title>A5. 区域价差</template>
          </el-menu-item>
          <el-menu-item index="/national-data/live-white-spread">
            <el-icon><TrendCharts /></el-icon>
            <template #title>A6. 毛白价差（全国）</template>
          </el-menu-item>
          <el-menu-item index="/national-data/frozen-capacity">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>A7. 冻品库容（分省区）</template>
          </el-menu-item>
          <el-menu-item index="/national-data/industry-chain">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>A8. 产业链数据汇总</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- B. 重点省区汇总 -->
        <el-sub-menu index="province-summary-group">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>重点省区汇总</span>
          </template>
          <el-menu-item index="/province-summary/overview">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>B1. 省区范围</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- C. 期货市场数据 -->
        <el-sub-menu index="futures-market-group">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>期货市场数据</span>
          </template>
          <el-menu-item index="/futures-market/premium">
            <el-icon><TrendCharts /></el-icon>
            <template #title>C1. 升贴水</template>
          </el-menu-item>
          <el-menu-item index="/futures-market/calendar-spread">
            <el-icon><TrendCharts /></el-icon>
            <template #title>C2. 月间价差</template>
          </el-menu-item>
          <el-menu-item index="/futures-market/volatility">
            <el-icon><TrendCharts /></el-icon>
            <template #title>C3. 波动率数据</template>
          </el-menu-item>
          <el-menu-item index="/futures-market/warehouse-receipt">
            <el-icon><TrendCharts /></el-icon>
            <template #title>C4. 仓单数据</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- D. 集团企业统计 -->
        <el-sub-menu index="enterprise-statistics-group">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>集团企业统计</span>
          </template>
          <el-menu-item index="/enterprise-statistics/cr5-daily">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>D1. CR5企业日度出栏统计</template>
          </el-menu-item>
          <el-menu-item index="/enterprise-statistics/southwest">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>D2.重点省份出栏统计</template>
          </el-menu-item>
          <el-menu-item index="/enterprise-statistics/sales-plan">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>D3. 销售计划</template>
          </el-menu-item>
          <el-menu-item index="/enterprise-statistics/structure-analysis">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>D4. 结构分析</template>
          </el-menu-item>
          <el-menu-item index="/enterprise-statistics/group-price">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>D4. 集团价格</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- E. 官方数据汇总 -->
        <el-sub-menu index="official-data-group">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>官方数据汇总</span>
          </template>
          <el-menu-item index="/official-data/scale-farm">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>E1. 规模场数据汇总</template>
          </el-menu-item>
          <el-menu-item index="/official-data/multi-source">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>E2. 多渠道汇总</template>
          </el-menu-item>
          <el-menu-item index="/official-data/supply-demand-curve">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>E3. 供需曲线</template>
          </el-menu-item>
          <el-menu-item index="/official-data/statistics-bureau">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>E4. 统计局数据汇总</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- C. 分析与预警 -->
        <el-sub-menu index="analysis-group">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>分析与预警</span>
          </template>
          <el-menu-item index="/analysis">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>多维分析</template>
          </el-menu-item>
          <el-menu-item index="/chart-builder">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>图表配置</template>
          </el-menu-item>
          <el-menu-item index="/template-center">
            <el-icon><Document /></el-icon>
            <template #title>模板中心</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- 9. 数据导入与质量（管理员） -->
        <el-sub-menu v-if="isAdminOrOperator" index="data-quality-group">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>数据导入与质量</span>
          </template>
          <el-menu-item index="/data-ingest">
            <el-icon><Upload /></el-icon>
            <template #title>数据导入</template>
          </el-menu-item>
          <el-menu-item index="/raw-viewer">
            <el-icon><Document /></el-icon>
            <template #title>原表查看器</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- E. 报表与导出 -->
        <el-sub-menu index="reports-group">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>报表与导出</span>
          </template>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <template #title>报告生成</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- F. 数据中心（仅管理员/运营可见） -->
        <el-sub-menu v-if="isAdminOrOperator" index="data-center-group">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>数据中心</span>
          </template>
          <el-menu-item index="/data-reconciliation">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>入库对账</template>
          </el-menu-item>
          <el-menu-item index="/import">
            <el-icon><Upload /></el-icon>
            <template #title>数据导入（旧）</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- G. 系统管理（仅管理员可见） -->
        <el-sub-menu v-if="isAdmin" index="system-group">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/templates">
            <el-icon><Document /></el-icon>
            <template #title>模板管理</template>
          </el-menu-item>
        </el-sub-menu>
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
import { House, Upload, DataAnalysis, Fold, Expand, FullScreen, Document, TrendCharts, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const isCollapse = ref(false)
const isFullscreen = ref(false)

// 权限判断
const isAdmin = computed(() => {
  const roles = userStore.user?.roles || []
  return roles.includes('admin') || roles.some((r: any) => r.code === 'admin')
})

const isAdminOrOperator = computed(() => {
  const roles = userStore.user?.roles || []
  return isAdmin.value || roles.includes('operator') || roles.some((r: any) => r.code === 'operator')
})

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
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo {
  height: 64px;
  line-height: 64px;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.logo:hover {
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.logo-img {
  height: 40px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.logo-text {
  font-size: 18px;
  white-space: nowrap;
  flex-shrink: 0;
  letter-spacing: 1px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.logo-text-collapsed {
  font-size: 16px;
  white-space: nowrap;
  flex-shrink: 0;
  font-weight: 600;
}

.sidebar-menu {
  border: none;
  background-color: transparent;
  padding: 8px 0;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  height: calc(100vh - 64px);
}

/* 滚动条样式 */
.sidebar-menu::-webkit-scrollbar {
  width: 4px;
}

.sidebar-menu::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.sidebar-menu::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.sidebar-menu::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 菜单项基础样式 */
.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  color: #cbd5e1;
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.06);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  font-weight: 500;
}

/* 一级菜单项（非子菜单）的样式优化 */
.sidebar-menu :deep(.el-menu-item:not(.el-sub-menu__title)) {
  margin: 4px 8px;
}

/* 数据导入菜单项特殊样式 */
.sidebar-menu :deep(.data-import-item) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  margin: 8px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(245, 87, 108, 0.3);
}

.sidebar-menu :deep(.data-import-item:hover) {
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  box-shadow: 0 6px 16px rgba(245, 87, 108, 0.4);
  transform: translateY(-1px);
}

.sidebar-menu :deep(.data-import-item.is-active) {
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  box-shadow: 0 6px 16px rgba(245, 87, 108, 0.5);
}

/* 子菜单样式 */
.sidebar-menu :deep(.el-sub-menu) {
  margin: 6px 8px;
  border-radius: 8px;
  overflow: visible;
  background-color: transparent;
}

.sidebar-menu :deep(.el-sub-menu__title) {
  padding-left: 16px !important;
  padding-right: 16px !important;
  font-weight: 500;
  transition: all 0.3s ease;
  height: 48px;
  line-height: 48px;
  color: #cbd5e1;
  border-radius: 8px;
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu.is-opened .el-sub-menu__title) {
  background-color: rgba(255, 255, 255, 0.08);
  color: #fff;
  border-radius: 8px 8px 0 0;
  margin-bottom: 0;
}

/* 子菜单项容器 */
.sidebar-menu :deep(.el-sub-menu .el-menu) {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 0 0 8px 8px;
  padding: 6px 4px;
  margin-top: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item) {
  margin: 3px 4px;
  padding-left: 52px !important;
  padding-right: 12px !important;
  background-color: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  height: 38px;
  line-height: 38px;
  color: #94a3b8;
  font-size: 13px;
  transition: all 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  position: relative;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item::before) {
  content: '';
  position: absolute;
  left: 36px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.3);
  transition: all 0.2s ease;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
  transform: translateX(3px);
  padding-left: 54px !important;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item:hover::before) {
  background-color: rgba(255, 255, 255, 0.5);
  width: 6px;
  height: 6px;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  transform: translateX(0);
  padding-left: 52px !important;
  margin-left: 4px;
  margin-right: 4px;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active::before) {
  background-color: rgba(255, 255, 255, 0.8);
  width: 6px;
  height: 6px;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active .el-icon) {
  color: #fff;
}

/* 图标样式 */
.sidebar-menu :deep(.el-icon) {
  font-size: 18px;
  margin-right: 8px;
  transition: transform 0.3s ease;
  flex-shrink: 0;
}

.sidebar-menu :deep(.el-menu-item:hover .el-icon),
.sidebar-menu :deep(.el-sub-menu__title:hover .el-icon) {
  transform: scale(1.1);
}

/* 子菜单项的图标样式 */
.sidebar-menu :deep(.el-sub-menu .el-menu-item .el-icon) {
  font-size: 16px;
  margin-right: 10px;
  color: #94a3b8;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active .el-icon) {
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item:hover .el-icon) {
  color: #e2e8f0;
}

/* 分隔线 */
.sidebar-menu :deep(.el-menu-item) + .el-sub-menu,
.sidebar-menu :deep(.el-sub-menu) + .el-menu-item,
.sidebar-menu :deep(.el-menu-item) + .el-menu-item {
  margin-top: 4px;
}

/* 子菜单项之间的分隔 */
.sidebar-menu :deep(.el-sub-menu .el-menu-item + .el-menu-item) {
  margin-top: 3px;
}

/* 子菜单展开时的视觉优化 */
.sidebar-menu :deep(.el-sub-menu.is-opened) {
  background-color: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 子菜单标题的图标旋转 */
.sidebar-menu :deep(.el-sub-menu.is-opened .el-sub-menu__icon-arrow) {
  transform: rotate(180deg);
}

.sidebar-menu :deep(.el-sub-menu__icon-arrow) {
  transition: transform 0.3s ease;
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
}

.sidebar-menu :deep(.el-sub-menu__title:hover .el-sub-menu__icon-arrow),
.sidebar-menu :deep(.el-sub-menu.is-opened .el-sub-menu__icon-arrow) {
  color: #fff;
}

/* 子菜单标题文字样式优化 */
.sidebar-menu :deep(.el-sub-menu__title span) {
  font-weight: 500;
  letter-spacing: 0.3px;
}

/* 一级菜单项（非子菜单）的样式优化 */
.sidebar-menu :deep(.el-menu-item:not(.el-sub-menu__title)) {
  margin: 4px 8px;
  padding-left: 16px !important;
  padding-right: 16px !important;
}

/* 折叠状态 */
.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}

.header {
  background: linear-gradient(90deg, #ffffff 0%, #f8fafc 100%);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #475569;
}

.header-right span {
  font-weight: 500;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .sidebar {
    width: 200px !important;
  }
  
  .logo-text {
    font-size: 16px;
  }
}
</style>
