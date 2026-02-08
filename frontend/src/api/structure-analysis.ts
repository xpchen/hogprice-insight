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

/**
 * 获取结构分析数据
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
