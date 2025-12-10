/**
 * Local service - API calls cho Local Mode (Làm chậm)
 */
import apiClient from './api';

export interface ProcessFrameRequest {
  camera_id: number;
  session_id: number;
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
  body_part: string;
  side?: string;
  frame_number?: number;
  timestamp?: number;
  snapshot_path?: string;
}

export interface ErrorNotification {
  id: number;
  type: string;
  description: string;
  timestamp: string;
  snapshot_path?: string;
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

export const localService = {
  // Xử lý một frame
  processFrame: async (request: ProcessFrameRequest): Promise<ProcessFrameResponse> => {
    const response = await apiClient.post('/api/local/process-frame', request);
    return response.data;
  },

  // Lấy danh sách lỗi (cho Practising mode)
  getErrorNotifications: async (sessionId: number): Promise<ErrorNotification[]> => {
    const response = await apiClient.get(`/api/local/${sessionId}/notifications`);
    return response.data;
  },

  // Lấy điểm hiện tại
  getCurrentScore: async (sessionId: number): Promise<ScoreInfo> => {
    const response = await apiClient.get(`/api/local/${sessionId}/score`);
    return response.data;
  },
};

