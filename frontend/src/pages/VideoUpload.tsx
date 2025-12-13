import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Alert,
  Grid,
  TextField,
  MenuItem,
  InputAdornment,
  Paper,
} from '@mui/material'
import {
  CloudUpload,
  VideoFile,
  CheckCircle,
  Visibility,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import ReactPlayer from 'react-player'

export default function VideoUpload() {
  const navigate = useNavigate()
  const { addSession, updateSession } = useSessionStore()
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'testing' | 'practising'>('testing')
  const [sessionId, setSessionId] = useState('')
  const [skeletonVideoUrl, setSkeletonVideoUrl] = useState<string | null>(null)
  const [showSkeletonVideo, setShowSkeletonVideo] = useState(false)
  const [videoError, setVideoError] = useState<string | null>(null)
  const [videoLoading, setVideoLoading] = useState(false)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv'],
    },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setUploadedFile(acceptedFiles[0])
      }
    },
    disabled: uploading,
  })

  const handleUpload = async () => {
    if (!uploadedFile) {
      toast.error('Vui lòng chọn file video')
      return
    }

    if (!sessionId.trim()) {
      toast.error('Vui lòng nhập Session ID')
      return
    }

    setUploading(true)
    setProgress(0)

    try {
      // Step 1: Start session
      toast.info('Đang khởi tạo session...')
      const sessionResult = await globalModeAPI.startSession(sessionId, mode)
      
      // Add session to store
      addSession({
        id: sessionId,
        mode,
        startTime: new Date(),
        score: 100,
        totalErrors: 0,
        status: 'active',
        audioSet: sessionResult.audio_set || false,
      })

      // Step 2: Upload and process video
      toast.info('Đang upload và xử lý video...')
      
      // Simulate progress (we don't have real progress from backend yet)
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 95) {
            clearInterval(progressInterval)
            return 95
          }
          return prev + 5
        })
      }, 500)

      const result = await globalModeAPI.uploadAndProcessVideo(sessionId, uploadedFile)
      
      clearInterval(progressInterval)
      setProgress(100)

      // Set skeleton video URL if available
      let skeletonVideoUrlFull = null
      if (result.skeleton_video_url) {
        const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        skeletonVideoUrlFull = `${apiBaseUrl}${result.skeleton_video_url}`
        console.log('✅ Skeleton video URL:', skeletonVideoUrlFull)
        setSkeletonVideoUrl(skeletonVideoUrlFull)
        setShowSkeletonVideo(true)
        setVideoLoading(true)
        setVideoError(null)
      } else {
        console.warn('⚠️ No skeleton video URL in response:', result)
        setVideoError('Video skeleton không được tạo. Có thể không phát hiện được keypoints.')
      }

      // Update session with results (including errors and skeleton video URL)
      updateSession(sessionId, {
        score: result.score || 100,
        totalErrors: result.total_errors || 0,
        status: 'completed',
        errors: result.errors || [],  // Store errors in session
        skeletonVideoUrl: skeletonVideoUrlFull,  // Store skeleton video URL
      })

      toast.success(
        `Xử lý hoàn tất! Đã phát hiện ${result.total_errors || 0} lỗi. Điểm: ${(result.score || 100).toFixed(1)}`
      )
      
      // Navigate to results page after a delay (allow user to see skeleton video)
      setTimeout(() => {
        navigate(`/results/${sessionId}`)
      }, 5000)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Có lỗi xảy ra khi upload và xử lý video')
      setProgress(0)
    } finally {
      setUploading(false)
    }
  }

  const generateSessionId = () => {
    const id = `session_${Date.now()}`
    setSessionId(id)
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Upload Video
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Chọn Video
              </Typography>
              
              <Box
                {...getRootProps()}
                sx={{
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'grey.300',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  backgroundColor: isDragActive ? 'primary.light' : 'grey.50',
                  transition: 'all 0.3s',
                  '&:hover': {
                    borderColor: 'primary.main',
                    backgroundColor: 'primary.light',
                  },
                }}
              >
                <input {...getInputProps()} />
                <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                {uploadedFile ? (
                  <Box>
                    <CheckCircle color="success" sx={{ fontSize: 48, mb: 1 }} />
                    <Typography variant="h6" gutterBottom>
                      {uploadedFile.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </Typography>
                  </Box>
                ) : (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      {isDragActive
                        ? 'Thả file vào đây...'
                        : 'Kéo thả video vào đây hoặc click để chọn'}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                      Hỗ trợ: MP4, AVI, MOV, MKV
                    </Typography>
                  </Box>
                )}
              </Box>

              {uploading && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress variant="determinate" value={progress} />
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                    Đang upload: {progress}%
                  </Typography>
                </Box>
              )}

              {/* Skeleton Video Preview */}
              {showSkeletonVideo && skeletonVideoUrl && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Video với Khớp Xương (Skeleton Overlay)
                  </Typography>
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
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {videoLoading && (
                        <Box sx={{ position: 'absolute', zIndex: 2 }}>
                          <CircularProgress />
                        </Box>
                      )}
                      {videoError && (
                        <Alert severity="error" sx={{ position: 'absolute', zIndex: 2, width: '90%' }}>
                          {videoError}
                        </Alert>
                      )}
                      <ReactPlayer
                        url={skeletonVideoUrl}
                        controls
                        playing={false}
                        width="100%"
                        height="100%"
                        onReady={() => {
                          console.log('✅ Skeleton video loaded successfully')
                          setVideoLoading(false)
                          setVideoError(null)
                        }}
                        onError={(error) => {
                          console.error('❌ Skeleton video error:', error)
                          setVideoError('Không thể tải video skeleton. Có thể do codec không được hỗ trợ hoặc file bị lỗi.')
                          setVideoLoading(false)
                        }}
                        onStart={() => {
                          console.log('▶️ Skeleton video started playing')
                          setVideoLoading(false)
                        }}
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
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                    Video này hiển thị khớp xương được phát hiện bởi mô hình YOLOv8-Pose. 
                    Mỗi khớp xương được vẽ bằng màu sắc khác nhau để dễ phân biệt.
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<Visibility />}
                    onClick={() => setShowSkeletonVideo(false)}
                    sx={{ mt: 1 }}
                  >
                    Ẩn Video
                  </Button>
                </Box>
              )}
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
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <Button size="small" onClick={generateSessionId}>
                        Tạo ID
                      </Button>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                select
                label="Chế Độ"
                value={mode}
                onChange={(e) => setMode(e.target.value as 'testing' | 'practising')}
                margin="normal"
              >
                <MenuItem value="testing">Testing</MenuItem>
                <MenuItem value="practising">Practising</MenuItem>
              </TextField>

              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleUpload}
                disabled={!uploadedFile || uploading || !sessionId}
                sx={{ mt: 3 }}
                startIcon={<VideoFile />}
              >
                {uploading ? 'Đang Upload...' : 'Upload & Xử Lý'}
              </Button>

              <Alert severity="info" sx={{ mt: 2 }}>
                Video sẽ được xử lý và chấm điểm tự động sau khi upload
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

