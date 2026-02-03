import request from './request'

export interface MetricInfo {
  id: number
  metric_group: string
  metric_name: string
  unit?: string
  freq: string
  raw_header: string
}

export interface GeoInfo {
  id: number
  province: string
  region?: string
}

export interface CompanyInfo {
  id: number
  company_name: string
  province?: string
}

export interface WarehouseInfo {
  id: number
  warehouse_name: string
  province?: string
}

export const metadataApi = {
  getMetrics: (groups?: string | string[], freq?: string) => {
    // 支持多指标组：如果是数组，转换为逗号分隔的字符串
    const groupParam = Array.isArray(groups) 
      ? (groups.length > 0 ? groups.join(',') : undefined)
      : groups
    return request.get<MetricInfo[]>('/dim/metrics', {
      params: { 
        group: groupParam,
        freq 
      }
    })
  },
  
  getGeo: () => {
    return request.get<GeoInfo[]>('/dim/geo')
  },
  
  getCompany: () => {
    return request.get<CompanyInfo[]>('/dim/company')
  },
  
  getWarehouse: () => {
    return request.get<WarehouseInfo[]>('/dim/warehouse')
  }
}
