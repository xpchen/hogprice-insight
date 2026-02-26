/**
 * 规模场数据汇总API客户端
 */
import request from './request'

export interface ProductionDataPoint {
  date: string
  value?: number | null
}

export interface ProductionIndicatorResponse {
  data: ProductionDataPoint[]
  indicator_name: string
  latest_date?: string | null
}

export interface ProductionIndicatorsResponse {
  indicators: Record<string, ProductionDataPoint[]>
  indicator_names: string[]
  latest_date?: string | null
}

/**
 * 获取母猪效能数据（F列：分娩窝数）
 */
export function getSowEfficiency(): Promise<ProductionIndicatorResponse> {
  return request({
    url: '/v1/production-indicators/sow-efficiency',
    method: 'get'
  })
}

/**
 * 获取压栏系数数据（N列：窝均健仔数-河南）
 */
export function getPressureCoefficient(): Promise<ProductionIndicatorResponse> {
  return request({
    url: '/v1/production-indicators/pressure-coefficient',
    method: 'get'
  })
}

/**
 * 获取涌益生产指标数据（5个省份的窝均健仔数）
 */
export function getYongyiProductionIndicators(): Promise<ProductionIndicatorsResponse> {
  return request({
    url: '/v1/production-indicators/yongyi-production-indicators',
    method: 'get'
  })
}

/** 合并单元格信息（1-based，与 Excel 一致） */
export interface MergedCellRange {
  min_row: number
  max_row: number
  min_col: number
  max_col: number
}

/** A1供给预测表格（多表头）：支持 2～3 行表头、合并单元格 */
export interface A1SupplyForecastTableResponse {
  header_row_0: string[]
  header_row_1: string[]
  header_row_2?: string[]
  rows: (string | number | null)[][]
  column_count: number
  merged_cells_json?: MergedCellRange[]
}

/**
 * 获取 A1供给预测 表格数据（C-L、P-S、W-X、AC-AF 列，多表头）
 */
export function getA1SupplyForecastTable(): Promise<A1SupplyForecastTableResponse> {
  return request({
    url: '/v1/production-indicators/a1-supply-forecast-table',
    method: 'get'
  })
}

/** A1 母猪效能、压栏系数季节性数据（F 列、N 列） */
export interface A1SeasonalityResponse {
  sow_efficiency: { x_values: (number | string)[]; series: { year: number; values: (number | null)[] }[]; meta: { unit: string; freq: string; metric_name: string } }
  pressure_coefficient: { x_values: (number | string)[]; series: { year: number; values: (number | null)[] }[]; meta: { unit: string; freq: string; metric_name: string } }
}

/** 获取 A1 表格 F 列（母猪效能）、N 列（压栏系数）季节性数据 */
export function getA1SowEfficiencyPressureSeasonality(): Promise<A1SeasonalityResponse> {
  return request({
    url: '/v1/production-indicators/a1-sow-efficiency-pressure-seasonality',
    method: 'get'
  })
}

/** 涌益生产指标季节性（月度-生产指标2 F:J 五指标） */
export interface YongyiProductionSeasonalityResponse {
  indicators: Record<string, { x_values: (number | string)[]; series: { year: number; values: (number | null)[] }[]; meta: { unit: string; freq: string; metric_name: string } }>
  indicator_names: string[]
}

/** 获取涌益生产指标季节性数据（窝均健仔数、产房存活率、配种分娩率、断奶成活率、育肥出栏成活率） */
export function getYongyiProductionSeasonality(): Promise<YongyiProductionSeasonalityResponse> {
  return request({
    url: '/v1/production-indicators/yongyi-production-seasonality',
    method: 'get'
  })
}
