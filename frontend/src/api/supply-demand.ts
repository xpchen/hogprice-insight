/**
 * E3. 供需曲线API客户端
 */
import request from './request'

export interface SupplyDemandCurvePoint {
  month: string
  slaughter_coefficient?: number | null
  price_coefficient?: number | null
}

export interface SupplyDemandCurveResponse {
  data: SupplyDemandCurvePoint[]
  latest_month?: string | null
}

export interface InventoryPricePoint {
  month: string
  inventory_index?: number | null
  price?: number | null
  inventory_month?: string | null
}

export interface InventoryPriceResponse {
  data: InventoryPricePoint[]
  latest_month?: string | null
}

/**
 * 获取长周期生猪供需曲线数据
 */
export function getSupplyDemandCurve(): Promise<SupplyDemandCurveResponse> {
  return request({
    url: '/v1/supply-demand/curve',
    method: 'get'
  })
}

/**
 * 获取能繁母猪存栏&猪价（滞后10个月）
 */
export function getBreedingInventoryPrice(): Promise<InventoryPriceResponse> {
  return request({
    url: '/v1/supply-demand/breeding-inventory-price',
    method: 'get'
  })
}

/**
 * 获取新生仔猪&猪价（滞后10个月）
 */
export function getPigletPrice(): Promise<InventoryPriceResponse> {
  return request({
    url: '/v1/supply-demand/piglet-price',
    method: 'get'
  })
}
