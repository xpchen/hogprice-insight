/**
 * SQL生成工具函数
 * 用于在数据缺失时生成INSERT SQL语句
 */

export interface MetricConfig {
  metric_key: string
  metric_name: string
  source_code: string
  sheet_name: string
  unit?: string
  tags?: Record<string, any>
  geo_code?: string
}

export interface SQLGenerationOptions {
  start_date: string
  end_date: string
  sample_count?: number // 生成示例数据的数量
  batch_id?: number
}

/**
 * 生成INSERT SQL语句
 */
export function generateInsertSQL(
  config: MetricConfig,
  options: SQLGenerationOptions
): string {
  const {
    metric_key,
    metric_name,
    source_code,
    sheet_name,
    unit,
    tags = {},
    geo_code
  } = config

  const {
    start_date,
    end_date,
    sample_count = 10,
    batch_id = 1
  } = options

  // 生成示例数据
  const values: string[] = []
  const start = new Date(start_date)
  const end = new Date(end_date)
  const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
  const step = Math.max(1, Math.floor(days / sample_count))

  for (let i = 0; i < sample_count; i++) {
    const currentDate = new Date(start)
    currentDate.setDate(start.getDate() + i * step)
    
    if (currentDate > end) break

    const dateStr = currentDate.toISOString().split('T')[0]
    
    // 生成示例值（可以根据实际需求调整）
    const sampleValue = generateSampleValue(metric_key, i)
    
    // 构建tags_json
    const tagsJson = JSON.stringify(tags)
    
    // 构建dedup_key
    const dedupKey = generateDedupKey(source_code, sheet_name, metric_key, geo_code || 'NATION', dateStr, tags)
    
    // 构建geo_id子查询
    const geoIdQuery = geo_code 
      ? `(SELECT id FROM dim_geo WHERE province = '${geo_code}' LIMIT 1)`
      : 'NULL'
    
    const value = `(${batch_id}, (SELECT id FROM dim_metric WHERE metric_key = '${metric_key}' LIMIT 1), '${dateStr}', ${sampleValue}, ${geoIdQuery}, '${tagsJson}', SHA1('${dedupKey}'), NOW())`
    values.push(value)
  }

  const sql = `-- ${metric_name} 示例数据
-- 数据源: ${source_code}
-- Sheet: ${sheet_name}
-- 指标: ${metric_key}
-- 时间范围: ${start_date} 至 ${end_date}
-- 单位: ${unit || 'N/A'}

INSERT INTO fact_observation (batch_id, metric_id, obs_date, value, geo_id, tags_json, dedup_key, created_at)
VALUES 
${values.join(',\n')};

-- 如果需要同时插入标签表
INSERT INTO fact_observation_tag (observation_id, tag_key, tag_value)
SELECT id, tag_key, tag_value
FROM fact_observation fo
CROSS JOIN JSON_TABLE(
  fo.tags_json,
  '$' COLUMNS (
    tag_key VARCHAR(64) PATH '$.key',
    tag_value VARCHAR(128) PATH '$.value'
  )
) AS jt
WHERE fo.metric_id = (SELECT id FROM dim_metric WHERE metric_key = '${metric_key}' LIMIT 1)
  AND fo.obs_date >= '${start_date}' 
  AND fo.obs_date <= '${end_date}'
  AND NOT EXISTS (
    SELECT 1 FROM fact_observation_tag fot 
    WHERE fot.observation_id = fo.id AND fot.tag_key = jt.tag_key
  );
`

  return sql
}

/**
 * 生成示例值（根据指标类型）
 */
function generateSampleValue(metricKey: string, index: number): number {
  // 价格类指标：10-20元/公斤
  if (metricKey.includes('PRICE') || metricKey.includes('价格')) {
    return (10 + Math.random() * 10).toFixed(2)
  }
  
  // 屠宰量类指标：1000-10000头
  if (metricKey.includes('SLAUGHTER') || metricKey.includes('屠宰')) {
    return Math.floor(1000 + Math.random() * 9000)
  }
  
  // 均重类指标：100-150kg
  if (metricKey.includes('WEIGHT') || metricKey.includes('均重')) {
    return (100 + Math.random() * 50).toFixed(2)
  }
  
  // 价差类指标：-2到2元/公斤
  if (metricKey.includes('SPREAD') || metricKey.includes('价差')) {
    return (-2 + Math.random() * 4).toFixed(2)
  }
  
  // 占比类指标：0-100%
  if (metricKey.includes('RATIO') || metricKey.includes('占比')) {
    return (Math.random() * 100).toFixed(2)
  }
  
  // 默认：10-100
  return (10 + Math.random() * 90).toFixed(2)
}

/**
 * 生成去重键
 */
function generateDedupKey(
  sourceCode: string,
  sheetName: string,
  metricKey: string,
  geoCode: string,
  dateStr: string,
  tags: Record<string, any>
): string {
  const canonicalTags = Object.keys(tags)
    .sort()
    .map(key => `${key}=${tags[key]}`)
    .join('|')
  
  return `${sourceCode}|${sheetName}|${metricKey}|${geoCode}|${dateStr}|${canonicalTags}`
}

/**
 * 批量生成多个指标的SQL
 */
export function generateBatchSQL(
  configs: MetricConfig[],
  options: SQLGenerationOptions
): string {
  const sqls = configs.map(config => generateInsertSQL(config, options))
  return sqls.join('\n\n')
}

/**
 * 下载SQL文件
 */
export function downloadSQL(sql: string, filename: string = 'insert_data.sql'): void {
  const blob = new Blob([sql], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
