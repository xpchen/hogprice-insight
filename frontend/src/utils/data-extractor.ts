/**
 * 数据抽取工具函数
 * 用于从数据库查询数据，如果没有数据则生成INSERT SQL
 */

import { queryObservations, ObservationResponse } from '@/api/observation'
import { generateInsertSQL, downloadSQL, MetricConfig, SQLGenerationOptions } from './sql-generator'

export interface DataExtractionResult {
  hasData: boolean
  data: ObservationResponse[]
  sql?: string
  message?: string
}

/**
 * 抽取数据
 * 如果数据库中有数据则返回数据，否则生成INSERT SQL
 */
export async function extractData(
  config: MetricConfig,
  options: SQLGenerationOptions
): Promise<DataExtractionResult> {
  try {
    // 查询数据库
    const data = await queryObservations({
      source_code: config.source_code,
      metric_key: config.metric_key,
      start_date: options.start_date,
      end_date: options.end_date,
      geo_code: config.geo_code,
      limit: 1000
    })

    if (data && data.length > 0) {
      return {
        hasData: true,
        data: data,
        message: `找到 ${data.length} 条数据`
      }
    } else {
      // 没有数据，生成INSERT SQL
      const sql = generateInsertSQL(config, options)
      return {
        hasData: false,
        data: [],
        sql: sql,
        message: '数据库中没有数据，已生成INSERT SQL语句'
      }
    }
  } catch (error: any) {
    console.error('数据抽取失败:', error)
    // 即使查询失败，也生成SQL作为备选
    const sql = generateInsertSQL(config, options)
    return {
      hasData: false,
      data: [],
      sql: sql,
      message: `数据查询失败: ${error.message}，已生成INSERT SQL语句`
    }
  }
}

/**
 * 批量抽取多个指标的数据
 */
export async function extractBatchData(
  configs: MetricConfig[],
  options: SQLGenerationOptions
): Promise<DataExtractionResult[]> {
  const results = await Promise.all(
    configs.map(config => extractData(config, options))
  )
  return results
}

/**
 * 下载生成的SQL文件
 */
export function downloadExtractedSQL(
  result: DataExtractionResult,
  filename?: string
): void {
  if (result.sql) {
    const defaultFilename = filename || `insert_${new Date().toISOString().split('T')[0]}.sql`
    downloadSQL(result.sql, defaultFilename)
  }
}
