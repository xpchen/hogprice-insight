/**
 * 企业集团统计API客户端
 */
import request from './request'

// 时间序列数据点
export interface TimeSeriesDataPoint {
  date: string  // YYYY-MM-DD格式
  value: number | null
}

// 时间序列系列
export interface TimeSeriesSeries {
  name: string
  data: TimeSeriesDataPoint[]
  unit?: string | null
}

// 企业统计响应
export interface EnterpriseStatisticsResponse {
  chart_title: string
  series: TimeSeriesSeries[]
  data_source: string
  update_time: string | null
  latest_date: string | null
}

/**
 * 获取CR5企业日度出栏统计
 */
export function getCr5Daily(months: number = 6): Promise<EnterpriseStatisticsResponse> {
  return request({
    url: '/v1/enterprise-statistics/cr5-daily',
    method: 'get',
    params: { months }
  })
}

/**
 * 获取四川重点企业日度出栏
 */
export function getSichuanDaily(months: number = 6): Promise<EnterpriseStatisticsResponse> {
  return request({
    url: '/v1/enterprise-statistics/sichuan-daily',
    method: 'get',
    params: { months }
  })
}

/**
 * 获取广西重点企业日度出栏
 */
export function getGuangxiDaily(months: number = 6): Promise<EnterpriseStatisticsResponse> {
  return request({
    url: '/v1/enterprise-statistics/guangxi-daily',
    method: 'get',
    params: { months }
  })
}

/**
 * 获取西南样本企业日度出栏
 */
export function getSouthwestSampleDaily(months: number = 6): Promise<EnterpriseStatisticsResponse> {
  return request({
    url: '/v1/enterprise-statistics/southwest-sample-daily',
    method: 'get',
    params: { months }
  })
}

// 省份汇总表格响应
export interface ProvinceSummaryTableResponse {
  columns: string[]  // 列名列表（包含日期、旬度、以及各省份各指标的组合）
  rows: Array<{
    date: string
    period_type?: string  // 旬度类型：上旬、中旬、月度
    [key: string]: string | number | null  // 动态列（省份-指标组合）
  }>
  data_source: string
  update_time: string | null
  latest_date: string | null
}

/**
 * 获取重点省份旬度汇总表格数据
 */
export function getProvinceSummaryTable(
  startDate?: string,
  endDate?: string
): Promise<ProvinceSummaryTableResponse> {
  const params: any = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  
  return request({
    url: '/v1/enterprise-statistics/province-summary-table',
    method: 'get',
    params
  })
}
