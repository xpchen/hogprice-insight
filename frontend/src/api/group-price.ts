/**
 * 集团价格API客户端
 */
import request from './request'

export interface GroupPriceDataPoint {
  date: string
  company: string
  price?: number | null
  premium_discount?: number | null
}

export interface GroupPriceTableResponse {
  data: GroupPriceDataPoint[]
  companies: string[]
  date_range: {
    start: string
    end: string
  }
  latest_date?: string | null
}

export interface WhiteStripMarketDataPoint {
  date: string
  market: string
  arrival_volume?: number | null
  price?: number | null
}

export interface WhiteStripMarketResponse {
  data: WhiteStripMarketDataPoint[]
  markets: string[]
  latest_date?: string | null
}

/**
 * 获取重点集团企业生猪出栏价格
 */
export function getGroupEnterprisePrice(
  days: number = 15
): Promise<GroupPriceTableResponse> {
  return request({
    url: '/v1/group-price/group-enterprise-price',
    method: 'get',
    params: {
      days
    }
  })
}

/**
 * 获取重点市场白条到货量&价格
 */
export function getWhiteStripMarket(
  days: number = 15
): Promise<WhiteStripMarketResponse> {
  return request({
    url: '/v1/group-price/white-strip-market',
    method: 'get',
    params: {
      days
    }
  })
}
