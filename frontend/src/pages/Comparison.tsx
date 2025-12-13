import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
} from '@mui/material'
import {
  CompareArrows,
  Assessment,
} from '@mui/icons-material'
import { useSessionStore } from '../store/useSessionStore'
import ComparisonChart from '../components/Comparison/ComparisonChart'
import ComparisonTable from '../components/Comparison/ComparisonTable'

export default function Comparison() {
  const { sessions } = useSessionStore()
  const [session1Id, setSession1Id] = useState('')
  const [session2Id, setSession2Id] = useState('')

  const completedSessions = sessions.filter((s) => s.status === 'completed')

  const session1 = session1Id ? sessions.find((s) => s.id === session1Id) : null
  const session2 = session2Id ? sessions.find((s) => s.id === session2Id) : null

  const canCompare = session1 && session2 && session1Id !== session2Id

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4, fontWeight: 700 }}>
        So Sánh Sessions
      </Typography>

      <Grid container spacing={3}>
        {/* Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Chọn Sessions Để So Sánh
              </Typography>
              <Grid container spacing={2} mt={1}>
                <Grid item xs={12} md={5}>
                  <FormControl fullWidth>
                    <InputLabel>Session 1</InputLabel>
                    <Select
                      value={session1Id}
                      onChange={(e) => setSession1Id(e.target.value)}
                      label="Session 1"
                    >
                      {completedSessions.map((session) => (
                        <MenuItem key={session.id} value={session.id}>
                          {session.id} - {session.score.toFixed(1)} điểm
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={2} display="flex" alignItems="center" justifyContent="center">
                  <CompareArrows sx={{ fontSize: 40, color: 'primary.main' }} />
                </Grid>
                <Grid item xs={12} md={5}>
                  <FormControl fullWidth>
                    <InputLabel>Session 2</InputLabel>
                    <Select
                      value={session2Id}
                      onChange={(e) => setSession2Id(e.target.value)}
                      label="Session 2"
                    >
                      {completedSessions.map((session) => (
                        <MenuItem key={session.id} value={session.id}>
                          {session.id} - {session.score.toFixed(1)} điểm
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              {!canCompare && (session1Id || session2Id) && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Vui lòng chọn 2 sessions khác nhau để so sánh
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Comparison Results */}
        {canCompare && session1 && session2 && (
          <>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Biểu Đồ So Sánh
                  </Typography>
                  <ComparisonChart session1={session1} session2={session2} />
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Bảng So Sánh Chi Tiết
                  </Typography>
                  <ComparisonTable session1={session1} session2={session2} />
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {completedSessions.length < 2 && (
          <Grid item xs={12}>
            <Alert severity="info">
              Cần ít nhất 2 sessions đã hoàn thành để so sánh. Hiện tại có {completedSessions.length} session(s).
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}

