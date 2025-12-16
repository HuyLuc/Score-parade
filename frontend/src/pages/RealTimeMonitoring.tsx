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
  Typography as MuiTypography,
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
  const [scores, setScores] = useState<Record<number, number>>({ 0: 100 })
  const [errorsCount, setErrorsCount] = useState<Record<number, number>>({ 0: 0 })
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null)
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
    if (!webcamRef.current || !isRunning || processing || !sessionId) return

    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    setProcessing(true)

    try {
      // Convert base64 to blob
      const response = await fetch(imageSrc)
      const blob = await response.blob()

      const timestamp = Date.now() / 1000
      const currentFrame = frameNumber
      const result = await globalModeAPI.processFrame(
        sessionId,
        blob,
        timestamp,
        currentFrame
      )

      const persons = result.persons || []
      const nextScores: Record<number, number> = { ...scores }
      const nextErrors: Record<number, number> = { ...errorsCount }
      if (persons.length > 0) {
        persons.forEach((p: any) => {
          nextScores[p.person_id] = p.score ?? nextScores[p.person_id] ?? 100
          nextErrors[p.person_id] = (p.errors?.length ?? 0)
        })
        // Select first ID if none selected
        if (selectedPersonId === null) {
          setSelectedPersonId(persons[0].person_id)
        }
      }
      setScores(nextScores)
      setErrorsCount(nextErrors)
      setFrameNumber((prev) => prev + 1)

      updateSession(sessionId, {
        score: Object.values(nextScores)[0] ?? 100,
        totalErrors: Object.values(nextErrors)[0] ?? 0,
      })

      const anyStopped = persons.some((p: any) => p.stopped)
      if (anyStopped) {
        setIsRunning(false)
        toast.info('Session đã dừng vì một người đạt ngưỡng dừng')
        navigate(`/results/${sessionId}`)
      }
    } catch (error: any) {
      console.error('Error processing frame:', error)
      // Don't show toast for every frame error to avoid spam
    } finally {
      setProcessing(false)
    }
  }, [isRunning, sessionId, frameNumber, processing, navigate, updateSession])

  useEffect(() => {
    if (!isRunning) return
    
    // Trong trình duyệt, setInterval trả về number, không phải NodeJS.Timeout
    let interval: number | null = null
    interval = window.setInterval(() => {
      captureAndProcess()
    }, 100) // Process every 100ms (~10 FPS)
    
    return () => {
      if (interval !== null) {
        window.clearInterval(interval)
      }
    }
  }, [isRunning]) // Remove captureAndProcess from deps to avoid re-render loop

  const fetchScore = async () => {
    if (!sessionId) return
    try {
      const result = await globalModeAPI.getScore(sessionId)
      const apiScores: Record<number, number> =
        result.scores || (result.score !== undefined ? { 0: result.score } : {})
      setScores(apiScores)
      if (selectedPersonId === null && Object.keys(apiScores).length > 0) {
        setSelectedPersonId(Number(Object.keys(apiScores)[0]))
      }
    } catch (error) {
      console.error('Error fetching score:', error)
    }
  }

  const personIds = Object.keys(scores).map(Number)
  const activePid = selectedPersonId ?? (personIds.length ? personIds[0] : 0)
  const activeScore = scores[activePid] ?? 100
  const activeErrors = errorsCount[activePid] ?? 0

  return (
    <Box>
      <Box
        sx={{
          mb: 4,
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 800 }}>
          Real-time Monitoring
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Giám sát camera trực tiếp, chấm điểm và đếm lỗi theo thời gian thực (hỗ trợ đa người, chọn ID để xem).
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 14px 40px rgba(15, 23, 42, 0.08)',
              border: '1px solid rgba(15,23,42,0.08)',
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Webcam Feed
                </Typography>
                <Chip
                  label={isRunning ? 'Đang chạy' : 'Đã dừng'}
                  color={isRunning ? 'success' : 'default'}
                />
              </Box>

              <Box
                sx={{
                  position: 'relative',
                  width: '100%',
                  backgroundColor: '#0b1224',
                  borderRadius: 3,
                  overflow: 'hidden',
                  aspectRatio: '16/9',
                  border: '1px solid rgba(255,255,255,0.06)',
                  boxShadow: '0 18px 48px rgba(15,23,42,0.35)',
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
                  Điểm Hiện Tại (ID đang chọn)
                </Typography>
                <Typography variant="h3" color="primary.main" sx={{ fontWeight: 700 }}>
                  {activeScore.toFixed(1)}
                </Typography>
              </Box>

              <Box mt={3}>
                <Typography variant="body2" color="textSecondary">
                  Tổng Số Lỗi (ID đang chọn)
                </Typography>
                <Typography variant="h4" color="error.main" sx={{ fontWeight: 700 }}>
                  {activeErrors}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {personIds.length > 1 && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Chọn người (ID) đang xem
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
          )}
        </Grid>
      </Grid>
    </Box>
  )
}

