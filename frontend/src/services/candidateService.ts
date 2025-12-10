/**
 * Candidate service - API calls cho candidates
 */
import apiClient from './api';

export interface Candidate {
  id: number;
  name: string;
  code?: string;
  age?: number;
  gender?: string;
  unit?: string;
  notes?: string;
  status: string;
  created_at: string;
}

export interface CandidateCreate {
  name: string;
  code?: string;
  age?: number;
  gender?: string;
  unit?: string;
  notes?: string;
}

export interface ImportResponse {
  success: boolean;
  created_count: number;
  errors: string[];
  candidates: Candidate[];
}

export const candidateService = {
  // Lấy tất cả candidates
  getAll: async (): Promise<Candidate[]> => {
    const response = await apiClient.get('/api/candidates/');
    return response.data;
  },

  // Lấy candidate theo ID
  getById: async (id: number): Promise<Candidate> => {
    const response = await apiClient.get(`/api/candidates/${id}`);
    return response.data;
  },

  // Tạo candidate mới
  create: async (data: CandidateCreate): Promise<Candidate> => {
    const response = await apiClient.post('/api/candidates/', data);
    return response.data;
  },

  // Cập nhật candidate
  update: async (id: number, data: Partial<CandidateCreate>): Promise<Candidate> => {
    const response = await apiClient.put(`/api/candidates/${id}`, data);
    return response.data;
  },

  // Xóa candidate
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/candidates/${id}`);
  },

  // Import từ Excel
  import: async (file: File): Promise<ImportResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/api/candidates/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Chọn candidate
  select: async (id: number): Promise<Candidate> => {
    const response = await apiClient.post(`/api/candidates/${id}/select`);
    return response.data;
  },
};

