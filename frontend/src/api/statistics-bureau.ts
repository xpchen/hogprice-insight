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
  total_volume?: number | null
  top_country1?: string | null
  top_country1_volume?: number | null
  top_country2?: string | null
  top_country2_volume?: number | null
}

export interface ImportMeatResponse {
  data: ImportMeatPoint[]
  latest_month?: string | null
}

/**
 * 获取统计局季度数据汇总（表1）
 */
export function getQuarterlyData(): Promise<QuarterlyDataResponse> {
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
