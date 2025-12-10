/**
 * CameraView - Component hiển thị video stream từ camera
 */
import React, { useEffect, useRef, useState } from 'react';
import { cameraService, CameraInfo } from '../services/cameraService';
import './CameraView.css';

interface CameraViewProps {
  cameraId: number;
  autoConnect?: boolean;
  showControls?: boolean;
  onError?: (error: string) => void;
  className?: string;
}

const CameraView: React.FC<CameraViewProps> = ({
  cameraId,
  autoConnect = true,
  showControls = true,
  onError,
  className = '',
}) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraInfo, setCameraInfo] = useState<CameraInfo | null>(null);
  const frameIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (autoConnect) {
      connectCamera();
    }

    return () => {
      disconnectCamera();
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    };
  }, [cameraId, autoConnect]);

  const connectCamera = async () => {
    try {
      setLoading(true);
      setError(null);
      await cameraService.connect(cameraId);
      setConnected(true);
      
      // Load camera info
      const cameras = await cameraService.getInfo();
      const info = cameras.find((c) => c.camera_id === cameraId);
      if (info) {
        setCameraInfo(info);
      }
      
      // Bắt đầu stream frames
      startStreaming();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || `Lỗi kết nối camera ${cameraId}`;
      setError(errorMsg);
      setConnected(false);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const disconnectCamera = async () => {
    try {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
      }
      await cameraService.disconnect(cameraId);
      setConnected(false);
      setCameraInfo(null);
    } catch (err: any) {
      console.error('Lỗi ngắt kết nối camera:', err);
    }
  };

  const startStreaming = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
    }

    // Update frame mỗi 100ms (10 FPS cho web)
    frameIntervalRef.current = window.setInterval(() => {
      if (imgRef.current) {
        // Thêm timestamp để tránh cache
        const frameUrl = cameraService.getFrameUrl(cameraId);
        imgRef.current.src = frameUrl;
      }
    }, 100);
  };

  const handleImageError = () => {
    if (connected) {
      setError('Lỗi lấy frame từ camera');
      setConnected(false);
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
      }
    }
  };

  return (
    <div className={`camera-view ${className}`}>
      <div className="camera-header">
        <h3>Camera {cameraId}</h3>
        {cameraInfo && (
          <span className="camera-info">
            {cameraInfo.width}x{cameraInfo.height} @ {cameraInfo.fps.toFixed(1)}fps
          </span>
        )}
      </div>

      <div className="camera-frame-container">
        {loading && <div className="loading">Đang kết nối...</div>}
        {error && <div className="error-message">{error}</div>}
        
        {connected ? (
          <img
            ref={imgRef}
            src={cameraService.getFrameUrl(cameraId)}
            alt={`Camera ${cameraId}`}
            onError={handleImageError}
            className="camera-frame"
          />
        ) : (
          !loading && !error && (
            <div className="camera-placeholder">
              Camera {cameraId} chưa kết nối
            </div>
          )
        )}
      </div>

      {showControls && (
        <div className="camera-controls">
          {!connected ? (
            <button onClick={connectCamera} className="btn btn-primary" disabled={loading}>
              {loading ? 'Đang kết nối...' : 'Kết nối'}
            </button>
          ) : (
            <button onClick={disconnectCamera} className="btn btn-secondary">
              Ngắt kết nối
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default CameraView;

