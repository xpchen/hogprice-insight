/**
 * 销售计划API客户端
 */
import request from './request'

export interface SalesPlanDataPoint {
  date: string
  region: string
  source: string
  actual_output?: number | null
  plan_output?: number | null
  month_on_month?: number | null
  plan_on_plan?: number | null
  plan_completion_rate?: number | null
}

export interface SalesPlanResponse {
  data: SalesPlanDataPoint[]
  data_source: string
  update_time?: string | null
  latest_date?: string | null
}

/**
 * 获取销售计划数据
 */
export function getSalesPlanData(
  indicator: string = '全部',
  region: string = '全部'
): Promise<SalesPlanResponse> {
  return request({
    url: '/v1/sales-plan/data',
    method: 'get',
    params: {
      indicator,
      region
    }
  })
}
