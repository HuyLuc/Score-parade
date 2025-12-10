/**
 * Audio service - Xử lý phát nhạc
 */
import apiClient from './api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const audioService = {
  // Lấy URL audio cho lệnh
  getCommandAudio: (command: string): string | null => {
    // Tạm thời: trả về đường dẫn file
    // Trong thực tế, có thể lấy từ API hoặc static files
    return `${API_BASE_URL}/static/audio/command/${command}.mp3`;
  },

  // Lấy URL audio cho mode
  getModeAudio: (
    criteria: string,  // di_deu hoặc di_nghiem
    mode: string,  // local hoặc global
    practiceType: string  // testing hoặc practising
  ): string | null => {
    if (mode === 'local') {
      const suffix = practiceType === 'testing' ? 'short' : 'long';
      return `${API_BASE_URL}/static/audio/${criteria}/local/practising_${suffix}.mp3`;
    } else {
      return `${API_BASE_URL}/static/audio/${criteria}/global/total.mp3`;
    }
  },

  // Phát audio
  playAudio: (audioUrl: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const audio = new Audio(audioUrl);
      audio.onended = () => resolve();
      audio.onerror = () => reject(new Error('Lỗi phát audio'));
      audio.play();
    });
  },
};

