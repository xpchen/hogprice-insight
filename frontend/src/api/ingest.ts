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
      timeout: 600000 // 10分钟超时
    })
  },

  executeImport: (formData: FormData, templateType?: string): Promise<any> => {
    return request.post('/ingest/execute', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      params: templateType ? { template_type: templateType } : undefined,
      timeout: 600000 // 10分钟超时
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
