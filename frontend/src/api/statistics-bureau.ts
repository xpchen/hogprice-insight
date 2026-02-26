/**
 * E4. 统计局数据汇总API客户端
 */
import request from './request'

export interface QuarterlyDataRow {
  period: string
  data: Record<string, number | null>
}

export interface QuarterlyDataResponse {
  headers: string[]
  data: QuarterlyDataRow[]
}

/** 合并单元格信息（1-based，与 Excel 一致） */
export interface MergedCellRange {
  min_row: number
  max_row: number
  min_col: number
  max_col: number
}

/** 统计局季度数据（按 Excel 原样：多级表头 + 合并单元格） */
export interface QuarterlyDataRawResponse {
  header_row_0: string[]
  header_row_1: string[]
  rows: (string | number | null)[][]
  column_count: number
  merged_cells_json?: MergedCellRange[]
}

export interface OutputSlaughterPoint {
  period: string
  output_volume?: number | null
  slaughter_volume?: number | null
  scale_rate?: number | null
}

export interface OutputSlaughterResponse {
  data: OutputSlaughterPoint[]
  latest_period?: string | null
}

export interface ImportMeatPoint {
  month: string
  price_coefficient?: number | null  // 猪价系数（月度均值/历年平均值）
}

export interface ImportMeatResponse {
  data: ImportMeatPoint[]
  latest_month?: string | null
}

/**
 * 获取统计局季度数据汇总（表1，按 Excel 原样多级表头）
 */
export function getQuarterlyData(): Promise<QuarterlyDataRawResponse> {
  return request({
    url: '/v1/statistics-bureau/quarterly-data',
    method: 'get'
  })
}

/**
 * 获取统计局生猪出栏量&屠宰量（图1）
 */
export function getOutputSlaughter(): Promise<OutputSlaughterResponse> {
  return request({
    url: '/v1/statistics-bureau/output-slaughter',
    method: 'get'
  })
}

/**
 * 获取猪肉进口数据（图2）
 */
export function getImportMeat(): Promise<ImportMeatResponse> {
  return request({
    url: '/v1/statistics-bureau/import-meat',
    method: 'get'
  })
}
