import request from './request'

export interface TimeSeriesRequest {
  date_range?: {
    start: string
    end: string
  }
  metric_ids?: number[]
  geo_ids?: number[]
  company_ids?: number[]
  warehouse_ids?: number[]
  tags_filter?: Record<string, any>
  group_by?: string[]
  time_dimension?: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
}

export interface TimeSeriesResponse {
  series: Array<{
    name: string
    data: Array<[string, number | null]>
    yAxisIndex?: number  // 指定使用哪个Y轴（0=左，1=右）
    unit?: string  // 单位
    color?: string  // 颜色
  }>
  categories: string[]
}

export interface SeasonalityRequest {
  metric_id: number
  years: number[]
  geo_ids?: number[]
  company_ids?: number[]
  warehouse_ids?: number[]
  tags_filter?: Record<string, any>
  x_mode?: 'week_of_year' | 'month_day'
  agg?: 'mean' | 'last'
}

export interface SeasonalityResponse {
  x_values: number[] | string[]
  series: Array<{
    year: number
    values: Array<number | null>
  }>
  meta: {
    unit: string
    freq: string
    metric_name: string
  }
}

export const queryApi = {
  timeseries: (params: TimeSeriesRequest) => {
    return request.post<TimeSeriesResponse>('/query/timeseries', params)
  },
  seasonality: (params: SeasonalityRequest) => {
    return request.post<SeasonalityResponse>('/query/seasonality', params)
  }
}
