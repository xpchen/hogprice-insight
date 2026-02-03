import request from './request'

export interface MissingDatesResponse {
  indicator_code: string
  region_code: string | null
  freq: string
  missing_dates: string[]
  total_missing: number
}

export interface DuplicatesResponse {
  indicator_code: string
  duplicates: Array<{
    indicator_code: string
    region_code: string
    date: string
    count: number
  }>
}

export interface AnomaliesResponse {
  indicator_code: string
  anomalies: Array<{
    indicator_code: string
    region_code: string
    date: string
    value: number
    mean: number
    std: number
    deviation: number
  }>
  threshold_config: any
}

export const reconciliationApi = {
  getMissingDates: (params: {
    indicator_code: string
    region_code?: string
    freq?: string
    start_date?: string
    end_date?: string
  }): Promise<MissingDatesResponse> => {
    return request.get('/reconciliation/missing', { params })
  },

  getDuplicates: (params: {
    indicator_code: string
    region_code?: string
    freq?: string
    start_date?: string
    end_date?: string
  }): Promise<DuplicatesResponse> => {
    return request.get('/reconciliation/duplicates', { params })
  },

  getAnomalies: (params: {
    indicator_code: string
    region_code?: string
    min_value?: number
    max_value?: number
    std_multiplier?: number
  }): Promise<AnomaliesResponse> => {
    return request.get('/reconciliation/anomalies', { params })
  }
}
