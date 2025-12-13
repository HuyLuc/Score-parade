import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useSessionStore } from '../../store/useSessionStore'
import { Box, Typography } from '@mui/material'

export default function ScoreChart() {
  const { sessions } = useSessionStore()

  const chartData = useMemo(() => {
    return sessions
      .filter((s) => s.status === 'completed')
      .slice(-10)
      .map((session, index) => ({
        name: `Session ${index + 1}`,
        score: session.score,
        errors: session.totalErrors,
      }))
  }, [sessions])

  if (chartData.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <Typography color="textSecondary">Chưa có dữ liệu để hiển thị</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis domain={[0, 100]} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#0ea5e9"
          strokeWidth={2}
          name="Điểm số"
        />
        <Line
          type="monotone"
          dataKey="errors"
          stroke="#ef4444"
          strokeWidth={2}
          name="Số lỗi"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

