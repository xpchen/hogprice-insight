/**
 * 价格展示API客户端
 */
import request from './request'

// 季节性数据响应
export interface SeasonalitySeries {
  year: number
  data: Array<{
    year: number
    month_day: string
    value: number | null
    lunar_day_index?: number | null
  }>
  color?: string | null
}

export interface SeasonalityResponse {
  metric_name: string
  unit: string
  series: SeasonalitySeries[]
  update_time: string | null
  latest_date: string | null
}

// 价格和价差响应
export interface PriceSpreadResponse {
  price_data: Array<{
    date: string
    year: number
    value: number | null
  }>
  spread_data: Array<{
    date: string
    year: number
    value: number | null
  }>
  available_years: number[]
  update_time: string | null
}

// 涨跌数据响应
export interface PriceChangesResponse {
  current_value: number | null
  latest_date: string | null
  day5_change: number | null
  day10_change: number | null
  day30_change: number | null
  yoy_change: number | null
  unit: string
}

/**
 * 获取全国猪价季节性数据
 */
export function getNationalPriceSeasonality(
  startYear?: number,
  endYear?: number
): Promise<SeasonalityResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: '/v1/price-display/national-price/seasonality',
    method: 'get',
    params
  })
}

/**
 * 获取标肥价差季节性数据
 */
export function getFatStdSpreadSeasonality(
  startYear?: number,
  endYear?: number,
  regionCode?: string
): Promise<SeasonalityResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  if (regionCode) params.region_code = regionCode
  
  return request({
    url: '/v1/price-display/fat-std-spread/seasonality',
    method: 'get',
    params
  })
}

/**
 * 获取猪价和标肥价差数据（可年度筛选）
 */
export function getPriceAndSpread(
  selectedYears?: number[]
): Promise<PriceSpreadResponse> {
  const params: any = {}
  if (selectedYears && selectedYears.length > 0) {
    params.selected_years = selectedYears.join(',')
  }
  
  return request({
    url: '/v1/price-display/price-and-spread',
    method: 'get',
    params
  })
}

/**
 * 获取日度屠宰量（农历）数据
 */
export function getSlaughterLunar(
  startYear?: number,
  endYear?: number
): Promise<SeasonalityResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: '/v1/price-display/slaughter/lunar',
    method: 'get',
    params
  })
}

/**
 * 获取价格/价差涨跌数据
 */
export function getPriceChanges(
  metricType: 'price' | 'spread'
): Promise<PriceChangesResponse> {
  return request({
    url: '/v1/price-display/price-changes',
    method: 'get',
    params: { metric_type: metricType }
  })
}

// 省区标肥价差信息
export interface ProvinceSpreadInfo {
  province_name: string
  province_code?: string | null
  metric_id: number
  latest_date: string | null
  latest_value: number | null
}

export interface ProvinceSpreadListResponse {
  provinces: ProvinceSpreadInfo[]
  unit: string
}

// 省区涨跌数据响应
export interface ProvinceChangesResponse {
  current_value: number | null
  latest_date: string | null
  day5_change: number | null
  day10_change: number | null
  unit: string
}

/**
 * 获取所有有标肥价差数据的省区列表
 */
export function getFatStdSpreadProvinces(): Promise<ProvinceSpreadListResponse> {
  return request({
    url: '/v1/price-display/fat-std-spread/provinces',
    method: 'get'
  })
}

/**
 * 获取指定省区的标肥价差季节性数据
 */
export function getFatStdSpreadProvinceSeasonality(
  provinceName: string,
  startYear?: number,
  endYear?: number
): Promise<SeasonalityResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: `/v1/price-display/fat-std-spread/province/${provinceName}/seasonality`,
    method: 'get',
    params
  })
}

/**
 * 获取指定省区标肥价差的涨跌数据
 */
export function getFatStdSpreadProvinceChanges(
  provinceName: string
): Promise<ProvinceChangesResponse> {
  return request({
    url: `/v1/price-display/fat-std-spread/province/${provinceName}/changes`,
    method: 'get'
  })
}

// 区域价差涨跌数据响应
export interface RegionSpreadChangesResponse {
  current_value: number | null
  latest_date: string | null
  day5_change: number | null
  day10_change: number | null
  unit: string
}

/**
 * 获取区域价差季节性数据
 */
export function getRegionSpreadSeasonality(
  regionPair: string,
  startYear?: number,
  endYear?: number
): Promise<SeasonalityResponse> {
  const params: any = { region_pair: regionPair }
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: '/v1/price-display/region-spread/seasonality',
    method: 'get',
    params
  })
}

