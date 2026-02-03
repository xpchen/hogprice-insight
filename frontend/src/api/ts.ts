import request from './request'

export interface TimeSeriesResponse {
  indicator_code: string
  indicator_name: string
  unit: string | null
  series: Array<{
    date: string
    value: number | null
  }>
  update_time: string | null
  metrics?: {
    chg_1?: number | null
    chg_5?: number | null
    chg_10?: number | null
    yoy?: number | null
    mom?: number | null
  }
}

export const tsApi = {
  getTimeseries: (params: {
    indicator_code: string
    region_code?: string
    freq?: string
    from_date?: string
    to_date?: string
    include_metrics?: boolean
  }): Promise<TimeSeriesResponse> => {
    return request.get('/ts', { params })
  }
}
