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
      <Box
        sx={{
          mb: 4,
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 800 }}>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Tổng quan hệ thống và các phiên chấm điểm gần đây
        </Typography>
      </Box>

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
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 12px 40px rgba(15, 23, 42, 0.08)',
              border: '1px solid rgba(37,99,235,0.08)',
            }}
          >
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                Biểu Đồ Điểm Số
              </Typography>
              <ScoreChart />
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Sessions */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              height: '100%',
              borderRadius: 3,
              boxShadow: '0 12px 40px rgba(15, 23, 42, 0.08)',
              border: '1px solid rgba(37,99,235,0.08)',
            }}
          >
            <CardContent sx={{ height: '100%' }}>
              <RecentSessions />
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 12px 40px rgba(15, 23, 42, 0.08)',
              border: '1px solid rgba(16,185,129,0.16)',
              background: 'linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.06))',
            }}
          >
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
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

