/**
 * Results service - EndOfSection & Summary APIs
 */
import apiClient from './api';

export interface SessionResult {
  session_id: number;
  candidate_id?: number;
  mode: string;
  session_type: string;
  score: {
    value: number | null;
    initial_value: number | null;
    is_passed: boolean | null;
    deductions: Array<{ time: string; deduction: number; reason: string }>;
  };
  local_errors: ErrorItem[];
  global_errors: ErrorItem[];
}

export interface ErrorItem {
  id: number;
  type: string;
  description: string;
  severity: number;
  deduction: number;
  timestamp?: string;
  snapshot_path?: string;
  video_path?: string;
  video_start_time?: number;
  video_end_time?: number;
}

export interface SummaryItem {
  id: number;
  candidate_id?: number;
  mode: string;
  session_type: string;
  started_at?: string;
  ended_at?: string;
  score?: number;
  is_passed?: boolean;
}

export const resultsService = {
  getSessionResult: async (sessionId: number): Promise<SessionResult> => {
    const response = await apiClient.get(`/api/results/session/${sessionId}`);
    return response.data;
  },

  listSessions: async (limit = 50): Promise<SummaryItem[]> => {
    const response = await apiClient.get('/api/results/sessions', { params: { limit } });
    return response.data;
  },

  getSummary: async (limit = 100): Promise<SummaryItem[]> => {
    const response = await apiClient.get('/api/results/summary', { params: { limit } });
    return response.data;
  },

  deleteSession: async (sessionId: number): Promise<void> => {
    await apiClient.delete(`/api/results/session/${sessionId}`);
  },
};

