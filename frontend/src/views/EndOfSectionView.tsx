/**
 * EndOfSectionView - Màn hình kết thúc phiên chấm
 */
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { resultsService, SessionResult } from '../services/resultsService';
import './EndOfSectionView.css';

interface LocationState {
  sessionId?: number;
}

const EndOfSectionView: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState;

  const [sessionResult, setSessionResult] = useState<SessionResult | null>(null);
  const [activeTab, setActiveTab] = useState<'local' | 'global'>('local');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResult();
  }, []);

  const loadResult = async () => {
    if (!state?.sessionId) {
      setError('Không có sessionId');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const result = await resultsService.getSessionResult(state.sessionId);
      setSessionResult(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tải kết quả');
    } finally {
      setLoading(false);
    }
  };

  const renderErrors = (errors: SessionResult['local_errors']) => {
    if (!errors || errors.length === 0) {
      return <p>Không có lỗi nào.</p>;
    }
    return (
      <div className="errors-list">
        {errors.map((e) => (
          <div key={e.id} className="error-item">
            <div>
              <strong>{e.type}</strong>: {e.description}
              <div className="meta">
                <span>Severity: {e.severity.toFixed(2)}</span>
                <span>Deduction: {e.deduction.toFixed(2)}</span>
                {e.timestamp && <span>Time: {e.timestamp}</span>}
              </div>
            </div>
            <div className="actions">
              {e.snapshot_path && (
                <button onClick={() => window.open(e.snapshot_path, '_blank')} className="btn btn-sm">
                  Xem ảnh
                </button>
              )}
              {e.video_path && (
                <button onClick={() => window.open(e.video_path, '_blank')} className="btn btn-sm">
                  Xem video
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) return <div className="loading">Đang tải...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!sessionResult) return null;

  const { score } = sessionResult;

  return (
    <div className="end-of-section-view">
      <h1>Kết thúc phiên chấm</h1>

      <div className="score-summary">
        <h2>Điểm: {score.value?.toFixed(1) ?? '--'} / {score.initial_value ?? '--'}</h2>
        <p>{score.is_passed ? 'Đạt' : 'Không đạt'}</p>
      </div>

      <div className="tabs">
        <button
          className={activeTab === 'local' ? 'active' : ''}
          onClick={() => setActiveTab('local')}
        >
          Làm chậm
        </button>
        <button
          className={activeTab === 'global' ? 'active' : ''}
          onClick={() => setActiveTab('global')}
        >
          Tổng hợp
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'local'
          ? renderErrors(sessionResult.local_errors)
          : renderErrors(sessionResult.global_errors)}
      </div>

      <div className="actions">
        <button className="btn btn-primary" onClick={() => navigate('/summary')}>
          Về Summary
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/candidates')}>
          Chọn thí sinh khác
        </button>
      </div>
    </div>
  );
};

export default EndOfSectionView;

