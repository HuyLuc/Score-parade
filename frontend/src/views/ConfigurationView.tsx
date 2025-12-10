/**
 * ConfigurationView - Màn hình cấu hình
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { configurationService, Configuration } from '../services/configurationService';
import './ConfigurationView.css';

const ConfigurationView: React.FC = () => {
  const navigate = useNavigate();
  const [config, setConfig] = useState<Configuration>({
    mode: 'testing',
    criteria: 'di_deu',
    difficulty: 'normal',
    operation_mode: 'release',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Password change
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    try {
      setLoading(true);
      const data = await configurationService.get();
      setConfig(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tải cấu hình');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof Configuration, value: string) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    try {
      setSaving(true);
      await configurationService.update(config);
      setSuccess('Cập nhật cấu hình thành công');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi cập nhật cấu hình');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('Mật khẩu mới và xác nhận không khớp');
      return;
    }

    if (passwordData.new_password.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự');
      return;
    }

    try {
      setChangingPassword(true);
      await configurationService.changePassword({
        old_password: passwordData.old_password,
        new_password: passwordData.new_password,
      });
      setSuccess('Đổi mật khẩu thành công');
      setShowPasswordForm(false);
      setPasswordData({
        old_password: '',
        new_password: '',
        confirm_password: '',
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi đổi mật khẩu');
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return <div className="loading">Đang tải...</div>;
  }

  return (
    <div className="configuration-view">
      <h1>Cấu hình hệ thống</h1>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <div className="config-sections">
        {/* Đổi mật khẩu */}
        <section className="config-section">
          <h2>Đổi mật khẩu</h2>
          {!showPasswordForm ? (
            <button
              onClick={() => setShowPasswordForm(true)}
              className="btn btn-primary"
            >
              Đổi mật khẩu
            </button>
          ) : (
            <form onSubmit={handlePasswordChange}>
              <div className="form-group">
                <label>Mật khẩu cũ</label>
                <input
                  type="password"
                  value={passwordData.old_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, old_password: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Mật khẩu mới</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, new_password: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Xác nhận mật khẩu mới</label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, confirm_password: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-actions">
                <button type="submit" disabled={changingPassword} className="btn btn-primary">
                  {changingPassword ? 'Đang đổi...' : 'Đổi mật khẩu'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordForm(false);
                    setPasswordData({
                      old_password: '',
                      new_password: '',
                      confirm_password: '',
                    });
                  }}
                  className="btn btn-secondary"
                >
                  Hủy
                </button>
              </div>
            </form>
          )}
        </section>

        {/* Cấu hình chấm điểm */}
        <section className="config-section">
          <h2>Cấu hình chấm điểm</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Chế độ</label>
              <select
                value={config.mode}
                onChange={(e) => handleChange('mode', e.target.value)}
              >
                <option value="testing">Kiểm tra (trừ điểm)</option>
                <option value="practising">Luyện tập (chỉ hiển thị lỗi)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Tiêu chí</label>
              <select
                value={config.criteria}
                onChange={(e) => handleChange('criteria', e.target.value)}
              >
                <option value="di_deu">Đi đều</option>
                <option value="di_nghiem">Đi nghiêm</option>
              </select>
            </div>

            <div className="form-group">
              <label>Mức độ khắt khe</label>
              <select
                value={config.difficulty}
                onChange={(e) => handleChange('difficulty', e.target.value)}
              >
                <option value="easy">Dễ (giảm 30% điểm trừ)</option>
                <option value="normal">Bình thường</option>
                <option value="hard">Khó (tăng 30% điểm trừ)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Chế độ hoạt động</label>
              <select
                value={config.operation_mode}
                onChange={(e) => handleChange('operation_mode', e.target.value)}
              >
                <option value="dev">Development (chi tiết log)</option>
                <option value="release">Release (tối ưu)</option>
              </select>
            </div>

            <div className="form-actions">
              <button type="submit" disabled={saving} className="btn btn-primary">
                {saving ? 'Đang lưu...' : 'Lưu cấu hình'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/candidates')}
                className="btn btn-secondary"
              >
                Quay lại
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
};

export default ConfigurationView;

