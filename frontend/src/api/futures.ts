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
  }
}
