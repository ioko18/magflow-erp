/**
 * eMAG Product Sync V2 - Simplified Interface
 * 
 * Simple buttons to sync products from MAIN and FBE accounts
 */

import React, { useEffect, useState, useCallback } from 'react'
import {
  Row,
  Col,
  Card,
  Button,
  Typography,
  Space,
  Statistic,
  Progress,
  Tag,
  notification,
  Table,
  Alert,
  Tabs,
  Input,
  Select,
  Spin
} from 'antd'
import {
  SyncOutlined,
  CloudSyncOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  ApiOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  SearchOutlined,
  HistoryOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import api from '../services/api'
import type { AxiosError } from 'axios'
import { ColumnsType } from 'antd/es/table'

const { Title, Text } = Typography
const { Option } = Select

// Interfaces
interface SyncStatistics {
  products_by_account: {
    main?: number
    fbe?: number
  }
  total_products: number
  recent_syncs: RecentSync[]
}

interface RecentSync {
  id: string
  account_type: string
  operation: string
  status: string
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  total_items: number
  created_items: number
  updated_items: number
  failed_items: number
}

interface SyncStatus {
  is_running: boolean
  current_sync: CurrentSync | null
  recent_syncs: RecentSync[]
}

interface CurrentSync {
  id: string
  account_type: string
  operation: string
  started_at: string
  total_items: number
  processed_items: number
}

interface ProductRecord {
  id: string
  emag_id: string | null
  sku: string
  name: string
  account_type: 'main' | 'fbe'
  price: number | null
  currency: string
  stock_quantity: number
  is_active: boolean
  status: string
  sync_status: string
  last_synced_at: string | null
  created_at: string
  updated_at: string
}

const EmagProductSyncV2Simple: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification()
  
  // State
  const [statistics, setStatistics] = useState<SyncStatistics>({
    products_by_account: {},
    total_products: 0,
    recent_syncs: []
  })
  
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    is_running: false,
    current_sync: null,
    recent_syncs: []
  })
  
  const [products, setProducts] = useState<ProductRecord[]>([])
  const [productsTotal, setProductsTotal] = useState(0)
  const [productsPagination, setProductsPagination] = useState({
    current: 1,
    pageSize: 20
  })
  
  const [loading, setLoading] = useState(false)
  const [syncLoading, setSyncLoading] = useState<{main: boolean, fbe: boolean, both: boolean}>({
    main: false,
    fbe: false,
    both: false
  })
  
  const [searchText, setSearchText] = useState('')
  const [selectedAccountType, setSelectedAccountType] = useState<string | undefined>(undefined)

  // Data Fetching
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await api.get('/emag/products/statistics')
      if (response.data) {
        setStatistics(response.data)
      }
    } catch (error) {
      console.error('Failed to fetch statistics:', error)
    }
  }, [])

  const fetchSyncStatus = useCallback(async () => {
    try {
      const response = await api.get('/emag/products/status')
      if (response.data) {
        setSyncStatus(response.data)
        
        if (syncStatus.is_running && !response.data.is_running) {
          notificationApi.success({
            message: 'Sincronizare Completă',
            description: 'Sincronizarea produselor s-a finalizat cu succes',
            duration: 5
          })
          await fetchStatistics()
        }
      }
    } catch (error) {
      console.error('Failed to fetch sync status:', error)
    }
  }, [syncStatus.is_running, fetchStatistics, notificationApi])

  const fetchProducts = useCallback(async (page = 1, pageSize = 20) => {
    try {
      setLoading(true)
      const response = await api.get('/emag/products/products', {
        params: {
          skip: (page - 1) * pageSize,
          limit: pageSize,
          account_type: selectedAccountType,
          search: searchText || undefined
        }
      })
      
      if (response.data?.status === 'success' && response.data.data) {
        setProducts(response.data.data.products || [])
        setProductsTotal(response.data.data.pagination?.total || 0)
      }
    } catch (error) {
      console.error('Failed to fetch products:', error)
      notificationApi.error({
        message: 'Eroare',
        description: 'Nu s-au putut încărca produsele'
      })
    } finally {
      setLoading(false)
    }
  }, [selectedAccountType, searchText, notificationApi])

  // Sync Actions
  const startSync = async (accountType: 'main' | 'fbe' | 'both') => {
    try {
      setSyncLoading(prev => ({ ...prev, [accountType]: true }))
      
      // Show initial notification with timer
      const startTime = Date.now()
      notificationApi.info({
        message: 'Sincronizare Pornită',
        description: `Se sincronizează produsele din contul ${accountType.toUpperCase()}. Durată estimată: ~2 minute. Vă rugăm așteptați și NU închideți pagina...`,
        duration: 5
      })
      
      // Show progress notification every 30 seconds
      const progressInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000)
        notificationApi.info({
          message: 'Sincronizare în Curs',
          description: `⏱️ ${elapsed}s / ~120s - Procesare în curs... Vă rugăm așteptați.`,
          duration: 3,
          key: 'sync-progress'
        })
      }, 30000)
      
      const syncPayload = {
        account_type: accountType,
        mode: 'full', // Use full sync to get all products
        max_pages: null, // No limit on pages
        items_per_page: 100,
        include_inactive: true,
        conflict_strategy: 'emag_priority',
        run_async: false // Run synchronously to get immediate feedback
      }
      
      // Set timeout to 5 minutes (300 seconds) for the sync request
      const response = await api.post('/emag/products/sync', syncPayload, {
        timeout: 300000 // 5 minutes in milliseconds
      })
      
      // Clear progress interval
      clearInterval(progressInterval)
      
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      
      if (response.data && response.data.status === 'completed') {
        const data = response.data.data
        notificationApi.success({
          message: `✅ Sincronizare Completă în ${elapsed}s!`,
          description: `Procesate: ${data.total_processed}, Create: ${data.created}, Update: ${data.updated}, Eșuate: ${data.failed}`,
          duration: 15,
          key: 'sync-progress'
        })
        
        // Refresh data
        await fetchSyncStatus()
        await fetchStatistics()
        await fetchProducts(1, productsPagination.pageSize)
        setProductsPagination(prev => ({ ...prev, current: 1 }))
      }
    } catch (error) {
      const axiosError = error as AxiosError<{ detail: string }>
      const errorMessage = axiosError.code === 'ECONNABORTED' 
        ? 'Timeout: Sincronizarea durează prea mult (>5 minute). Verifică backend-ul.'
        : axiosError.response?.data?.detail || 'Nu s-a putut porni sincronizarea'
      
      notificationApi.error({
        message: 'Eroare Sincronizare',
        description: errorMessage,
        duration: 10,
        key: 'sync-progress'
      })
    } finally {
      setSyncLoading(prev => ({ ...prev, [accountType]: false }))
    }
  }

  // Effects
  useEffect(() => {
    fetchStatistics()
    fetchSyncStatus()
    fetchProducts(productsPagination.current, productsPagination.pageSize)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (syncStatus.is_running) {
      const interval = setInterval(() => {
        fetchSyncStatus()
      }, 3000)
      
      return () => clearInterval(interval)
    }
  }, [syncStatus.is_running, fetchSyncStatus])

  useEffect(() => {
    fetchProducts(1, productsPagination.pageSize)
    setProductsPagination(prev => ({ ...prev, current: 1 }))
  }, [searchText, selectedAccountType]) // eslint-disable-line react-hooks/exhaustive-deps

  // Export CSV
  const exportToCSV = () => {
    const csvContent = [
      ['SKU', 'Name', 'Account', 'Price', 'Currency', 'Stock', 'Status', 'Last Synced'],
      ...products.map(p => [
        p.sku,
        p.name,
        p.account_type.toUpperCase(),
        p.price || '',
        p.currency,
        p.stock_quantity,
        p.is_active ? 'Active' : 'Inactive',
        p.last_synced_at ? new Date(p.last_synced_at).toLocaleString() : 'Never'
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `emag_products_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
    
    notificationApi.success({
      message: 'Export Reușit',
      description: `Exportate ${products.length} produse`
    })
  }

  // Current Sync Progress
  const renderCurrentSync = () => {
    if (!syncStatus.current_sync) return null
    
    const { current_sync } = syncStatus
    const progressPercent = current_sync.total_items > 0
      ? Math.round((current_sync.processed_items / current_sync.total_items) * 100)
      : 0
    
    return (
      <Card
        title={
          <Space>
            <Spin indicator={<SyncOutlined spin />} />
            <Text strong>Sincronizare în Curs</Text>
            <Tag color="processing">{current_sync.account_type.toUpperCase()}</Tag>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Progress
            percent={progressPercent}
            status="active"
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Statistic
                title="Operație"
                value={current_sync.operation}
                prefix={<DatabaseOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Procesate"
                value={current_sync.processed_items}
                suffix={`/ ${current_sync.total_items}`}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Pornit la"
                value={new Date(current_sync.started_at).toLocaleTimeString()}
              />
            </Col>
          </Row>
        </Space>
      </Card>
    )
  }

  // Products Table Columns
  const productsColumns: ColumnsType<ProductRecord> = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      fixed: 'left',
      render: (sku: string) => <Text strong copyable>{sku}</Text>
    },
    {
      title: 'Nume Produs',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: 'Cont',
      dataIndex: 'account_type',
      key: 'account_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'main' ? 'blue' : 'green'}>
          {type.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Preț',
      dataIndex: 'price',
      key: 'price',
      width: 120,
      render: (price: number | null, record) => 
        price ? `${price.toFixed(2)} ${record.currency}` : '-'
    },
    {
      title: 'Stoc',
      dataIndex: 'stock_quantity',
      key: 'stock_quantity',
      width: 80,
      render: (stock: number) => (
        <Tag color={stock > 0 ? 'success' : 'error'}>
          {stock}
        </Tag>
      )
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Activ' : 'Inactiv'}
        </Tag>
      )
    },
    {
      title: 'Ultima Sincronizare',
      dataIndex: 'last_synced_at',
      key: 'last_synced_at',
      width: 160,
      render: (date: string | null) => 
        date ? new Date(date).toLocaleString() : 'Niciodată'
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      {contextHolder}
      
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space direction="vertical" size={0}>
            <Title level={2} style={{ margin: 0 }}>
              <CloudSyncOutlined /> Sincronizare Produse eMAG
            </Title>
            <Text type="secondary">
              Sincronizare simplă pentru conturile MAIN și FBE
            </Text>
          </Space>
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchStatistics()
              fetchSyncStatus()
              fetchProducts(productsPagination.current, productsPagination.pageSize)
            }}
          >
            Reîmprospătare
          </Button>
        </Col>
      </Row>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Produse"
              value={statistics.total_products}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Cont MAIN"
              value={statistics.products_by_account.main || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Cont FBE"
              value={statistics.products_by_account.fbe || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Space direction="vertical">
              <Text strong>Status</Text>
              <Tag color={syncStatus.is_running ? 'processing' : 'default'}>
                {syncStatus.is_running ? 'Sincronizare...' : 'Inactiv'}
              </Tag>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Current Sync Progress */}
      {syncStatus.is_running && syncStatus.current_sync && (
        <Row style={{ marginBottom: 24 }}>
          <Col span={24}>
            {renderCurrentSync()}
          </Col>
        </Row>
      )}

      {/* Sync Buttons - SIMPLIFIED */}
      {!syncStatus.is_running && (
        <Card
          title={
            <Space>
              <ThunderboltOutlined />
              <Text strong>Pornire Sincronizare</Text>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Alert
            message="Instrucțiuni"
            description="Apasă pe unul dintre butoanele de mai jos pentru a sincroniza produsele din contul respectiv. Sincronizarea va rula în fundal."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Button
                type="primary"
                size="large"
                block
                icon={<SyncOutlined />}
                loading={syncLoading.main}
                onClick={() => startSync('main')}
                style={{ height: '80px', fontSize: '16px' }}
              >
                <div>
                  <div><strong>Sincronizare MAIN</strong></div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    Toate produsele din contul MAIN
                  </div>
                </div>
              </Button>
            </Col>
            <Col xs={24} md={8}>
              <Button
                type="primary"
                size="large"
                block
                icon={<SyncOutlined />}
                loading={syncLoading.fbe}
                onClick={() => startSync('fbe')}
                style={{ height: '80px', fontSize: '16px', backgroundColor: '#722ed1', borderColor: '#722ed1' }}
              >
                <div>
                  <div><strong>Sincronizare FBE</strong></div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    Toate produsele din contul FBE
                  </div>
                </div>
              </Button>
            </Col>
            <Col xs={24} md={8}>
              <Button
                type="primary"
                size="large"
                block
                icon={<CloudSyncOutlined />}
                loading={syncLoading.both}
                onClick={() => startSync('both')}
                style={{ height: '80px', fontSize: '16px', backgroundColor: '#13c2c2', borderColor: '#13c2c2' }}
              >
                <div>
                  <div><strong>Sincronizare AMBELE</strong></div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    MAIN + FBE (recomandat)
                  </div>
                </div>
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* Products Table */}
      <Card>
        <Tabs 
          defaultActiveKey="products"
          items={[
            {
              key: 'products',
              label: (
                <Space>
                  <DatabaseOutlined />
                  <span>Produse Sincronizate ({productsTotal})</span>
                </Space>
              ),
              children: (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  {/* Filters */}
                  <Row gutter={[16, 16]} align="middle">
                    <Col flex="auto">
                      <Space wrap>
                        <Input
                          placeholder="Caută după nume sau SKU..."
                          prefix={<SearchOutlined />}
                          value={searchText}
                          onChange={(e) => setSearchText(e.target.value)}
                          style={{ width: 250 }}
                          allowClear
                        />
                        <Select
                          placeholder="Filtrează după cont"
                          value={selectedAccountType}
                          onChange={setSelectedAccountType}
                          style={{ width: 150 }}
                          allowClear
                        >
                          <Option value="main">MAIN</Option>
                          <Option value="fbe">FBE</Option>
                        </Select>
                      </Space>
                    </Col>
                    <Col>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={exportToCSV}
                        disabled={products.length === 0}
                      >
                        Export CSV
                      </Button>
                    </Col>
                  </Row>
                  
                  {/* Products Table */}
                  <Table
                    columns={productsColumns}
                    dataSource={products}
                    rowKey="id"
                    loading={loading}
                    scroll={{ x: 1200 }}
                    pagination={{
                      current: productsPagination.current,
                      pageSize: productsPagination.pageSize,
                      total: productsTotal,
                      showSizeChanger: true,
                      showTotal: (total) => `Total ${total} produse`,
                      pageSizeOptions: ['10', '20', '50', '100'],
                      onChange: (page, pageSize) => {
                        setProductsPagination({ current: page, pageSize })
                        fetchProducts(page, pageSize)
                      }
                    }}
                  />
                </Space>
              )
            },
            {
              key: 'history',
              label: (
                <Space>
                  <HistoryOutlined />
                  <span>Istoric Sincronizări</span>
                </Space>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {syncStatus.recent_syncs.length === 0 ? (
                    <Alert message="Nu există sincronizări recente" type="info" />
                  ) : (
                    syncStatus.recent_syncs.map((sync) => (
                      <Card key={sync.id} size="small">
                        <Row gutter={16}>
                          <Col span={6}>
                            <Text strong>Cont:</Text> <Tag color={sync.account_type === 'main' ? 'blue' : 'green'}>{sync.account_type.toUpperCase()}</Tag>
                          </Col>
                          <Col span={6}>
                            <Text strong>Status:</Text> <Tag color={sync.status === 'completed' ? 'success' : sync.status === 'failed' ? 'error' : 'processing'}>{sync.status}</Tag>
                          </Col>
                          <Col span={6}>
                            <Text strong>Produse:</Text> {sync.total_items} (Create: {sync.created_items}, Update: {sync.updated_items})
                          </Col>
                          <Col span={6}>
                            <Text strong>Dată:</Text> {new Date(sync.started_at).toLocaleString()}
                          </Col>
                        </Row>
                      </Card>
                    ))
                  )}
                </Space>
              )
            }
          ]}
        />
      </Card>
    </div>
  )
}

export default EmagProductSyncV2Simple
