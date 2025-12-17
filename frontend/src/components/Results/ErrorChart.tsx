import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Box, Typography } from '@mui/material'

interface Error {
  error_type?: string
  type?: string
  severity?: number
  [key: string]: any  // Allow additional properties
}

interface ErrorChartProps {
  errors: Error[]
}

export default function ErrorChart({ errors }: ErrorChartProps) {
  const chartData = useMemo(() => {
    const errorCounts: Record<string, number> = {}
    
    errors.forEach((error) => {
      // Support both 'error_type' and 'type' fields
      const errorType = (error as any).error_type || (error as any).type || 'unknown'
      errorCounts[errorType] = (errorCounts[errorType] || 0) + 1
    })

    return Object.entries(errorCounts).map(([type, count]) => ({
      type,
      count,
    }))
  }, [errors])

  if (chartData.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <Typography color="textSecondary">Chưa có dữ liệu lỗi để hiển thị</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="type" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="count" fill="#ef4444" name="Số lượng lỗi" />
      </BarChart>
    </ResponsiveContainer>
  )
}

