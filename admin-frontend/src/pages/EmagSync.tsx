import React, { useEffect, useState, useRef } from 'react'
import { 
  Row, Col, Card, Button, Table, Typography, Space, Progress, Tag, notification,
  Select, Switch, Tooltip, Modal, InputNumber, Alert, Statistic,
  Divider, Badge, Timeline, Descriptions
} from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  EyeOutlined,
  DownloadOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  CloudSyncOutlined,
  DatabaseOutlined,
  WarningOutlined,
  ShoppingCartOutlined
} from '@ant-design/icons'
import api from '../services/api'
import type { AxiosError } from 'axios'

const { Title } = Typography

interface SyncRecord {
  sync_id: string
  account_type: string
  status: string
  total_offers_processed: number
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  error_message?: string
}

interface EmagData {
  total_products: number
  total_offers: number
  main_products: number
  fbe_products: number
  recent_syncs: SyncRecord[]
}

interface SyncOptions {
  mode: 'single' | 'both' | 'main' | 'fbe'
  maxPages: number
  batchSize: number
  progressInterval: number
}

interface SyncProgress {
  isRunning: boolean
  currentAccount?: string
  currentPage?: number
  totalPages?: number
  processedOffers: number
  estimatedTimeRemaining?: number
}

const AUTO_REFRESH_INTERVAL_MS = 60 * 60 * 1000 // 1 hour

