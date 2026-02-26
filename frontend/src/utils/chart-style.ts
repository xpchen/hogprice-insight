/**
 * 图表样式统一配置：图例圆点、坐标轴小数、年份颜色等
 */

/** axisLabel 内不显示最大/最小刻度（ECharts 要求在此层级） */
export const axisLabelHideMinMax = { showMinLabel: false, showMaxLabel: false }

/** @deprecated 请使用 axisLabel: { ...axisLabelHideMinMax, formatter } 合并到 axisLabel */
export const yAxisHideMinMaxLabel = { axisLabel: { showMinLabel: false, showMaxLabel: false } }

/** 图例圆点配置（参照 A2.均重） */
export const legendCircleConfig = {
  icon: 'circle' as const,
  itemWidth: 10,
  itemHeight: 10,
  itemGap: 15,
  type: 'plain' as const
}

/** 数值轴标签：整数原样，小数保留两位 */
export function axisLabelDecimalFormatter(value: number): string {
  if (Number.isInteger(value)) return String(value)
  return value.toFixed(2)
}

/** 数量轴标签：显示整数（出栏量、计划量等） */
export function axisLabelIntegerFormatter(value: number): string {
  return String(Math.round(value))
}

/** 百分比轴标签：保留两位小数 */
export function axisLabelPercentFormatter(value: number): string {
  if (Number.isInteger(value)) return `${value}%`
  return `${value.toFixed(2)}%`
}

/** 年份色板（循环使用，保证每年单独颜色） */
const yearPalette = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272',
  '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f', '#ffdb5c', '#c4ccd3',
  '#1E90FF', '#FF69B4', '#32CD32', '#FFA500', '#4169E1', '#FFB6C1'
]

const BASE_YEAR = 2019

/** 根据年份返回唯一颜色（全部年份单独颜色，无灰色） */
export function getYearColor(year: number): string {
  const idx = (year - BASE_YEAR) % yearPalette.length
  return yearPalette[idx >= 0 ? idx : (idx + yearPalette.length) % yearPalette.length]
}
