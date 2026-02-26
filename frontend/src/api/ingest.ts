import request from './request'

export interface PreviewResponse {
  template_type: string
  sheets: Array<{
    name: string
    rows: number
    columns: string[]
    sample_data?: any[]
    error?: string
  }>
  date_range: {
    start: string
    end: string
  } | null
  sample_rows: any[]
  field_mappings: any
}

export interface BatchInfo {
  id: number
  filename: string
  source_code: string
  status: string
  total_rows: number
  success_rows: number
  failed_rows: number
  created_at: string
}

export interface BatchDetail extends BatchInfo {
  date_range: {
    start: string
    end: string
  } | null
  errors: Array<{
    sheet: string
    row: number
    col: string
    error_type: string
    message: string
  }>
  mapping: any
}

/** 获取 API 基础 URL（用于 EventSource 等） */
function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || ''
}

export const ingestApi = {
  uploadFile: (formData: FormData): Promise<{ batch_id: number; template_type: string; filename: string }> => {
    return request.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  previewImport: (formData: FormData): Promise<PreviewResponse> => {
    return request.post('/ingest/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 600000
    })
  },

  /** 提交导入任务（后台执行），立即返回 task_id */
  submitImport: (files: File[]): Promise<{ task_id: string; total_files: number; message: string }> => {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    return request.post('/ingest/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000
    })
  },

  /** 创建 SSE 连接获取导入进度（需携带 token） */
  createSSEStream: (taskId: string): EventSource => {
    const token = localStorage.getItem('token')
    const base = getApiBaseUrl() || ''
    const path = `/api/ingest/sse/${taskId}${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const url = base ? `${base.replace(/\/$/, '')}${path}` : path
    return new EventSource(url)
  },

  executeImport: (formData: FormData, templateType?: string): Promise<any> => {
    return request.post('/ingest/execute', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      params: templateType ? { template_type: templateType } : undefined,
      timeout: 600000
    })
  },

  getBatches: (skip = 0, limit = 20): Promise<BatchInfo[]> => {
    return request.get('/ingest/batches', {
      params: { skip, limit }
    })
  },

  getBatchDetail: (batchId: number): Promise<BatchDetail> => {
    return request.get(`/ingest/batches/${batchId}`)
  }
}
