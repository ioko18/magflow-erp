import React, { useEffect, useState } from 'react'
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Button,
  Tag,
  Space,
  Spin,
  Alert,
  notification
} from 'antd'
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ShopOutlined,
  UsergroupAddOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { formatDistanceToNow } from 'date-fns'
import api from '../../services/api'
import DashboardCharts from '../../components/dashboard/DashboardCharts'

const { Title, Text } = Typography

interface DashboardData {
  totalSales: number
  totalOrders: number
  totalCustomers: number
  emagProducts: number
  inventoryValue: number
  salesGrowth: number
  ordersGrowth: number
  customersGrowth: number
  emagGrowth: number
  systemHealth: {
    database: 'healthy' | 'warning' | 'error'
    api: 'healthy' | 'warning' | 'error'
    emag: 'healthy' | 'warning' | 'error'
  }
  salesData?: Array<{
    name: string
    sales: number
    orders: number
    profit: number
  }>
  topProducts?: Array<{
    name: string
    value: number
    sales: number
  }>
  inventoryStatus?: Array<{
    category: string
    inStock: number
    lowStock: number
    outOfStock: number
  }>
}

const DEFAULT_DASHBOARD_DATA: DashboardData = {
  totalSales: 0,
  totalOrders: 0,
  totalCustomers: 0,
  emagProducts: 0,
  inventoryValue: 0,
  salesGrowth: 0,
  ordersGrowth: 0,
  customersGrowth: 0,
  emagGrowth: 0,
  systemHealth: {
    database: 'healthy',
    api: 'healthy',
    emag: 'healthy'
  }
}

