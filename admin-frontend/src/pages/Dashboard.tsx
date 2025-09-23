import React, { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Progress, Table, Typography, Space, Button, notification } from 'antd'
import {
  ShoppingCartOutlined,
  DollarOutlined,
  UserOutlined,
  LinkOutlined,
  SyncOutlined,
  EyeOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined
} from '@ant-design/icons'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import axios from 'axios'

const { Title } = Typography

interface DashboardData {
  totalSales: number
  totalOrders: number
  totalCustomers: number
  emagProducts: number
  inventoryValue: number
  syncStatus: string
  recentOrders: any[]
  salesData: any[]
  topProducts: any[]
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData>({
    totalSales: 0,
    totalOrders: 0,
    totalCustomers: 0,
    emagProducts: 0,
    inventoryValue: 0,
    syncStatus: 'unknown',
    recentOrders: [],
    salesData: [],
    topProducts: []
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)

      // Fetch dashboard data from API
      const response = await axios.get('/api/v1/admin/dashboard')
      setData(response.data.data)

      notification.success({
        message: 'Dashboard Updated',
        description: 'Latest data loaded successfully',
      })
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      notification.error({
        message: 'Dashboard Error',
        description: 'Failed to load dashboard data',
      })

      // Use mock data for development
      setData({
        totalSales: 45670.89,
        totalOrders: 234,
        totalCustomers: 89,
        emagProducts: 10,
        inventoryValue: 123400.50,
        syncStatus: 'success',
        recentOrders: [
          { id: 1, customer: 'John Doe', amount: 299.99, status: 'completed', date: '2024-01-15' },
          { id: 2, customer: 'Jane Smith', amount: 149.50, status: 'processing', date: '2024-01-15' },
          { id: 3, customer: 'Bob Johnson', amount: 79.99, status: 'shipped', date: '2024-01-14' },
        ],
        salesData: [
          { name: 'Jan', sales: 4000, orders: 24 },
          { name: 'Feb', sales: 3000, orders: 18 },
          { name: 'Mar', sales: 2000, orders: 12 },
          { name: 'Apr', sales: 2780, orders: 15 },
          { name: 'May', sales: 1890, orders: 11 },
          { name: 'Jun', sales: 2390, orders: 16 },
        ],
        topProducts: [
          { name: 'iPhone 15', value: 35, sales: 15420 },
          { name: 'MacBook Pro', value: 25, sales: 28900 },
          { name: 'iPad Air', value: 20, sales: 8750 },
          { name: 'AirPods Pro', value: 20, sales: 3240 },
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSyncEmag = async () => {
    try {
      await axios.post('/api/v1/emag/sync')
      notification.success({
        message: 'eMAG Sync Started',
        description: 'Synchronization process initiated',
      })
    } catch (error) {
      notification.error({
        message: 'Sync Failed',
        description: 'Failed to start eMAG synchronization',
      })
    }
  }

  return (
    <div className="dashboard">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>Dashboard</Title>
        <p style={{ color: '#666' }}>Welcome to MagFlow ERP Admin Dashboard</p>
      </div>

      {/* Key Metrics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Sales"
              value={data.totalSales}
              prefix={<DollarOutlined />}
              suffix="RON"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Orders"
              value={data.totalOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Customers"
              value={data.totalCustomers}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="eMAG Products"
              value={data.emagProducts}
              prefix={<LinkOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Sales Chart */}
        <Col xs={24} lg={12}>
          <Card
            title="Sales Overview"
            extra={
              <Button type="primary" size="small" onClick={handleSyncEmag}>
                <SyncOutlined /> Sync eMAG
              </Button>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={data.salesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="sales" stroke="#1890ff" fill="#1890ff" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* Product Distribution */}
        <Col xs={24} lg={12}>
          <Card title="Top Products">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data.topProducts}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {data.topProducts.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Recent Orders Table */}
      <Row style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="Recent Orders">
            <Table
              dataSource={data.recentOrders}
              columns={[
                {
                  title: 'Order ID',
                  dataIndex: 'id',
                  key: 'id',
                },
                {
                  title: 'Customer',
                  dataIndex: 'customer',
                  key: 'customer',
                },
                {
                  title: 'Amount',
                  dataIndex: 'amount',
                  key: 'amount',
                  render: (amount) => `$${amount}`,
                },
                {
                  title: 'Status',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status) => (
                    <span style={{
                      color: status === 'completed' ? '#52c41a' :
                             status === 'processing' ? '#1890ff' : '#fa8c16'
                    }}>
                      {status}
                    </span>
                  ),
                },
                {
                  title: 'Date',
                  dataIndex: 'date',
                  key: 'date',
                },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
