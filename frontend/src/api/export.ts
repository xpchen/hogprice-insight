import request from './request'

export interface ExportRequest {
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
  include_detail?: boolean
  include_summary?: boolean
  include_chart?: boolean
  include_cover?: boolean
}

export const exportApi = {
  exportExcel: (params: ExportRequest) => {
    return request.post('/export/excel', params, {
      responseType: 'blob'
    }).then((blob) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `hogprice_export_${new Date().getTime()}.xlsx`
      link.click()
      window.URL.revokeObjectURL(url)
    })
  }
}
