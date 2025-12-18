import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
} from '@mui/material'
import { Info } from '@mui/icons-material'
import { toast } from 'react-toastify'
import { baremAPI } from '../services/api'

interface Criterion {
  id: string
  name: string
  description: string
  error_type: string
  weight: number
  threshold: number
  deduction_per_error: number
  examples: string[]
}

export default function Barem() {
  const [criteria, setCriteria] = useState<Criterion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBarem()
  }, [])

  const fetchBarem = async () => {
    setLoading(true)
    try {
      const data = await baremAPI.getBarem()
      setCriteria(data)
    } catch (err: any) {
      toast.error('Không thể tải barem')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 800 }}>
          Barem Chấm Điểm
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Xem các tiêu chí chấm điểm và điểm trừ cho từng loại lỗi
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Lưu ý:</strong> Điểm ban đầu là 100 điểm. Mỗi lỗi sẽ bị trừ điểm theo trọng số và mức độ nghiêm trọng.
          Điểm trừ = Trọng số × Mức độ nghiêm trọng (severity).
        </Typography>
      </Alert>

      <Card>
        <CardContent>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Tiêu chí</strong></TableCell>
                  <TableCell><strong>Mô tả</strong></TableCell>
                  <TableCell align="center"><strong>Trọng số</strong></TableCell>
                  <TableCell align="center"><strong>Ngưỡng</strong></TableCell>
                  <TableCell align="center"><strong>Điểm trừ/Lỗi</strong></TableCell>
                  <TableCell><strong>Ví dụ lỗi</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      Đang tải...
                    </TableCell>
                  </TableRow>
                ) : criteria.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      Không có dữ liệu
                    </TableCell>
                  </TableRow>
                ) : (
                  criteria.map((criterion) => (
                    <TableRow key={criterion.id}>
                      <TableCell>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          {criterion.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {criterion.description}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={criterion.weight.toFixed(1)}
                          color={criterion.weight >= 1.0 ? 'error' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">
                          {typeof criterion.threshold === 'number'
                            ? criterion.threshold.toFixed(1)
                            : criterion.threshold}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="error" sx={{ fontWeight: 600 }}>
                          -{criterion.deduction_per_error.toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box>
                          {criterion.examples.map((example, idx) => (
                            <Typography
                              key={idx}
                              variant="caption"
                              display="block"
                              color="text.secondary"
                            >
                              • {example}
                            </Typography>
                          ))}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
            <Info sx={{ verticalAlign: 'middle', mr: 1 }} />
            Giải Thích
          </Typography>
          <Box component="ul" sx={{ pl: 2 }}>
            <li>
              <strong>Trọng số:</strong> Hệ số nhân cho điểm trừ. Trọng số càng cao, lỗi càng nghiêm trọng.
            </li>
            <li>
              <strong>Ngưỡng:</strong> Giá trị sai lệch tối đa cho phép. Vượt quá ngưỡng này sẽ bị tính là lỗi.
            </li>
            <li>
              <strong>Điểm trừ/Lỗi:</strong> Điểm trừ trung bình cho mỗi lỗi (trọng số × severity trung bình).
            </li>
            <li>
              <strong>Điểm trượt:</strong> Dưới 50 điểm trong chế độ kiểm tra sẽ bị trượt và kết thúc kiểm tra.
            </li>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}

