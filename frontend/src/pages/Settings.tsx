import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Divider,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Save,
  Refresh,
  Info,
  HelpOutline,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { configAPI } from '../services/api'

interface ScoringConfig {
  error_weights: Record<string, number>
  initial_score: number
  fail_threshold: number
  error_thresholds: Record<string, number>
  error_grouping: Record<string, any>
}

const ERROR_DESCRIPTIONS: Record<string, string> = {
  arm_angle: 'Góc tay (độ) - Lỗi khi tay không đúng góc so với golden template',
  leg_angle: 'Góc chân (độ) - Lỗi khi chân không đúng góc so với golden template',
  arm_height: 'Độ cao tay (pixel) - Lỗi khi tay quá cao hoặc quá thấp',
  leg_height: 'Độ cao chân (pixel) - Lỗi khi chân quá cao hoặc quá thấp',
  head_angle: 'Góc đầu (độ) - Lỗi khi đầu cúi hoặc ngẩng quá mức',
  torso_stability: 'Ổn định thân (0-1) - Lỗi khi thân người không ổn định',
  rhythm: 'Nhịp điệu (giây) - Lỗi khi không đúng nhịp với nhạc',
  distance: 'Khoảng cách (pixel) - Lỗi khi khoảng cách giữa các bộ phận không đúng',
  speed: 'Tốc độ (pixel/frame) - Lỗi khi di chuyển quá nhanh hoặc quá chậm',
}

export default function Settings() {
  const [config, setConfig] = useState<ScoringConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await configAPI.getScoringConfig()
      setConfig(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể tải cấu hình')
      toast.error('Không thể tải cấu hình')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!config) return

    setSaving(true)
    setError(null)
    try {
      await configAPI.updateScoringConfig({
        error_weights: config.error_weights,
        initial_score: config.initial_score,
        fail_threshold: config.fail_threshold,
        error_thresholds: config.error_thresholds,
        error_grouping: config.error_grouping,
      })
      toast.success('Cấu hình đã được lưu thành công!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể lưu cấu hình')
      toast.error('Không thể lưu cấu hình')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!window.confirm('Bạn có chắc chắn muốn reset cấu hình về mặc định?')) {
      return
    }

    setSaving(true)
    setError(null)
    try {
      const data = await configAPI.resetScoringConfig()
      setConfig(data.config)
      toast.success('Cấu hình đã được reset về mặc định!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Không thể reset cấu hình')
      toast.error('Không thể reset cấu hình')
    } finally {
      setSaving(false)
    }
  }

  const updateErrorWeight = (errorType: string, value: number) => {
    if (!config) return
    setConfig({
      ...config,
      error_weights: {
        ...config.error_weights,
        [errorType]: value,
      },
    })
  }

  const updateErrorThreshold = (errorType: string, value: number) => {
    if (!config) return
    setConfig({
      ...config,
      error_thresholds: {
        ...config.error_thresholds,
        [errorType]: value,
      },
    })
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Đang tải cấu hình...</Typography>
      </Box>
    )
  }

  if (!config) {
    return (
      <Box>
        <Alert severity="error">
          Không thể tải cấu hình. Vui lòng thử lại.
        </Alert>
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Cấu Hình Chấm Điểm
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleReset}
            disabled={saving}
          >
            Reset Mặc Định
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Đang Lưu...' : 'Lưu Cấu Hình'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* General Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Cấu Hình Chung
              </Typography>
              <Divider sx={{ my: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Điểm Ban Đầu"
                    type="number"
                    value={config.initial_score}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        initial_score: parseFloat(e.target.value) || 100,
                      })
                    }
                    helperText="Điểm số ban đầu khi bắt đầu chấm điểm"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Ngưỡng Đạt"
                    type="number"
                    value={config.fail_threshold}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        fail_threshold: parseFloat(e.target.value) || 50,
                      })
                    }
                    helperText="Điểm tối thiểu để đạt (chỉ áp dụng cho Testing mode)"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Weights */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Typography variant="h6">
                  Trọng Số Trừ Điểm (Error Weights)
                </Typography>
                <Tooltip title="Trọng số này quyết định mức độ trừ điểm cho mỗi loại lỗi. Giá trị càng cao, trừ điểm càng nhiều.">
                  <IconButton size="small">
                    <HelpOutline fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Loại Lỗi</strong></TableCell>
                      <TableCell align="right"><strong>Trọng Số</strong></TableCell>
                      <TableCell><strong>Mô Tả</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(config.error_weights).map(([errorType, weight]) => (
                      <TableRow key={errorType}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {errorType}
                            </Typography>
                            <Tooltip title={ERROR_DESCRIPTIONS[errorType] || 'Không có mô tả'}>
                              <IconButton size="small">
                                <Info fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <TextField
                            type="number"
                            value={weight}
                            onChange={(e) =>
                              updateErrorWeight(
                                errorType,
                                parseFloat(e.target.value) || 0
                              )
                            }
                            inputProps={{
                              min: 0,
                              max: 10,
                              step: 0.1,
                              style: { textAlign: 'right', width: '100px' },
                            }}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="textSecondary">
                            {ERROR_DESCRIPTIONS[errorType] || 'Không có mô tả'}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Thresholds */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Typography variant="h6">
                  Ngưỡng Phát Hiện Lỗi (Error Thresholds)
                </Typography>
                <Tooltip title="Ngưỡng này quyết định khi nào một lỗi được coi là đáng kể. Giá trị càng cao, càng khó phát hiện lỗi.">
                  <IconButton size="small">
                    <HelpOutline fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Loại Lỗi</strong></TableCell>
                      <TableCell align="right"><strong>Ngưỡng</strong></TableCell>
                      <TableCell><strong>Đơn Vị</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(config.error_thresholds).map(([errorType, threshold]) => (
                      <TableRow key={errorType}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {errorType}
                            </Typography>
                            <Tooltip title={ERROR_DESCRIPTIONS[errorType] || 'Không có mô tả'}>
                              <IconButton size="small">
                                <Info fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <TextField
                            type="number"
                            value={threshold}
                            onChange={(e) =>
                              updateErrorThreshold(
                                errorType,
                                parseFloat(e.target.value) || 0
                              )
                            }
                            inputProps={{
                              min: 0,
                              step: 0.1,
                              style: { textAlign: 'right', width: '120px' },
                            }}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="textSecondary">
                            {errorType.includes('angle') || errorType === 'head_angle'
                              ? 'độ'
                              : errorType === 'torso_stability' || errorType === 'rhythm'
                              ? '0-1'
                              : 'pixel'}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
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

