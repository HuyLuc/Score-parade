/**
 * SummaryView - Màn hình tổng hợp kết quả
 */
import React, { useEffect, useState } from 'react';
import { resultsService, SummaryItem } from '../services/resultsService';
import './SummaryView.css';

const SummaryView: React.FC = () => {
  const [items, setItems] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSummary();
  }, []);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const data = await resultsService.getSummary(100);
      setItems(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tải summary');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Bạn có chắc muốn xoá phiên chấm này?')) return;
    try {
      await resultsService.deleteSession(id);
      await loadSummary();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Lỗi xoá phiên');
    }
  };

  if (loading) return <div className="loading">Đang tải...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="summary-view">
      <h1>Tổng hợp kết quả</h1>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Thí sinh</th>
            <th>Chế độ</th>
            <th>Loại</th>
            <th>Bắt đầu</th>
            <th>Kết thúc</th>
            <th>Điểm</th>
            <th>Trạng thái</th>
            <th>Hành động</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.candidate_id ?? '-'}</td>
              <td>{item.mode}</td>
              <td>{item.session_type}</td>
              <td>{item.started_at || '-'}</td>
              <td>{item.ended_at || '-'}</td>
              <td>{item.score?.toFixed(1) ?? '-'}</td>
              <td>{item.is_passed === true ? 'Đạt' : item.is_passed === false ? 'Trượt' : '-'}</td>
              <td>
                <button className="btn btn-sm" onClick={() => handleDelete(item.id)}>
                  Xoá
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SummaryView;

