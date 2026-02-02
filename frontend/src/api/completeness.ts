import request from './request'

export interface CompletenessItem {
  metric_id: number
  metric_name: string
  metric_group: string
  latest_date: string | null
  missing_days: number
  coverage_ratio: number
}

export interface CompletenessResponse {
  as_of: string
  window: number
  summary: {
    total: number
    ok: number
    late: number
  }
  items: CompletenessItem[]
}

export const completenessApi = {
  getCompleteness: (asOf?: string, window?: number, metricGroup?: string) => {
    return request.get<CompletenessResponse>('/dim/metrics/completeness', {
      params: {
        as_of: asOf,
        window,
        metric_group: metricGroup
      }
    })
  }
}
