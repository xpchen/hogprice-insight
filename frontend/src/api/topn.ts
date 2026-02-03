import request from './request'

export interface TopNItem {
  dimension_id: number
  dimension_name: string
  latest_value: number | null
  baseline_value: number | null
  delta?: number | null
  pct_change?: number | null
  streak_days?: number
  streak_direction?: 'up' | 'down'
  rank: number
}

export interface TopNResponse {
  metric_id: number
  metric_name: string
  dimension: string
  rank_by: string
  window_days: number
  items: TopNItem[]
}

export interface TopNRequest {
  metric_id: number
  dimension: 'geo' | 'company' | 'warehouse'
  window_days?: number
  rank_by?: 'delta' | 'pct_change' | 'seasonal_percentile' | 'streak'
  filters?: Record<string, any>
  topk?: number
}

export const topnApi = {
  queryTopN: (data: TopNRequest) => {
    return request.post<TopNResponse>('/query/topn', data)
  }
}
