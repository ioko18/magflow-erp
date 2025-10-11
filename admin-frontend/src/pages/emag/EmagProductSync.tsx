/**
 * eMAG Product Sync Page - Complete Rewrite
 * 
 * Comprehensive product synchronization interface for eMAG MAIN and FBE accounts.
 * Supports full sync, incremental updates, and real-time monitoring.
 * 
 * Features:
 * - Full product sync for both MAIN and FBE accounts (2545+ products)
 * - Real-time sync progress tracking
 * - Advanced sync options (pagination, rate limiting, filters)
 * - Comprehensive statistics and analytics
 * - Error handling and recovery
 * - Manual and automated sync modes
 */

import React, { useEffect, useState, useCallback, useRef } from 'react'
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
  Tooltip,
  Switch,
  Modal,
  Form,
  InputNumber,
  Alert,
  Tabs,
  Timeline,
  Descriptions,
  Empty,
  Divider,
  Input,
  Select,
  Drawer
} from 'antd'
import {
  SyncOutlined,
  CloudSyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  SettingOutlined,
  DashboardOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  FireOutlined,
  StopOutlined,
  DownloadOutlined,
  SearchOutlined,
  EyeOutlined
} from '@ant-design/icons'
import api from '../../services/api'
import { logError, logInfo } from '../../utils/errorLogger'
import type { AxiosError } from 'axios'
import { ColumnsType } from 'antd/es/table'
import {
  ValidationStatusBadge,
  GeniusBadge,
  EanSearchModal,
  SmartDealsChecker,
  ProductFamilyGroup
} from '../../components/emag'

const { Title, Text } = Typography

// ============================================================================
// INTERFACES
// ============================================================================

interface SyncStats {
  total_products: number
  main_products: number
  fbe_products: number
  total_offers: number
  last_sync_at: string | null
  sync_in_progress: boolean
}

interface SyncProgress {
  account_type: 'main' | 'fbe' | 'both'
  status: 'idle' | 'running' | 'completed' | 'error'
  current_page: number
  total_pages: number
  products_processed: number
  products_created: number
  products_updated: number
  errors: number
  start_time: string
  elapsed_seconds: number
  estimated_remaining_seconds: number | null
  throughput: number
  error_message: string | null
}

interface ProductRecord {
  id: string
  sku: string
  name: string
  account_type: 'main' | 'fbe'
  price: number | null
  currency: string
  stock_quantity: number
  is_active: boolean
  last_synced_at: string | null
  sync_status: string
  brand: string | null
  emag_category_name: string | null
  // v4.4.9 fields
  validation_status?: number | null
  validation_status_description?: string | null
  genius_eligibility?: number | null
  genius_eligibility_type?: number | null
  genius_computed?: number | null
  family_id?: number | null
  family_name?: string | null
  family_type_id?: number | null
  part_number_key?: string | null
}

interface SyncHistory {
  sync_id: string
  account_type: string
  status: string
  products_processed: number
  products_created: number
  products_updated: number
  errors: number
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
}

interface SyncOptions {
  max_pages_per_account: number
  delay_between_requests: number
  include_inactive: boolean
  batch_size: number
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const EmagProductSync: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification()
  
