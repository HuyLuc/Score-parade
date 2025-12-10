/**
 * BaremView - Màn hình xem và chỉnh sửa barem điểm
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { baremService, Criterion } from '../services/baremService';
import './BaremView.css';

const BaremView: React.FC = () => {
  const navigate = useNavigate();
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('all');
  const [editedWeights, setEditedWeights] = useState<Record<number, number>>({});

  useEffect(() => {
    loadCriteria();
  }, [selectedType]);

  const loadCriteria = async () => {
    try {
      setLoading(true);
      const data = selectedType === 'all'
        ? await baremService.getAll()
        : await baremService.getByType(selectedType);
      setCriteria(data);
      // Khởi tạo editedWeights với giá trị hiện tại
      const weights: Record<number, number> = {};
      data.forEach((c) => {
        weights[c.id] = c.weight;
      });
      setEditedWeights(weights);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tải barem');
    } finally {
      setLoading(false);
    }
  };

  const handleWeightChange = (criterionId: number, newWeight: number) => {
    setEditedWeights((prev) => ({
      ...prev,
      [criterionId]: newWeight,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Tạo danh sách updates
    const updates = Object.entries(editedWeights).map(([id, weight]) => ({
      criterion_id: parseInt(id),
      weight: weight,
    }));

    try {
      setSaving(true);
      const result = await baremService.updateMultipleWeights(updates);
      
      if (result.success) {
        setSuccess(result.message);
        await loadCriteria(); // Reload để lấy giá trị mới
      } else {
        setError(result.message || 'Có lỗi khi cập nhật');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi cập nhật barem');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    const weights: Record<number, number> = {};
    criteria.forEach((c) => {
      weights[c.id] = c.weight;
    });
    setEditedWeights(weights);
  };

  // Nhóm criteria theo type
  const groupedCriteria = criteria.reduce((acc, criterion) => {
    const type = criterion.criterion_type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(criterion);
    return acc;
  }, {} as Record<string, Criterion[]>);

  if (loading) {
    return <div className="loading">Đang tải...</div>;
  }

  return (
    <div className="barem-view">
      <h1>Barem điểm</h1>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <div className="filter-section">
        <label>
          Lọc theo loại:
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tất cả</option>
            <option value="posture">Tư thế</option>
            <option value="rhythm">Nhịp</option>
            <option value="distance">Khoảng cách</option>
            <option value="speed">Tốc độ</option>
          </select>
        </label>
      </div>

      <form onSubmit={handleSubmit}>
        {Object.entries(groupedCriteria).map(([type, typeCriteria]) => (
          <div key={type} className="criteria-group">
            <h2>{getTypeLabel(type)}</h2>
            <table>
              <thead>
                <tr>
                  <th>Tiêu chí</th>
                  <th>Trọng số hiện tại</th>
                  <th>Trọng số mới</th>
                  <th>Áp dụng cho</th>
                </tr>
              </thead>
              <tbody>
                {typeCriteria.map((criterion) => (
                  <tr key={criterion.id}>
                    <td>{criterion.content}</td>
                    <td>{criterion.weight.toFixed(2)}</td>
                    <td>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={editedWeights[criterion.id] || criterion.weight}
                        onChange={(e) =>
                          handleWeightChange(criterion.id, parseFloat(e.target.value) || 0)
                        }
                        className="weight-input"
                      />
                    </td>
                    <td>{criterion.applies_to || 'Tất cả'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        <div className="form-actions">
          <button type="submit" disabled={saving} className="btn btn-primary">
            {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
          </button>
          <button type="button" onClick={handleReset} className="btn btn-secondary">
            Reset
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
    </div>
  );
};

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    posture: 'Tư thế (Làm chậm)',
    rhythm: 'Nhịp (Tổng hợp)',
    distance: 'Khoảng cách (Tổng hợp)',
    speed: 'Tốc độ (Tổng hợp)',
  };
  return labels[type] || type;
}

export default BaremView;

