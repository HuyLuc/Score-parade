/**
 * RegisterView - Đăng ký tài khoản
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';
import './Auth.css';

const RegisterView: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    username: '',
    password: '',
    age: '',
    gender: '',
    rank: '',
    insignia: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.name.trim() || !form.username.trim() || !form.password.trim()) {
      setError('Vui lòng điền đầy đủ tên, username và mật khẩu');
      return;
    }

    try {
      setLoading(true);
      await apiClient.post('/api/auth/register', {
        name: form.name.trim(),
        username: form.username.trim(),
        password: form.password,
        age: form.age ? Number(form.age) : undefined,
        gender: form.gender || undefined,
        rank: form.rank || undefined,
        insignia: form.insignia || undefined,
      });
      setSuccess('Đăng ký thành công. Vui lòng đăng nhập.');
      setTimeout(() => navigate('/login'), 800);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Đăng ký thất bại');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-view">
      <h1>Đăng ký</h1>
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Họ tên *
          <input name="name" value={form.name} onChange={handleChange} required />
        </label>
        <label>
          Username *
          <input name="username" value={form.username} onChange={handleChange} required />
        </label>
        <label>
          Mật khẩu *
          <input type="password" name="password" value={form.password} onChange={handleChange} required />
        </label>
        <label>
          Tuổi
          <input type="number" name="age" value={form.age} onChange={handleChange} min={18} max={100} />
        </label>
        <label>
          Giới tính
          <select name="gender" value={form.gender} onChange={handleChange}>
            <option value="">-- Chọn --</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
          </select>
        </label>
        <label>
          Cấp bậc
          <input name="rank" value={form.rank} onChange={handleChange} />
        </label>
        <label>
          Quân hàm
          <input name="insignia" value={form.insignia} onChange={handleChange} />
        </label>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Đang đăng ký...' : 'Đăng ký'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/login')}>
            Đăng nhập
          </button>
        </div>
      </form>
    </div>
  );
};

export default RegisterView;

