import React, { useEffect, useState } from 'react'
import { Row, Col, Card, Button, Table, Typography, Space, Badge, Progress, notification, Tag } from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
  EyeOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import axios from 'axios'

const { Title } = Typography

interface SyncRecord {
  sync_id: string
  status: string
  total_offers_processed: number
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
}

interface EmagData {
  total_products: number
  total_offers: number
  recent_syncs: SyncRecord[]
}

const EmagSync: React.FC = () => {
  const [data, setData] = useState<EmagData>({
    total_products: 0,
    total_offers: 0,
    recent_syncs: []
  })
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    fetchEmagData()
  }, [])

  const fetchEmagData = async () => {
    try {
      setLoading(true)
      const response = await axios.get('/api/v1/emag/status')
      setData(response.data.data)
    } catch (error) {
      console.error('Error fetching eMAG data:', error)
      notification.error({
        message: 'Error',
        description: 'Failed to load eMAG data',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      await axios.post('/api/v1/emag/sync')
      notification.success({
        message: 'Sync Started',
        description: 'eMAG synchronization has been initiated',
      })

      // Refresh data after a short delay
      setTimeout(() => {
        fetchEmagData()
      }, 2000)

    } catch (error) {
      notification.error({
        message: 'Sync Failed',
        description: 'Failed to start eMAG synchronization',
      })
    } finally {
      setSyncing(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      default:
        return <ClockCircleOutlined style={{ color: '#fa8c16' }} />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'green'
      case 'running':
        return 'blue'
      case 'failed':
        return 'red'
      default:
        return 'orange'
    }
  }

  const columns = [
    {
      title: 'Sync ID',
      dataIndex: 'sync_id',
      key: 'sync_id',
      render: (sync_id: string) => sync_id.substring(0, 12) + '...',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>
            {status.toUpperCase()}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Offers Processed',
      dataIndex: 'total_offers_processed',
      key: 'total_offers_processed',
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Duration',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (seconds: number | null) =>
        seconds ? `${Math.round(seconds)}s` : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Space>
          <Button icon={<EyeOutlined />} size="small">
            View
          </Button>
          <Button icon={<DownloadOutlined />} size="small">
            Export
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="emag-sync">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>eMAG Integration</Title>
        <p style={{ color: '#666' }}>
          Manage eMAG marketplace integration and synchronization
        </p>
      </div>

      {/* Status Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <LinkOutlined style={{ fontSize: '24px', color: '#1890ff', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                {data.total_products}
              </div>
              <div style={{ color: '#666' }}>eMAG Products</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <SyncOutlined style={{ fontSize: '24px', color: '#52c41a', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                {data.total_offers}
              </div>
              <div style={{ color: '#666' }}>Synced Offers</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <CheckCircleOutlined style={{ fontSize: '24px', color: '#52c41a', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                {data.recent_syncs.filter(s => s.status === 'completed').length}
              </div>
              <div style={{ color: '#666' }}>Successful Syncs</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <ClockCircleOutlined style={{ fontSize: '24px', color: '#fa8c16', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fa8c16' }}>
                {data.recent_syncs.filter(s => s.status === 'running').length}
              </div>
              <div style={{ color: '#666' }}>Active Syncs</div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Sync Controls */}
      <Card
        title="Synchronization Control"
        style={{ marginBottom: 24 }}
        extra={
          <Button
            type="primary"
            icon={<SyncOutlined spin={syncing} />}
            onClick={handleSync}
            loading={syncing}
          >
            {syncing ? 'Syncing...' : 'Start Sync'}
          </Button>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <div style={{ padding: '16px', background: '#f6f6f6', borderRadius: '8px' }}>
              <h4>Manual Sync</h4>
              <p style={{ color: '#666', marginBottom: '16px' }}>
                Start a manual synchronization with eMAG marketplace.
                This will fetch the latest products and offers.
              </p>
              <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={handleSync}
                loading={syncing}
                block
              >
                {syncing ? 'Synchronizing...' : 'Sync Now'}
              </Button>
            </div>
          </Col>
          <Col xs={24} md={12}>
            <div style={{ padding: '16px', background: '#f0f9ff', borderRadius: '8px' }}>
              <h4>Sync Status</h4>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span>Products Synced:</span>
                  <span style={{ fontWeight: 'bold' }}>{data.total_products}</span>
                </div>
                <Progress
                  percent={Math.min((data.total_products / 50) * 100, 100)}
                  size="small"
                  status={data.total_products > 0 ? "success" : "active"}
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Offers Processed:</span>
                  <span style={{ fontWeight: 'bold' }}>{data.total_offers}</span>
                </div>
                <Progress
                  percent={Math.min((data.total_offers / 50) * 100, 100)}
                  size="small"
                  status={data.total_offers > 0 ? "success" : "active"}
                />
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Sync History */}
      <Card title="Sync History">
        <Table
          dataSource={data.recent_syncs}
          columns={columns}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
          size="small"
        />
      </Card>
    </div>
  )
}

export default EmagSync
