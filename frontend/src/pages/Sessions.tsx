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

  // Deduplicate sessions by ID (keep the most recent one)
  const uniqueSessions = sessions.reduce((acc, session) => {
    const existing = acc.find(s => s.id === session.id)
    if (!existing) {
      acc.push(session)
    } else {
      // Replace with newer session (compare by startTime)
      const existingTime = typeof existing.startTime === 'string' 
        ? new Date(existing.startTime).getTime() 
        : existing.startTime.getTime()
      const newTime = typeof session.startTime === 'string' 
        ? new Date(session.startTime).getTime() 
        : session.startTime.getTime()
      if (newTime > existingTime) {
        const index = acc.indexOf(existing)
        acc[index] = session
      }
    }
    return acc
  }, [] as typeof sessions)

  const filteredSessions = uniqueSessions.filter((session) =>
    session.id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDelete = async (sessionId: string) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa session này?')) {
      return
    }

    setDeletingId(sessionId)
    try {
      // Try to delete from backend (suppress toast for expected 404)
      // Backend now returns success even if session not found, but we suppress toast anyway
      try {
        await globalModeAPI.deleteSession(sessionId, true)  // suppressToast = true
      } catch (error: any) {
        // If backend returns error (shouldn't happen after our fix, but just in case)
        if (error.response?.status !== 404) {
          // Only log non-404 errors
          console.warn('Backend delete failed (non-404):', error)
        }
      }
      
      // Remove ALL sessions with this ID from frontend store (in case of duplicates)
      // Use setState directly to ensure immediate update
      const currentSessions = useSessionStore.getState().sessions
      const sessionsToKeep = currentSessions.filter(s => s.id !== sessionId)
      
      // Update store and clear activeSessionId if needed
      useSessionStore.setState((state) => ({
        sessions: sessionsToKeep,
        activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId
      }))
      
      toast.success('Session đã được xóa')
    } catch (error: any) {
      // If something else goes wrong, still try to remove from store
      const currentSessions = useSessionStore.getState().sessions
      const sessionsToKeep = currentSessions.filter(s => s.id !== sessionId)
      useSessionStore.setState({ sessions: sessionsToKeep })
      toast.success('Session đã được xóa khỏi danh sách')
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
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Quản Lý Sessions
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Tìm kiếm, xem và xoá các phiên chấm điểm đã lưu.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => window.location.reload()}
        >
          Làm Mới
        </Button>
      </Box>

      <Card
        sx={{
          borderRadius: 3,
          boxShadow: '0 14px 40px rgba(15,23,42,0.08)',
          border: '1px solid rgba(15,23,42,0.08)',
        }}
      >
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
                  filteredSessions.map((session, index) => (
                    <TableRow key={`${session.id}-${index}-${session.startTime}`} hover>
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
                        {format(
                          typeof session.startTime === 'string' 
                            ? new Date(session.startTime) 
                            : session.startTime, 
                          'dd/MM/yyyy HH:mm'
                        )}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          // Hỗ trợ cả single-score (number) lẫn map {personId: score}
                          const scoreValue =
                            typeof session.score === 'number'
                              ? session.score
                              : Number(Object.values(session.score ?? {})[0] ?? 0)
                          const color =
                            scoreValue >= 80
                              ? 'success.main'
                              : scoreValue >= 60
                              ? 'warning.main'
                              : 'error.main'
                          return (
                            <Typography variant="body2" color={color} sx={{ fontWeight: 600 }}>
                              {scoreValue.toFixed(1)}
                            </Typography>
                          )
                        })()}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          // Hỗ trợ cả number lẫn map {personId: totalErrors}
                          if (typeof session.totalErrors === 'number') return session.totalErrors
                          const sum = Object.values(session.totalErrors ?? {}).reduce(
                            (acc: number, val: any) => acc + (typeof val === 'number' ? val : 0),
                            0
                          )
                          return sum
                        })()}
                      </TableCell>
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

