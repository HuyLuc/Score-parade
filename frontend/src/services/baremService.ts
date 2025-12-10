/**
 * Barem service - API calls cho barem điểm
 */
import apiClient from './api';

export interface Criterion {
  id: number;
  content: string;
  weight: number;
  criterion_type: string;  // posture, rhythm, distance, speed
  applies_to?: string;  // di_deu, di_nghiem
}

export interface UpdateWeightRequest {
  criterion_id: number;
  weight: number;
}

export const baremService = {
  // Lấy tất cả criteria
  getAll: async (criteriaType?: string): Promise<Criterion[]> => {
    const params = criteriaType ? { criteria_type: criteriaType } : {};
    const response = await apiClient.get('/api/barem/', { params });
    return response.data;
  },

  // Lấy criteria theo loại
  getByType: async (type: string): Promise<Criterion[]> => {
    const response = await apiClient.get(`/api/barem/by-type/${type}`);
    return response.data;
  },

  // Cập nhật trọng số một criterion
  updateWeight: async (criterionId: number, weight: number): Promise<void> => {
    await apiClient.put(`/api/barem/weight/${criterionId}`, null, {
      params: { weight },
    });
  },

  // Cập nhật nhiều trọng số
  updateMultipleWeights: async (updates: UpdateWeightRequest[]): Promise<{ success: boolean; message: string; errors?: string[] }> => {
    const response = await apiClient.put('/api/barem/weights', { updates });
    return response.data;
  },
};

