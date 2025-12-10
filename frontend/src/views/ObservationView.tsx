/**
 * ObservationView - Màn hình chấm thí sinh
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import CameraView from '../components/CameraView';
import { candidateService, Candidate } from '../services/candidateService';
import { configurationService, Configuration } from '../services/configurationService';
import { getCommandAudio, getModeAudio } from '../services/audioService';
import { localService, ProcessFrameResponse, ErrorNotification } from '../services/localService';
import { globalService } from '../services/globalService';
import { cameraService } from '../services/cameraService';
import './ObservationView.css';

interface LocationState {
  candidateId?: number;
  sessionId?: number;
}

const ObservationView: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState;
  
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [config, setConfig] = useState<Configuration | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(state?.sessionId || null);
  const [showPopup, setShowPopup] = useState(true);
  const [camerasConnected, setCamerasConnected] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [localModeActive, setLocalModeActive] = useState(false);
  const [globalModeActive, setGlobalModeActive] = useState(false);
  const [currentScore, setCurrentScore] = useState(100);
  const [errors, setErrors] = useState<ErrorNotification[]>([]);
  const [isFailed, setIsFailed] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  
  const processingIntervalRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    loadData();
    return () => {
      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const loadData = async () => {
    try {
      // Load candidate
      if (state?.candidateId) {
        const candidateData = await candidateService.getById(state.candidateId);
        setCandidate(candidateData);
      }
      
      // Load configuration
      const configData = await configurationService.get();
      setConfig(configData);
    } catch (err: any) {
      console.error('Lỗi tải dữ liệu:', err);
    }
  };

  const handleConnectCameras = async () => {
    try {
      // Kết nối 2 cameras
      await cameraService.connect(0);
      await cameraService.connect(1);
      setCamerasConnected(true);
    } catch (err: any) {
      console.error('Lỗi kết nối camera:', err);
      alert('Lỗi kết nối camera: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleSelectCandidate = () => {
    // TODO: Hiển thị dialog chọn candidate
    // Tạm thời: dùng candidate từ state
    setShowPopup(false);
  };

  const handlePlayAudio = async () => {
    if (!config || !sessionId) return;

    try {
      setAudioPlaying(true);
      
      // Phát lệnh trước
      const commandAudio = getCommandAudio('nghiem_di_deu_buoc');
      if (commandAudio && audioRef.current) {
        audioRef.current.src = commandAudio;
        await new Promise((resolve) => {
          if (audioRef.current) {
            audioRef.current.onended = resolve;
            audioRef.current.play();
          }
        });
      }
      
      // Phát nhạc cho Local Mode
      const localAudio = getModeAudio(
        config.criteria,
        'local',
        config.mode
      );
      
      if (localAudio && audioRef.current) {
        audioRef.current.src = localAudio;
        await new Promise((resolve) => {
          if (audioRef.current) {
            audioRef.current.onended = resolve;
            audioRef.current.play();
          }
        });
        
        // Bắt đầu Local Mode
        startLocalMode();
      }
    } catch (err: any) {
      console.error('Lỗi phát nhạc:', err);
      setAudioPlaying(false);
    }
  };

  const startLocalMode = () => {
    setLocalModeActive(true);
    setStartTime(Date.now());
    
    // Xử lý frame theo chu kỳ (mỗi 1 giây)
    processingIntervalRef.current = window.setInterval(async () => {
      if (!sessionId) return;
      
      try {
        // Xử lý frame từ camera 0 (có thể xử lý cả 2 cameras)
        const result: ProcessFrameResponse = await localService.processFrame({
          camera_id: 0,
          session_id: sessionId,
        });
        
        // Cập nhật điểm
        setCurrentScore(result.new_score);
        setIsFailed(result.is_failed);
        
        // Nếu là practising mode, lấy notifications
        if (config?.mode === 'practising') {
          const notifications = await localService.getErrorNotifications(sessionId);
          setErrors(notifications);
        }
        
        // Kiểm tra nếu điểm < 50 (testing mode)
        if (config?.mode === 'testing' && result.is_failed) {
          stopLocalMode();
          navigate('/end-of-section', { state: { sessionId } });
          return;
        }
        
        // Sau khi Local Mode kết thúc (audio hết), chuyển sang Global Mode
        if (audioRef.current && audioRef.current.ended && !globalModeActive) {
          stopLocalMode();
          startGlobalMode();
        }
      } catch (err: any) {
        console.error('Lỗi xử lý frame:', err);
      }
    }, 1000); // Mỗi 1 giây
  };
  
  const startGlobalMode = async () => {
    if (!config || !sessionId) return;
    
    try {
      setGlobalModeActive(true);
      setStartTime(Date.now());
      
      // Phát nhạc Global Mode
      const globalAudio = getModeAudio(
        config.criteria,
        'global',
        config.mode
      );
      
      if (globalAudio && audioRef.current) {
        audioRef.current.src = globalAudio;
        audioRef.current.play();
      }
      
      // Bắt đầu ghi video
      await cameraService.startRecording(0, sessionId);
      await cameraService.startRecording(1, sessionId);
      
      // Xử lý frame theo chu kỳ
      processingIntervalRef.current = window.setInterval(async () => {
        if (!sessionId || !startTime) return;
        
        try {
          const timestamp = (Date.now() - startTime) / 1000; // Giây
          
          // Xử lý frame từ camera 0
          const result = await globalService.processFrame({
            camera_id: 0,
            session_id: sessionId,
            timestamp: timestamp,
          });
          
          // Cập nhật điểm
          setCurrentScore(result.new_score);
          setIsFailed(result.is_failed);
          
          // Nếu là practising mode, lấy notifications
          if (config?.mode === 'practising') {
            const notifications = await globalService.getErrorNotifications(sessionId);
            setErrors(notifications);
          }
          
          // Kiểm tra nếu điểm < 50 (testing mode)
          if (config?.mode === 'testing' && result.is_failed) {
            stopGlobalMode();
            navigate('/end-of-section', { state: { sessionId } });
          }
        } catch (err: any) {
          console.error('Lỗi xử lý frame Global:', err);
        }
      }, 1000); // Mỗi 1 giây
    } catch (err: any) {
      console.error('Lỗi bắt đầu Global Mode:', err);
    }
  };
  
  const stopGlobalMode = async () => {
    if (processingIntervalRef.current) {
      clearInterval(processingIntervalRef.current);
      processingIntervalRef.current = null;
    }
    
    // Dừng ghi video
    try {
      await cameraService.stopRecording(0);
      await cameraService.stopRecording(1);
    } catch (err) {
      console.error('Lỗi dừng video:', err);
    }
    
    setGlobalModeActive(false);
  };

  const stopLocalMode = () => {
    if (processingIntervalRef.current) {
      clearInterval(processingIntervalRef.current);
      processingIntervalRef.current = null;
    }
    setLocalModeActive(false);
  };

  const handleCancel = () => {
    navigate('/candidates');
  };

  return (
    <div className="observation-view">
      <h1>Chấm thí sinh</h1>
      
      {candidate && (
        <div className="candidate-info">
          <h2>{candidate.name}</h2>
          {candidate.code && <p>Mã: {candidate.code}</p>}
        </div>
      )}

      {/* Popup ban đầu */}
      {showPopup && (
        <div className="modal">
          <div className="modal-content">
            <h2>Thông tin chấm</h2>
            {config && (
              <div className="config-info">
                <p><strong>Tiêu chí:</strong> {config.criteria === 'di_deu' ? 'Đi đều' : 'Đi nghiêm'}</p>
                <p><strong>Chế độ:</strong> {config.mode === 'testing' ? 'Kiểm tra' : 'Luyện tập'}</p>
                <p><strong>Mức độ:</strong> {config.difficulty}</p>
              </div>
            )}
            {candidate && (
              <div className="candidate-info-popup">
                <p><strong>Thí sinh:</strong> {candidate.name}</p>
              </div>
            )}
            <div className="modal-actions">
              <button onClick={handleSelectCandidate} className="btn btn-primary">
                OK
              </button>
              <button onClick={handleCancel} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hiển thị 2 cameras */}
      {!showPopup && (
        <>
          <div className="cameras-container">
            <div className="camera-wrapper">
              <CameraView cameraId={0} autoConnect={false} />
            </div>
            <div className="camera-wrapper">
              <CameraView cameraId={1} autoConnect={false} />
            </div>
          </div>

          <div className="controls">
            {!camerasConnected && (
              <button onClick={handleConnectCameras} className="btn btn-primary">
                Kết nối cameras
              </button>
            )}
            
            {camerasConnected && !audioPlaying && (
              <button onClick={handlePlayAudio} className="btn btn-success">
                Phát nhạc
              </button>
            )}
          </div>

          {/* Hiển thị mode hiện tại */}
          {(localModeActive || globalModeActive) && (
            <div className="mode-indicator">
              {localModeActive && <span className="badge badge-info">Làm chậm</span>}
              {globalModeActive && <span className="badge badge-success">Tổng hợp</span>}
            </div>
          )}

          {/* Hiển thị điểm (Testing mode) */}
          {config?.mode === 'testing' && (localModeActive || globalModeActive) && (
            <div className="score-display">
              <h3>Điểm: {currentScore.toFixed(1)} / 100</h3>
              {isFailed && (
                <div className="failed-message">
                  Điểm &lt; 50 - Trượt!
                </div>
              )}
            </div>
          )}

          {/* Hiển thị lỗi (Practising mode - Stack notifications) */}
          {config?.mode === 'practising' && errors.length > 0 && (
            <div className="error-notifications">
              <h3>Lỗi phát hiện:</h3>
              <div className="notifications-stack">
                {errors.slice(0, 5).map((error) => (
                  <div key={error.id} className="notification-item">
                    <strong>{error.type}:</strong> {error.description}
                    {error.snapshot_path && (
                      <button
                        onClick={() => window.open(error.snapshot_path, '_blank')}
                        className="btn btn-sm"
                      >
                        Xem ảnh
                      </button>
                    )}
                    {error.video_path && (
                      <button
                        onClick={() => window.open(error.video_path, '_blank')}
                        className="btn btn-sm"
                      >
                        Xem video
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <audio ref={audioRef} />
    </div>
  );
};

export default ObservationView;

