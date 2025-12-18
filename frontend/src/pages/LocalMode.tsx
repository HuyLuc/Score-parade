import { useState, useRef, useCallback, useEffect } from 'react'
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
  FormControlLabel,
  Switch,
} from '@mui/material'
import {
  Stop,
  PlayArrow,
  VolumeUp,
  VolumeOff,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { candidatesAPI, localModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import { ttsManager } from '../utils/ttsManager'
import { generateSessionId as generateSessionCode } from '../utils/sessionId'

export default function LocalMode() {
  const webcamRef = useRef<Webcam>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [mode, setMode] = useState<'testing' | 'practising'>('testing')
  const [scores, setScores] = useState<Record<number, number>>({ 0: 100 })
  const [errorsCount, setErrorsCount] = useState<Record<number, number>>({ 0: 0 })
  const [frameNumber, setFrameNumber] = useState(0)
  const [processing, setProcessing] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [candidateId, setCandidateId] = useState<string>('')
  const [candidates, setCandidates] = useState<{ id: string; full_name: string }[]>([])
  const { addSession, updateSession, setActiveSession } = useSessionStore()

  useEffect(() => {
    // Tạo Session ID dạng local_01, local_02... (tăng tự động)
    setSessionId(generateSessionCode('local'))
    ttsManager.setEnabled(ttsEnabled)

    // Load danh sách thí sinh cho dropdown
    candidatesAPI
      .getCandidates(0, 100, true)
      .then((data: any) => {
        if (Array.isArray(data?.items)) {
          setCandidates(
            data.items.map((c: any) => ({
              id: c.id,
              full_name: c.full_name || 'Không tên',
            })),
          )
        } else if (Array.isArray(data)) {
          // Fallback nếu API trả về list trực tiếp
          setCandidates(
            data.map((c: any) => ({
              id: c.id,
              full_name: c.full_name || 'Không tên',
            })),
          )
        }
      })
      .catch(() => {
        console.warn('Không thể tải danh sách thí sinh cho Local Mode')
      })

    return () => {
      ttsManager.clear()
    }
  }, [])

  useEffect(() => {
    ttsManager.setEnabled(ttsEnabled)
  }, [ttsEnabled])

  const startSession = async () => {
    if (!sessionId.trim()) {
      toast.error('Vui lòng nhập Session ID')
      return
    }

    try {
      await localModeAPI.startSession(sessionId, mode, candidateId || undefined)

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
      toast.success('Session Làm chậm đã bắt đầu')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Không thể bắt đầu session Local Mode')
    }
  }

  const stopSession = async () => {
    setIsRunning(false)
    setFrameNumber(0)
    ttsManager.stop()

    try {
      if (sessionId) {
        // Local Mode không có endpoint /stop riêng, chỉ cần cập nhật trạng thái client
        updateSession(sessionId, { status: 'completed' })
      }
    } catch (error) {
      console.error('Error stopping local session:', error)
      toast.error('Có lỗi khi dừng session Local Mode')
    }
  }

  const captureAndProcess = useCallback(async () => {
    if (!webcamRef.current || !isRunning || processing || !sessionId) return

    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    setProcessing(true)

    try {
      const response = await fetch(imageSrc)
      const blob = await response.blob()

      const timestamp = Date.now() / 1000
      const currentFrame = frameNumber
      const result = await localModeAPI.processFrame(
        sessionId,
        blob,
        timestamp,
        currentFrame,
      )

      const persons = result.persons || []
      const nextScores: Record<number, number> = { ...scores }
      const nextErrors: Record<number, number> = { ...errorsCount }

      if (persons.length > 0) {
        persons.forEach((p: any) => {
          const pid = p.person_id ?? 0
          nextScores[pid] = p.score ?? nextScores[pid] ?? 100
          nextErrors[pid] = (p.errors?.length ?? 0)

          // Đọc lỗi mới bằng TTS (giống Global mode)
          if (p.errors && Array.isArray(p.errors) && p.errors.length > 0) {
            const oldErrorCount = errorsCount[pid] || 0
            const newErrorCount = p.errors.length
            if (newErrorCount > oldErrorCount) {
              const latestError = p.errors[p.errors.length - 1]
              if (latestError) {
                ttsManager.queueError(
                  latestError.type || latestError.error_type || 'unknown',
                  latestError.message || latestError.description || '',
                  pid,
                )
              }
            }
          }
        })
      }

      setScores(nextScores)
      setErrorsCount(nextErrors)
      setFrameNumber((prev) => prev + 1)

      updateSession(sessionId, {
        score: Object.values(nextScores)[0] ?? 100,
        totalErrors: Object.values(nextErrors)[0] ?? 0,
      })
    } catch (error: any) {
      console.error('Error processing local frame:', error)
    } finally {
      setProcessing(false)
    }
  }, [isRunning, sessionId, frameNumber, processing, scores, errorsCount, updateSession])

  useEffect(() => {
    if (!isRunning) return

    let interval: number | null = null
    interval = window.setInterval(() => {
      captureAndProcess()
    }, 150) // chậm hơn chút vì Làm chậm không cần quá dày

    return () => {
      if (interval !== null) {
        window.clearInterval(interval)
      }
    }
  }, [isRunning, captureAndProcess])

  const handlePlayCommand = () => {
    // Phát câu lệnh "Nghiêm. Đi đều bước" bằng TTS
    ttsManager.speak('Nghiêm. Đi đều bước')
  }

  const personIds = Object.keys(scores).map(Number)
  const activePid = personIds.length ? personIds[0] : 0
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
          Local Mode - Làm Chậm
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Kiểm tra tư thế tay, chân, vai, đầu, cổ, lưng theo thời gian thực với 1 camera. Chế độ
          Kiểm tra sẽ trừ điểm dần, Luyện tập chỉ hiển thị lỗi.
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
                  Webcam - Bài Làm Chậm
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
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
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

              <Box display="flex" gap={2} mt={2} flexWrap="wrap">
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
                  startIcon={<VolumeUp />}
                  onClick={handlePlayCommand}
                >
                  Phát lệnh "Nghiêm. Đi đều bước"
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Cấu Hình Làm Chậm
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
                <MenuItem value="testing">Testing (trừ điểm, dừng khi điểm dưới ngưỡng)</MenuItem>
                <MenuItem value="practising">Practising (chỉ hiển thị lỗi)</MenuItem>
              </TextField>

              <TextField
                select
                fullWidth
                label="Thí sinh được chấm (tùy chọn)"
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                margin="normal"
                helperText="Liên kết session với hồ sơ thí sinh trong database"
              >
                <MenuItem value="">-- Không chọn --</MenuItem>
                {candidates.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.full_name}
                  </MenuItem>
                ))}
              </TextField>

              <FormControlLabel
                control={
                  <Switch
                    checked={ttsEnabled}
                    onChange={(e) => setTtsEnabled(e.target.checked)}
                  />
                }
                label={
                  <Box display="flex" alignItems="center" gap={0.5}>
                    {ttsEnabled ? <VolumeUp fontSize="small" /> : <VolumeOff fontSize="small" />}
                    <span>Đọc lỗi bằng giọng nói</span>
                  </Box>
                }
                sx={{ mt: 1, display: 'block' }}
              />

              <Alert severity="info" sx={{ mt: 2 }}>
                Frame: {frameNumber} • Điểm hiện tại: {activeScore.toFixed(1)} • Tổng lỗi:{' '}
                {activeErrors}
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}


