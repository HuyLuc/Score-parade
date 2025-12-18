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
  FormControlLabel,
  Switch,
} from '@mui/material'
import {
  Stop,
  PlayArrow,
  Refresh,
  VolumeUp,
  VolumeOff,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { candidatesAPI, globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import { drawSkeleton, drawPersonLabel, parseKeypoints, Keypoint } from '../utils/skeletonDrawer'
import { ttsManager } from '../utils/ttsManager'

export default function RealTimeMonitoring() {
  const navigate = useNavigate()
  const webcamRef = useRef<Webcam>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [mode, setMode] = useState<'testing' | 'practising'>('practising')
  const [scores, setScores] = useState<Record<number, number>>({ 0: 100 })
  const [errorsCount, setErrorsCount] = useState<Record<number, number>>({ 0: 0 })
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null)
  const [totalPersons, setTotalPersons] = useState<number>(0)
  const [stablePersonIds, setStablePersonIds] = useState<number[]>([])
  const [frameNumber, setFrameNumber] = useState(0)
  const [processing, setProcessing] = useState(false)
  const [showSkeleton, setShowSkeleton] = useState(true)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [currentKeypoints, setCurrentKeypoints] = useState<Record<number, Keypoint[]>>({})
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [candidateId, setCandidateId] = useState<string>('')
  const [candidates, setCandidates] = useState<{ id: string; full_name: string }[]>([])
  const { addSession, updateSession, setActiveSession } = useSessionStore()

  useEffect(() => {
    generateSessionId()
    // Khởi tạo TTS
    ttsManager.setEnabled(ttsEnabled)

    // Load danh sách thí sinh cho dropdown (chỉ lần đầu)
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
        }
      })
      .catch(() => {
        // Không hiển thị toast để tránh spam, chỉ log
        console.warn('Không thể tải danh sách thí sinh cho RealTimeMonitoring')
      })
    
    return () => {
      // Cleanup khi component unmount
      ttsManager.clear()
    }
  }, [])

  // Cập nhật TTS khi toggle
  useEffect(() => {
    ttsManager.setEnabled(ttsEnabled)
  }, [ttsEnabled])

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
      await globalModeAPI.startSession(sessionId, mode, {
        audioFile: audioFile || undefined,
        candidateId: candidateId || undefined,
      })
      
      addSession({
        id: sessionId,
        mode,
        startTime: new Date(),
        score: 100,
        totalErrors: 0,
        status: 'active',
        audioSet: Boolean(audioFile),
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
    ttsManager.stop() // Dừng TTS
    setCurrentKeypoints({}) // Clear skeleton
    
    try {
      if (sessionId) {
        // Gọi endpoint stop để lưu session vào DB với status="completed"
        try {
          const result = await globalModeAPI.stopSession(sessionId)
          
          // Cập nhật session store với dữ liệu từ backend
          const finalScore = Object.values(result.scores || {})[0]
          const finalTotalErrors = Object.values(result.total_errors || {})[0]
          updateSession(sessionId, {
            status: 'completed',
            score: typeof finalScore === 'number' ? finalScore : 100,
            totalErrors: typeof finalTotalErrors === 'number' ? finalTotalErrors : 0,
          })
          
          toast.success('Session đã dừng và lưu vào database')
        } catch (stopError: any) {
          console.warn('Error stopping session via API:', stopError)
          // Fallback: chỉ cập nhật local state
          updateSession(sessionId, { status: 'completed' })
          toast.success('Session đã dừng')
        }
      }
    } catch (error) {
      console.error('Error stopping session:', error)
      toast.error('Có lỗi khi dừng session')
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
      const nextKeypoints: Record<number, Keypoint[]> = {}
      
      if (persons.length > 0) {
        persons.forEach((p: any) => {
          const pid = p.person_id
          nextScores[pid] = p.score ?? nextScores[pid] ?? 100
          nextErrors[pid] = (p.errors?.length ?? 0)
          
          // Parse keypoints nếu có
          if (p.keypoints) {
            const parsed = parseKeypoints(p.keypoints)
            if (parsed) {
              nextKeypoints[pid] = parsed
              // Debug: log keypoints để kiểm tra
              if (frameNumber % 30 === 0) { // Log mỗi 30 frames để không spam
                console.log(`[Skeleton] Person ${pid} keypoints:`, parsed.length, 'keypoints detected')
              }
            } else {
              if (frameNumber % 30 === 0) {
                console.warn(`[Skeleton] Person ${pid} keypoints parse failed:`, p.keypoints)
              }
            }
          } else {
            if (frameNumber % 30 === 0) {
              console.warn(`[Skeleton] Person ${pid} no keypoints in response`)
            }
          }
          
          // Đọc lỗi mới bằng TTS
          if (p.errors && Array.isArray(p.errors) && p.errors.length > 0) {
            // Chỉ đọc lỗi mới (so sánh với lỗi cũ)
            const oldErrorCount = errorsCount[pid] || 0
            const newErrorCount = p.errors.length
            if (newErrorCount > oldErrorCount) {
              // Có lỗi mới - đọc lỗi cuối cùng
              const latestError = p.errors[p.errors.length - 1]
              if (latestError) {
                ttsManager.queueError(
                  latestError.type || latestError.error_type || 'unknown',
                  latestError.message || latestError.description || '',
                  pid
                )
              }
            }
          }
        })
        // Select first ID if none selected
        if (selectedPersonId === null) {
          setSelectedPersonId(persons[0].person_id)
        }
      }
      setScores(nextScores)
      setErrorsCount(nextErrors)
      setCurrentKeypoints(nextKeypoints)
      // Cập nhật thông tin số người và các ID ổn định từ backend (nếu có)
      if (Array.isArray(result.stable_person_ids) && result.stable_person_ids.length > 0) {
        setStablePersonIds(result.stable_person_ids.map((id: any) => Number(id)))
        setTotalPersons(result.total_persons ?? result.stable_person_ids.length)
      } else {
        const idsFromResult = Array.isArray(result.person_ids)
          ? result.person_ids.map((id: any) => Number(id))
          : persons.map((p: any) => Number(p.person_id))
        setStablePersonIds(idsFromResult)
        setTotalPersons(result.total_persons ?? idsFromResult.length)
      }
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

  // Effect để vẽ skeleton lên canvas – vẽ lại mỗi khi keypoints hoặc toggle thay đổi
  useEffect(() => {
    if (!canvasRef.current || !showSkeleton) {
      return
    }

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size theo kích thước container (display size)
    const container = canvas.parentElement
    if (!container) return

    const rect = container.getBoundingClientRect()
    const displayWidth = rect.width
    const displayHeight = rect.height

    canvas.width = displayWidth
    canvas.height = displayHeight

    // Clear canvas
    ctx.clearRect(0, 0, displayWidth, displayHeight)

    // Lấy kích thước thật của frame (screenshot) từ webcam
    const videoElement = webcamRef.current?.video
    const srcWidth = videoElement?.videoWidth || 1280
    const srcHeight = videoElement?.videoHeight || 720

    const scaleX = displayWidth / srcWidth
    const scaleY = displayHeight / srcHeight

    // Vẽ skeleton cho tất cả người
    Object.entries(currentKeypoints).forEach(([personIdStr, keypoints]) => {
      const personId = Number(personIdStr)
      if (!keypoints || keypoints.length !== 17) return

      drawSkeleton(ctx, keypoints, scaleX, scaleY)
      drawPersonLabel(ctx, personId, keypoints, scaleX, scaleY)
    })
  }, [currentKeypoints, showSkeleton])

  useEffect(() => {
    if (!isRunning) return

    // Trong trình duyệt, setInterval trả về number, không phải NodeJS.Timeout
    let interval: number | null = null
    interval = window.setInterval(() => {
      // Đã có cờ `processing` trong captureAndProcess để tránh request chồng chéo
      captureAndProcess()
    }, 100) // 100ms ~ 10 FPS để giảm tải server, vẫn đủ mượt cho skeleton

    return () => {
      if (interval !== null) {
        window.clearInterval(interval)
      }
    }
  }, [isRunning]) // Remove captureAndProcess from deps để tránh re-render loop

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
  const effectivePersonIds = (stablePersonIds.length ? stablePersonIds : personIds)
  const activePid = selectedPersonId ?? (effectivePersonIds.length ? effectivePersonIds[0] : 0)
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
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user',
                  }}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                  onUserMedia={(stream) => {
                    // Log để debug kích thước video thực tế
                    const videoTrack = stream.getVideoTracks()[0]
                    const settings = videoTrack.getSettings()
                    console.log('Webcam video size:', settings.width, 'x', settings.height)
                  }}
                />
                {/* Canvas overlay cho skeleton */}
                <canvas
                  ref={canvasRef}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none',
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

              {/* Chọn thí sinh */}
              <TextField
                select
                fullWidth
                label="Thí sinh được chấm (tùy chọn)"
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                margin="normal"
                helperText="Liên kết session realtime với hồ sơ thí sinh trong database"
              >
                <MenuItem value="">-- Không chọn --</MenuItem>
                {candidates.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.full_name}
                  </MenuItem>
                ))}
              </TextField>

              {/* Chọn file audio cho beat detection (tùy chọn) */}
              <Box mt={2}>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Audio nhạc/khẩu lệnh cho kiểm tra nhịp (tùy chọn)
                </Typography>
                <Button
                  variant="outlined"
                  component="label"
                  size="small"
                  sx={{ mr: 1 }}
                >
                  Chọn file audio
                  <input
                    type="file"
                    accept="audio/*"
                    hidden
                    onChange={(e) => {
                      const file = e.target.files?.[0] || null
                      setAudioFile(file)
                    }}
                  />
                </Button>
                {audioFile && (
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    Đã chọn: {audioFile.name}
                  </Typography>
                )}
              </Box>

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

              <FormControlLabel
                control={
                  <Switch
                    checked={showSkeleton}
                    onChange={(e) => setShowSkeleton(e.target.checked)}
                  />
                }
                label="Hiển thị khớp xương"
                sx={{ mt: 1, display: 'block' }}
              />

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
                Frame: {frameNumber} • Số người đang được chấm: {totalPersons || (effectivePersonIds.length || 0)}
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

          {effectivePersonIds.length > 1 && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Chọn người (ID) đang xem
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {effectivePersonIds.map((pid) => (
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

