import { useNavigate } from 'react-router-dom'
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Box,
  Chip,
} from '@mui/material'
import { ArrowForward, CheckCircle, StopCircle, PlayCircle } from '@mui/icons-material'
import { useSessionStore } from '../../store/useSessionStore'
import { format } from 'date-fns'

export default function RecentSessions() {
  const { sessions } = useSessionStore()
  const navigate = useNavigate()

  const recentSessions = sessions
    .sort((a, b) => {
      const timeA = typeof a.startTime === 'string' ? new Date(a.startTime).getTime() : a.startTime.getTime()
      const timeB = typeof b.startTime === 'string' ? new Date(b.startTime).getTime() : b.startTime.getTime()
      return timeB - timeA
    })
    .slice(0, 5)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />
      case 'stopped':
        return <StopCircle color="error" />
      default:
        return <PlayCircle color="primary" />
    }
  }

  const getStatusColor = (status: string): 'success' | 'error' | 'primary' => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'stopped':
        return 'error'
      default:
        return 'primary'
    }
  }

  if (recentSessions.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sessions Gần Đây
          </Typography>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <Typography color="textSecondary">Chưa có sessions</Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Sessions Gần Đây
        </Typography>
        <List>
          {recentSessions.map((session) => (
            <ListItem
              key={session.id}
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                mb: 1,
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(session.status)}
                    <Typography variant="subtitle1">{session.id}</Typography>
                    <Chip
                      label={session.status}
                      size="small"
                      color={getStatusColor(session.status)}
                    />
                  </Box>
                }
                secondary={
                  <>
                    <Typography variant="body2" color="textSecondary">
                      {format(
                        typeof session.startTime === 'string' 
                          ? new Date(session.startTime) 
                          : session.startTime, 
                        'dd/MM/yyyy HH:mm'
                      )}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Điểm: {session.score.toFixed(1)} | Lỗi: {session.totalErrors}
                    </Typography>
                  </>
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  onClick={() => navigate(`/results/${session.id}`)}
                >
                  <ArrowForward />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  )
}

