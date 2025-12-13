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
} from '@mui/material'
import {
  Download,
  ArrowBack,
  Assessment,
} from '@mui/icons-material'
import ReactPlayer from 'react-player'
import { globalModeAPI } from '../services/api'
import { useSessionStore } from '../store/useSessionStore'
import ErrorChart from '../components/Results/ErrorChart'
import { exportToPDF, exportToExcel } from '../utils/export'

interface Error {
  frame_number: number
  timestamp: number
  error_type: string
  severity: number
  description: string
}

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { getSession } = useSessionStore()
  const [errors, setErrors] = useState<Error[]>([])
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState(true)

  const session = sessionId ? getSession(sessionId) : null

  useEffect(() => {
    if (sessionId) {
      fetchResults()
    }
  }, [sessionId])

  const fetchResults = async () => {
    if (!sessionId) return

    setLoading(true)
    try {
      const [scoreData, errorsData] = await Promise.all([
        globalModeAPI.getScore(sessionId),
        globalModeAPI.getErrors(sessionId),
      ])

      setScore(scoreData.score)
      setErrors(errorsData.errors || [])
    } catch (error) {
      console.error('Error fetching results:', error)
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
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
          Kết Quả
        </Typography>
        <Card>
          <CardContent>
            <Typography>Vui lòng chọn một session để xem kết quả</Typography>
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
                      errors.map((error, index) => (
                        <TableRow key={index}>
                          <TableCell>{error.frame_number}</TableCell>
                          <TableCell>
                            {new Date(error.timestamp * 1000).toLocaleTimeString()}
                          </TableCell>
                          <TableCell>
                            <Chip label={error.error_type} size="small" />
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
                      ))
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

