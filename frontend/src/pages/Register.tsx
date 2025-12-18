import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  Grid,
} from '@mui/material'
import { PersonAdd } from '@mui/icons-material'
import { toast } from 'react-toastify'
import { authAPI } from '../services/api'

export default function Register() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    age: '',
    rank: '',
    insignia: '',
    gender: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp')
      return
    }

    if (formData.password.length < 6) {
      setError('Mật khẩu phải có ít nhất 6 ký tự')
      return
    }

    setLoading(true)

    try {
      await authAPI.register({
        username: formData.username,
        password: formData.password,
        full_name: formData.full_name || undefined,
        age: formData.age ? parseInt(formData.age) : undefined,
        rank: formData.rank || undefined,
        insignia: formData.insignia || undefined,
        gender: formData.gender || undefined,
      })
      toast.success('Đăng ký thành công! Vui lòng đăng nhập.')
      navigate('/login')
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Đăng ký thất bại'
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="md">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          py: 4,
        }}
      >
        <Card sx={{ width: '100%' }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <PersonAdd sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
                Đăng Ký Tài Khoản
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Tạo tài khoản mới để sử dụng hệ thống
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Tên đăng nhập *"
                    value={formData.username}
                    onChange={handleChange('username')}
                    required
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Họ và tên"
                    value={formData.full_name}
                    onChange={handleChange('full_name')}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Mật khẩu *"
                    type="password"
                    value={formData.password}
                    onChange={handleChange('password')}
                    required
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Xác nhận mật khẩu *"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={handleChange('confirmPassword')}
                    required
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Tuổi"
                    type="number"
                    value={formData.age}
                    onChange={handleChange('age')}
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Cấp bậc"
                    value={formData.rank}
                    onChange={handleChange('rank')}
                    placeholder="VD: Đại đội trưởng"
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Quân hàm"
                    value={formData.insignia}
                    onChange={handleChange('insignia')}
                    placeholder="VD: Đại uý"
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Giới tính"
                    value={formData.gender}
                    onChange={handleChange('gender')}
                    SelectProps={{ native: true }}
                  >
                    <option value="">Chọn giới tính</option>
                    <option value="male">Nam</option>
                    <option value="female">Nữ</option>
                    <option value="other">Khác</option>
                  </TextField>
                </Grid>
              </Grid>

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ mt: 3, mb: 2 }}
                startIcon={<PersonAdd />}
              >
                {loading ? 'Đang đăng ký...' : 'Đăng Ký'}
              </Button>

              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Đã có tài khoản?{' '}
                  <Link to="/login" style={{ color: 'inherit', textDecoration: 'underline' }}>
                    Đăng nhập ngay
                  </Link>
                </Typography>
              </Box>
            </form>
          </CardContent>
        </Card>
      </Box>
    </Container>
  )
}