const EmagSync: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification()
  const [data, setData] = useState<EmagData>({
    total_products: 0,
    total_offers: 0,
    main_products: 0,
    fbe_products: 0,
    recent_syncs: []
  })
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncOptions, setSyncOptions] = useState<SyncOptions>({
    mode: 'both',
    maxPages: 100,
    batchSize: 50,
    progressInterval: 10
  })
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    isRunning: false,
    processedOffers: 0
  })
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false)
  const [syncDetailsModal, setSyncDetailsModal] = useState<{ visible: boolean; record?: SyncRecord }>({ visible: false })
  const progressInterval = useRef<number | null>(null)
  const [ordersSyncLoading, setOrdersSyncLoading] = useState(false)

  useEffect(() => {
    fetchEmagData()
    
    // Auto-refresh data every 60 minutes
    const refreshInterval = setInterval(() => {
      if (!syncing && !syncProgress.isRunning) {
        fetchEmagData()
      }
    }, AUTO_REFRESH_INTERVAL_MS)
    
    return () => clearInterval(refreshInterval)
  }, [syncing, syncProgress.isRunning])

  const fetchEmagData = async () => {
    try {
      setLoading(true)
      // Fetch sync status from the admin dashboard endpoint (no auth required)
      const response = await api.get('/admin/dashboard')
      const syncData = response.data.data
      
      // Fetch account-specific data
      const [mainResponse, fbeResponse] = await Promise.allSettled([
        api.get('/admin/emag-products?account_type=main&limit=1'),
        api.get('/admin/emag-products?account_type=fbe&limit=1')
      ])

      const mainCount = mainResponse.status === 'fulfilled' ? 
        mainResponse.value.data.data?.pagination?.total || 0 : 0
      const fbeCount = fbeResponse.status === 'fulfilled' ? 
        fbeResponse.value.data.data?.pagination?.total || 0 : 0

      setData({
        total_products: syncData.emagProducts || 0,
        total_offers: syncData.emagProducts || 0,
        main_products: mainCount,
        fbe_products: fbeCount,
        recent_syncs: syncData.recentSyncs ? syncData.recentSyncs.map((sync: any) => ({
          sync_id: sync.sync_id,
          account_type: sync.account_type || 'main',
          status: sync.status,
          total_offers_processed: sync.offers_processed || 0,
          started_at: sync.started_at,
          completed_at: sync.completed_at,
          duration_seconds: parseFloat(sync.duration_seconds) || null,
          error_message: sync.error_message
        })) : []
      })
    } catch (error) {
      console.error('Error fetching eMAG data:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      notificationApi.warning({
        message: 'eMAG status indisponibil',
        description:
          axiosError.response?.data?.detail ??
          'Nu s-a putut obține statusul de la backend. Se vor afișa date demonstrative până când serviciul API este disponibil.',
      })

      setData({
        total_products: 24,
        total_offers: 87,
        main_products: 15,
        fbe_products: 9,
        recent_syncs: [
          {
            sync_id: 'demo-sync-001',
            account_type: 'main',
            status: 'completed',
            total_offers_processed: 42,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            duration_seconds: 38,
          },
          {
            sync_id: 'demo-sync-002',
            account_type: 'fbe',
            status: 'failed',
            total_offers_processed: 12,
            started_at: new Date(Date.now() - 3600 * 1000).toISOString(),
            completed_at: null,
            duration_seconds: null,
            error_message: 'Connection timeout'
          },
        ],
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async (mode: 'single' | 'both' | 'main' | 'fbe' = syncOptions.mode) => {
    try {
      setSyncing(true)
      setSyncProgress({ isRunning: true, processedOffers: 0 })
      
      // Start progress tracking
      startProgressTracking()
      
      const syncPayload = {
        mode,
        maxPages: syncOptions.maxPages,
        batchSize: syncOptions.batchSize,
        progressInterval: syncOptions.progressInterval
      }
      
      await api.post('/emag/sync', syncPayload)
      
      notificationApi.success({
        message: '🚀 Sincronizare Inițiată',
        description: (
          <div>
            <p><strong>{mode === 'both' ? 'Multi-Account Sync' : `${mode.toUpperCase()} Account Sync`}</strong></p>
            <p>📊 Max Pages: {syncOptions.maxPages} | Batch Size: {syncOptions.batchSize}</p>
            <p>⏱️ Progress updates every {syncOptions.progressInterval} batches</p>
          </div>
        ),
        duration: 6,
        placement: 'topRight'
      })

      // Refresh data after a short delay
      setTimeout(() => {
        fetchEmagData()
      }, 2000)

    } catch (error) {
      console.error('Error starting eMAG sync:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      notificationApi.error({
        message: 'Eroare Sincronizare',
        description:
          axiosError.response?.data?.detail ??
          'Nu s-a putut porni sincronizarea. Verifică serviciul API și încearcă din nou.',
        duration: 6
      })
      setSyncProgress({ isRunning: false, processedOffers: 0 })
    } finally {
      setSyncing(false)
    }
  }

  const startProgressTracking = () => {
    if (progressInterval.current) {
      clearInterval(progressInterval.current)
    }
    
    progressInterval.current = window.setInterval(async () => {
      try {
        // Fetch current sync progress
        const response = await api.get('/admin/sync-progress')
        const progress = response.data.data
        
        setSyncProgress(prev => ({
          ...prev,
          currentAccount: progress.currentAccount,
          currentPage: progress.currentPage,
          totalPages: progress.totalPages,
          processedOffers: progress.processedOffers,
          estimatedTimeRemaining: progress.estimatedTimeRemaining
        }))
        
        // Stop tracking if sync is complete
        if (!progress.isRunning) {
          stopProgressTracking()
          setSyncProgress({ isRunning: false, processedOffers: progress.processedOffers })
          fetchEmagData() // Refresh final data
        }
      } catch (error) {
        console.error('Error fetching sync progress:', error)
      }
    }, 2000) // Update every 2 seconds
  }

  const stopProgressTracking = () => {
    if (progressInterval.current) {
      clearInterval(progressInterval.current)
      progressInterval.current = null
    }
  }

  const handleOrderSync = async () => {
    try {
      setOrdersSyncLoading(true)
      await api.post('/emag/sync/orders')
      notificationApi.success({
        message: 'Sincronizare Comenzi',
        description: 'Sincronizarea comenzilor eMAG a fost inițiată cu succes.',
        placement: 'topRight'
      })
    } catch (error) {
      console.error('Error starting order sync:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      notificationApi.error({
        message: 'Eroare Sincronizare Comenzi',
        description:
          axiosError.response?.data?.detail ??
          'Nu s-a putut porni sincronizarea comenzilor. Verifică serviciul API și încearcă din nou.',
        placement: 'topRight'
      })
    } finally {
      setOrdersSyncLoading(false)
    }
  }

  const handleViewSyncDetails = (record: SyncRecord) => {
    setSyncDetailsModal({ visible: true, record })
  }

  const handleExportSyncData = async (record: SyncRecord) => {
    try {
      const response = await api.get(`/admin/sync-export/${record.sync_id}`, {
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `emag-sync-${record.sync_id}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      notificationApi.success({
        message: 'Export Reușit',
        description: 'Datele de sincronizare au fost exportate cu succes.'
      })
    } catch (error) {
      console.error('Error exporting sync data:', error)
      notificationApi.error({
        message: 'Eroare Export',
        description: 'Nu s-au putut exporta datele de sincronizare.'
      })
    }
  }

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      stopProgressTracking()
    }
  }, [])

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
      render: (sync_id: string) => (
        <Tooltip title={sync_id}>
          <code style={{ fontSize: '12px' }}>
            {sync_id.substring(0, 12)}...
          </code>
        </Tooltip>
      ),
    },
    {
      title: 'Account',
      dataIndex: 'account_type',
      key: 'account_type',
      render: (account_type: string) => (
        <Badge 
          color={account_type === 'main' ? 'blue' : 'green'} 
          text={account_type.toUpperCase()}
        />
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: SyncRecord) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>
            {status.toUpperCase()}
          </Tag>
          {record.error_message && (
            <Tooltip title={record.error_message}>
              <WarningOutlined style={{ color: '#ff4d4f' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Offers Processed',
      dataIndex: 'total_offers_processed',
      key: 'total_offers_processed',
      render: (count: number) => (
        <Statistic 
          value={count} 
          valueStyle={{ fontSize: '14px' }}
        />
      ),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => new Date(date).toLocaleString('ro-RO'),
    },
    {
      title: 'Duration',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (seconds: number | null) => {
        if (!seconds) return '-'
        const minutes = Math.floor(seconds / 60)
        const remainingSeconds = Math.round(seconds % 60)
        return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: SyncRecord) => (
        <Space>
          <Tooltip title="View Details">
            <Button 
              icon={<EyeOutlined />} 
              size="small"
              onClick={() => handleViewSyncDetails(record)}
            >
              View
            </Button>
          </Tooltip>
          <Tooltip title="Export Data">
            <Button 
              icon={<DownloadOutlined />} 
              size="small"
              onClick={() => handleExportSyncData(record)}
            >
              Export
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  // Note: Authentication check removed since we're using endpoints that don't require auth

  return (
    <div className="emag-sync">
      {contextHolder}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2}>eMAG Integration</Title>
            <p style={{ color: '#666', margin: 0 }}>
              Manage eMAG marketplace integration and synchronization
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '12px', color: '#999', marginBottom: '4px' }}>
              🔄 Auto-refresh: 60m
            </div>
            <div style={{ fontSize: '11px', color: '#ccc' }}>
              Last updated: {new Date().toLocaleTimeString('ro-RO')}
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Status Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <LinkOutlined style={{ fontSize: '24px', color: '#1890ff', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                {data.total_products}
              </div>
              <div style={{ color: '#666' }}>Total Products</div>
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ fontSize: '12px', color: '#999' }}>
                MAIN: {data.main_products} | FBE: {data.fbe_products}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <div style={{ textAlign: 'center' }}>
              <DatabaseOutlined style={{ fontSize: '24px', color: '#52c41a', marginBottom: '8px' }} />
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                {data.total_offers}
              </div>
              <div style={{ color: '#666' }}>Synced Offers</div>
              {syncProgress.isRunning && (
                <Progress 
                  percent={syncProgress.currentPage && syncProgress.totalPages ? 
                    Math.round((syncProgress.currentPage / syncProgress.totalPages) * 100) : 0}
                  size="small"
                  status="active"
                  style={{ marginTop: '8px' }}
                />
              )}
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
              {syncProgress.isRunning ? (
                <SyncOutlined spin style={{ fontSize: '24px', color: '#1890ff', marginBottom: '8px' }} />
              ) : (
                <ClockCircleOutlined style={{ fontSize: '24px', color: '#fa8c16', marginBottom: '8px' }} />
              )}
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: syncProgress.isRunning ? '#1890ff' : '#fa8c16' }}>
                {syncProgress.isRunning ? syncProgress.processedOffers : data.recent_syncs.filter(s => s.status === 'running').length}
              </div>
              <div style={{ color: '#666' }}>
                {syncProgress.isRunning ? 'Processing...' : 'Active Syncs'}
              </div>
              {syncProgress.isRunning && syncProgress.currentAccount && (
                <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
                  {syncProgress.currentAccount.toUpperCase()} Account
                </div>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Enhanced Sync Controls */}
      <Card
        title={
          <Space>
            <CloudSyncOutlined />
            <span>Multi-Account Synchronization Control</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <Tooltip title="Advanced Options">
              <Button
                icon={<SettingOutlined />}
                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              >
                Options
              </Button>
            </Tooltip>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchEmagData}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        {/* Sync Mode Selection */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ marginBottom: '12px' }}>
            <ThunderboltOutlined style={{ marginRight: '8px' }} />
            Sync Mode
          </h4>
          <Select
            value={syncOptions.mode}
            onChange={(value) => setSyncOptions(prev => ({ ...prev, mode: value }))}
            style={{ width: '200px', marginRight: '16px' }}
          >
            <Select.Option value="both">
              <Space>
                <CloudSyncOutlined />
                Both Accounts (MAIN + FBE)
              </Space>
            </Select.Option>
            <Select.Option value="main">
              <Space>
                <DatabaseOutlined />
                MAIN Account Only
              </Space>
            </Select.Option>
            <Select.Option value="fbe">
              <Space>
                <LinkOutlined />
                FBE Account Only
              </Space>
            </Select.Option>
          </Select>
          
          <Button
            type="primary"
            size="large"
            icon={<SyncOutlined spin={syncing} />}
            onClick={() => handleSync()}
            loading={syncing}
            disabled={syncProgress.isRunning}
          >
            {syncing ? 'Synchronizing...' : `Start ${syncOptions.mode === 'both' ? 'Multi-Account' : syncOptions.mode.toUpperCase()} Sync`}
          </Button>
        </div>

        {/* Advanced Options */}
        {showAdvancedOptions && (
          <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px', marginBottom: '24px' }}>
            <h4 style={{ marginBottom: '16px' }}>
              <SettingOutlined style={{ marginRight: '8px' }} />
              Advanced Sync Options
            </h4>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: '500' }}>
                    Max Pages:
                  </label>
                  <InputNumber
                    min={1}
                    max={1000}
                    value={syncOptions.maxPages}
                    onChange={(value) => setSyncOptions(prev => ({ ...prev, maxPages: value || 100 }))}
                    style={{ width: '100%' }}
                  />
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: '500' }}>
                    Batch Size:
                  </label>
                  <InputNumber
                    min={10}
                    max={200}
                    value={syncOptions.batchSize}
                    onChange={(value) => setSyncOptions(prev => ({ ...prev, batchSize: value || 50 }))}
                    style={{ width: '100%' }}
                  />
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: '500' }}>
                    Progress Interval:
                  </label>
                  <InputNumber
                    min={1}
                    max={100}
                    value={syncOptions.progressInterval}
                    onChange={(value) => setSyncOptions(prev => ({ ...prev, progressInterval: value || 10 }))}
                    style={{ width: '100%' }}
                  />
                </div>
              </Col>
            </Row>
          </div>
        )}

        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <div style={{ padding: '16px', background: '#f6f6f6', borderRadius: '8px' }}>
              <h4>
                <PlayCircleOutlined style={{ marginRight: '8px' }} />
                Quick Actions
              </h4>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  icon={<DatabaseOutlined />}
                  onClick={() => handleSync('main')}
                  loading={syncing}
                  block
                  disabled={syncProgress.isRunning}
                >
                  Sync MAIN Account
                </Button>
                <Button
                  type="primary"
                  icon={<LinkOutlined />}
                  onClick={() => handleSync('fbe')}
                  loading={syncing}
                  block
                  disabled={syncProgress.isRunning}
                >
                  Sync FBE Account
                </Button>
                <Button
                  type="primary"
                  icon={<CloudSyncOutlined />}
                  onClick={() => handleSync('both')}
                  loading={syncing}
                  block
                  disabled={syncProgress.isRunning}
                >
                  Sync Both Accounts
                </Button>
                <Button
                  icon={<ShoppingCartOutlined />}
                  onClick={handleOrderSync}
                  loading={ordersSyncLoading}
                  block
                  disabled={ordersSyncLoading}
                >
                  Sync Orders
                </Button>
              </Space>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ padding: '16px', background: '#f0f9ff', borderRadius: '8px' }}>
              <h4>
                <InfoCircleOutlined style={{ marginRight: '8px' }} />
                Sync Progress
              </h4>
              {syncProgress.isRunning ? (
                <div>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span>Current Account:</span>
                      <Badge 
                        color={syncProgress.currentAccount === 'main' ? 'blue' : 'green'}
                        text={syncProgress.currentAccount?.toUpperCase() || 'Unknown'}
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span>Page Progress:</span>
                      <span>{syncProgress.currentPage || 0} / {syncProgress.totalPages || '?'}</span>
                    </div>
                    <Progress
                      percent={syncProgress.currentPage && syncProgress.totalPages ? 
                        Math.round((syncProgress.currentPage / syncProgress.totalPages) * 100) : 0}
                      size="small"
                      status="active"
                    />
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span>Offers Processed:</span>
                      <span style={{ fontWeight: 'bold' }}>{syncProgress.processedOffers}</span>
                    </div>
                    {syncProgress.estimatedTimeRemaining && (
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        Est. time remaining: {Math.round(syncProgress.estimatedTimeRemaining / 60)}m
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span>MAIN Products:</span>
                      <span style={{ fontWeight: 'bold' }}>{data.main_products}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span>FBE Products:</span>
                      <span style={{ fontWeight: 'bold' }}>{data.fbe_products}</span>
                    </div>
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Total Offers:</span>
                      <span style={{ fontWeight: 'bold' }}>{data.total_offers}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ padding: '16px', background: '#fff7e6', borderRadius: '8px' }}>
              <h4>
                <InfoCircleOutlined style={{ marginRight: '8px' }} />
                Sync Information
              </h4>
              <Timeline
                items={[
                  {
                    color: 'blue',
                    children: (
                      <div style={{ fontSize: '12px' }}>
                        <strong>Multi-Account Support</strong><br />
                        Sync from both MAIN and FBE accounts simultaneously
                      </div>
                    )
                  },
                  {
                    color: 'green',
                    children: (
                      <div style={{ fontSize: '12px' }}>
                        <strong>Real-time Progress</strong><br />
                        Track sync progress with live updates
                      </div>
                    )
                  },
                  {
                    color: 'orange',
                    children: (
                      <div style={{ fontSize: '12px' }}>
                        <strong>Advanced Options</strong><br />
                        Configure batch size, page limits, and intervals
                      </div>
                    )
                  }
                ]}
              />
            </div>
          </Col>
        </Row>
      </Card>

      {/* Enhanced Sync History */}
      <Card 
        title={
          <Space>
            <DatabaseOutlined />
            <span>Sync History & Analytics</span>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Show only successful syncs">
              <Switch 
                checkedChildren="Success Only" 
                unCheckedChildren="All Syncs"
                onChange={() => {
                  // Filter logic can be added here
                }}
              />
            </Tooltip>
          </Space>
        }
      >
        {data.recent_syncs.length > 0 && (
          <Alert
            message="Sync Performance Summary"
            description={
              <div>
                <span>
                  Last 24h: {data.recent_syncs.filter(s => 
                    new Date(s.started_at) > new Date(Date.now() - 24 * 60 * 60 * 1000)
                  ).length} syncs | 
                </span>
                <span style={{ marginLeft: '8px' }}>
                  Success Rate: {Math.round(
                    (data.recent_syncs.filter(s => s.status === 'completed').length / data.recent_syncs.length) * 100
                  )}% | 
                </span>
                <span style={{ marginLeft: '8px' }}>
                  Avg Duration: {Math.round(
                    data.recent_syncs
                      .filter(s => s.duration_seconds)
                      .reduce((acc, s) => acc + (s.duration_seconds || 0), 0) / 
                    data.recent_syncs.filter(s => s.duration_seconds).length || 0
                  )}s
                </span>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: '16px' }}
          />
        )}
        
        <Table
          rowKey="sync_id"
          dataSource={data.recent_syncs}
          columns={columns}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} of ${total} sync records`,
          }}
          size="small"
        />
      </Card>

      {/* Sync Details Modal */}
      <Modal
        title={
          <Space>
            <EyeOutlined />
            <span>Sync Details</span>
            {syncDetailsModal.record && (
              <Badge 
                color={syncDetailsModal.record.account_type === 'main' ? 'blue' : 'green'}
                text={syncDetailsModal.record.account_type.toUpperCase()}
              />
            )}
          </Space>
        }
        open={syncDetailsModal.visible}
        onCancel={() => setSyncDetailsModal({ visible: false })}
        footer={[
          <Button key="close" onClick={() => setSyncDetailsModal({ visible: false })}>
            Close
          </Button>,
          syncDetailsModal.record && (
            <Button 
              key="export" 
              type="primary" 
              icon={<DownloadOutlined />}
              onClick={() => handleExportSyncData(syncDetailsModal.record!)}
            >
              Export Data
            </Button>
          )
        ]}
        width={800}
      >
        {syncDetailsModal.record && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Sync ID" span={2}>
              <code>{syncDetailsModal.record.sync_id}</code>
            </Descriptions.Item>
            <Descriptions.Item label="Account Type">
              <Badge 
                color={syncDetailsModal.record.account_type === 'main' ? 'blue' : 'green'}
                text={syncDetailsModal.record.account_type.toUpperCase()}
              />
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Space>
                {getStatusIcon(syncDetailsModal.record.status)}
                <Tag color={getStatusColor(syncDetailsModal.record.status)}>
                  {syncDetailsModal.record.status.toUpperCase()}
                </Tag>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Offers Processed">
              <Statistic 
                value={syncDetailsModal.record.total_offers_processed} 
                valueStyle={{ fontSize: '16px' }}
              />
            </Descriptions.Item>
            <Descriptions.Item label="Duration">
              {syncDetailsModal.record.duration_seconds ? (
                <span>
                  {Math.floor(syncDetailsModal.record.duration_seconds / 60)}m {' '}
                  {Math.round(syncDetailsModal.record.duration_seconds % 60)}s
                </span>
              ) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Started At" span={2}>
              {new Date(syncDetailsModal.record.started_at).toLocaleString('ro-RO')}
            </Descriptions.Item>
            {syncDetailsModal.record.completed_at && (
              <Descriptions.Item label="Completed At" span={2}>
                {new Date(syncDetailsModal.record.completed_at).toLocaleString('ro-RO')}
              </Descriptions.Item>
            )}
            {syncDetailsModal.record.error_message && (
              <Descriptions.Item label="Error Message" span={2}>
                <Alert
                  message="Sync Error"
                  description={syncDetailsModal.record.error_message}
                  type="error"
                  showIcon
                />
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default EmagSync
