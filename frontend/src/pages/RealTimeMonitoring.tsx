import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Webcam from 'react-webcam'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material'
import {
  Videocam,
  Stop,
  PlayArrow,
  Refresh,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'

export default function RealTimeMonitoring() {
  const navigate = useNavigate()
  const webcamRef = useRef<Webcam>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [mode, setMode] = useState<'testing' | 'practising'>('practising')
  const [currentScore, setCurrentScore] = useState(100)
  const [totalErrors, setTotalErrors] = useState(0)
  const [frameNumber, setFrameNumber] = useState(0)
  const [processing, setProcessing] = useState(false)
  const { addSession, updateSession, setActiveSession } = useSessionStore()

  useEffect(() => {
    generateSessionId()
  }, [])

  const generateSessionId = () => {
    const id = `realtime_${Date.now()}`
    setSessionId(id)
  }

  const startSession = async () => {
    if (!sessionId.trim()) {
      toast.error('Vui lòng nhập Session ID')
      return
    }

    try {
      await globalModeAPI.startSession(sessionId, mode)
      
      addSession({
        id: sessionId,
        mode,
        startTime: new Date(),
        score: 100,
        totalErrors: 0,
        status: 'active',
        audioSet: false,
      })

      setActiveSession(sessionId)
      setIsRunning(true)
      toast.success('Session đã bắt đầu')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Không thể bắt đầu session')
    }
  }

  const stopSession = async () => {
    setIsRunning(false)
    setFrameNumber(0)
    
    try {
      if (sessionId) {
        await globalModeAPI.deleteSession(sessionId)
        updateSession(sessionId, { status: 'completed' })
      }
      toast.success('Session đã dừng')
    } catch (error) {
      console.error('Error stopping session:', error)
    }
  }

  const captureAndProcess = useCallback(async () => {
    if (!webcamRef.current || !isRunning || processing) return

    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    setProcessing(true)

    try {
      // Convert base64 to blob
      const response = await fetch(imageSrc)
      const blob = await response.blob()

      const timestamp = Date.now() / 1000
      const result = await globalModeAPI.processFrame(
        sessionId,
        blob,
        timestamp,
        frameNumber
      )

      setCurrentScore(result.score)
      setTotalErrors(result.total_errors || 0)
      setFrameNumber((prev) => prev + 1)

      updateSession(sessionId, {
        score: result.score,
        totalErrors: result.total_errors || 0,
      })

      if (result.stopped) {
        setIsRunning(false)
        toast.info('Session đã hoàn thành')
        navigate(`/results/${sessionId}`)
      }
    } catch (error: any) {
      console.error('Error processing frame:', error)
    } finally {
      setProcessing(false)
    }
  }, [isRunning, sessionId, frameNumber, processing, navigate, updateSession])

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isRunning) {
      interval = setInterval(() => {
        captureAndProcess()
      }, 100) // Process every 100ms (~10 FPS)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isRunning, captureAndProcess])

  const fetchScore = async () => {
    if (!sessionId) return
    try {
      const result = await globalModeAPI.getScore(sessionId)
      setCurrentScore(result.score)
    } catch (error) {
      console.error('Error fetching score:', error)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Real-time Monitoring
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Webcam Feed</Typography>
                <Chip
                  label={isRunning ? 'Đang chạy' : 'Đã dừng'}
                  color={isRunning ? 'success' : 'default'}
                />
              </Box>

              <Box
                sx={{
                  position: 'relative',
                  width: '100%',
                  backgroundColor: 'black',
                  borderRadius: 2,
                  overflow: 'hidden',
                  aspectRatio: '16/9',
                }}
              >
                <Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{
                    width: 1280,
                    height: 720,
                    facingMode: 'user',
                  }}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />
                {processing && (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      backgroundColor: 'rgba(0,0,0,0.7)',
                      color: 'white',
                      px: 2,
                      py: 1,
                      borderRadius: 2,
                    }}
                  >
                    <CircularProgress size={20} color="inherit" />
                    <Typography variant="body2">Đang xử lý...</Typography>
                  </Box>
                )}
              </Box>

              <Box display="flex" gap={2} mt={2}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayArrow />}
                  onClick={startSession}
                  disabled={isRunning}
                >
                  Bắt Đầu
                </Button>
                <Button
                  variant="contained"
                  color="error"
                  startIcon={<Stop />}
                  onClick={stopSession}
                  disabled={!isRunning}
                >
                  Dừng
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Refresh />}
                  onClick={fetchScore}
                  disabled={!isRunning}
                >
                  Làm Mới Điểm
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Cấu Hình
              </Typography>

              <TextField
                fullWidth
                label="Session ID"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                margin="normal"
                helperText="ID duy nhất cho session này"
              />

              <TextField
                fullWidth
                select
                label="Chế Độ"
                value={mode}
                onChange={(e) => setMode(e.target.value as 'testing' | 'practising')}
                margin="normal"
                disabled={isRunning}
              >
                <MenuItem value="testing">Testing</MenuItem>
                <MenuItem value="practising">Practising</MenuItem>
              </TextField>

              <Alert severity="info" sx={{ mt: 2 }}>
                Frame: {frameNumber}
              </Alert>
            </CardContent>
          </Card>

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Thống Kê
              </Typography>

              <Box mt={2}>
                <Typography variant="body2" color="textSecondary">
                  Điểm Hiện Tại
                </Typography>
                <Typography variant="h3" color="primary.main" sx={{ fontWeight: 700 }}>
                  {currentScore.toFixed(1)}
                </Typography>
              </Box>

              <Box mt={3}>
                <Typography variant="body2" color="textSecondary">
                  Tổng Số Lỗi
                </Typography>
                <Typography variant="h4" color="error.main" sx={{ fontWeight: 700 }}>
                  {totalErrors}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

