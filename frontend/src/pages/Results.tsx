import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
} from '@mui/material'
import {
  Download,
  ArrowBack,
  Assessment,
} from '@mui/icons-material'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import ErrorChart from '../components/Results/ErrorChart'
import { exportToPDF, exportToExcel } from '../utils/export'

interface Error {
  frame_number?: number
  start_frame?: number  // For sequence errors
  end_frame?: number    // For sequence errors
  timestamp: number
  error_type?: string
  type?: string  // Alternative field name
  severity: number
  description: string
  is_sequence?: boolean  // Flag for sequence errors
}

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { getSession, sessions } = useSessionStore()
  const [errors, setErrors] = useState<Error[]>([])
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState(true)

  const session = sessionId ? getSession(sessionId) : null

  useEffect(() => {
    if (sessionId) {
      fetchResults()
    } else {
      // If no sessionId, stop loading immediately
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const fetchResults = async () => {
    if (!sessionId) return

    setLoading(true)
    try {
      // Try to get from API first (suppress toast for expected 404)
      try {
        const [scoreData, errorsData] = await Promise.all([
          globalModeAPI.getScore(sessionId, true),  // suppressToast = true
          globalModeAPI.getErrors(sessionId, true),  // suppressToast = true
        ])

        setScore(scoreData.score)
        setErrors(errorsData.errors || [])
      } catch (apiError: any) {
        // If API fails (e.g., session not found in backend memory),
        // try to get from session store
        console.warn('API fetch failed, trying store:', apiError)
        
        if (session) {
          // Use data from store
          setScore(session.score || 0)
          // Try to get errors from store first, then API
          if (session.errors && session.errors.length > 0) {
            setErrors(session.errors)
          } else {
            // Try API as fallback (silently, don't show error if it fails)
            try {
              const errorsData = await globalModeAPI.getErrors(sessionId, true)
              setErrors(errorsData.errors || [])
            } catch {
              // Silently fail, use empty errors
              setErrors([])
            }
          }
        } else {
          // No session in store either
          console.warn('Session not found in API or store, showing empty results')
          setScore(0)
          setErrors([])
        }
      }
    } catch (error) {
      console.error('Error fetching results:', error)
      // Fallback to store data if available
      if (session) {
        setScore(session.score || 0)
        setErrors([])
      }
    } finally {
      setLoading(false)
    }
  }

  const handleExportPDF = () => {
    if (!sessionId || !session) return
    exportToPDF(session, errors, score)
  }

  const handleExportExcel = () => {
    if (!sessionId || !session) return
    exportToExcel(session, errors, score)
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (!session && !sessionId) {
    // Show list of sessions to choose from
    const completedSessions = sessions.filter(s => s.status === 'completed')
    
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
          Kết Quả Chấm Điểm
        </Typography>
        <Card>
          <CardContent>
            {completedSessions.length === 0 ? (
              <>
                <Typography variant="h6" gutterBottom>
                  Chưa có session nào hoàn thành
                </Typography>
                <Typography color="textSecondary" sx={{ mb: 3 }}>
                  Vui lòng upload video hoặc thực hiện chấm điểm real-time để xem kết quả.
                </Typography>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    onClick={() => navigate('/upload')}
                  >
                    Upload Video
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/monitoring')}
                  >
                    Real-time Monitoring
                  </Button>
                </Box>
              </>
            ) : (
              <>
                <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                  Chọn session để xem kết quả:
                </Typography>
                <List>
                  {completedSessions.map((s) => (
                    <ListItem key={s.id} disablePadding>
                      <ListItemButton onClick={() => navigate(`/results/${s.id}`)}>
                        <Assessment sx={{ mr: 2, color: 'primary.main' }} />
                        <ListItemText
                          primary={`Session: ${s.id}`}
                          secondary={`Điểm: ${s.score.toFixed(1)} | Lỗi: ${s.totalErrors} | ${s.startTime instanceof Date ? s.startTime.toLocaleString() : new Date(s.startTime).toLocaleString()}`}
                        />
                        <Chip
                          label={s.score >= 80 ? 'ĐẠT' : s.score >= 60 ? 'TRUNG BÌNH' : 'KHÔNG ĐẠT'}
                          color={s.score >= 80 ? 'success' : s.score >= 60 ? 'warning' : 'error'}
                          size="small"
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
                <Box mt={2}>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/sessions')}
                  >
                    Xem tất cả sessions
                  </Button>
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Kết Quả Chấm Điểm
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate('/sessions')}
          >
            Quay Lại
          </Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={handleExportPDF}
          >
            Export PDF
          </Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={handleExportExcel}
          >
            Export Excel
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Score Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Điểm Số
              </Typography>
              <Typography
                variant="h2"
                color={score >= 80 ? 'success.main' : score >= 60 ? 'warning.main' : 'error.main'}
                sx={{ fontWeight: 700 }}
              >
                {score.toFixed(1)}
              </Typography>
              <Chip
                label={score >= 80 ? 'ĐẠT' : score >= 60 ? 'TRUNG BÌNH' : 'KHÔNG ĐẠT'}
                color={score >= 80 ? 'success' : score >= 60 ? 'warning' : 'error'}
                sx={{ mt: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Stats */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="textSecondary">
                    Tổng Lỗi
                  </Typography>
                  <Typography variant="h4">{errors.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="textSecondary">
                    Session ID
                  </Typography>
                  <Typography variant="body1" noWrap>
                    {sessionId}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="textSecondary">
                    Chế Độ
                  </Typography>
                  <Typography variant="body1">{session?.mode}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="textSecondary">
                    Trạng Thái
                  </Typography>
                  <Chip
                    label={session?.status}
                    size="small"
                    color={
                      session?.status === 'completed'
                        ? 'success'
                        : session?.status === 'active'
                        ? 'primary'
                        : 'error'
                    }
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Error Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Biểu Đồ Lỗi
              </Typography>
              <ErrorChart errors={errors} />
            </CardContent>
          </Card>
        </Grid>

        {/* Errors Table */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Chi Tiết Lỗi
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Frame</TableCell>
                      <TableCell>Thời Gian</TableCell>
                      <TableCell>Loại Lỗi</TableCell>
                      <TableCell>Mức Độ</TableCell>
                      <TableCell>Mô Tả</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {errors.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography color="textSecondary">
                            Không có lỗi nào được phát hiện
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      errors.map((error, index) => {
                        const errorType = error.error_type || error.type || 'unknown'
                        const frameNumber = error.frame_number || error.start_frame || 0
                        const frameDisplay = error.is_sequence && error.end_frame
                          ? `${error.start_frame}-${error.end_frame}`
                          : frameNumber.toString()
                        
                        return (
                          <TableRow key={index}>
                            <TableCell>{frameDisplay}</TableCell>
                            <TableCell>
                              {error.timestamp 
                                ? new Date(error.timestamp * 1000).toLocaleTimeString()
                                : '-'}
                            </TableCell>
                            <TableCell>
                              <Chip label={errorType} size="small" />
                              {error.is_sequence && (
                                <Chip 
                                  label="Sequence" 
                                  size="small" 
                                  color="info" 
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={error.severity.toFixed(2)}
                                size="small"
                                color={
                                  error.severity > 0.7
                                    ? 'error'
                                    : error.severity > 0.4
                                    ? 'warning'
                                    : 'info'
                                }
                              />
                            </TableCell>
                            <TableCell>{error.description}</TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