const Dashboard: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification()
  const [data, setData] = useState<DashboardData>(DEFAULT_DASHBOARD_DATA)
  const [loading, setLoading] = useState(true)
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null)

  useEffect(() => {
    fetchDashboardData()
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchDashboardData, 300000)
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await api.get('/admin/dashboard')
      
      if (response.data?.status === 'success' && response.data?.data) {
        setData({
          ...DEFAULT_DASHBOARD_DATA,
          ...response.data.data
        })
        setLastRefreshTime(new Date())
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      notificationApi.error({
        message: 'Eroare la încărcarea datelor',
        description: 'Nu s-au putut încărca datele dashboard-ului',
        duration: 4
      })
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchDashboardData()
    notificationApi.success({
      message: 'Date actualizate',
      description: 'Dashboard-ul a fost actualizat cu succes',
      duration: 2
    })
  }

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#52c41a'
      case 'warning': return '#faad14'
      case 'error': return '#ff4d4f'
      default: return '#d9d9d9'
    }
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircleOutlined />
      case 'warning': return <ExclamationCircleOutlined />
      case 'error': return <CloseCircleOutlined />
      default: return <InfoCircleOutlined />
    }
  }

  const lastRefreshLabel = lastRefreshTime
    ? `Actualizat ${formatDistanceToNow(lastRefreshTime, { addSuffix: true })}`
    : 'Niciodată actualizat'

  return (
    <div className="dashboard" style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {contextHolder}
      
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={2} style={{ margin: 0, color: '#001529' }}>
              Dashboard MagFlow ERP
            </Title>
            <Text type="secondary" style={{ fontSize: '14px' }}>
              Bine ați venit! Monitorizați performanța afacerii dvs.
            </Text>
          </div>
          <Space>
            <Tag icon={<ClockCircleOutlined />} color="blue">
              {lastRefreshLabel}
            </Tag>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh}
              loading={loading}
              type="primary"
            >
              Actualizează
            </Button>
          </Space>
        </div>

        {/* System Health Status */}
        <Alert
          message="Status Sistem"
          description={
            <Space size="large">
              <Space>
                {getHealthIcon(data.systemHealth.database)}
                <span style={{ color: getHealthColor(data.systemHealth.database) }}>
                  Bază de date: {data.systemHealth.database === 'healthy' ? 'Sănătos' : data.systemHealth.database === 'warning' ? 'Atenție' : 'Eroare'}
                </span>
              </Space>
              <Space>
                {getHealthIcon(data.systemHealth.api)}
                <span style={{ color: getHealthColor(data.systemHealth.api) }}>
                  API: {data.systemHealth.api === 'healthy' ? 'Sănătos' : data.systemHealth.api === 'warning' ? 'Atenție' : 'Eroare'}
                </span>
              </Space>
              <Space>
                {getHealthIcon(data.systemHealth.emag)}
                <span style={{ color: getHealthColor(data.systemHealth.emag) }}>
                  eMAG: {data.systemHealth.emag === 'healthy' ? 'Sănătos' : data.systemHealth.emag === 'warning' ? 'Atenție' : 'Eroare'}
                </span>
              </Space>
            </Space>
          }
          type={
            data.systemHealth.database === 'error' || data.systemHealth.api === 'error' || data.systemHealth.emag === 'error'
              ? 'error'
              : data.systemHealth.database === 'warning' || data.systemHealth.api === 'warning' || data.systemHealth.emag === 'warning'
              ? 'warning'
              : 'success'
          }
          showIcon
          style={{ marginBottom: 24 }}
        />
      </div>

      {/* Key Metrics Cards */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {/* Vânzări Totale */}
          <Col xs={24} sm={12} lg={8} xl={4.8}>
            <Card 
              hoverable
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <Statistic
                title={<span style={{ fontSize: '14px', fontWeight: 500 }}>Vânzări Totale</span>}
                value={data.totalSales}
                precision={2}
                prefix={<DollarOutlined style={{ color: '#3f8600' }} />}
                suffix="RON"
                valueStyle={{ color: '#3f8600', fontSize: '24px', fontWeight: 'bold' }}
              />
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #f0f0f0' }}>
                {data.salesGrowth >= 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 6, fontSize: '16px' }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 6, fontSize: '16px' }} />
                )}
                <span style={{ 
                  color: data.salesGrowth >= 0 ? '#3f8600' : '#cf1322',
                  fontSize: '13px',
                  fontWeight: 500
                }}>
                  {data.salesGrowth >= 0 ? '+' : ''}{data.salesGrowth.toFixed(1)}% față de luna trecută
                </span>
              </div>
            </Card>
          </Col>

          {/* Număr Comenzi */}
          <Col xs={24} sm={12} lg={8} xl={4.8}>
            <Card 
              hoverable
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <Statistic
                title={<span style={{ fontSize: '14px', fontWeight: 500 }}>Număr Comenzi</span>}
                value={data.totalOrders}
                prefix={<ShopOutlined style={{ color: '#1890ff' }} />}
                valueStyle={{ color: '#1890ff', fontSize: '24px', fontWeight: 'bold' }}
              />
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #f0f0f0' }}>
                {data.ordersGrowth >= 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 6, fontSize: '16px' }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 6, fontSize: '16px' }} />
                )}
                <span style={{ 
                  color: data.ordersGrowth >= 0 ? '#3f8600' : '#cf1322',
                  fontSize: '13px',
                  fontWeight: 500
                }}>
                  {data.ordersGrowth >= 0 ? '+' : ''}{data.ordersGrowth.toFixed(1)}% față de luna trecută
                </span>
              </div>
            </Card>
          </Col>

          {/* Număr Clienți */}
          <Col xs={24} sm={12} lg={8} xl={4.8}>
            <Card 
              hoverable
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <Statistic
                title={<span style={{ fontSize: '14px', fontWeight: 500 }}>Număr Clienți</span>}
                value={data.totalCustomers}
                prefix={<UsergroupAddOutlined style={{ color: '#722ed1' }} />}
                valueStyle={{ color: '#722ed1', fontSize: '24px', fontWeight: 'bold' }}
              />
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #f0f0f0' }}>
                {data.customersGrowth >= 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 6, fontSize: '16px' }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 6, fontSize: '16px' }} />
                )}
                <span style={{ 
                  color: data.customersGrowth >= 0 ? '#3f8600' : '#cf1322',
                  fontSize: '13px',
                  fontWeight: 500
                }}>
                  {data.customersGrowth >= 0 ? '+' : ''}{data.customersGrowth.toFixed(1)}% față de luna trecută
                </span>
              </div>
            </Card>
          </Col>

          {/* Produse eMAG */}
          <Col xs={24} sm={12} lg={8} xl={4.8}>
            <Card 
              hoverable
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <Statistic
                title={<span style={{ fontSize: '14px', fontWeight: 500 }}>Produse eMAG</span>}
                value={data.emagProducts}
                prefix={<ApiOutlined style={{ color: '#fa8c16' }} />}
                valueStyle={{ color: '#fa8c16', fontSize: '24px', fontWeight: 'bold' }}
              />
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #f0f0f0' }}>
                {data.emagGrowth >= 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 6, fontSize: '16px' }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 6, fontSize: '16px' }} />
                )}
                <span style={{ 
                  color: data.emagGrowth >= 0 ? '#3f8600' : '#cf1322',
                  fontSize: '13px',
                  fontWeight: 500
                }}>
                  {data.emagGrowth >= 0 ? '+' : ''}{data.emagGrowth.toFixed(1)}% față de luna trecută
                </span>
              </div>
            </Card>
          </Col>

          {/* Valoare Stocuri */}
          <Col xs={24} sm={12} lg={8} xl={4.8}>
            <Card 
              hoverable
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
            >
              <Statistic
                title={<span style={{ fontSize: '14px', fontWeight: 500 }}>Valoare Stocuri</span>}
                value={data.inventoryValue}
                precision={2}
                prefix={<DatabaseOutlined style={{ color: '#13c2c2' }} />}
                suffix="RON"
                valueStyle={{ color: '#13c2c2', fontSize: '24px', fontWeight: 'bold' }}
              />
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid #f0f0f0' }}>
                <InfoCircleOutlined style={{ color: '#8c8c8c', marginRight: 6, fontSize: '16px' }} />
                <span style={{ 
                  color: '#8c8c8c',
                  fontSize: '13px',
                  fontWeight: 500
                }}>
                  Valoare totală inventar
                </span>
              </div>
            </Card>
          </Col>
        </Row>
      </Spin>

      {/* Dashboard Charts */}
      <DashboardCharts
        salesData={data.salesData}
        topProducts={data.topProducts}
        inventoryStatus={data.inventoryStatus}
      />

      {/* Info Section */}
      <div style={{ marginTop: 32 }}>
        <Card 
          title={<span style={{ fontSize: '16px', fontWeight: 600 }}>Informații Dashboard</span>}
          style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Alert
              message="Dashboard Simplificat"
              description="Acest dashboard afișează cele 5 metrici cheie ale afacerii dvs. Funcționalități suplimentare (grafice, rapoarte detaliate, analize) vor fi adăugate treptat în versiunile viitoare."
              type="info"
              showIcon
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
              <Card size="small" style={{ background: '#f6ffed', border: '1px solid #b7eb8f' }}>
                <Space>
                  <ThunderboltOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                  <div>
                    <Text strong>Date în Timp Real</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>Toate metricile sunt calculate din baza de date</Text>
                  </div>
                </Space>
              </Card>
              <Card size="small" style={{ background: '#e6f7ff', border: '1px solid #91d5ff' }}>
                <Space>
                  <InfoCircleOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
                  <div>
                    <Text strong>Auto-Refresh</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>Datele se actualizează automat la fiecare 5 minute</Text>
                  </div>
                </Space>
              </Card>
              <Card size="small" style={{ background: '#fff7e6', border: '1px solid #ffd591' }}>
                <Space>
                  <ExclamationCircleOutlined style={{ fontSize: '20px', color: '#fa8c16' }} />
                  <div>
                    <Text strong>Monitorizare Sistem</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>Status în timp real pentru DB, API și eMAG</Text>
                  </div>
                </Space>
              </Card>
            </div>
          </Space>
        </Card>
      </div>
    </div>
  )
}

export default Dashboard
