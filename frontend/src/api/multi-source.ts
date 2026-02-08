/**
 * E2. 多渠道汇总API客户端
 */
import request from './request'

export interface MultiSourceDataPoint {
  month: string
  cull_slaughter_yongyi?: number | null
  cull_slaughter_ganglian?: number | null
  breeding_inventory_yongyi?: number | null
  breeding_inventory_ganglian_nation?: number | null
  breeding_inventory_ganglian_scale?: number | null
  breeding_inventory_ganglian_small?: number | null
  breeding_inventory_nyb?: number | null
  breeding_feed_yongyi?: number | null
  breeding_feed_ganglian?: number | null
  breeding_feed_association?: number | null
  piglet_inventory_yongyi?: number | null
  piglet_inventory_ganglian_nation?: number | null
  piglet_inventory_ganglian_scale?: number | null
  piglet_inventory_ganglian_small?: number | null
  piglet_inventory_nyb?: number | null
  piglet_feed_yongyi?: number | null
  piglet_feed_ganglian?: number | null
  piglet_feed_association?: number | null
  hog_inventory_yongyi?: number | null
  hog_inventory_ganglian_nation?: number | null
  hog_inventory_ganglian_scale?: number | null
  hog_inventory_ganglian_small?: number | null
  hog_inventory_nyb?: number | null
  hog_inventory_nyb_5month?: number | null
  hog_feed_yongyi?: number | null
  hog_feed_ganglian?: number | null
  hog_feed_association?: number | null
}

export interface MultiSourceResponse {
  data: MultiSourceDataPoint[]
  latest_month?: string | null
}

/**
 * 获取多渠道汇总数据
 */
export function getMultiSourceData(
  months: number = 10
): Promise<MultiSourceResponse> {
  return request({
    url: '/v1/multi-source/data',
    method: 'get',
    params: {
      months
    }
  })
}
