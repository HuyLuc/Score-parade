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
    // Check if we should suppress toast for this error
    const suppressToast = error.config?.suppressToast === true
    
    // Don't show toast for expected 404 errors when suppressToast is true
    if (suppressToast && error.response?.status === 404) {
      return Promise.reject(error)
    }
    
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
  getScore: async (sessionId: string, suppressToast: boolean = false) => {
    const response = await api.get(`/api/global/${sessionId}/score`, {
      suppressToast: suppressToast
    } as any)
    return response.data
  },

  // Get all errors
  getErrors: async (sessionId: string, suppressToast: boolean = false) => {
    const response = await api.get(`/api/global/${sessionId}/errors`, {
      suppressToast: suppressToast
    } as any)
    return response.data
  },

  // Reset session
  resetSession: async (sessionId: string) => {
    const response = await api.post(`/api/global/${sessionId}/reset`)
    return response.data
  },

  // Delete session
  deleteSession: async (sessionId: string, suppressToast: boolean = false) => {
    const response = await api.delete(`/api/global/${sessionId}`, {
      suppressToast: suppressToast
    } as any)
    return response.data
  },

  // Upload and process video
  uploadAndProcessVideo: async (sessionId: string, videoFile: File) => {
    const formData = new FormData()
    formData.append('video_file', videoFile)

    const response = await api.post(`/api/global/${sessionId}/upload-video`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// Config API
export const configAPI = {
  // Get scoring configuration
  getScoringConfig: async () => {
    const response = await api.get('/api/config/scoring')
    return response.data
  },

  // Update scoring configuration
  updateScoringConfig: async (config: {
    error_weights?: Record<string, number>
    initial_score?: number
    fail_threshold?: number
    error_thresholds?: Record<string, number>
    error_grouping?: Record<string, any>
  }) => {
    const response = await api.put('/api/config/scoring', config)
    return response.data
  },

  // Reset scoring configuration
  resetScoringConfig: async () => {
    const response = await api.post('/api/config/scoring/reset')
    return response.data
  },
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api

