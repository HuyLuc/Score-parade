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
} from '@mui/material'
import {
  CloudUpload,
  VideoFile,
  CheckCircle,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'

export default function VideoUpload() {
  const navigate = useNavigate()
  const { addSession } = useSessionStore()
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'testing' | 'practising'>('testing')
  const [sessionId, setSessionId] = useState('')

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
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      // Start session
      const result = await globalModeAPI.startSession(sessionId, mode)
      
      clearInterval(progressInterval)
      setProgress(100)

      // Add session to store
      addSession({
        id: sessionId,
        mode,
        startTime: new Date(),
        score: 100,
        totalErrors: 0,
        status: 'active',
        audioSet: result.audio_set || false,
      })

      toast.success('Upload thành công! Đang xử lý video...')
      
      // Navigate to results page
      setTimeout(() => {
        navigate(`/results/${sessionId}`)
      }, 1000)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Có lỗi xảy ra khi upload')
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
                    <Button size="small" onClick={generateSessionId}>
                      Tạo ID
                    </Button>
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

