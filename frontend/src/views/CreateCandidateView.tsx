/**
 * CreateCandidateView - Màn hình tạo thí sinh mới
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { candidateService, CandidateCreate } from '../services/candidateService';
import './CreateCandidateView.css';

const CreateCandidateView: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<CandidateCreate>({
    name: '',
    code: '',
    age: undefined,
    gender: '',
    unit: '',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'age' ? (value ? parseInt(value) : undefined) : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.name.trim()) {
      setError('Tên thí sinh không được để trống');
      return;
    }

    try {
      setLoading(true);
      const candidate = await candidateService.create(formData);
      
      // Chọn candidate vừa tạo và chuyển sang ObservationView
      await candidateService.select(candidate.id);
      navigate('/observation');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tạo thí sinh');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    navigate('/candidates');
  };

  const handleErase = () => {
    setFormData({
      name: '',
      code: '',
      age: undefined,
      gender: '',
      unit: '',
      notes: '',
    });
    setError(null);
  };

  return (
    <div className="create-candidate-view">
      <h1>Tạo thí sinh mới</h1>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">
            Tên thí sinh <span className="required">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="code">Mã thí sinh</label>
          <input
            type="text"
            id="code"
            name="code"
            value={formData.code}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label htmlFor="age">Tuổi</label>
          <input
            type="number"
            id="age"
            name="age"
            value={formData.age || ''}
            onChange={handleChange}
            min="1"
            max="150"
          />
        </div>

        <div className="form-group">
          <label htmlFor="gender">Giới tính</label>
          <select id="gender" name="gender" value={formData.gender} onChange={handleChange}>
            <option value="">-- Chọn --</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="unit">Đơn vị</label>
          <input
            type="text"
            id="unit"
            name="unit"
            value={formData.unit}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label htmlFor="notes">Ghi chú</label>
          <textarea
            id="notes"
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            rows={4}
          />
        </div>

        <div className="form-actions">
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? 'Đang tạo...' : 'Submit'}
          </button>
          <button type="button" onClick={handleErase} className="btn btn-secondary">
            Erase
          </button>
          <button type="button" onClick={handleCancel} className="btn btn-secondary">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateCandidateView;

