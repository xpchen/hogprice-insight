import request from './request'

export interface ImportResponse {
  batch_id: number
  summary: {
    total_rows: number
    success_rows: number
    failed_rows: number
    sheets_processed: number
  }
  errors: Array<{
    sheet?: string
    row?: number
    col?: number
    reason: string
  }>
}

export interface BatchInfo {
  id: number
  filename: string
  status: string
  total_rows: number
  success_rows: number
  failed_rows: number
  created_at: string
}

export const importApi = {
  importExcel: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<ImportResponse>('/data/import-excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  getBatches: (skip = 0, limit = 100) => {
    return request.get<BatchInfo[]>('/data/batches', {
      params: { skip, limit }
    })
  },
  
  getBatchDetail: (batchId: number) => {
    return request.get(`/data/batches/${batchId}`)
  }
}
