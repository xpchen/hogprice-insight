/**
 * Observation查询API客户端
 */
import request from './request'

export interface ObservationQueryParams {
  source_code?: string
  metric_key?: string
  start_date?: string
  end_date?: string
  period_type?: 'day' | 'week' | 'month'
  geo_code?: string
  tag_key?: string
  tag_value?: string
  indicator?: string
  nation_col?: string
  limit?: number
  offset?: number
}

/** 可选请求配置（如超时） */
export interface ObservationRequestConfig {
  timeout?: number
}

export interface ObservationResponse {
  id: number
  metric_name: string
  obs_date: string | null
  period_type: string | null
  period_start: string | null
  period_end: string | null
  value: number | null
  raw_value: string | null
  geo_code: string | null
  tags: Record<string, any>
  unit: string | null
}

export interface TagInfo {
  tag_key: string
  tag_value: string
  count: number
}

export interface RawSheetInfo {
  id: number
  raw_file_id: number
  sheet_name: string
  row_count: number | null
  col_count: number | null
  parse_status: string | null
  parser_type: string | null
  error_count: number | null
  observation_count: number | null
}

export interface RawTableResponse {
  raw_sheet_id: number
  table_json: any[][]
  merged_cells_json: any[] | null
  created_at: string
}

/**
 * 查询observation数据
 * @param params 查询参数
 * @param config 可选配置，如 timeout（毫秒）
 */
export function queryObservations(
  params: ObservationQueryParams,
  config?: ObservationRequestConfig
): Promise<ObservationResponse[]> {
  return request.get('/v1/observation/query', { params, ...config })
}

/**
 * 获取可用的tag键值对
 */
export function getAvailableTags(tag_key?: string, source_code?: string): Promise<TagInfo[]> {
  return request.get('/v1/observation/tags', {
    params: { tag_key, source_code }
  })
}

/**
 * 获取raw_sheet列表
 */
export function getRawSheets(params: {
  batch_id?: number
  raw_file_id?: number
  parse_status?: string
}): Promise<RawSheetInfo[]> {
  return request.get('/v1/observation/raw/sheets', { params })
}

/**
 * 获取raw_table JSON数据
 */
export function getRawTable(raw_sheet_id: number): Promise<RawTableResponse> {
  return request.get('/v1/observation/raw/table', {
    params: { raw_sheet_id }
  })
}