  // State Management
  const [stats, setStats] = useState<SyncStats>({
    total_products: 0,
    main_products: 0,
    fbe_products: 0,
    total_offers: 0,
    last_sync_at: null,
    sync_in_progress: false
  })
  
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null)
  const [products, setProducts] = useState<ProductRecord[]>([])
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([])
  
  const [loading, setLoading] = useState(false)
  const [syncLoading, setSyncLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [optionsModalVisible, setOptionsModalVisible] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState<ProductRecord | null>(null)
  const [productDetailsVisible, setProductDetailsVisible] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [selectedBrand, setSelectedBrand] = useState<string | undefined>(undefined)
  const [selectedAccountType, setSelectedAccountType] = useState<string | undefined>(undefined)
  
  // v4.4.9 feature modals
  const [eanSearchVisible, setEanSearchVisible] = useState(false)
  const [smartDealsVisible, setSmartDealsVisible] = useState(false)
  const [selectedProductForSmartDeals, setSelectedProductForSmartDeals] = useState<{
    id: string
    price: number
    currency: string
  } | null>(null)
  
  const [syncOptions, setSyncOptions] = useState<SyncOptions>({
    max_pages_per_account: 20,
    delay_between_requests: 0.5,  // Backend requires >= 0.5 seconds
    include_inactive: true,
    batch_size: 100
  })
  
  const [form] = Form.useForm()
  const progressIntervalRef = useRef<number | null>(null)
  const statsIntervalRef = useRef<number | null>(null)

  // ============================================================================
  // DATA FETCHING
  // ============================================================================

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/emag/enhanced/status', {
        params: { account_type: 'both' }
      })
      
      if (response.data) {
        setStats({
          total_products: response.data.total_products || 0,
          main_products: response.data.main_products || 0,
          fbe_products: response.data.fbe_products || 0,
          total_offers: response.data.total_offers || 0,
          last_sync_at: response.data.last_sync_at || null,
          sync_in_progress: response.data.sync_in_progress || false
        })
      }
    } catch (error) {
      logError(error as Error, { component: 'EmagProductSync', action: 'fetchStats' })
    }
  }, [])

  const fetchSyncProgress = useCallback(async () => {
    if (!stats.sync_in_progress) {
      return
    }
    
    try {
      const response = await api.get('/emag/enhanced/products/sync-progress')
      
      if (response.data) {
        setSyncProgress(response.data)
        
        // Auto-refresh stats when sync completes
        if (response.data.status === 'completed') {
          setSyncProgress(null)
          await fetchStats()
          notificationApi.success({
            message: 'Sync Complete',
            description: `Successfully synced ${response.data.products_processed} products`,
            duration: 5
          })
        } else if (response.data.status === 'error') {
          notificationApi.error({
            message: 'Sync Error',
            description: response.data.error_message || 'Sync failed with errors',
            duration: 0
          })
        }
      }
    } catch (error) {
      logError(error as Error, { component: 'EmagProductSync', action: 'fetchSyncProgress' })
    }
  }, [stats.sync_in_progress, fetchStats, notificationApi])

  const fetchProducts = useCallback(async (page = 1, pageSize = 10) => {
    try {
      setLoading(true)
      const response = await api.get('/emag/enhanced/products/all', {
        params: {
          account_type: 'both',
          page,
          page_size: pageSize,
          include_inactive: false
        }
      })
      
      if (response.data && response.data.products) {
        setProducts(response.data.products)
      }
    } catch (error) {
      logError(error as Error, { component: 'EmagProductSync', action: 'fetchProducts' })
      notificationApi.error({
        message: 'Failed to load products',
        description: 'Could not fetch products from database'
      })
    } finally {
      setLoading(false)
    }
  }, [notificationApi])

  const fetchSyncHistory = useCallback(async () => {
    try {
      const response = await api.get('/emag/sync/history', {
        params: { limit: 10 }
      })
      
      if (response.data && response.data.history) {
        setSyncHistory(response.data.history)
      }
    } catch (error) {
      logError(error as Error, { component: 'EmagProductSync', action: 'fetchSyncHistory' })
    }
  }, [])

  // ============================================================================
  // SYNC ACTIONS
  // ============================================================================

  const startFullSync = async (accountType: 'main' | 'fbe' | 'both' = 'both') => {
    try {
      setSyncLoading(true)
      
      // Backend sync handles both accounts automatically - no account_type param needed
      const response = await api.post('/emag/enhanced/sync/all-products', {
        max_pages_per_account: syncOptions.max_pages_per_account,
        delay_between_requests: syncOptions.delay_between_requests,
        include_inactive: syncOptions.include_inactive
      })
      
      if (response.data) {
        notificationApi.success({
          message: 'Sync Started',
          description: `Full product sync initiated for ${accountType.toUpperCase()} account(s)`,
          duration: 3
        })
        
        // Start progress monitoring
        setSyncProgress({
          account_type: accountType,
          status: 'running',
          current_page: 0,
          total_pages: 0,
          products_processed: 0,
          products_created: 0,
          products_updated: 0,
          errors: 0,
          start_time: new Date().toISOString(),
          elapsed_seconds: 0,
          estimated_remaining_seconds: null,
          throughput: 0,
          error_message: null
        })
        
        // Update stats to show sync in progress
        setStats(prev => ({ ...prev, sync_in_progress: true }))
      }
    } catch (error) {
      const axiosError = error as AxiosError<{ detail: string }>
      notificationApi.error({
        message: 'Sync Failed',
        description: axiosError.response?.data?.detail || 'Failed to start synchronization',
        duration: 5
      })
    } finally {
      setSyncLoading(false)
    }
  }

  const stopSync = async () => {
    try {
      await api.post('/emag/enhanced/sync/stop')
      
      notificationApi.info({
        message: 'Sync Stopped',
        description: 'Synchronization has been stopped by user',
        duration: 3
      })
      
      setSyncProgress(null)
      setStats(prev => ({ ...prev, sync_in_progress: false }))
      await fetchStats()
    } catch (error) {
      notificationApi.error({
        message: 'Failed to stop sync',
        description: 'Could not stop the synchronization process'
      })
    }
  }

  // ============================================================================
  // EFFECTS
  // ============================================================================

  useEffect(() => {
    fetchStats()
    fetchProducts()
    fetchSyncHistory()
  }, [fetchStats, fetchProducts, fetchSyncHistory])

  // Auto-refresh stats
  useEffect(() => {
    if (autoRefresh) {
      statsIntervalRef.current = setInterval(() => {
        fetchStats()
      }, 30000) // 30 seconds
      
      return () => {
        if (statsIntervalRef.current) {
          clearInterval(statsIntervalRef.current)
        }
      }
    }
  }, [autoRefresh, fetchStats])

  // Monitor sync progress
  useEffect(() => {
    if (stats.sync_in_progress || syncProgress) {
      progressIntervalRef.current = setInterval(() => {
        fetchSyncProgress()
      }, 2000) // 2 seconds
      
      return () => {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current)
        }
      }
    }
  }, [stats.sync_in_progress, syncProgress, fetchSyncProgress])

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const exportToCSV = () => {
    const csvContent = [
      ['SKU', 'Name', 'Account', 'Brand', 'Category', 'Price', 'Currency', 'Stock', 'Status', 'Last Synced'],
      ...products.map(p => [
        p.sku,
        p.name,
        p.account_type.toUpperCase(),
        p.brand || '',
        p.emag_category_name || '',
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
      message: 'Export Successful',
      description: `Exported ${products.length} products to CSV`
    })
  }

  const getFilteredProducts = () => {
    return products.filter(product => {
      const matchesSearch = !searchText || 
        product.name.toLowerCase().includes(searchText.toLowerCase()) ||
        product.sku.toLowerCase().includes(searchText.toLowerCase())
      
      const matchesBrand = !selectedBrand || product.brand === selectedBrand
      const matchesAccount = !selectedAccountType || product.account_type === selectedAccountType
      
      return matchesSearch && matchesBrand && matchesAccount
    })
  }

  const uniqueBrands = Array.from(new Set(products.map(p => p.brand).filter(Boolean)))

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  const renderSyncButton = (accountType: 'main' | 'fbe' | 'both', title: string) => {
    const isDisabled = stats.sync_in_progress || syncLoading
    
    return (
      <Tooltip title={isDisabled ? 'Sync already in progress' : `Start full sync for ${title}`}>
        <Button
          type={accountType === 'both' ? 'primary' : 'default'}
          size="large"
          icon={<CloudSyncOutlined />}
          onClick={() => startFullSync(accountType)}
          loading={syncLoading}
          disabled={isDisabled}
          block
        >
          Sync {title}
        </Button>
      </Tooltip>
    )
  }

  const renderProgressCard = () => {
    if (!syncProgress) return null
    
    const progressPercent = syncProgress.total_pages > 0
      ? Math.round((syncProgress.current_page / syncProgress.total_pages) * 100)
      : 0
    
    const status = syncProgress.status === 'running' ? 'active' : 
                   syncProgress.status === 'completed' ? 'success' :
                   syncProgress.status === 'error' ? 'exception' : 'normal'
    
    return (
      <Card
        title={
          <Space>
            <SyncOutlined spin />
            <Text strong>Sync in Progress</Text>
            <Tag color="processing">{syncProgress.account_type.toUpperCase()}</Tag>
          </Space>
        }
        extra={
          <Button
            danger
            size="small"
            icon={<StopOutlined />}
            onClick={stopSync}
          >
            Stop Sync
          </Button>
        }
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Progress
            percent={progressPercent}
            status={status}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Statistic
                title="Progress"
                value={syncProgress.current_page}
                suffix={`/ ${syncProgress.total_pages} pages`}
                prefix={<DatabaseOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Processed"
                value={syncProgress.products_processed}
                suffix="products"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Created"
                value={syncProgress.products_created}
                prefix={<FireOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Updated"
                value={syncProgress.products_updated}
                prefix={<ReloadOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
          </Row>
          
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Statistic
                title="Throughput"
                value={syncProgress.throughput}
                suffix="prod/sec"
                precision={1}
                prefix={<ThunderboltOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Elapsed"
                value={syncProgress.elapsed_seconds}
                suffix="seconds"
                prefix={<ClockCircleOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Errors"
                value={syncProgress.errors}
                prefix={<WarningOutlined />}
                valueStyle={{ color: syncProgress.errors > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Col>
          </Row>
          
          {syncProgress.estimated_remaining_seconds && (
            <Alert
              message={`Estimated time remaining: ${Math.round(syncProgress.estimated_remaining_seconds / 60)} minutes`}
              type="info"
              showIcon
              icon={<ClockCircleOutlined />}
            />
          )}
          
          {syncProgress.error_message && (
            <Alert
              message="Sync Error"
              description={syncProgress.error_message}
              type="error"
              showIcon
              closable
            />
          )}
        </Space>
      </Card>
    )
  }

  const productsColumns: ColumnsType<ProductRecord> = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      fixed: 'left',
      render: (sku: string) => <Text strong>{sku}</Text>
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      fixed: 'left',
      render: (_: unknown, record: ProductRecord) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedProduct(record)
            setProductDetailsVisible(true)
          }}
        />
      )
    },
    {
      title: 'Product Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: { showTitle: false },
      render: (name: string) => (
        <Tooltip title={name}>
          <Text>{name}</Text>
        </Tooltip>
      )
    },
    {
      title: 'Account',
      dataIndex: 'account_type',
      key: 'account_type',
      width: 100,
      filters: [
        { text: 'MAIN', value: 'main' },
        { text: 'FBE', value: 'fbe' }
      ],
      onFilter: (value, record) => record.account_type === value,
      render: (type: string) => (
        <Tag color={type === 'main' ? 'blue' : 'green'}>
          {type.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Brand',
      dataIndex: 'brand',
      key: 'brand',
      width: 120,
      render: (brand: string | null) => brand || '-'
    },
    {
      title: 'Category',
      dataIndex: 'emag_category_name',
      key: 'emag_category_name',
      width: 150,
      ellipsis: true,
      render: (category: string | null) => category || '-'
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price: number | null, record) => 
        price ? `${price.toFixed(2)} ${record.currency}` : '-'
    },
    {
      title: 'Stock',
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
      filters: [
        { text: 'Active', value: true },
        { text: 'Inactive', value: false }
      ],
      onFilter: (value, record) => record.is_active === value,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      )
    },
    {
      title: 'Validation',
      dataIndex: 'validation_status',
      key: 'validation_status',
      width: 120,
      render: (_: unknown, record: ProductRecord) => (
        <ValidationStatusBadge
          status={record.validation_status}
          description={record.validation_status_description}
        />
      )
    },
    {
      title: 'Genius',
      key: 'genius',
      width: 140,
      render: (_: unknown, record: ProductRecord) => (
        <GeniusBadge
          eligibility={record.genius_eligibility}
          eligibilityType={record.genius_eligibility_type}
          computed={record.genius_computed}
        />
      )
    },
    {
      title: 'Family',
      key: 'family',
      width: 150,
      render: (_: unknown, record: ProductRecord) => (
        <ProductFamilyGroup
          familyId={record.family_id}
          familyName={record.family_name}
          familyTypeId={record.family_type_id}
        />
      )
    },
    {
      title: 'Sync Status',
      dataIndex: 'sync_status',
      key: 'sync_status',
      width: 100,
      render: (status: string) => {
        const color = status === 'synced' ? 'success' :
                     status === 'pending' ? 'processing' :
                     status === 'error' ? 'error' : 'default'
        return <Tag color={color}>{status}</Tag>
      }
    },
    {
      title: 'Last Synced',
      dataIndex: 'last_synced_at',
      key: 'last_synced_at',
      width: 160,
      render: (date: string | null) => 
        date ? new Date(date).toLocaleString() : 'Never'
    }
  ]

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  return (
    <div style={{ padding: '24px' }}>
      {contextHolder}
      
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space direction="vertical" size={0}>
            <Title level={2} style={{ margin: 0 }}>
              <CloudSyncOutlined /> eMAG Product Sync
            </Title>
            <Text type="secondary">
              Complete product synchronization for MAIN and FBE accounts
            </Text>
          </Space>
        </Col>
        <Col>
          <Space>
            <Tooltip title="Auto-refresh statistics every 30 seconds">
              <Space>
                <Text>Auto-refresh:</Text>
                <Switch
                  checked={autoRefresh}
                  onChange={setAutoRefresh}
                  checkedChildren="ON"
                  unCheckedChildren="OFF"
                />
              </Space>
            </Tooltip>
            <Tooltip title="Search products by EAN code">
              <Button
                icon={<SearchOutlined />}
                onClick={() => setEanSearchVisible(true)}
              >
                EAN Search
              </Button>
            </Tooltip>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                form.setFieldsValue(syncOptions)
                setOptionsModalVisible(true)
              }}
            >
              Options
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                fetchStats()
                fetchProducts()
                fetchSyncHistory()
              }}
            >
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Products"
              value={stats.total_products}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="MAIN Account"
              value={stats.main_products}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="FBE Account"
              value={stats.fbe_products}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Offers"
              value={stats.total_offers}
              prefix={<FireOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Progress Card (shown during sync) */}
      {syncProgress && (
        <Row style={{ marginBottom: 24 }}>
          <Col span={24}>
            {renderProgressCard()}
          </Col>
        </Row>
      )}

      {/* Sync Controls */}
      {!stats.sync_in_progress && (
        <Card
          title={
            <Space>
              <RocketOutlined />
              <Text strong>Sync Controls</Text>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              {renderSyncButton('both', 'Both Accounts')}
            </Col>
            <Col xs={24} md={8}>
              {renderSyncButton('main', 'MAIN Only')}
            </Col>
            <Col xs={24} md={8}>
              {renderSyncButton('fbe', 'FBE Only')}
            </Col>
          </Row>
          
          <Divider />
          
          <Alert
            message="Full Synchronization Info"
            description={
              <Space direction="vertical">
                <Text>• MAIN Account: ~1,274 products expected</Text>
                <Text>• FBE Account: ~1,271 products expected</Text>
                <Text>• Total: ~2,545 products will be synchronized</Text>
                <Text>• Estimated time: 2-3 minutes per account</Text>
                <Text>• Rate limit: 3 requests/second (eMAG API v4.4.9)</Text>
              </Space>
            }
            type="info"
            showIcon
            icon={<DashboardOutlined />}
          />
        </Card>
      )}

      {/* Tabs for Products and History */}
      <Card>
        <Tabs 
          defaultActiveKey="products"
          items={[
            {
              key: 'products',
              label: (
                <Space>
                  <DatabaseOutlined />
                  <span>Products ({stats.total_products})</span>
                </Space>
              ),
              children: (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  {/* Filters and Actions */}
                  <Row gutter={[16, 16]} align="middle">
                    <Col flex="auto">
                      <Space wrap>
                        <Input
                          placeholder="Search by name or SKU..."
                          prefix={<SearchOutlined />}
                          value={searchText}
                          onChange={(e) => setSearchText(e.target.value)}
                          style={{ width: 250 }}
                          allowClear
                        />
                        <Select
                          placeholder="Filter by Account"
                          value={selectedAccountType}
                          onChange={setSelectedAccountType}
                          style={{ width: 150 }}
                          allowClear
                        >
                          <Select.Option value="main">MAIN</Select.Option>
                          <Select.Option value="fbe">FBE</Select.Option>
                        </Select>
                        <Select
                          placeholder="Filter by Brand"
                          value={selectedBrand}
                          onChange={setSelectedBrand}
                          style={{ width: 200 }}
                          allowClear
                          showSearch
                        >
                          {uniqueBrands.map(brand => (
                            <Select.Option key={brand} value={brand}>
                              {brand}
                            </Select.Option>
                          ))}
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
                    dataSource={getFilteredProducts()}
                    rowKey="id"
                    loading={loading}
                    scroll={{ x: 1500 }}
                    pagination={{
                      showSizeChanger: true,
                      showTotal: (total) => `Total ${total} products`,
                      pageSizeOptions: ['10', '20', '50', '100']
                    }}
                  />
                </Space>
              )
            },
            {
              key: 'history',
              label: (
                <Space>
                  <ClockCircleOutlined />
                  <span>Sync History</span>
                </Space>
              ),
              children: (
                <Timeline>
                  {syncHistory.length === 0 ? (
                    <Empty description="No sync history available" />
                  ) : (
                    syncHistory.map((history, index) => (
                      <Timeline.Item
                        key={history.sync_id || `sync-${index}`}
                        color={history.status === 'completed' ? 'green' : 
                               history.status === 'error' ? 'red' : 'blue'}
                        dot={
                          history.status === 'completed' ? <CheckCircleOutlined /> :
                          history.status === 'error' ? <CloseCircleOutlined /> :
                          <SyncOutlined spin />
                        }
                      >
                        <Space direction="vertical" size="small">
                          <Space>
                            <Tag color={history.account_type === 'main' ? 'blue' : 'green'}>
                              {history.account_type ? history.account_type.toUpperCase() : 'N/A'}
                            </Tag>
                            <Tag color={history.status === 'completed' ? 'success' : 'error'}>
                              {history.status || 'unknown'}
                            </Tag>
                            <Text type="secondary">
                              {history.started_at ? new Date(history.started_at).toLocaleString() : 'N/A'}
                            </Text>
                          </Space>
                          <Descriptions size="small" column={4}>
                            <Descriptions.Item label="Processed">
                              {history.products_processed || 0}
                            </Descriptions.Item>
                            <Descriptions.Item label="Created">
                              {history.products_created || 0}
                            </Descriptions.Item>
                            <Descriptions.Item label="Updated">
                              {history.products_updated || 0}
                            </Descriptions.Item>
                            <Descriptions.Item label="Errors">
                              {history.errors || 0}
                            </Descriptions.Item>
                          </Descriptions>
                          {history.duration_seconds && (
                            <Text type="secondary">
                              Duration: {Math.round(history.duration_seconds)} seconds
                            </Text>
                          )}
                        </Space>
                      </Timeline.Item>
                    ))
                  )}
                </Timeline>
              )
            }
          ]}
        />
      </Card>

      {/* Sync Options Modal */}
      <Modal
        title="Sync Options"
        open={optionsModalVisible}
        onOk={() => {
          form.validateFields().then((values) => {
            setSyncOptions(values)
            setOptionsModalVisible(false)
            notificationApi.success({
              message: 'Options Updated',
              description: 'Sync options have been updated successfully'
            })
          })
        }}
        onCancel={() => setOptionsModalVisible(false)}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={syncOptions}
        >
          <Form.Item
            label="Max Pages per Account"
            name="max_pages_per_account"
            tooltip="Maximum number of pages to fetch per account (100 products per page)"
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
          
          <Form.Item
            label="Delay Between Requests (seconds)"
            name="delay_between_requests"
            tooltip="Delay between API requests to respect rate limits (min: 0.5s)"
          >
            <InputNumber min={0.5} max={30} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          
          <Form.Item
            label="Include Inactive Products"
            name="include_inactive"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          
          <Form.Item
            label="Batch Size"
            name="batch_size"
            tooltip="Number of products to save in each database batch"
          >
            <InputNumber min={10} max={500} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Product Details Drawer */}
      <Drawer
        title={<Space><DatabaseOutlined /> Product Details</Space>}
        open={productDetailsVisible}
        onClose={() => setProductDetailsVisible(false)}
        width={600}
      >
        {selectedProduct && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="SKU">
              <Text strong>{selectedProduct.sku}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Name">
              {selectedProduct.name}
            </Descriptions.Item>
            <Descriptions.Item label="Account">
              <Tag color={selectedProduct.account_type === 'main' ? 'blue' : 'green'}>
                {selectedProduct.account_type.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Brand">
              {selectedProduct.brand || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Category">
              {selectedProduct.emag_category_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Price">
              {selectedProduct.price ? `${selectedProduct.price.toFixed(2)} ${selectedProduct.currency}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Stock">
              <Tag color={selectedProduct.stock_quantity > 0 ? 'success' : 'error'}>
                {selectedProduct.stock_quantity}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedProduct.is_active ? 'success' : 'default'}>
                {selectedProduct.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Sync Status">
              <Tag color={
                selectedProduct.sync_status === 'synced' ? 'success' :
                selectedProduct.sync_status === 'pending' ? 'processing' :
                selectedProduct.sync_status === 'error' ? 'error' : 'default'
              }>
                {selectedProduct.sync_status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Last Synced">
              {selectedProduct.last_synced_at ? new Date(selectedProduct.last_synced_at).toLocaleString() : 'Never'}
            </Descriptions.Item>
            <Descriptions.Item label="Validation Status">
              <ValidationStatusBadge
                status={selectedProduct.validation_status}
                description={selectedProduct.validation_status_description}
              />
            </Descriptions.Item>
            <Descriptions.Item label="Genius Program">
              <GeniusBadge
                eligibility={selectedProduct.genius_eligibility}
                eligibilityType={selectedProduct.genius_eligibility_type}
                computed={selectedProduct.genius_computed}
                showDetails={true}
              />
            </Descriptions.Item>
            {selectedProduct.family_name && (
              <Descriptions.Item label="Product Family">
                <ProductFamilyGroup
                  familyId={selectedProduct.family_id}
                  familyName={selectedProduct.family_name}
                  familyTypeId={selectedProduct.family_type_id}
                />
              </Descriptions.Item>
            )}
            {selectedProduct.part_number_key && (
              <Descriptions.Item label="Part Number Key">
                <Text copyable>{selectedProduct.part_number_key}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
        
        {/* Smart Deals Check Button */}
        {selectedProduct && selectedProduct.price && (
          <div style={{ marginTop: 16 }}>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              block
              onClick={() => {
                setSelectedProductForSmartDeals({
                  id: selectedProduct.id,
                  price: selectedProduct.price!,
                  currency: selectedProduct.currency
                })
                setSmartDealsVisible(true)
              }}
            >
              Check Smart Deals Eligibility
            </Button>
          </div>
        )}
      </Drawer>

      {/* EAN Search Modal */}
      <EanSearchModal
        visible={eanSearchVisible}
        onClose={() => setEanSearchVisible(false)}
        onProductSelected={(product) => {
          logInfo('Selected eMAG product', { component: 'EmagProductSync', productId: product.id, productName: product.name })
          notificationApi.success({
            message: 'Product Selected',
            description: `Selected: ${product.name}`,
            placement: 'topRight'
          })
        }}
      />

      {/* Smart Deals Checker Modal */}
      <SmartDealsChecker
        visible={smartDealsVisible}
        onClose={() => {
          setSmartDealsVisible(false)
          setSelectedProductForSmartDeals(null)
        }}
        productId={selectedProductForSmartDeals?.id}
        currentPrice={selectedProductForSmartDeals?.price}
        currency={selectedProductForSmartDeals?.currency}
      />
    </div>
  )
}

export default EmagProductSync
