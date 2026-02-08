/**
 * 规模场数据汇总API客户端
 */
import request from './request'

export interface ProductionDataPoint {
  date: string
  value?: number | null
}

export interface ProductionIndicatorResponse {
  data: ProductionDataPoint[]
  indicator_name: string
  latest_date?: string | null
}

export interface ProductionIndicatorsResponse {
  indicators: Record<string, ProductionDataPoint[]>
  indicator_names: string[]
  latest_date?: string | null
}

/**
 * 获取母猪效能数据（F列：分娩窝数）
 */
export function getSowEfficiency(): Promise<ProductionIndicatorResponse> {
  return request({
    url: '/v1/production-indicators/sow-efficiency',
    method: 'get'
  })
}

/**
 * 获取压栏系数数据（N列：窝均健仔数-河南）
 */
export function getPressureCoefficient(): Promise<ProductionIndicatorResponse> {
  return request({
    url: '/v1/production-indicators/pressure-coefficient',
    method: 'get'
  })
}

/**
 * 获取涌益生产指标数据（5个省份的窝均健仔数）
 */
export function getYongyiProductionIndicators(): Promise<ProductionIndicatorsResponse> {
  return request({
    url: '/v1/production-indicators/yongyi-production-indicators',
    method: 'get'
  })
}
