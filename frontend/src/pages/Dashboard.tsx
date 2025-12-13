import { useEffect, useState } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
} from '@mui/material'
import {
  TrendingUp,
  Assessment,
  Videocam,
  History,
} from '@mui/icons-material'
import { useSessionStore } from '../store/useSessionStore'
import { healthCheck } from '../services/api'
import StatCard from '../components/Dashboard/StatCard'
import RecentSessions from '../components/Dashboard/RecentSessions'
import ScoreChart from '../components/Dashboard/ScoreChart'

export default function Dashboard() {
  const { sessions } = useSessionStore()
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'unhealthy' | 'checking'>('checking')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck()
        setHealthStatus('healthy')
      } catch (error) {
        setHealthStatus('unhealthy')
      } finally {
        setLoading(false)
      }
    }
    checkHealth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const activeSessions = sessions.filter((s) => s.status === 'active').length
  const completedSessions = sessions.filter((s) => s.status === 'completed').length
  const averageScore =
    sessions.length > 0
      ? sessions.reduce((sum, s) => sum + s.score, 0) / sessions.length
      : 0

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stat Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Sessions Hoạt Động"
            value={activeSessions}
            icon={<Videocam />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Sessions Hoàn Thành"
            value={completedSessions}
            icon={<History />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Điểm Trung Bình"
            value={averageScore.toFixed(1)}
            icon={<TrendingUp />}
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Tổng Sessions"
            value={sessions.length}
            icon={<Assessment />}
            color="secondary"
          />
        </Grid>

        {/* Charts */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Biểu Đồ Điểm Số
              </Typography>
              <ScoreChart />
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Sessions */}
        <Grid item xs={12} md={4}>
          <RecentSessions />
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Trạng Thái Hệ Thống
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor:
                      healthStatus === 'healthy' ? 'success.main' : 'error.main',
                  }}
                />
                <Typography>
                  Backend API:{' '}
                  {healthStatus === 'healthy' ? 'Hoạt động bình thường' : 'Không kết nối được'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