/**
 * 获取区域价差涨跌数据
 */
export function getRegionSpreadChanges(
  regionPair: string
): Promise<RegionSpreadChangesResponse> {
  return request({
    url: '/v1/price-display/region-spread/changes',
    method: 'get',
    params: { region_pair: regionPair }
  })
}

// 毛白价差双轴数据响应
export interface LiveWhiteSpreadDualAxisResponse {
  spread_data: Array<{
    date: string
    value: number | null
  }>
  ratio_data: Array<{
    date: string
    value: number | null
  }>
  spread_unit: string
  ratio_unit: string
  update_time: string | null
  latest_date: string | null
}

/**
 * 获取毛白价差双轴数据
 */
export function getLiveWhiteSpreadDualAxis(
  startDate?: string,
  endDate?: string
): Promise<LiveWhiteSpreadDualAxisResponse> {
  const params: any = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  
  return request({
    url: '/v1/price-display/live-white-spread/dual-axis',
    method: 'get',
    params
  })
}

// 冻品库容率省份信息
export interface FrozenInventoryProvinceInfo {
  province_name: string
  metric_id: number
  latest_date: string | null
  latest_value: number | null
}

export interface FrozenInventoryProvinceListResponse {
  provinces: FrozenInventoryProvinceInfo[]
  unit: string
}

// 冻品库容率季节性数据响应（包含涨跌信息）
export interface FrozenInventorySeasonalityResponse {
  metric_name: string
  unit: string
  province_name: string
  series: SeasonalitySeries[]
  update_time: string | null
  latest_date: string | null
  period_change: number | null  // 本期涨跌（较上期）
  yoy_change: number | null  // 较去年同期涨跌
}

/**
 * 获取所有有冻品库容率数据的省份列表
 */
export function getFrozenInventoryProvinces(): Promise<FrozenInventoryProvinceListResponse> {
  return request({
    url: '/v1/price-display/frozen-inventory/provinces',
    method: 'get'
  })
}

/**
 * 获取指定省份的冻品库容率季节性数据
 */
export function getFrozenInventoryProvinceSeasonality(
  provinceName: string,
  startYear?: number,
  endYear?: number
): Promise<FrozenInventorySeasonalityResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: `/v1/price-display/frozen-inventory/province/${provinceName}/seasonality`,
    method: 'get',
    params
  })
}

// 产业链数据季节性数据响应（包含涨跌信息）
export interface IndustryChainSeasonalityResponse {
  metric_name: string
  unit: string
  series: SeasonalitySeries[]
  update_time: string | null
  latest_date: string | null
  period_change: number | null  // 本期涨跌（较上期）
  yoy_change: number | null  // 较去年同期涨跌
}

/**
 * 获取产业链数据季节性数据（周度1-52周）
 * 
 * 支持的指标：
 * - 二元母猪价格
 * - 仔猪价格
 * - 淘汰母猪价格
 * - 淘汰母猪折扣率
 * - 猪料比
 * - 屠宰利润
 * - 自养利润
 * - 代养利润
 * - 白条价格
 * - 1#鲜肉价格
 * - 2#冻肉价格
 * - 4#冻肉价格
 * - 2号冻肉/1#鲜肉
 * - 4#冻肉/白条
 */
export function getIndustryChainSeasonality(
  metricName: string,
  startYear?: number,
  endYear?: number
): Promise<IndustryChainSeasonalityResponse> {
  const params: any = {
    metric_name: metricName
  }
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: `/v1/price-display/industry-chain/seasonality`,
    method: 'get',
    params
  })
}

// 省份指标数据响应
export interface ProvinceIndicatorsResponse {
  province_name: string
  indicators: Record<string, SeasonalityResponse>  // key: 指标名称, value: 季节性数据
}

/**
 * 获取指定省份的6个指标季节性数据
 * 
 * 6个指标：
 * 1. 日度 均价
 * 2. 日度 散户标肥价差
 * 3. 周度 出栏均重
 * 4. 周度 宰后均重
 * 5. 周度 90KG占比
 * 6. 周度 冻品库容
 */
export function getProvinceIndicatorsSeasonality(
  provinceName: string,
  startYear?: number,
  endYear?: number
): Promise<ProvinceIndicatorsResponse> {
  const params: any = {}
  if (startYear) params.start_year = startYear
  if (endYear) params.end_year = endYear
  
  return request({
    url: `/v1/price-display/province-indicators/${provinceName}/seasonality`,
    method: 'get',
    params
  })
}
