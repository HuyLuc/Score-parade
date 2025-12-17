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
  Switch,
  FormControlLabel,
  MenuItem,
} from '@mui/material'
import {
  Save,
  Refresh,
  Info,
  HelpOutline,
} from '@mui/icons-material'
import { toast } from 'react-toastify'
import { configAPI } from '../services/api'

interface ErrorGroupingConfig {
  enabled: boolean
  min_sequence_length: number
  max_gap_frames: number
  severity_aggregation: string
  sequence_deduction: number
}

interface ScoringConfig {
  error_weights: Record<string, number>
  initial_score: number
  fail_threshold: number
  multi_person_enabled?: boolean
  error_thresholds: Record<string, number>
  error_grouping: ErrorGroupingConfig
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
        multi_person_enabled: config.multi_person_enabled,
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
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Cấu Hình Chấm Điểm
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Điều chỉnh mức độ khắt khe, chấm đa người và cách gộp lỗi. Mỗi lần bấm{' '}
            <strong>Lưu Cấu Hình</strong> hệ thống sẽ áp dụng ngay cho các phiên chấm điểm mới.
          </Typography>
        </Box>
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
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 14px 40px rgba(15,23,42,0.08)',
              border: '1px solid rgba(15,23,42,0.08)',
            }}
          >
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
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
                    helperText="Điểm số ban đầu trước khi trừ lỗi"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={!!config.multi_person_enabled}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            multi_person_enabled: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Bật chấm đa người (tự gắn ID và chấm riêng từng người)"
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1.5 }}>
                    Khi bật, hệ thống sẽ tự đếm số người trong khung hình, gán ID ổn định và trả điểm riêng cho từng người.
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Ngưỡng Đạt (Testing)"
                    type="number"
                    value={config.fail_threshold}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        fail_threshold: parseFloat(e.target.value) || 50,
                      })
                    }
                    helperText="Điểm tối thiểu để được coi là ĐẠT trong chế độ Testing. Practising luôn dùng để luyện tập, không trượt."
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Weights */}
        <Grid item xs={12}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 14px 40px rgba(15,23,42,0.08)',
              border: '1px solid rgba(15,23,42,0.08)',
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
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
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 14px 40px rgba(15,23,42,0.08)',
              border: '1px solid rgba(15,23,42,0.08)',
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
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

        {/* Error Grouping */}
        <Grid item xs={12}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 14px 40px rgba(15,23,42,0.08)',
              border: '1px solid rgba(15,23,42,0.08)',
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Gộp Chuỗi Lỗi Liên Tiếp (Error Grouping)
                </Typography>
                <Tooltip title="Giúp tránh trừ điểm nhiều lần cho cùng một động tác sai lặp lại liên tiếp.">
                  <IconButton size="small">
                    <HelpOutline fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={!!config.error_grouping?.enabled}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            error_grouping: {
                              ...config.error_grouping,
                              enabled: e.target.checked,
                            },
                          })
                        }
                      />
                    }
                    label="Bật gộp lỗi liên tiếp thành 1 lỗi"
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1.5 }}>
                    Khi bật, nhiều frame lỗi liền nhau sẽ được gộp lại và chỉ trừ điểm một lần cho cả chuỗi.
                  </Typography>
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Số Frame Tối Thiểu Tạo Chuỗi"
                    type="number"
                    value={config.error_grouping?.min_sequence_length ?? 2}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        error_grouping: {
                          ...config.error_grouping,
                          min_sequence_length: parseInt(e.target.value || '2', 10),
                        },
                      })
                    }
                    helperText="Ví dụ: 2 nghĩa là từ 2 frame lỗi liên tiếp trở lên mới gộp thành 1 lỗi."
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Số Frame Được Phép Hụt Trong Chuỗi"
                    type="number"
                    value={config.error_grouping?.max_gap_frames ?? 1}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        error_grouping: {
                          ...config.error_grouping,
                          max_gap_frames: parseInt(e.target.value || '1', 10),
                        },
                      })
                    }
                    helperText="Cho phép bỏ qua tối đa bao nhiêu frame sạch giữa chuỗi lỗi."
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    select
                    fullWidth
                    label="Cách tính điểm cho chuỗi lỗi"
                    value={config.error_grouping?.severity_aggregation || 'mean'}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        error_grouping: {
                          ...config.error_grouping,
                          severity_aggregation: e.target.value,
                        },
                      })
                    }
                    helperText="Chọn cách lấy điểm để trừ cho cả chuỗi lỗi."
                  >
                    <MenuItem value="mean">Lấy trung bình (nên dùng)</MenuItem>
                    <MenuItem value="max">Lấy lỗi nặng nhất trong chuỗi</MenuItem>
                    <MenuItem value="median">Lấy mức giữa (bỏ qua vài giá trị lệch)</MenuItem>
                  </TextField>
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Điểm Trừ Cho Mỗi Chuỗi Lỗi"
                    type="number"
                    value={config.error_grouping?.sequence_deduction ?? 1.0}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        error_grouping: {
                          ...config.error_grouping,
                          sequence_deduction: parseFloat(e.target.value || '1') || 1,
                        },
                      })
                    }
                    helperText="Điểm trừ áp dụng cho mỗi chuỗi lỗi (không phải từng frame)."
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

