/**
 * Global service - API calls cho Global Mode (Tổng hợp)
 */
import apiClient from './api';

export interface ProcessFrameRequest {
  camera_id: number;
  session_id: number;
  timestamp: number;  // Timestamp của frame (giây)
}

export interface ProcessFrameResponse {
  errors: ErrorInfo[];
  score_deduction: number;
  new_score: number;
  is_failed: boolean;
}

export interface ErrorInfo {
  type: string;
  description: string;
  severity: number;
  deduction: number;
  timestamp?: number;
  video_path?: string;
  video_start_time?: number;
  video_end_time?: number;
}

export interface ErrorNotification {
  id: number;
  type: string;
  description: string;
  timestamp: string;
  video_path?: string;
  video_start_time?: number;
  video_end_time?: number;
}

export interface ScoreInfo {
  value: number;
  initial_value: number;
  is_passed: boolean;
  deductions: Array<{
    time: string;
    deduction: number;
    reason: string;
  }>;
}

export const globalService = {
  // Xử lý một frame
  processFrame: async (request: ProcessFrameRequest): Promise<ProcessFrameResponse> => {
    const response = await apiClient.post('/api/global/process-frame', request);
    return response.data;
  },

  // Lấy danh sách lỗi (cho Practising mode)
  getErrorNotifications: async (sessionId: number): Promise<ErrorNotification[]> => {
    const response = await apiClient.get(`/api/global/${sessionId}/notifications`);
    return response.data;
  },

  // Lấy điểm hiện tại
  getCurrentScore: async (sessionId: number): Promise<ScoreInfo> => {
    const response = await apiClient.get(`/api/global/${sessionId}/score`);
    return response.data;
  },
};

