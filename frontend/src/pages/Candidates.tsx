import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  MenuItem,
} from '@mui/material'
import {
  Add,
  Edit,
  Delete,
  Upload,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { candidatesAPI } from '../services/api'

interface Candidate {
  id: string
  full_name: string
  age?: number
  gender?: string
  rank?: string
  insignia?: string
  avatar_path?: string
  notes?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function Candidates() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [openDialog, setOpenDialog] = useState(false)
  const [editingCandidate, setEditingCandidate] = useState<Candidate | null>(null)
  const [formData, setFormData] = useState({
    full_name: '',
    age: '',
    gender: '',
    rank: '',
    insignia: '',
    notes: '',
  })

  useEffect(() => {
    fetchCandidates()
  }, [])

  const fetchCandidates = async () => {
    setLoading(true)
    try {
      const data = await candidatesAPI.getCandidates()
      setCandidates(data)
    } catch (err: any) {
      toast.error('Không thể tải danh sách thí sinh')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenDialog = (candidate?: Candidate) => {
    if (candidate) {
      setEditingCandidate(candidate)
      setFormData({
        full_name: candidate.full_name,
        age: candidate.age?.toString() || '',
        gender: candidate.gender || '',
        rank: candidate.rank || '',
        insignia: candidate.insignia || '',
        notes: candidate.notes || '',
      })
    } else {
      setEditingCandidate(null)
      setFormData({
        full_name: '',
        age: '',
        gender: '',
        rank: '',
        insignia: '',
        notes: '',
      })
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingCandidate(null)
  }

  const handleSave = async () => {
    try {
      if (editingCandidate) {
        await candidatesAPI.updateCandidate(editingCandidate.id, {
          full_name: formData.full_name,
          age: formData.age ? parseInt(formData.age) : undefined,
          gender: formData.gender || undefined,
          rank: formData.rank || undefined,
          insignia: formData.insignia || undefined,
          notes: formData.notes || undefined,
        })
        toast.success('Cập nhật thí sinh thành công')
      } else {
        await candidatesAPI.createCandidate({
          full_name: formData.full_name,
          age: formData.age ? parseInt(formData.age) : undefined,
          gender: formData.gender || undefined,
          rank: formData.rank || undefined,
          insignia: formData.insignia || undefined,
          notes: formData.notes || undefined,
        })
        toast.success('Tạo thí sinh thành công')
      }
      handleCloseDialog()
      fetchCandidates()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra')
    }
  }

  const handleDelete = async (candidateId: string) => {
    if (!window.confirm('Bạn có chắc muốn xóa thí sinh này?')) return

    try {
      await candidatesAPI.deleteCandidate(candidateId)
      toast.success('Đã xóa thí sinh')
      fetchCandidates()
    } catch (err: any) {
      toast.error('Không thể xóa thí sinh')
    }
  }

  const handleImportExcel = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await candidatesAPI.importExcel(file)
      toast.success(result.message || `Đã import ${result.imported_count} thí sinh`)
      fetchCandidates()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi import Excel')
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 800 }}>
            Quản Lý Thí Sinh
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Thêm, sửa, xóa và import danh sách thí sinh
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Upload />}
            component="label"
          >
            Import Excel
            <input
              type="file"
              hidden
              accept=".xlsx,.xls"
              onChange={handleImportExcel}
            />
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Thêm Thí Sinh
          </Button>
        </Box>
      </Box>

      <Card>
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>STT</TableCell>
                  <TableCell>Họ và Tên</TableCell>
                  <TableCell>Tuổi</TableCell>
                  <TableCell>Giới tính</TableCell>
                  <TableCell>Cấp bậc</TableCell>
                  <TableCell>Quân hàm</TableCell>
                  <TableCell>Trạng thái</TableCell>
                  <TableCell align="right">Thao tác</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      Đang tải...
                    </TableCell>
                  </TableRow>
                ) : candidates.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      Chưa có thí sinh nào
                    </TableCell>
                  </TableRow>
                ) : (
                  candidates.map((candidate, index) => (
                    <TableRow key={candidate.id}>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell>{candidate.full_name}</TableCell>
                      <TableCell>{candidate.age || '-'}</TableCell>
                      <TableCell>
                        {candidate.gender === 'male' ? 'Nam' :
                         candidate.gender === 'female' ? 'Nữ' : '-'}
                      </TableCell>
                      <TableCell>{candidate.rank || '-'}</TableCell>
                      <TableCell>{candidate.insignia || '-'}</TableCell>
                      <TableCell>
                        {candidate.is_active ? (
                          <Typography color="success.main">Hoạt động</Typography>
                        ) : (
                          <Typography color="error.main">Đã xóa</Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(candidate)}
                          color="primary"
                        >
                          <Edit />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(candidate.id)}
                          color="error"
                        >
                          <Delete />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Dialog Create/Edit Candidate */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingCandidate ? 'Sửa Thí Sinh' : 'Thêm Thí Sinh Mới'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Họ và tên *"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Tuổi"
                type="number"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Giới tính"
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
              >
                <MenuItem value="">Chọn giới tính</MenuItem>
                <MenuItem value="male">Nam</MenuItem>
                <MenuItem value="female">Nữ</MenuItem>
                <MenuItem value="other">Khác</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Cấp bậc"
                value={formData.rank}
                onChange={(e) => setFormData({ ...formData, rank: e.target.value })}
                placeholder="VD: Chiến sĩ"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Quân hàm"
                value={formData.insignia}
                onChange={(e) => setFormData({ ...formData, insignia: e.target.value })}
                placeholder="VD: Binh nhì"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Ghi chú"
                multiline
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Hủy</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.full_name}>
            {editingCandidate ? 'Cập nhật' : 'Tạo'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

