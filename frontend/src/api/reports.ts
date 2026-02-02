import request from './request'

export interface ReportTemplateInfo {
  id: number
  name: string
  is_public: boolean
  owner_id: number | null
  created_at: string
}

export interface ReportRunInfo {
  id: number
  template_id: number
  status: 'pending' | 'running' | 'success' | 'failed'
  output_path: string | null
  created_at: string
  finished_at: string | null
}

export interface ReportRunRequest {
  template_id: number
  params: Record<string, any>
}

export const reportsApi = {
  // 获取报告模板列表
  getTemplates: () => {
    return request.get<ReportTemplateInfo[]>('/reports/templates')
  },
  
  // 生成报告
  createRun: (data: ReportRunRequest) => {
    return request.post<ReportRunInfo>('/reports/run', data)
  },
  
  // 查询报告运行状态
  getRun: (runId: number) => {
    return request.get<ReportRunInfo>(`/reports/run/${runId}`)
  },
  
  // 下载报告
  downloadReport: (runId: number) => {
    return request.get(`/reports/run/${runId}/download`, {
      responseType: 'blob'
    }).then((blob) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `report_${runId}.xlsx`
      link.click()
      window.URL.revokeObjectURL(url)
    })
  }
}
