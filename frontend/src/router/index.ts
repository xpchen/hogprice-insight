import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'import',
        name: 'Import',
        component: () => import('../views/Import.vue')
      },
      {
        path: 'analysis',
        name: 'Analysis',
        component: () => import('../views/Analysis.vue')
      },
      {
        path: 'chart-builder',
        name: 'ChartBuilder',
        component: () => import('../views/ChartBuilder.vue')
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('../views/Templates.vue')
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/Reports.vue')
      },
      {
        path: 'template-center',
        name: 'TemplateCenter',
        component: () => import('../views/TemplateCenter.vue')
      },
      // A. 全国重点数据
      {
        path: 'national-data/price',
        name: 'NationalDataPrice',
        component: () => import('../views/national-data/Price.vue')
      },
      {
        path: 'national-data/weight',
        name: 'NationalDataWeight',
        component: () => import('../views/national-data/Weight.vue')
      },
      {
        path: 'national-data/slaughter',
        name: 'NationalDataSlaughter',
        component: () => import('../views/national-data/Slaughter.vue')
      },
      {
        path: 'national-data/fat-std-spread',
        name: 'NationalDataFatStdSpread',
        component: () => import('../views/national-data/FatStdSpread.vue')
      },
      {
        path: 'national-data/region-spread',
        name: 'NationalDataRegionSpread',
        component: () => import('../views/national-data/RegionSpread.vue')
      },
      {
        path: 'national-data/live-white-spread',
        name: 'NationalDataLiveWhiteSpread',
        component: () => import('../views/national-data/LiveWhiteSpread.vue')
      },
      {
        path: 'national-data/frozen-capacity',
        name: 'NationalDataFrozenCapacity',
        component: () => import('../views/national-data/FrozenCapacity.vue')
      },
      {
        path: 'national-data/industry-chain',
        name: 'NationalDataIndustryChain',
        component: () => import('../views/national-data/IndustryChain.vue')
      },
      // B. 重点省区汇总
      {
        path: 'province-summary/overview',
        name: 'ProvinceSummaryOverview',
        component: () => import('../views/province-summary/Overview.vue')
      },
      {
        path: 'province-summary/range',
        name: 'ProvinceSummaryRange',
        component: () => import('../views/province-summary/ProvinceRange.vue')
      },
      // C. 期货市场数据
      {
        path: 'futures-market/premium',
        name: 'FuturesMarketPremium',
        component: () => import('../views/futures-market/Premium.vue')
      },
      {
        path: 'futures-market/calendar-spread',
        name: 'FuturesMarketCalendarSpread',
        component: () => import('../views/futures-market/CalendarSpread.vue')
      },
      {
        path: 'futures-market/region-premium',
        name: 'FuturesMarketRegionPremium',
        component: () => import('../views/futures-market/RegionPremium.vue')
      },
      {
        path: 'futures-market/volatility',
        name: 'FuturesMarketVolatility',
        component: () => import('../views/futures-market/Volatility.vue')
      },
      // D. 集团企业统计
      {
        path: 'enterprise-statistics/cr5-daily',
        name: 'EnterpriseStatisticsCr5Daily',
        component: () => import('../views/enterprise-statistics/Cr5Daily.vue')
      },
      {
        path: 'enterprise-statistics/southwest',
        name: 'EnterpriseStatisticsSouthwest',
        component: () => import('../views/enterprise-statistics/Southwest.vue')
      },
      {
        path: 'enterprise-statistics/sales-plan',
        name: 'EnterpriseStatisticsSalesPlan',
        component: () => import('../views/enterprise-statistics/SalesPlan.vue')
      },
      {
        path: 'enterprise-statistics/structure-analysis',
        name: 'EnterpriseStatisticsStructureAnalysis',
        component: () => import('../views/enterprise-statistics/StructureAnalysis.vue')
      },
      {
        path: 'enterprise-statistics/group-price',
        name: 'EnterpriseStatisticsGroupPrice',
        component: () => import('../views/enterprise-statistics/GroupPrice.vue')
      },
      // E. 官方数据汇总
      {
        path: 'official-data/scale-farm',
        name: 'OfficialDataScaleFarm',
        component: () => import('../views/enterprise-statistics/ProductionIndicators.vue')
      },
      {
        path: 'official-data/multi-source',
        name: 'OfficialDataMultiSource',
        component: () => import('../views/official-data/MultiSource.vue')
      },
      {
        path: 'official-data/supply-demand-curve',
        name: 'OfficialDataSupplyDemandCurve',
        component: () => import('../views/official-data/SupplyDemandCurve.vue')
      },
      {
        path: 'official-data/statistics-bureau',
        name: 'OfficialDataStatisticsBureau',
        component: () => import('../views/official-data/StatisticsBureau.vue')
      },
      // 保留旧路由（向后兼容）
      {
        path: 'price',
        name: 'Price',
        component: () => import('../views/Price.vue')
      },
      {
        path: 'slaughter',
        name: 'Slaughter',
        component: () => import('../views/Slaughter.vue')
      },
      {
        path: 'weight',
        name: 'Weight',
        component: () => import('../views/Weight.vue')
      },
      {
        path: 'frozen',
        name: 'Frozen',
        component: () => import('../views/Frozen.vue')
      },
      {
        path: 'industry-chain',
        name: 'IndustryChain',
        component: () => import('../views/IndustryChain.vue')
      },
      {
        path: 'futures',
        name: 'Futures',
        component: () => import('../views/Futures.vue')
      },
      {
        path: 'options',
        name: 'Options',
        component: () => import('../views/Options.vue')
      },
      {
        path: 'data-ingest',
        name: 'DataIngest',
        component: () => import('../views/DataIngest.vue')
      },
      {
        path: 'data-reconciliation',
        name: 'DataReconciliation',
        component: () => import('../views/DataReconciliation.vue')
      },
      {
        path: 'delivery-cities',
        name: 'DeliveryCities',
        component: () => import('../views/DeliveryCities.vue')
      },
      {
        path: 'raw-viewer',
        name: 'RawViewer',
        component: () => import('../views/RawViewer.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
