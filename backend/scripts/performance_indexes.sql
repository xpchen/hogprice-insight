-- =============================================================================
-- 核心表性能优化 SQL（基于 API 查询模式分析）
-- 执行前请确认索引名未与现有重复；若已存在可跳过或先 DROP INDEX。
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. fact_observation
-- 常见查询：metric_id + period_type + obs_date 范围，ORDER BY obs_date
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fact_obs_metric_period_date
ON fact_observation (metric_id, period_type, obs_date);

-- -----------------------------------------------------------------------------
-- 2. fact_futures_daily
-- 常见查询：按 trade_date 取当日主力（ORDER BY open_interest DESC）
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fact_futures_date_oi
ON fact_futures_daily (trade_date, open_interest DESC);

-- -----------------------------------------------------------------------------
-- 3. dim_metric
-- 常见查询：sheet_name + freq（如「分省区猪价」+ D/daily）
-- -----------------------------------------------------------------------------
CREATE INDEX idx_dim_metric_sheet_freq
ON dim_metric (sheet_name, freq);

-- -----------------------------------------------------------------------------
-- 4. raw_sheet
-- 常见查询：raw_file_id + sheet_name（JOIN RawFile 后按 sheet_name 过滤）
-- -----------------------------------------------------------------------------
CREATE INDEX idx_raw_sheet_file_name
ON raw_sheet (raw_file_id, sheet_name);

-- -----------------------------------------------------------------------------
-- 5. fact_indicator_ts
-- 常见查询：indicator_code + freq + trade_date / week_end 范围
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fact_indicator_ts_code_freq_date
ON fact_indicator_ts (indicator_code, freq, trade_date);

CREATE INDEX idx_fact_indicator_ts_code_freq_week
ON fact_indicator_ts (indicator_code, freq, week_end);

-- -----------------------------------------------------------------------------
-- 6. 更新表统计信息（建议在低峰期执行）
-- -----------------------------------------------------------------------------
ANALYZE TABLE fact_observation;
ANALYZE TABLE fact_futures_daily;
ANALYZE TABLE dim_metric;
ANALYZE TABLE fact_indicator_ts;
ANALYZE TABLE fact_indicator_metrics;
ANALYZE TABLE raw_sheet;
ANALYZE TABLE fact_observation_tag;
