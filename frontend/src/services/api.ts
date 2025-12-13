import axios from 'axios'
import { toast } from 'react-toastify'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Có lỗi xảy ra'
    toast.error(message)
    return Promise.reject(error)
  }
)

// Global Mode API
export const globalModeAPI = {
  // Start a session
  startSession: async (sessionId: string, mode: 'testing' | 'practising', audioFile?: File, audioPath?: string) => {
    const formData = new FormData()
    formData.append('mode', mode)
    if (audioFile) {
      formData.append('audio_file', audioFile)
    }
    if (audioPath) {
      formData.append('audio_path', audioPath)
    }
    
    const response = await api.post(`/api/global/${sessionId}/start`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Process a frame
  processFrame: async (
    sessionId: string,
    frameData: Blob,
    timestamp: number,
    frameNumber: number
  ) => {
    const formData = new FormData()
    formData.append('frame_data', frameData, 'frame.jpg')
    formData.append('timestamp', timestamp.toString())
    formData.append('frame_number', frameNumber.toString())

    const response = await api.post(`/api/global/${sessionId}/process-frame`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Get current score
  getScore: async (sessionId: string) => {
    const response = await api.get(`/api/global/${sessionId}/score`)
    return response.data
  },

  // Get all errors
  getErrors: async (sessionId: string) => {
    const response = await api.get(`/api/global/${sessionId}/errors`)
    return response.data
  },

  // Reset session
  resetSession: async (sessionId: string) => {
    const response = await api.post(`/api/global/${sessionId}/reset`)
    return response.data
  },

  // Delete session
  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/api/global/${sessionId}`)
    return response.data
  },
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api

