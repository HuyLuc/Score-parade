/**
 * Camera service - API calls cho camera
 */
import apiClient from './api';

export interface CameraInfo {
  camera_id: number;
  width: number;
  height: number;
  fps: number;
  is_opened: boolean;
}

export interface SnapshotResponse {
  success: boolean;
  message: string;
  file_path?: string;
}

export const cameraService = {
  // Kết nối camera
  connect: async (cameraId: number): Promise<void> => {
    await apiClient.post('/api/camera/connect', { camera_id: cameraId });
  },

  // Ngắt kết nối camera
  disconnect: async (cameraId: number): Promise<void> => {
    await apiClient.post(`/api/camera/disconnect/${cameraId}`);
  },

  // Lấy thông tin tất cả cameras
  getInfo: async (): Promise<CameraInfo[]> => {
    const response = await apiClient.get('/api/camera/info');
    return response.data;
  },

  // Lấy frame từ camera (URL cho img src)
  getFrameUrl: (cameraId: number): string => {
    const baseURL = apiClient.defaults.baseURL || 'http://localhost:8000';
    return `${baseURL}/api/camera/${cameraId}/frame?t=${Date.now()}`;
  },

  // Chụp snapshot
  captureSnapshot: async (cameraId: number, sessionId?: number): Promise<SnapshotResponse> => {
    const response = await apiClient.post(`/api/camera/${cameraId}/snapshot`, null, {
      params: sessionId ? { session_id: sessionId } : {},
    });
    return response.data;
  },

  // Bắt đầu ghi video
  startRecording: async (cameraId: number, sessionId?: number): Promise<void> => {
    await apiClient.post(`/api/camera/${cameraId}/video/start`, null, {
      params: sessionId ? { session_id: sessionId } : {},
    });
  },

  // Dừng ghi video
  stopRecording: async (cameraId: number): Promise<{ success: boolean; message: string; file_path: string }> => {
    const response = await apiClient.post(`/api/camera/${cameraId}/video/stop`);
    return response.data;
  },
};

