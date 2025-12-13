import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Button,
  TextField,
  InputAdornment,
} from '@mui/material'
import {
  Delete,
  Visibility,
  Search,
  Refresh,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { format } from 'date-fns'
import { useSessionStore } from '../store/useSessionStore'
import { globalModeAPI } from '../services/api'

export default function Sessions() {
  const navigate = useNavigate()
  const { sessions, removeSession } = useSessionStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filteredSessions = sessions.filter((session) =>
    session.id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDelete = async (sessionId: string) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa session này?')) {
      return
    }

    setDeletingId(sessionId)
    try {
      await globalModeAPI.deleteSession(sessionId)
      removeSession(sessionId)
      toast.success('Session đã được xóa')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Không thể xóa session')
    } finally {
      setDeletingId(null)
    }
  }

  const handleView = (sessionId: string) => {
    navigate(`/results/${sessionId}`)
  }

  const getStatusColor = (status: string): 'success' | 'error' | 'primary' => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'stopped':
        return 'error'
      default:
        return 'primary'
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Quản Lý Sessions
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => window.location.reload()}
        >
          Làm Mới
        </Button>
      </Box>

      <Card>
        <CardContent>
          <Box mb={3}>
            <TextField
              fullWidth
              placeholder="Tìm kiếm session..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Session ID</TableCell>
                  <TableCell>Chế Độ</TableCell>
                  <TableCell>Thời Gian Bắt Đầu</TableCell>
                  <TableCell>Điểm Số</TableCell>
                  <TableCell>Tổng Lỗi</TableCell>
                  <TableCell>Trạng Thái</TableCell>
                  <TableCell align="right">Thao Tác</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredSessions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="textSecondary" sx={{ py: 4 }}>
                        {searchTerm ? 'Không tìm thấy session nào' : 'Chưa có sessions'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredSessions.map((session) => (
                    <TableRow key={session.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {session.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={session.mode}
                          size="small"
                          color={session.mode === 'testing' ? 'primary' : 'secondary'}
                        />
                      </TableCell>
                      <TableCell>
                        {format(new Date(session.startTime), 'dd/MM/yyyy HH:mm')}
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          color={
                            session.score >= 80
                              ? 'success.main'
                              : session.score >= 60
                              ? 'warning.main'
                              : 'error.main'
                          }
                          sx={{ fontWeight: 600 }}
                        >
                          {session.score.toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell>{session.totalErrors}</TableCell>
                      <TableCell>
                        <Chip
                          label={session.status}
                          size="small"
                          color={getStatusColor(session.status)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleView(session.id)}
                          color="primary"
                        >
                          <Visibility />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(session.id)}
                          color="error"
                          disabled={deletingId === session.id}
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

          <Box mt={2}>
            <Typography variant="body2" color="textSecondary">
              Tổng cộng: {filteredSessions.length} session(s)
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}

