import request from './request'

export interface OptionsDailyResponse {
  option_code: string
  series: Array<{
    date: string
    option_code: string
    close: number | null
    settle: number | null
    delta: number | null
    iv: number | null
    volume: number | null
    open_interest: number | null
  }>
}

export const optionsApi = {
  getOptionsDaily: (params: {
    underlying: string
    type?: string
    strike?: number
    from_date?: string
    to_date?: string
  }): Promise<OptionsDailyResponse> => {
    return request.get('/options/daily', { params })
  }
}
