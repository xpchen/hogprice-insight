import request from './request'

export interface FuturesDailyResponse {
  contract_code: string
  series: Array<{
    date: string
    open: number | null
    high: number | null
    low: number | null
    close: number | null
    settle: number | null
    volume: number | null
    open_interest: number | null
  }>
}

export interface PremiumDataPoint {
  date: string
  futures_settle: number | null
  spot_price: number | null
  premium: number | null
}

export interface PremiumSeries {
  contract_month: number
  contract_name: string
  data: PremiumDataPoint[]
}

export interface PremiumResponse {
  series: PremiumSeries[]
  update_time: string | null
}

export interface PremiumDataPointV2 {
  date: string
  futures_settle: number | null
  spot_price: number | null
  premium: number | null
  premium_ratio?: number | null
  year?: number | null
}

export interface PremiumSeriesV2 {
  contract_month: number
  contract_name: string
  region: string
  data: PremiumDataPointV2[]
}

export interface PremiumResponseV2 {
  series: PremiumSeriesV2[]
  region_premiums: Record<string, number>
  update_time: string | null
}

export interface CalendarSpreadDataPoint {
  date: string
  near_contract_settle: number | null
  far_contract_settle: number | null
  spread: number | null
}

export interface CalendarSpreadSeries {
  spread_name: string
  near_month: number
  far_month: number
  data: CalendarSpreadDataPoint[]
}

export interface CalendarSpreadResponse {
  series: CalendarSpreadSeries[]
  update_time: string | null
}

export interface RegionPremiumData {
  region: string
  contract_month: number
  contract_name: string
  spot_price: number | null
  futures_settle: number | null
  premium: number | null
  date: string
}

export interface RegionPremiumResponse {
  data: RegionPremiumData[]
  update_time: string | null
}

export interface VolatilityDataPoint {
  date: string
  close_price: number | null
  volatility: number | null
  year?: number | null
}

export interface VolatilitySeries {
  contract_code: string
  contract_month: number
  data: VolatilityDataPoint[]
}

export interface VolatilityResponse {
  series: VolatilitySeries[]
  update_time: string | null
}

export const futuresApi = {
  getFuturesDaily: (params: {
    contract: string
    from_date?: string
    to_date?: string
  }): Promise<FuturesDailyResponse> => {
    return request.get('/futures/daily', { params })
  },

  getMainContract: (date?: string): Promise<any> => {
    return request.get('/futures/main', { params: { date } })
  },

  getPremium: (params: {
    contract_month?: number
    start_year?: number
    end_year?: number
  }): Promise<PremiumResponse> => {
    return request.get('/futures/premium', { params })
  },

  getCalendarSpread: (params: {
    spread_pair?: string
    start_year?: number
    end_year?: number
  }): Promise<CalendarSpreadResponse> => {
    return request.get('/futures/calendar-spread', { params })
  },

  getRegionPremium: (params: {
    contract_month: number
    regions?: string
    trade_date?: string
  }): Promise<RegionPremiumResponse> => {
    return request.get('/futures/region-premium', { params })
  },

  getVolatility: (params: {
    contract_month?: number
    min_volatility?: number
    max_volatility?: number
    start_date?: string
    end_date?: string
  }): Promise<VolatilityResponse> => {
    return request.get('/futures/volatility', { params })
  },

  getPremiumV2: (params: {
    contract_month?: number
    region?: string
    view_type?: string
    format_type?: string
  }): Promise<PremiumResponseV2> => {
    return request.get('/futures/premium/v2', { params })
  }
}
