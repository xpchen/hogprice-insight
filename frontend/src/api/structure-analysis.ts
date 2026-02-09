/**
 * 结构分析API客户端
 */
import request from './request'

export interface StructureDataPoint {
  date: string
  source: string
  value?: number | null
}

export interface StructureAnalysisResponse {
  data: StructureDataPoint[]
  latest_date?: string | null
}

export interface StructureTableRow {
  month: string
  cr20?: number | null
  yongyi?: number | null
  ganglian?: number | null
  ministry_scale?: number | null
  ministry_scattered?: number | null
  slaughter?: number | null
}

export interface StructureTableResponse {
  data: StructureTableRow[]
  latest_month?: string | null
}

/**
 * 获取结构分析数据（图表格式）
 */
export function getStructureAnalysisData(
  sources?: string
): Promise<StructureAnalysisResponse> {
  return request({
    url: '/v1/structure-analysis/data',
    method: 'get',
    params: {
      sources
    }
  })
}

/**
 * 获取结构分析表格数据
 */
export function getStructureAnalysisTable(): Promise<StructureTableResponse> {
  return request({
    url: '/v1/structure-analysis/table',
    method: 'get'
  })
}
