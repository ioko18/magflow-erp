import React, { useState } from 'react'
import { Form, Input, Button, Card, Typography, Space, Alert } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

interface LoginForm {
  username: string
  password: string
}

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const onFinish = async (values: LoginForm) => {
    setLoading(true)
    setError('')

    try {
      // Call the login endpoint
      const api = (await import('../services/api')).default
      
      const response = await api.post('/auth/simple-login', {
        username: values.username,
        password: values.password
      }, {
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      const { access_token, refresh_token } = response.data
      
      // Store the tokens
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      localStorage.setItem('user', JSON.stringify({
        username: values.username,
        role: 'admin'
      }))
      
      // Set the default Authorization header for API calls
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      // Redirect to dashboard
      navigate('/dashboard')
    } catch (err) {
      setError('Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px',
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          borderRadius: '12px',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#1890ff', margin: 0 }}>
            MagFlow ERP
          </Title>
          <p style={{ color: '#666', margin: '8px 0 0 0' }}>
            Admin Dashboard
          </p>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
            closable
            onClose={() => setError('')}
          />
        )}

        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Please input your username!' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Username"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please input your password!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<LoginOutlined />}
              block
              style={{ height: 48, fontSize: 16 }}
            >
              Sign In
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Space direction="vertical" size="small">
            <div style={{ color: '#999', fontSize: 14 }}>
              Demo Credentials:
            </div>
            <div style={{ color: '#666', fontSize: 13 }}>
              Username: <strong>admin@magflow.local</strong>
            </div>
            <div style={{ color: '#666', fontSize: 13 }}>
              Password: <strong>secret</strong>
            </div>
          </Space>
        </div>
      </Card>
    </div>
  )
}

export default Login
