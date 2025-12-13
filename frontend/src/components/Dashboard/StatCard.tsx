import { Card, CardContent, Box, Typography, useTheme } from '@mui/material'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  color: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
}

export default function StatCard({ title, value, icon, color }: StatCardProps) {
  const theme = useTheme()
  const colorValue = theme.palette[color].main
  
  return (
    <Card
      sx={{
        height: '100%',
        background: `linear-gradient(135deg, ${colorValue}15 0%, ${colorValue}05 100%)`,
        border: `1px solid ${colorValue}30`,
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
              {value}
            </Typography>
          </Box>
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              backgroundColor: `${color}.main`,
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

