import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 调试日志
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data || config.params)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 调试日志
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
    }
    return response.data
  },
  (error) => {
    // 调试日志
    if (import.meta.env.DEV) {
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      })
    }
    
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/7208489b-4a4f-4400-8c21-52139d8c0ebd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'request.ts:39',message:'API request error',data:{url:error.config?.url,method:error.config?.method,status:error.response?.status,statusText:error.response?.statusText,data:error.response?.data,message:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H1'})}).catch(()=>{});
    // #endregion
    
    // 401错误处理：只有在非登录页面时才自动跳转
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname
      // 如果不在登录页面，才清除token并跳转
      if (currentPath !== '/login') {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default request
