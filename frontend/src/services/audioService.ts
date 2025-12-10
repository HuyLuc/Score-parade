/**
 * Audio service - Xử lý phát nhạc
 */
import apiClient from './api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Lấy URL audio cho lệnh
export const getCommandAudio = (command: string): string | null => {
  return `${API_BASE_URL}/static/audio/command/${command}.mp3`;
};

// Lấy URL audio cho mode
export const getModeAudio = (
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
};

// Phát audio
export const playAudio = (audioUrl: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const audio = new Audio(audioUrl);
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error('Lỗi phát audio'));
    audio.play();
  });
};

export const audioService = { getCommandAudio, getModeAudio, playAudio };
export default audioService;

