import request from './request'

export interface TemplateInfo {
  id: number
  name: string
  chart_type: string | null
  is_public: boolean
  owner_id: number | null
  created_at: string
}

export interface TemplateDetail extends TemplateInfo {
  spec_json: any  // ChartSpec JSON
}

export interface TemplateCreate {
  name: string
  chart_type: 'seasonality' | 'timeseries'
  spec_json: any
  is_public?: boolean
}

export interface TemplateUpdate {
  name?: string
  spec_json?: any
  is_public?: boolean
}

export const templatesApi = {
  // 获取模板列表
  getTemplates: (scope: 'mine' | 'public' | 'all' = 'mine', chartType?: string) => {
    return request.get<TemplateInfo[]>('/templates', {
      params: {
        scope,
        chart_type: chartType
      }
    })
  },
  
  // 获取预设模板列表（8套）
  getPresetTemplates: () => {
    return request.get<any[]>('/templates/preset')
  },
  
  // 获取单个预设模板
  getPresetTemplate: (templateId: string) => {
    return request.get<any>(`/templates/preset/${templateId}`)
  },
  
  // 执行预设模板
  executePresetTemplate: (templateId: string, params: Record<string, any>) => {
    return request.post<any>(`/templates/preset/${templateId}/execute`, {
      params
    })
  },
  
  // 初始化预设模板到数据库（仅admin）
  initPresetTemplates: () => {
    return request.post('/templates/init-preset')
  },
  
  // 获取模板详情
  getTemplate: (id: number) => {
    return request.get<TemplateDetail>(`/templates/${id}`)
  },
  
  // 创建模板
  createTemplate: (data: TemplateCreate) => {
    return request.post<TemplateDetail>('/templates', data)
  },
  
  // 更新模板
  updateTemplate: (id: number, data: TemplateUpdate) => {
    return request.put<TemplateDetail>(`/templates/${id}`, data)
  },
  
  // 删除模板
  deleteTemplate: (id: number) => {
    return request.delete(`/templates/${id}`)
  }
}
