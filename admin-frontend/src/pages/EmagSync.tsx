import React, { useEffect, useState, useRef } from 'react'
import {
  Row, Col, Card, Button, Table, Typography, Space, Progress, Tag, notification,
  Switch, Tooltip, Modal, InputNumber, Alert, Statistic, Radio,
  Divider, Badge, Descriptions, Steps, Timeline, Drawer, Tabs
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
  CloudSyncOutlined,
  DatabaseOutlined,
  WarningOutlined,
  ShoppingCartOutlined,
  ApiOutlined,
  MonitorOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  RocketOutlined,
  HeartOutlined
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
  maxPages: number
  delayBetweenRequests: number
}

interface SyncProgress {
  isRunning: boolean
  currentAccount?: string
  currentPage?: number
  totalPages?: number
  processedOffers: number
  estimatedTimeRemaining?: number
  syncType?: 'products' | 'offers' | 'orders'
  startTime?: string
  throughput?: number
  errors?: number
  warnings?: number
}

interface ProductRecord {
  id: string
  sku: string
  name: string
  account_type: string
  price?: number
  currency?: string
  stock_quantity?: number
  status?: string
  is_active?: boolean
  last_synced_at?: string | null
  sync_status?: string
  brand?: string | null
  category_name?: string | null
}

const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000 // 5 minutes for better real-time updates
const SYNC_PROGRESS_INTERVAL_MS = 2000 // 2 seconds
const HEALTH_CHECK_INTERVAL_MS = 30 * 1000 // 30 seconds

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
  const [syncingProducts, setSyncingProducts] = useState(false)
  const [syncingOffers, setSyncingOffers] = useState(false)
  const [syncOptions, setSyncOptions] = useState<SyncOptions>({
    maxPages: 100,
    delayBetweenRequests: 1.0
  })
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    isRunning: false,
    processedOffers: 0
  })
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false)
  const [syncDetailsModal, setSyncDetailsModal] = useState<{ visible: boolean; record?: SyncRecord }>({ visible: false })
  const progressInterval = useRef<number | null>(null)
  const [ordersSyncLoading, setOrdersSyncLoading] = useState(false)
  const [products, setProducts] = useState<ProductRecord[]>([])
  const [productsLoading, setProductsLoading] = useState(false)
  const [productAccountFilter, setProductAccountFilter] = useState<'both' | 'main' | 'fbe'>('both')
  const [healthStatus, setHealthStatus] = useState<{ status: 'healthy' | 'warning' | 'error', message?: string }>({ status: 'healthy' })
  const [realTimeUpdates, setRealTimeUpdates] = useState(true)
  const [syncDrawerVisible, setSyncDrawerVisible] = useState(false)
  const healthCheckInterval = useRef<number | null>(null)

  useEffect(() => {
    fetchEmagData()

    // Auto-refresh data every 60 minutes
    const refreshInterval = setInterval(() => {
      if (!syncingProducts && !syncingOffers && !syncProgress.isRunning) {
        fetchEmagData()
      }
    }, AUTO_REFRESH_INTERVAL_MS)

    return () => clearInterval(refreshInterval)
  }, [syncingProducts, syncingOffers, syncProgress.isRunning])

  const fetchEmagData = async () => {
    try {
      setLoading(true)
      setProductsLoading(true)

      // Debug: Check if user is authenticated
      const token = localStorage.getItem('access_token')
      console.log('🔐 Auth token present:', !!token)
      console.log('🔐 Token length:', token?.length || 0)

      let productList: ProductRecord[] = []
      let mainProductsCount = 0
      let fbeProductsCount = 0
      let offersCount = 0

      try {
        const productsResponse = await api.get('/emag/enhanced/products/all', {
          params: {
            account_type: 'both',
            max_pages_per_account: 5,
            include_inactive: false
          }
        })
        const responseProducts = productsResponse?.data?.products
        if (Array.isArray(responseProducts)) {
          productList = responseProducts
          mainProductsCount = productList.filter(product => product.account_type === 'main').length
          fbeProductsCount = productList.filter(product => product.account_type === 'fbe').length
        }
      } catch (error) {
        console.warn('Failed to fetch combined product list:', error)
      }

      if (!productList.length) {
        try {
          const mainProductsResponse = await api.get('/emag/enhanced/products/all', {
            params: {
              account_type: 'main',
              max_pages_per_account: 5,
              include_inactive: false
            }
          })
          const mainProducts = Array.isArray(mainProductsResponse?.data?.products) ? mainProductsResponse.data.products : []
          productList = [...productList, ...mainProducts]
          mainProductsCount = mainProductsResponse?.data?.total_count || mainProducts.length || mainProductsCount
        } catch (error) {
          console.warn('Failed to fetch main products:', error)
        }

        try {
          const fbeProductsResponse = await api.get('/emag/enhanced/products/all', {
            params: {
              account_type: 'fbe',
              max_pages_per_account: 5,
              include_inactive: false
            }
          })
          const fbeProducts = Array.isArray(fbeProductsResponse?.data?.products) ? fbeProductsResponse.data.products : []
          productList = [...productList, ...fbeProducts]
          fbeProductsCount = fbeProductsResponse?.data?.total_count || fbeProducts.length || fbeProductsCount
        } catch (error) {
          console.warn('Failed to fetch FBE products:', error)
        }
      }

      try {
        const offersResponse = await api.get('/emag/enhanced/offers/all?account_type=both&max_pages_per_account=1')
        offersCount = offersResponse?.data?.total_count || 0
      } catch (error) {
        console.warn('Failed to fetch offers:', error)
      }

      // Get sync progress (but don't return early if no active sync)
      let syncProgressData: any = { status: 'no_data' }
      try {
        const syncProgressResponse = await api.get('/emag/enhanced/products/sync-progress')
        syncProgressData = syncProgressResponse.data
      } catch (error) {
        console.warn('Failed to fetch sync progress:', error)
      }

      if (syncProgressData.status === 'no_data') {
        if (syncProgressData.detail) {
          notificationApi.info({
            message: 'eMAG sync încă neinițiat',
            description: syncProgressData.detail,
            placement: 'topRight',
          })
        }
      }

      // Always get sync history for the table display (but use mock data if API fails)
      let syncHistoryData: any = { sync_records: [] }
      try {
        const syncHistoryResponse = await api.get('/emag/enhanced/status?account_type=main')
        if (syncHistoryResponse.data.latest_sync) {
          syncHistoryData = { sync_records: [syncHistoryResponse.data.latest_sync] }
        }
      } catch (error) {
        console.warn('Failed to fetch sync history:', error)
      }

      const uniqueProductsMap = new Map<string, ProductRecord>()
      for (const product of productList) {
        const key = `${product?.id ?? ''}-${product?.sku ?? ''}-${product?.account_type ?? ''}`
        if (key.trim()) {
          uniqueProductsMap.set(key, product)
        }
      }

      const uniqueProducts = Array.from(uniqueProductsMap.values())
      const uniqueMainCount = uniqueProducts.filter(product => product.account_type === 'main').length
      const uniqueFbeCount = uniqueProducts.filter(product => product.account_type === 'fbe').length

      console.log('✅ Fetched eMAG products', {
        total: productList.length,
        unique: uniqueProducts.length,
        main: uniqueMainCount,
        fbe: uniqueFbeCount,
        sample: uniqueProducts.slice(0, 3)
      })

      setProducts(uniqueProducts)

      setData({
        total_products: uniqueProducts.length || (mainProductsCount || 0) + (fbeProductsCount || 0),
        total_offers: offersCount || 0,
        main_products: uniqueMainCount || mainProductsCount || 0,
        fbe_products: uniqueFbeCount || fbeProductsCount || 0,
        recent_syncs: Array.isArray(syncHistoryData.sync_records) ? syncHistoryData.sync_records : []
      })

    } catch (error) {
      console.error('Error fetching eMAG data:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      const backendDetail = axiosError.response?.data?.detail
      const isRateLimit = axiosError.response?.status === 429
      const isCorsError = axiosError.message?.includes('CORS') || axiosError.code === 'ERR_NETWORK'

      let errorMessage = 'eMAG status indisponibil'
      let errorDescription = backendDetail ?? 'Nu s-a putut obține statusul de la backend. Se vor afișa date demonstrative până când serviciul API este disponibil.'

      if (isRateLimit) {
        errorMessage = 'Prea multe cereri'
        errorDescription = 'Sistemul a detectat prea multe cereri. Vă rugăm să așteptați câteva secunde și să încercați din nou.'
      } else if (isCorsError) {
        errorMessage = 'Eroare de conectivitate'
        errorDescription = 'Nu s-a putut conecta la server. Verificați dacă serverul backend rulează pe portul corect.'
      }

      notificationApi.warning({
        message: errorMessage,
        description: errorDescription,
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
            error_message: backendDetail ?? 'Connection timeout'
          },
        ],
      })
      setProducts([])
    } finally {
      setLoading(false)
      setProductsLoading(false)
    }
  }

  const handleSyncProducts = async () => {
    try {
      setSyncingProducts(true)
      setSyncProgress({ isRunning: true, processedOffers: 0 })

      // Debug: Check authentication
      const token = localStorage.getItem('access_token')
      console.log('🔐 Sync Products - Auth token present:', !!token)

      // Start progress tracking
      startProgressTracking()

      await api.post('/emag/enhanced/sync/all-products', {
        max_pages_per_account: syncOptions.maxPages,
        delay_between_requests: syncOptions.delayBetweenRequests,
        include_inactive: false
      })

      notificationApi.success({
        message: '🚀 Sincronizare Produse Inițiată',
        description: (
          <div>
            <p><strong>Sync Complete Products (MAIN + FBE)</strong></p>
            <p>📊 Max Pages: {syncOptions.maxPages} | Delay: {syncOptions.delayBetweenRequests}s</p>
            <p>⏱️ Se sincronizează toate produsele din ambele conturi</p>
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
      console.error('Error starting products sync:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      notificationApi.error({
        message: 'Eroare Sincronizare Produse',
        description:
          axiosError.response?.data?.detail ??
          'Nu s-a putut porni sincronizarea produselor. Verifică conexiunea și încearcă din nou.',
        duration: 6
      })
      setSyncProgress({ isRunning: false, processedOffers: 0 })
    } finally {
      setSyncingProducts(false)
    }
  }

  const handleSyncOffers = async () => {
    try {
      setSyncingOffers(true)
      setSyncProgress({ isRunning: true, processedOffers: 0 })

      // Debug: Check authentication
      const token = localStorage.getItem('access_token')
      console.log('🔐 Sync Offers - Auth token present:', !!token)

      // Start progress tracking
      startProgressTracking()

      await api.post('/emag/enhanced/sync/all-offers', {
        max_pages_per_account: syncOptions.maxPages,
        delay_between_requests: syncOptions.delayBetweenRequests
      })

      notificationApi.success({
        message: '🚀 Sincronizare Oferte Inițiată',
        description: (
          <div>
            <p><strong>Sync Complete Offers (MAIN + FBE)</strong></p>
            <p>📊 Max Pages: {syncOptions.maxPages} | Delay: {syncOptions.delayBetweenRequests}s</p>
            <p>⏱️ Se sincronizează toate ofertele din ambele conturi</p>
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
      console.error('Error starting offers sync:', error)
      const axiosError = error as AxiosError<{ detail?: string }>
      notificationApi.error({
        message: 'Eroare Sincronizare Oferte',
        description:
          axiosError.response?.data?.detail ??
          'Nu s-a putut porni sincronizarea ofertelor. Verifică conexiunea și încearcă din nou.',
        duration: 6
      })
      setSyncProgress({ isRunning: false, processedOffers: 0 })
    } finally {
      setSyncingOffers(false)
    }
  }

  const startProgressTracking = () => {
    if (progressInterval.current) {
      clearInterval(progressInterval.current)
    }

    progressInterval.current = window.setInterval(async () => {
      try {
        // Fetch current sync progress
        const response = await api.get('/emag/enhanced/products/sync-progress')
        const progress = response.data

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
    }, SYNC_PROGRESS_INTERVAL_MS) // Update every 2 seconds
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
      await api.post('/emag/enhanced/sync/orders')
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
          'Nu s-a putut porni sincronizarea comenzilor. Verifică conexiunea și încearcă din nou.',
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
      const response = await api.get(`/emag/enhanced/sync/export?include_products=true&include_offers=true&account_type=both&format=json`, {
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

  // Health check monitoring
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.get('/health')
        setHealthStatus({ status: 'healthy', message: 'All systems operational' })
      } catch (error) {
        setHealthStatus({ status: 'error', message: 'Backend connection failed' })
      }
    }

    if (realTimeUpdates) {
      checkHealth() // Initial check
      healthCheckInterval.current = window.setInterval(checkHealth, HEALTH_CHECK_INTERVAL_MS)
    }

    return () => {
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current)
      }
    }
  }, [realTimeUpdates])

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      stopProgressTracking()
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current)
      }
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
      render: (sync_id: string) => {
        if (!sync_id) return '-'
        return (
          <Tooltip title={sync_id}>
            <code style={{ fontSize: '12px' }}>
              {sync_id.substring(0, 12)}...
            </code>
          </Tooltip>
        )
      },
    },
    {
      title: 'Account',
      dataIndex: 'account_type',
      key: 'account_type',
      render: (account_type: string) => {
        if (!account_type) return '-'
        return (
          <Badge
            color={account_type === 'main' ? 'blue' : 'green'}
            text={account_type.toUpperCase()}
          />
        )
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: SyncRecord) => {
        if (!status) return '-'
        return (
          <Space>
            {getStatusIcon(status)}
            <Tag color={getStatusColor(status)}>
              {status.toUpperCase()}
            </Tag>
            {record?.error_message && (
              <Tooltip title={record.error_message}>
                <WarningOutlined style={{ color: '#ff4d4f' }} />
              </Tooltip>
            )}
          </Space>
        )
      },
    },
    {
      title: 'Offers Processed',
      dataIndex: 'total_offers_processed',
      key: 'total_offers_processed',
      render: (count: number) => {
        const safeCount = count || 0
        return (
          <Statistic
            value={safeCount}
            valueStyle={{ fontSize: '14px' }}
          />
        )
      },
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => {
        if (!date) return '-'
        try {
          return new Date(date).toLocaleString('ro-RO')
        } catch (error) {
          return '-'
        }
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (seconds: number | null) => {
        if (!seconds || seconds <= 0) return '-'
        const minutes = Math.floor(seconds / 60)
        const remainingSeconds = Math.round(seconds % 60)
        return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: SyncRecord) => {
        if (!record) return null
        return (
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
        )
      },
    },
  ]

  const productColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (sku: string) => sku || '-'
    },
    {
      title: 'Produs',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => name || '-'
    },
    {
      title: 'Cont',
      dataIndex: 'account_type',
      key: 'account_type',
      render: (account_type: string) => (
        <Badge
          color={account_type === 'main' ? 'blue' : 'green'}
          text={(account_type || '-').toUpperCase()}
        />
      )
    },
    {
      title: 'Brand',
      dataIndex: 'brand',
      key: 'brand',
      render: (brand: string | null) => brand || '-'
    },
    {
      title: 'Categorie',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (category_name: string | null | undefined) => category_name || '-'
    },
    {
      title: 'Preț',
      key: 'price',
      render: (_: unknown, record: ProductRecord) => {
        if (typeof record.price !== 'number') {
          return '-'
        }
        try {
          return new Intl.NumberFormat('ro-RO', {
            style: 'currency',
            currency: record.currency || 'RON'
          }).format(record.price)
        } catch (error) {
          return record.price.toFixed(2)
        }
      }
    },
    {
      title: 'Stoc',
      dataIndex: 'stock_quantity',
      key: 'stock_quantity',
      render: (stock_quantity: number | undefined) => (typeof stock_quantity === 'number' ? stock_quantity : '-')
    },
    {
      title: 'Status',
      dataIndex: 'sync_status',
      key: 'sync_status',
      render: (sync_status: string | undefined) => (
        sync_status ? <Tag color={sync_status === 'synced' ? 'green' : 'orange'}>{sync_status.toUpperCase()}</Tag> : '-' 
      )
    },
    {
      title: 'Ultima sincronizare',
      dataIndex: 'last_synced_at',
      key: 'last_synced_at',
      render: (last_synced_at: string | null | undefined) => {
        if (!last_synced_at) return '-'
        try {
          return new Date(last_synced_at).toLocaleString('ro-RO')
        } catch (error) {
          return last_synced_at
        }
      }
    }
  ]

  const filteredProducts = productAccountFilter === 'both'
    ? products
    : products.filter(product => product.account_type === productAccountFilter)

  return (
    <div className="emag-sync">
      {contextHolder}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2}>
              <Space>
                <RocketOutlined style={{ color: '#1890ff' }} />
                eMAG Integration v2.0
              </Space>
            </Title>
            <p style={{ color: '#666', margin: 0 }}>
              Advanced eMAG marketplace integration with real-time monitoring
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <Space direction="vertical" size="small" style={{ alignItems: 'flex-end' }}>
              <Badge
                status={healthStatus.status === 'healthy' ? 'success' : healthStatus.status === 'warning' ? 'warning' : 'error'}
                text={`System ${healthStatus.status === 'healthy' ? 'Healthy' : healthStatus.status === 'warning' ? 'Warning' : 'Error'}`}
              />
              <div style={{ fontSize: '12px', color: '#999' }}>
                🔄 Auto-refresh: {realTimeUpdates ? '5m' : 'Off'}
              </div>
              <div style={{ fontSize: '11px', color: '#ccc' }}>
                Last updated: {new Date().toLocaleTimeString('ro-RO')}
              </div>
            </Space>
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
            <Tooltip title="Real-time Updates">
              <Switch
                checked={realTimeUpdates}
                onChange={setRealTimeUpdates}
                checkedChildren={<MonitorOutlined />}
                unCheckedChildren={<MonitorOutlined />}
              />
            </Tooltip>
            <Tooltip title="Advanced Metrics">
              <Button
                icon={<ThunderboltOutlined />}
                onClick={() => setSyncDrawerVisible(true)}
                type={'default'}
              >
                Metrics
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
        {/* Advanced Options */}
        {showAdvancedOptions && (
          <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px', marginBottom: '24px' }}>
            <h4 style={{ marginBottom: '16px' }}>
              <SettingOutlined style={{ marginRight: '8px' }} />
              Advanced Sync Options
            </h4>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: '500' }}>
                    Max Pages per Account:
                  </label>
                  <InputNumber
                    min={1}
                    max={500}
                    value={syncOptions.maxPages}
                    onChange={(value) => setSyncOptions(prev => ({ ...prev, maxPages: value || 100 }))}
                    style={{ width: '100%' }}
                  />
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: '500' }}>
                    Delay Between Requests (seconds):
                  </label>
                  <InputNumber
                    min={0.1}
                    max={10.0}
                    step={0.1}
                    value={syncOptions.delayBetweenRequests}
                    onChange={(value) => setSyncOptions(prev => ({ ...prev, delayBetweenRequests: value || 1.0 }))}
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
                  icon={<CloudSyncOutlined />}
                  onClick={handleSyncProducts}
                  loading={syncingProducts}
                  block
                  disabled={syncProgress.isRunning}
                >
                  Sync All Products (MAIN + FBE)
                </Button>
                <Button
                  icon={<ShoppingCartOutlined />}
                  onClick={handleSyncOffers}
                  loading={syncingOffers}
                  block
                  disabled={syncProgress.isRunning}
                >
                  Sync All Offers (MAIN + FBE)
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
        </Row>
      </Card>

      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <span>Produse sincronizate</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
        extra={
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            value={productAccountFilter}
            onChange={(event) => setProductAccountFilter(event.target.value)}
          >
            <Radio.Button value="both">Toate</Radio.Button>
            <Radio.Button value="main">MAIN</Radio.Button>
            <Radio.Button value="fbe">FBE</Radio.Button>
          </Radio.Group>
        }
      >
        <Table
          rowKey={(record) => record?.id || `${record?.sku}-${record?.account_type}`}
          dataSource={filteredProducts}
          columns={productColumns}
          loading={loading || productsLoading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          scroll={{ x: 800 }}
          locale={{ emptyText: 'Nu există produse sincronizate disponibile.' }}
        />
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
          rowKey={(record) => record?.sync_id || Math.random().toString()}
          dataSource={Array.isArray(data.recent_syncs) ? data.recent_syncs : []}
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

      {/* Advanced Metrics Drawer */}
      <Drawer
        title={
          <Space>
            <ThunderboltOutlined />
            <span>Advanced Sync Metrics & Analytics</span>
          </Space>
        }
        placement="right"
        size="large"
        onClose={() => setSyncDrawerVisible(false)}
        open={syncDrawerVisible}
      >
        <Tabs
          defaultActiveKey="performance"
          items={[
            {
              key: 'performance',
              label: (
                <span>
                  <MonitorOutlined />
                  Performance
                </span>
              ),
              children: (
                <div>
                  <Alert
                    message="Real-time Performance Metrics"
                    description="Monitor sync performance, throughput, and system health in real-time."
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="Sync Throughput"
                          value={syncProgress.throughput || 0}
                          suffix="items/min"
                          prefix={<ApiOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="Error Rate"
                          value={syncProgress.errors || 0}
                          suffix="%"
                          prefix={<WarningOutlined />}
                          valueStyle={{ color: syncProgress.errors && syncProgress.errors > 5 ? '#cf1322' : '#3f8600' }}
                        />
                      </Card>
                    </Col>
                    <Col span={24}>
                      <Card size="small" title="Sync Timeline">
                        <Timeline
                          items={[
                            {
                              dot: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
                              children: 'System initialized and ready',
                            },
                            {
                              dot: syncProgress.isRunning ? <SyncOutlined spin style={{ color: '#1890ff' }} /> : <ClockCircleOutlined style={{ color: '#fa8c16' }} />,
                              children: syncProgress.isRunning ? `Syncing ${syncProgress.currentAccount?.toUpperCase()} account` : 'Waiting for sync operation',
                            },
                            {
                              dot: <BulbOutlined style={{ color: '#722ed1' }} />,
                              children: 'Advanced analytics available',
                            },
                          ]}
                        />
                      </Card>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'health',
              label: (
                <span>
                  <HeartOutlined />
                  System Health
                </span>
              ),
              children: (
                <div>
                  <Alert
                    message={`System Status: ${healthStatus.status.toUpperCase()}`}
                    description={healthStatus.message}
                    type={healthStatus.status === 'healthy' ? 'success' : healthStatus.status === 'warning' ? 'warning' : 'error'}
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Steps
                    direction="vertical"
                    current={healthStatus.status === 'healthy' ? 2 : healthStatus.status === 'warning' ? 1 : 0}
                    items={[
                      {
                        title: 'Backend Connection',
                        description: 'FastAPI server connectivity',
                        status: healthStatus.status === 'error' ? 'error' : 'finish',
                      },
                      {
                        title: 'eMAG API Integration',
                        description: 'eMAG marketplace API status',
                        status: healthStatus.status === 'warning' ? 'error' : 'finish',
                      },
                      {
                        title: 'Database Operations',
                        description: 'PostgreSQL database health',
                        status: healthStatus.status === 'healthy' ? 'finish' : 'wait',
                      },
                    ]}
                  />
                </div>
              ),
            },
          ]}
        />
      </Drawer>
    </div>
  )
}

export default EmagSync
