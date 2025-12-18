import axios from 'axios'
import { toast } from 'react-toastify'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add JWT token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
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
    multi_person_enabled?: boolean
    error_thresholds?: Record<string, number>
    error_grouping?: Record<string, any>
    difficulty_level?: string
    scoring_criterion?: string
    app_mode?: string
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

// Auth API
export const authAPI = {
  register: async (data: {
    username: string
    password: string
    full_name?: string
    age?: number
    rank?: string
    insignia?: string
    gender?: string
  }) => {
    const response = await api.post('/api/auth/register', data)
    return response.data
  },

  login: async (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    // Save token
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token)
      localStorage.setItem('user', JSON.stringify(response.data.user))
    }
    return response.data
  },

  logout: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  },

  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me')
    return response.data
  },

  changePassword: async (oldPassword: string, newPassword: string) => {
    const response = await api.post('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
    return response.data
  },
}

// Candidates API
export const candidatesAPI = {
  getCandidates: async (skip = 0, limit = 100, isActive?: boolean) => {
    const params = new URLSearchParams()
    params.append('skip', skip.toString())
    params.append('limit', limit.toString())
    if (isActive !== undefined) {
      params.append('is_active', isActive.toString())
    }
    const response = await api.get(`/api/candidates?${params}`)
    return response.data
  },

  getCandidate: async (candidateId: string) => {
    const response = await api.get(`/api/candidates/${candidateId}`)
    return response.data
  },

  createCandidate: async (data: {
    full_name: string
    age?: number
    gender?: string
    rank?: string
    insignia?: string
    avatar_path?: string
    notes?: string
  }) => {
    const response = await api.post('/api/candidates', data)
    return response.data
  },

  updateCandidate: async (candidateId: string, data: {
    full_name?: string
    age?: number
    gender?: string
    rank?: string
    insignia?: string
    avatar_path?: string
    notes?: string
    is_active?: boolean
  }) => {
    const response = await api.put(`/api/candidates/${candidateId}`, data)
    return response.data
  },

  deleteCandidate: async (candidateId: string) => {
    const response = await api.delete(`/api/candidates/${candidateId}`)
    return response.data
  },

  importExcel: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/api/candidates/import-excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// Barem API
export const baremAPI = {
  getBarem: async () => {
    const response = await api.get('/api/barem')
    return response.data
  },

  getWeights: async () => {
    const response = await api.get('/api/barem/weights')
    return response.data
  },

  getThresholds: async () => {
    const response = await api.get('/api/barem/thresholds')
    return response.data
  },
}

// Local Mode API (Làm chậm)
export const localModeAPI = {
  startSession: async (sessionId: string, mode: 'testing' | 'practising', candidateId?: string) => {
    const formData = new FormData()
    formData.append('mode', mode)
    if (candidateId) {
      formData.append('candidate_id', candidateId)
    }
    const response = await api.post(`/api/local/${sessionId}/start`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

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

    const response = await api.post(`/api/local/${sessionId}/process-frame`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getScore: async (sessionId: string) => {
    const response = await api.get(`/api/local/${sessionId}/score`)
    return response.data
  },

  getErrors: async (sessionId: string) => {
    const response = await api.get(`/api/local/${sessionId}/errors`)
    return response.data
  },

  resetSession: async (sessionId: string) => {
    const response = await api.post(`/api/local/${sessionId}/reset`)
    return response.data
  },

  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/api/local/${sessionId}`)
    return response.data
  },
}

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api

