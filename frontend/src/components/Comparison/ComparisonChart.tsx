import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Session } from '../../store/useSessionStore'

interface ComparisonChartProps {
  session1: Session
  session2: Session
}

export default function ComparisonChart({ session1, session2 }: ComparisonChartProps) {
  const data = [
    {
      name: 'Điểm Số',
      'Session 1': session1.score,
      'Session 2': session2.score,
    },
    {
      name: 'Tổng Lỗi',
      'Session 1': session1.totalErrors,
      'Session 2': session2.totalErrors,
    },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="Session 1" fill="#0ea5e9" />
        <Bar dataKey="Session 2" fill="#8b5cf6" />
      </BarChart>
    </ResponsiveContainer>
  )
}

