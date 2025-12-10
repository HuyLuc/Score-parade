/**
 * Configuration service - API calls cho configuration
 */
import apiClient from './api';

export interface Configuration {
  mode: string;  // testing hoặc practising
  criteria: string;  // di_deu hoặc di_nghiem
  difficulty: string;  // easy, normal, hard
  operation_mode: string;  // dev hoặc release
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export const configurationService = {
  // Lấy cấu hình hiện tại
  get: async (): Promise<Configuration> => {
    const response = await apiClient.get('/api/configuration/');
    return response.data;
  },

  // Cập nhật cấu hình
  update: async (config: Partial<Configuration>): Promise<Configuration> => {
    const response = await apiClient.put('/api/configuration/', config);
    return response.data;
  },

  // Đổi mật khẩu
  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await apiClient.post('/api/configuration/change-password', data);
  },
};

