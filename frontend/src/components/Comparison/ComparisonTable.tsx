import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
} from '@mui/material'
import { Session } from '../../store/useSessionStore'
import { format } from 'date-fns'

interface ComparisonTableProps {
  session1: Session
  session2: Session
}

export default function ComparisonTable({ session1, session2 }: ComparisonTableProps) {
  const formatStartTime = (startTime: Date | string) => {
    const date = typeof startTime === 'string' ? new Date(startTime) : startTime
    return format(date, 'dd/MM/yyyy HH:mm')
  }

  const rows = [
    { label: 'Session ID', value1: session1.id, value2: session2.id },
    { label: 'Chế Độ', value1: session1.mode, value2: session2.mode },
    { label: 'Thời Gian Bắt Đầu', value1: formatStartTime(session1.startTime), value2: formatStartTime(session2.startTime) },
    { label: 'Điểm Số', value1: session1.score.toFixed(1), value2: session2.score.toFixed(1) },
    { label: 'Tổng Lỗi', value1: session1.totalErrors, value2: session2.totalErrors },
    { label: 'Trạng Thái', value1: session1.status, value2: session2.status },
  ]

  const scoreDiff = session1.score - session2.score
  const errorDiff = session1.totalErrors - session2.totalErrors

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Tiêu Chí</TableCell>
            <TableCell align="center">Session 1</TableCell>
            <TableCell align="center">Session 2</TableCell>
            <TableCell align="center">Chênh Lệch</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => {
            const isScore = row.label === 'Điểm Số'
            const isError = row.label === 'Tổng Lỗi'
            const diff = isScore ? scoreDiff : isError ? errorDiff : null

            return (
              <TableRow key={row.label}>
                <TableCell component="th" scope="row">
                  <strong>{row.label}</strong>
                </TableCell>
                <TableCell align="center">{row.value1}</TableCell>
                <TableCell align="center">{row.value2}</TableCell>
                <TableCell align="center">
                  {diff !== null && (
                    <Box
                      sx={{
                        color: diff > 0 ? 'success.main' : diff < 0 ? 'error.main' : 'text.secondary',
                        fontWeight: 600,
                      }}
                    >
                      {diff > 0 ? '+' : ''}{diff.toFixed(1)}
                    </Box>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

