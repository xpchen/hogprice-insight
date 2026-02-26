/**
 * 全国重点数据API
 */
import request from './request'
import { queryObservations, ObservationResponse } from './observation'

export interface NationalPriceData {
  priceData: ObservationResponse[] // 全国出栏均价
  spreadData: ObservationResponse[] // 标肥价差
  slaughterData: ObservationResponse[] // 日度屠宰量
}

export interface WeightData {
  preSlaughterWeight: ObservationResponse[] // 宰前均重
  outWeight: ObservationResponse[] // 出栏均重
  scaleFarmWeight: ObservationResponse[] // 规模场出栏均重
  retailWeight: ObservationResponse[] // 散户出栏均重
  weight90kgRatio: ObservationResponse[] // 90kg占比
  weight150kgRatio: ObservationResponse[] // 150kg占比
}

export interface SlaughterData {
  slaughterData: ObservationResponse[] // 日度屠宰量
  priceData: ObservationResponse[] // 价格数据（用于量价走势）
}

/**
 * 获取全国价格数据
 */
export async function getNationalPriceData(
  startDate: string,
  endDate: string
): Promise<NationalPriceData> {
  const [priceData, spreadData, slaughterData] = await Promise.all([
    // 全国出栏均价（涌益日度）
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_D_PRICE_NATION_AVG',
      start_date: startDate,
      end_date: endDate,
      period_type: 'day'
    }),
    // 标肥价差（钢联）
    queryObservations({
      source_code: 'GANGLIAN',
      metric_key: 'GL_D_FAT_STD_SPREAD',
      start_date: startDate,
      end_date: endDate,
      period_type: 'day'
    }),
    // 日度屠宰量（涌益日度）
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_D_SLAUGHTER_TOTAL_1',
      start_date: startDate,
      end_date: endDate,
      period_type: 'day'
    })
  ])

  return {
    priceData: priceData || [],
    spreadData: spreadData || [],
    slaughterData: slaughterData || []
  }
}

/**
 * 获取均重数据
 */
export async function getWeightData(
  startDate: string,
  endDate: string
): Promise<WeightData> {
  const [
    preSlaughterWeight,
    outWeight,
    scaleFarmWeight,
    retailWeight,
    weight90kgRatio,
    weight150kgRatio
  ] = await Promise.all([
    // 图1：宰前均重 - sheet表：周度-屠宰厂宰前活猪重，AD列全国平均值
    // 查询全国平均值（geo_code为NATION或没有省份标签）
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_SLAUGHTER_PRELIVE_WEIGHT',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      geo_code: 'NATION'
    }),
    // 图2：出栏均重 - sheet表：周度-体重 X列 全国2
    // 查询indicator='均重'且geo_code='NATION'的数据（全国数据）
    // 注意：数据库中nation_col可能为NULL，所以不筛选nation_col
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_OUT_WEIGHT',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      indicator: '均重',
      geo_code: 'NATION'
    }),
    // 图3：规模场 出栏均重 - sheet表：周度-体重拆分 C列 集团
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_WEIGHT_GROUP',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      tag_key: 'crowd',
      tag_value: '集团'
    }),
    // 图4：散户 出栏均重 - sheet表：周度-体重拆分 D列 散户
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_WEIGHT_SCATTER',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      tag_key: 'crowd',
      tag_value: '散户'
    }),
    // 图5：90Kg出栏占比 - sheet表：周度-体重 X列 全国2
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_OUT_WEIGHT',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      indicator: '90Kg出栏占比',
      geo_code: 'NATION'
    }),
    // 图6：150Kg出栏占重 - sheet表：周度-体重 X列 全国2
    queryObservations({
      source_code: 'YONGYI',
      metric_key: 'YY_W_OUT_WEIGHT',
      start_date: startDate,
      end_date: endDate,
      period_type: 'week',
      indicator: '150Kg出栏占重',
      geo_code: 'NATION'
    })
  ])

  return {
    preSlaughterWeight: preSlaughterWeight || [],
    outWeight: outWeight || [],
    scaleFarmWeight: scaleFarmWeight || [],
    retailWeight: retailWeight || [],
    weight90kgRatio: weight90kgRatio || [],
    weight150kgRatio: weight150kgRatio || []
  }
}

/**
 * 获取日度屠宰量数据（用于 A3 屠宰量&价格 图表）
 * 屠宰量与价格均来自涌益日度「价格+宰量」sheet：
 * - 屠宰量：YY_D_SLAUGHTER_TOTAL_1（日屠宰量合计1）
 * - 价格：YY_D_PRICE_NATION_AVG（全国均价）
 */
export async function getSlaughterData(
  startDate: string,
  endDate: string
): Promise<SlaughterData> {
  const limit = 2000 // 3 年日度约 1100 条，留余量
  const timeout = 600000 // 10分钟超时，数据量大时避免超时
  const [slaughterData, priceData] = await Promise.all([
    // 日度屠宰量（价格+宰量 sheet）
    queryObservations(
      {
        source_code: 'YONGYI',
        metric_key: 'YY_D_SLAUGHTER_TOTAL_1',
        start_date: startDate,
        end_date: endDate,
        period_type: 'day',
        limit
      },
      { timeout }
    ),
    // 全国均价（同一 sheet，保证日期一致）
    queryObservations(
      {
        source_code: 'YONGYI',
        metric_key: 'YY_D_PRICE_NATION_AVG',
        start_date: startDate,
        end_date: endDate,
        period_type: 'day',
        limit
      },
      { timeout }
    )
  ])

  return {
    slaughterData: slaughterData || [],
    priceData: priceData || []
  }
}
