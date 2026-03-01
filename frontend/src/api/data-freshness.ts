import request from './request'

export interface TableFreshnessItem {
  table: string
  label: string
  source: string | null
  source_name: string | null
  latest_date: string | null
  row_count: number
  days_ago: number | null
}

export interface FreshnessSummary {
  total_tables: number
  total_rows: number
  last_import_time: string | null
  oldest_source_date: string | null
}

export interface ImportBatchItem {
  id: number
  filename: string
  mode: string
  status: string
  row_count: number
  duration_ms: number
  created_at: string | null
}

export interface DataFreshnessResponse {
  tables: TableFreshnessItem[]
  summary: FreshnessSummary
  import_batches: ImportBatchItem[]
}

export const dataFreshnessApi = {
  getDataFreshness: (): Promise<DataFreshnessResponse> => {
    return request.get('/data-freshness')
  }
}
