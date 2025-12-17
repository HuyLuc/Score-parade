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
  Visibility,
  VisibilityOff,
} from '@mui/icons-material'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import ErrorChart from '../components/Results/ErrorChart'
import { exportToPDF, exportToExcel } from '../utils/export'
import ReactPlayer from 'react-player'

interface ErrorDetail {
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

const toNumericScore = (score: any): number => {
  if (typeof score === 'number') return score
  if (score && typeof score === 'object') {
    const v = Object.values(score as Record<string | number, number>)[0]
    return typeof v === 'number' ? v : 0
  }
  return 0
}

const toNumericErrors = (errs: any): number => {
  if (typeof errs === 'number') return errs
  if (errs && typeof errs === 'object') {
    return Object.values(errs as Record<string | number, number>).reduce(
      (acc, v) => acc + (typeof v === 'number' ? v : 0),
      0
    )
  }
  return 0
}

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { getSession, sessions } = useSessionStore()
  const [errorsPerPerson, setErrorsPerPerson] = useState<Record<number, ErrorDetail[]>>({})
  const [scores, setScores] = useState<Record<number, number>>({})
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [showSkeletonVideo, setShowSkeletonVideo] = useState(false)

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

        // Handle multi-person results
        const apiScores: Record<number, number> =
          scoreData.scores
            ? scoreData.scores
            : scoreData.score !== undefined
            ? { 0: toNumericScore(scoreData.score) }
            : {}

        const apiErrors: Record<number, ErrorDetail[]> =
          errorsData.errors ||
          (Array.isArray(errorsData.errors) ? { 0: errorsData.errors as ErrorDetail[] } : {})

        setScores(apiScores)
        setErrorsPerPerson(apiErrors)
        // Select first person_id if not set
        const firstPid = Object.keys(apiScores).map(Number)[0] ?? Object.keys(apiErrors).map(Number)[0] ?? null
        setSelectedPersonId((prev) => prev ?? firstPid)
      } catch (apiError: any) {
        // If API fails (e.g., session not found in backend memory),
        // try to get from session store
        console.warn('API fetch failed, trying store:', apiError)
        
        if (session) {
          // Use data from store
          setScores({ 0: toNumericScore(session.score) })
          const storedErrors = session.errors && session.errors.length > 0 ? session.errors : []
          setErrorsPerPerson({ 0: storedErrors })
          setSelectedPersonId(0)
        } else {
          // No session in store either
          console.warn('Session not found in API or store, showing empty results')
          setScores({ 0: 0 })
          setErrorsPerPerson({ 0: [] })
          setSelectedPersonId(0)
        }
      }
    } catch (error) {
      console.error('Error fetching results:', error)
      // Fallback to store data if available
      if (session) {
          setScores({ 0: toNumericScore(session.score) })
        setErrorsPerPerson({ 0: [] })
        setSelectedPersonId(0)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleExportPDF = () => {
    if (!sessionId || !session) return
    const pid = selectedPersonId ?? 0
    exportToPDF(session, errorsPerPerson[pid] || [], scores[pid] || 0)
  }

  const handleExportExcel = () => {
    if (!sessionId || !session) return
    const pid = selectedPersonId ?? 0
    exportToExcel(session, errorsPerPerson[pid] || [], scores[pid] || 0)
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
                        {(() => {
                          const sc = toNumericScore(s.score)
                          const err = toNumericErrors(s.totalErrors)
                          const label =
                            sc >= 80 ? 'ĐẠT' : sc >= 60 ? 'TRUNG BÌNH' : 'KHÔNG ĐẠT'
                          const color = sc >= 80 ? 'success' : sc >= 60 ? 'warning' : 'error'
                          return (
                            <>
                              <ListItemText
                                primary={`Session: ${s.id}`}
                                secondary={`Điểm: ${sc.toFixed(1)} | Lỗi: ${err} | ${
                                  s.startTime instanceof Date
                                    ? s.startTime.toLocaleString()
                                    : new Date(s.startTime).toLocaleString()
                                }`}
                              />
                              <Chip label={label} color={color} size="small" />
                            </>
                          )
                        })()}
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

  const personIds = Object.keys(scores).map(Number)
  const activePid = selectedPersonId ?? personIds[0] ?? null
  const activeScore = (activePid !== null && scores[activePid] !== undefined) ? scores[activePid] : 0
  const activeErrors = (activePid !== null && errorsPerPerson[activePid]) ? errorsPerPerson[activePid] : []
  const totalErrorsCount = activeErrors.length

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Kết Quả Chấm Điểm
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Xem điểm số, lỗi chi tiết và tải xuống báo cáo.
          </Typography>
        </Box>
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
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 16px 48px rgba(15,23,42,0.08)',
              border: '1px solid rgba(37,99,235,0.08)',
            }}
          >
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                Điểm Số {activePid !== null ? `(ID: ${activePid})` : ''}
              </Typography>
              <Typography
                variant="h2"
                color={activeScore >= 80 ? 'success.main' : activeScore >= 60 ? 'warning.main' : 'error.main'}
                sx={{ fontWeight: 700 }}
              >
                {activeScore.toFixed(1)}
              </Typography>
              <Chip
                label={activeScore >= 80 ? 'ĐẠT' : activeScore >= 60 ? 'TRUNG BÌNH' : 'KHÔNG ĐẠT'}
                color={activeScore >= 80 ? 'success' : activeScore >= 60 ? 'warning' : 'error'}
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
                    Tổng Lỗi (ID đang chọn)
                  </Typography>
                  <Typography variant="h4">{totalErrorsCount}</Typography>
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

        {/* Skeleton Video */}
        {session?.skeletonVideoUrl && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    Video với Khớp Xương (Skeleton Overlay)
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={showSkeletonVideo ? <VisibilityOff /> : <Visibility />}
                    onClick={() => setShowSkeletonVideo(!showSkeletonVideo)}
                  >
                    {showSkeletonVideo ? 'Ẩn Video' : 'Hiển Thị Video'}
                  </Button>
                </Box>
                {showSkeletonVideo && (
                  <Paper
                    elevation={2}
                    sx={{
                      position: 'relative',
                      paddingTop: '56.25%', // 16:9 aspect ratio
                      backgroundColor: '#000',
                      borderRadius: 2,
                      overflow: 'hidden',
                    }}
                  >
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                      }}
                    >
                      <ReactPlayer
                        url={session.skeletonVideoUrl}
                        controls
                        playing={false}
                        width="100%"
                        height="100%"
                        config={{
                          file: {
                            attributes: {
                              controlsList: 'nodownload',
                            },
                          },
                        }}
                      />
                    </Box>
                  </Paper>
                )}
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  Video này hiển thị khớp xương được phát hiện bởi mô hình YOLOv8-Pose. 
                  Mỗi khớp xương được vẽ bằng màu sắc khác nhau để dễ phân biệt.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Person selector (multi-person) */}
        {personIds.length > 1 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Chọn người (ID) để xem kết quả
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {personIds.map((pid) => (
                    <Chip
                      key={pid}
                      label={`ID ${pid}`}
                      color={pid === activePid ? 'primary' : 'default'}
                      onClick={() => setSelectedPersonId(pid)}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Error Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Biểu Đồ Lỗi
              </Typography>
              <ErrorChart errors={activeErrors} />
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
                    {activeErrors.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography color="textSecondary">
                            Không có lỗi nào được phát hiện
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      activeErrors.map((error, index) => {
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

