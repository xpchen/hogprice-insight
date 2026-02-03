import request from './request'

export interface DashboardCard {
  card_id: string
  title: string
  chart_type: string
  data: any
  update_time: string
  config: any
}

export interface DashboardResponse {
  cards: DashboardCard[]
  global_filters: {
    date_range: {
      start: string
      end: string
    }
    regions: string[]
    years: number[]
  }
}

export const dashboardApi = {
  getDefaultDashboard: (): Promise<DashboardResponse> => {
    return request.get('/dashboard/default')
  }
}
