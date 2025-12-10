/**
 * ListOfCandidatesView - Màn hình danh sách thí sinh
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { candidateService, Candidate } from '../services/candidateService';
import './ListOfCandidatesView.css';

const ListOfCandidatesView: React.FC = () => {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    loadCandidates();
  }, []);

  const loadCandidates = async () => {
    try {
      setLoading(true);
      const data = await candidateService.getAll();
      setCandidates(data);
      // Tự động chọn candidate đầu tiên nếu có
      if (data.length > 0 && !selectedCandidateId) {
        setSelectedCandidateId(data[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi tải danh sách thí sinh');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCandidate = (id: number) => {
    setSelectedCandidateId(id);
  };

  const handleNext = async () => {
    if (!selectedCandidateId) return;
    
    try {
      await candidateService.select(selectedCandidateId);
      navigate('/observation');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi chọn thí sinh');
    }
  };

  const handleConfigure = () => {
    navigate('/configuration');
  };

  const handleImport = () => {
    setShowImportDialog(true);
  };

  const handleCreateNew = () => {
    navigate('/candidates/create');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImportFile(e.target.files[0]);
    }
  };

  const handleImportSubmit = async () => {
    if (!importFile) return;

    try {
      setImporting(true);
      const result = await candidateService.import(importFile);
      
      if (result.success) {
        setImportResult({
          success: true,
          message: `Import thành công ${result.created_count} thí sinh`,
        });
        setShowImportDialog(false);
        setImportFile(null);
        await loadCandidates();
        
        // Chọn candidate đầu tiên trong danh sách mới
        if (result.candidates.length > 0) {
          setSelectedCandidateId(result.candidates[0].id);
        }
      } else {
        setImportResult({
          success: false,
          message: `Import có lỗi: ${result.errors.join(', ')}`,
        });
      }
    } catch (err: any) {
      setImportResult({
        success: false,
        message: err.response?.data?.detail || 'Lỗi import file',
      });
    } finally {
      setImporting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Bạn có chắc muốn xóa thí sinh này?')) return;

    try {
      await candidateService.delete(id);
      await loadCandidates();
      if (selectedCandidateId === id) {
        setSelectedCandidateId(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Lỗi xóa thí sinh');
    }
  };

  const handleEdit = (id: number) => {
    navigate(`/candidates/${id}/edit`);
  };

  if (loading) {
    return <div className="loading">Đang tải...</div>;
  }

  return (
    <div className="list-of-candidates-view">
      <h1>Danh sách thí sinh</h1>

      {error && <div className="error-message">{error}</div>}
      {importResult && (
        <div className={importResult.success ? 'success-message' : 'error-message'}>
          {importResult.message}
        </div>
      )}

      <div className="actions">
        <button onClick={handleImport} className="btn btn-primary">
          Import Excel
        </button>
        <button onClick={handleCreateNew} className="btn btn-primary">
          Tạo mới
        </button>
        <button onClick={handleConfigure} className="btn btn-secondary">
          Cấu hình
        </button>
        <button
          onClick={handleNext}
          disabled={!selectedCandidateId}
          className="btn btn-success"
        >
          Next
        </button>
      </div>

      <div className="candidates-list">
        {candidates.length === 0 ? (
          <p>Chưa có thí sinh nào. Hãy import hoặc tạo mới.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Chọn</th>
                <th>Mã</th>
                <th>Tên</th>
                <th>Tuổi</th>
                <th>Giới tính</th>
                <th>Đơn vị</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr
                  key={candidate.id}
                  className={selectedCandidateId === candidate.id ? 'selected' : ''}
                >
                  <td>
                    <input
                      type="radio"
                      name="candidate"
                      checked={selectedCandidateId === candidate.id}
                      onChange={() => handleSelectCandidate(candidate.id)}
                    />
                  </td>
                  <td>{candidate.code || '-'}</td>
                  <td>{candidate.name}</td>
                  <td>{candidate.age || '-'}</td>
                  <td>{candidate.gender || '-'}</td>
                  <td>{candidate.unit || '-'}</td>
                  <td>{candidate.status}</td>
                  <td>
                    <button onClick={() => handleEdit(candidate.id)} className="btn btn-sm">
                      Sửa
                    </button>
                    <button
                      onClick={() => handleDelete(candidate.id)}
                      className="btn btn-sm btn-danger"
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showImportDialog && (
        <div className="modal">
          <div className="modal-content">
            <h2>Import từ Excel</h2>
            <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />
            <div className="modal-actions">
              <button
                onClick={handleImportSubmit}
                disabled={!importFile || importing}
                className="btn btn-primary"
              >
                {importing ? 'Đang import...' : 'Import'}
              </button>
              <button
                onClick={() => {
                  setShowImportDialog(false);
                  setImportFile(null);
                }}
                className="btn btn-secondary"
              >
                Hủy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ListOfCandidatesView;

