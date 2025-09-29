import React, { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Typography,
  Button,
  Progress,
  Tag,
  Space,
  Spin,
  Alert,
  Segmented,
  Modal,
  InputNumber,
  Slider,
  Divider,
  List,
  notification
} from 'antd'
import {
  ShoppingCartOutlined,
  DollarOutlined,
  UserOutlined,
  LinkOutlined,
  SyncOutlined,
  RiseOutlined,
  FallOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  EyeOutlined,
  DownloadOutlined,
  FireOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  AlertOutlined,
  InfoCircleOutlined,
  AimOutlined,
  SafetyOutlined,
  WarningOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend
} from 'recharts'
import { formatDistanceToNow } from 'date-fns'
import api from '../services/api'

const { Title, Text } = Typography

type SalesRange = '7d' | '30d' | '12m'
type InsightTone = 'positive' | 'warning' | 'negative' | 'neutral'

interface ForecastPoint {
  period: string
  actual?: number
  forecast: number
}

interface InventoryRiskItem {
  key: string
  category: string
  lowStock: number
  outOfStock: number
  riskPercent: number
  total: number
  severity: 'low' | 'medium' | 'high'
}

interface InsightItem {
  key: string
  title: string
  description: string
  tone: InsightTone
}

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
  salesGrowth: number
  ordersGrowth: number
  customersGrowth: number
  emagGrowth: number
  systemHealth: {
    database: 'healthy' | 'warning' | 'error'
    api: 'healthy' | 'warning' | 'error'
    emag: 'healthy' | 'warning' | 'error'
  }
  realtimeMetrics: {
    activeUsers: number
    pendingOrders: number
    lowStockItems: number
    syncProgress: number
  }
  performanceData: any[]
  inventoryStatus: any[]
  salesDataByRange: Record<SalesRange | string, any[]>
  revenueForecast?: ForecastPoint[]
}

type DashboardApiResponse = Partial<Omit<DashboardData, 'systemHealth' | 'realtimeMetrics'>> & {
  systemHealth?: Partial<DashboardData['systemHealth']>
  realtimeMetrics?: Partial<DashboardData['realtimeMetrics']>
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

const DEFAULT_DASHBOARD_DATA: DashboardData = {
  totalSales: 0,
  totalOrders: 0,
  totalCustomers: 0,
  emagProducts: 0,
  inventoryValue: 0,
  syncStatus: 'unknown',
  recentOrders: [],
  salesData: [],
  topProducts: [],
  salesGrowth: 0,
  ordersGrowth: 0,
  customersGrowth: 0,
  emagGrowth: 0,
  systemHealth: {
    database: 'healthy',
    api: 'healthy',
    emag: 'healthy'
  },
  realtimeMetrics: {
    activeUsers: 0,
    pendingOrders: 0,
    lowStockItems: 0,
    syncProgress: 0
  },
  performanceData: [],
  inventoryStatus: [],
  salesDataByRange: {
    '7d': [],
    '30d': [],
    '12m': []
  },
  revenueForecast: []
}

const mergeDashboardData = (payload: DashboardApiResponse = {}): DashboardData => ({
  ...DEFAULT_DASHBOARD_DATA,
  ...payload,
  recentOrders: payload.recentOrders ?? DEFAULT_DASHBOARD_DATA.recentOrders,
  salesData: payload.salesData ?? DEFAULT_DASHBOARD_DATA.salesData,
  topProducts: payload.topProducts ?? DEFAULT_DASHBOARD_DATA.topProducts,
  performanceData: payload.performanceData ?? DEFAULT_DASHBOARD_DATA.performanceData,
  inventoryStatus: payload.inventoryStatus ?? DEFAULT_DASHBOARD_DATA.inventoryStatus,
  revenueForecast: payload.revenueForecast ?? DEFAULT_DASHBOARD_DATA.revenueForecast,
  systemHealth: {
    ...DEFAULT_DASHBOARD_DATA.systemHealth,
    ...(payload.systemHealth ?? {})
  },
  realtimeMetrics: {
    ...DEFAULT_DASHBOARD_DATA.realtimeMetrics,
    ...(payload.realtimeMetrics ?? {})
  },
  salesDataByRange: (() => {
    const mergedRanges = {
      ...DEFAULT_DASHBOARD_DATA.salesDataByRange,
      ...(payload.salesDataByRange ?? {})
    }

    if (!mergedRanges['30d']) {
      mergedRanges['30d'] = payload.salesData ?? DEFAULT_DASHBOARD_DATA.salesData
    }
    if (!mergedRanges['7d']) {
      const source = mergedRanges['30d'] ?? []
      mergedRanges['7d'] = source.slice(-7)
    }
    if (!mergedRanges['12m']) {
      const source = mergedRanges['30d'] ?? []
      mergedRanges['12m'] = source
    }

    return mergedRanges
  })()
})

const Dashboard: React.FC = () => {
  const [notificationApi, contextHolder] = notification.useNotification()
  const [data, setData] = useState<DashboardData>(DEFAULT_DASHBOARD_DATA)
  const [loading, setLoading] = useState(true)
  const [realTimeLoading, setRealTimeLoading] = useState(false)
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true)
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null)
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('all')
  const [selectedSalesRange, setSelectedSalesRange] = useState<SalesRange>('30d')
  const [salesTarget, setSalesTarget] = useState<number>(60000)
  const [isTargetModalOpen, setIsTargetModalOpen] = useState(false)
  const [editingTarget, setEditingTarget] = useState<number>(salesTarget)
  const [showForecastDetails, setShowForecastDetails] = useState(false)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const formatCurrency = useCallback((value: number) => {
    if (!Number.isFinite(value)) {
      return '0 RON'
    }
    return `${value.toLocaleString('ro-RO')} RON`
  }, [])

  const revenueForecast = useMemo<ForecastPoint[]>(() => {
    if (Array.isArray(data.revenueForecast) && data.revenueForecast.length) {
      return data.revenueForecast
    }

    const baseSeries = (data.salesDataByRange?.['30d'] ?? []).slice(-4)
    if (baseSeries.length) {
      const rollingAverage = baseSeries.reduce((sum, point) => sum + (point.sales ?? 0), 0) / baseSeries.length
      return [
        ...baseSeries.map((point, index) => ({
          period: point.name ?? `Week ${index + 1}`,
          actual: Number(point.sales ?? 0),
          forecast: Number(point.sales ?? 0)
        })),
        {
          period: `Next Week`,
          forecast: Math.round(rollingAverage * 1.06)
        },
        {
          period: `Week +2`,
          forecast: Math.round(rollingAverage * 1.12)
        }
      ]
    }

    return [
      { period: 'Week 1', actual: 18900, forecast: 19250 },
      { period: 'Week 2', actual: 17250, forecast: 17600 },
      { period: 'Week 3', actual: 19560, forecast: 20100 },
      { period: 'Week 4', forecast: 21320 },
      { period: 'Week 5', forecast: 21980 }
    ]
  }, [data.revenueForecast, data.salesDataByRange])

  const upcomingForecast = useMemo(() => {
    const futurePoints = revenueForecast.filter(point => point.actual == null)
    if (!futurePoints.length) {
      return null
    }

    const [nextPoint] = futurePoints
    const previousForecast = revenueForecast
      .slice(0, revenueForecast.indexOf(nextPoint))
      .reverse()
      .find(point => point.forecast != null)

    const growth = previousForecast
      ? ((nextPoint.forecast - previousForecast.forecast) / Math.max(previousForecast.forecast, 1)) * 100
      : 0

    return {
      nextPoint,
      growth
    }
  }, [revenueForecast])

  const forecastSummary = useMemo(() => {
    if (!revenueForecast.length) {
      return {
        average: 0,
        deviation: 0
      }
    }

    const values = revenueForecast.map(point => point.forecast)
    const average = values.reduce((sum, value) => sum + value, 0) / values.length
    const deviation = Math.sqrt(
      values.reduce((sum, value) => sum + Math.pow(value - average, 2), 0) / values.length
    )

    return {
      average,
      deviation
    }
  }, [revenueForecast])

  const toggleForecastDetails = useCallback(() => {
    setShowForecastDetails(prev => !prev)
  }, [])

  const operationsScore = useMemo(() => {
    let score = 100
    const breakdown: {
      key: string
      label: string
      status: 'positive' | 'warning' | 'critical'
      description: string
    }[] = []

    const realtimeMetrics = data.realtimeMetrics ?? {
      pendingOrders: 0,
      lowStockItems: 0,
      syncProgress: 0
    }

    const systemHealth = data.systemHealth ?? {
      database: 'healthy',
      api: 'healthy',
      emag: 'healthy'
    }

    const { pendingOrders = 0, lowStockItems = 0, syncProgress = 0 } = realtimeMetrics

    if (pendingOrders <= 5) {
      breakdown.push({
        key: 'pendingOrders',
        label: 'Order Queue',
        status: 'positive',
        description: `${pendingOrders} orders pending`
      })
    } else if (pendingOrders <= 10) {
      score -= 8
      breakdown.push({
        key: 'pendingOrders',
        label: 'Order Queue',
        status: 'warning',
        description: `${pendingOrders} orders pending`
      })
    } else {
      score -= 16
      breakdown.push({
        key: 'pendingOrders',
        label: 'Order Queue',
        status: 'critical',
        description: `${pendingOrders} orders pending`
      })
    }

    if (lowStockItems <= 3) {
      breakdown.push({
        key: 'lowStock',
        label: 'Inventory Levels',
        status: 'positive',
        description: `${lowStockItems} products flagged`
      })
    } else if (lowStockItems <= 6) {
      score -= 8
      breakdown.push({
        key: 'lowStock',
        label: 'Inventory Levels',
        status: 'warning',
        description: `${lowStockItems} products flagged`
      })
    } else {
      score -= 15
      breakdown.push({
        key: 'lowStock',
        label: 'Inventory Levels',
        status: 'critical',
        description: `${lowStockItems} products flagged`
      })
    }

    if (syncProgress >= 90) {
      score += 4
      breakdown.push({
        key: 'syncProgress',
        label: 'Sync Progress',
        status: 'positive',
        description: `${syncProgress}% complete`
      })
    } else if (syncProgress >= 70) {
      breakdown.push({
        key: 'syncProgress',
        label: 'Sync Progress',
        status: 'warning',
        description: `${syncProgress}% complete`
      })
    } else {
      score -= 12
      breakdown.push({
        key: 'syncProgress',
        label: 'Sync Progress',
        status: 'critical',
        description: `${syncProgress}% complete`
      })
    }

    const healthStatuses = [systemHealth.database, systemHealth.api, systemHealth.emag]
    const unhealthyCount = healthStatuses.filter(status => status !== 'healthy').length
    if (unhealthyCount === 0) {
      breakdown.push({
        key: 'systemHealth',
        label: 'System Health',
        status: 'positive',
        description: 'All services operational'
      })
    } else if (unhealthyCount === 1) {
      score -= 10
      breakdown.push({
        key: 'systemHealth',
        label: 'System Health',
        status: 'warning',
        description: 'Degraded service detected'
      })
    } else {
      score -= 20
      breakdown.push({
        key: 'systemHealth',
        label: 'System Health',
        status: 'critical',
        description: 'Multiple services degraded'
      })
    }

    const performanceMetrics = Array.isArray(data.performanceData) ? data.performanceData : []
    const belowTarget = performanceMetrics.filter(metric => metric?.value < metric?.target).length
    if (belowTarget === 0 && performanceMetrics.length) {
      score += 4
      breakdown.push({
        key: 'performance',
        label: 'Platform KPIs',
        status: 'positive',
        description: 'All performance KPIs on target'
      })
    } else if (belowTarget > 0) {
      const penalty = Math.min(12, belowTarget * 4)
      score -= penalty
      breakdown.push({
        key: 'performance',
        label: 'Platform KPIs',
        status: penalty > 8 ? 'critical' : 'warning',
        description: `${belowTarget} KPI${belowTarget === 1 ? '' : 's'} below target`
      })
    }

    const clampedScore = Math.max(0, Math.min(100, Math.round(score)))
    let grade: 'Excellent' | 'Good' | 'Needs Attention'
    let color: string

    if (clampedScore >= 85) {
      grade = 'Excellent'
      color = 'green'
    } else if (clampedScore >= 70) {
      grade = 'Good'
      color = 'blue'
    } else {
      grade = 'Needs Attention'
      color = 'red'
    }

    return {
      score: clampedScore,
      grade,
      color,
      breakdown
    }
  }, [data.performanceData, data.realtimeMetrics, data.systemHealth])

  const slaTargets = useMemo(() => ({
    fulfillmentTimeHours: 24,
    ticketResolutionHours: 48,
    firstResponseMinutes: 60
  }), [])

  const slaMetrics = useMemo(() => {
    const mockTickets = [
      { id: 'TCK-1024', createdAt: '2024-01-15T08:30:00Z', firstResponseAt: '2024-01-15T08:50:00Z', resolvedAt: '2024-01-15T18:15:00Z' },
      { id: 'TCK-1025', createdAt: '2024-01-15T09:10:00Z', firstResponseAt: '2024-01-15T11:05:00Z', resolvedAt: '2024-01-16T10:10:00Z' },
      { id: 'TCK-1026', createdAt: '2024-01-14T12:00:00Z', firstResponseAt: '2024-01-14T13:10:00Z', resolvedAt: '2024-01-15T07:45:00Z' },
      { id: 'TCK-1027', createdAt: '2024-01-15T06:20:00Z', firstResponseAt: '2024-01-15T07:05:00Z', resolvedAt: '2024-01-15T16:40:00Z' }
    ]

    const getHoursBetween = (start: string, end: string) => {
      const startDate = new Date(start)
      const endDate = new Date(end)
      return (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60)
    }

    const getMinutesBetween = (start: string, end: string) => {
      const startDate = new Date(start)
      const endDate = new Date(end)
      return (endDate.getTime() - startDate.getTime()) / (1000 * 60)
    }

    const fulfillmentTimes = mockTickets.map(ticket => getHoursBetween(ticket.createdAt, ticket.resolvedAt))
    const responseTimes = mockTickets.map(ticket => getMinutesBetween(ticket.createdAt, ticket.firstResponseAt))

    const averageFulfillmentHours = fulfillmentTimes.reduce((sum, hours) => sum + hours, 0) / fulfillmentTimes.length
    const fulfillmentCompliance = (fulfillmentTimes.filter(hours => hours <= slaTargets.fulfillmentTimeHours).length / fulfillmentTimes.length) * 100

    const averageResponseMinutes = responseTimes.reduce((sum, minutes) => sum + minutes, 0) / responseTimes.length
    const responseCompliance = (responseTimes.filter(minutes => minutes <= slaTargets.firstResponseMinutes).length / responseTimes.length) * 100

    const resolutionTimes = mockTickets.map(ticket => getHoursBetween(ticket.firstResponseAt, ticket.resolvedAt))
    const averageResolutionHours = resolutionTimes.reduce((sum, hours) => sum + hours, 0) / resolutionTimes.length
    const resolutionCompliance = (resolutionTimes.filter(hours => hours <= slaTargets.ticketResolutionHours - slaTargets.fulfillmentTimeHours / 2).length / resolutionTimes.length) * 100

    return {
      averageFulfillmentHours,
      fulfillmentCompliance,
      averageResponseMinutes,
      responseCompliance,
      averageResolutionHours,
      resolutionCompliance,
      recentTickets: mockTickets.slice(0, 3)
    }
  }, [slaTargets])

  const upcomingInventoryRisks = useMemo(() => {
    const categories = Array.isArray(data.inventoryStatus) ? data.inventoryStatus : []

    const riskItems = categories
      .map(category => {
        const inStock = Number(category?.inStock ?? 0)
        const lowStock = Number(category?.lowStock ?? 0)
        const outOfStock = Number(category?.outOfStock ?? 0)
        const total = inStock + lowStock + outOfStock
        const depletionRate = total ? ((lowStock + outOfStock) / total) * 100 : 0

        return {
          category: category?.category ?? 'Unknown',
          inStock,
          lowStock,
          outOfStock,
          total,
          depletionRate,
          status: depletionRate >= 40 ? 'critical' : depletionRate >= 20 ? 'warning' : 'healthy'
        }
      })
      .filter(item => item.total > 0)
      .sort((a, b) => b.depletionRate - a.depletionRate)

    return {
      riskItems,
      topRisks: riskItems.slice(0, 3)
    }
  }, [data.inventoryStatus])

  const actionCenterItems = useMemo(() => {
    const items: {
      key: string
      title: string
      description: string
      type: 'inventory' | 'sla' | 'operations' | 'forecast'
      priority: 'high' | 'medium' | 'low'
      cta: string
    }[] = []

    upcomingInventoryRisks.topRisks.forEach(risk => {
      items.push({
        key: `inventory-${risk.category}`,
        title: `Replenish ${risk.category}`,
        description: `${risk.depletionRate.toFixed(1)}% depletion projected. Reorder ~${Math.max(0, Math.round(risk.total * 0.3))} units to ensure coverage.`,
        type: 'inventory',
        priority: risk.depletionRate >= 40 ? 'high' : 'medium',
        cta: 'Plan Purchase Order'
      })
    })

    if (operationsScore.grade === 'Needs Attention') {
      items.push({
        key: 'operations-health',
        title: 'Stabilize operations health',
        description: `Operations score at ${operationsScore.score}. ${operationsScore.breakdown.find(item => item.status === 'critical')?.label ?? 'Review KPI breakdown'} requires attention.`,
        type: 'operations',
        priority: 'high',
        cta: 'View Operations Report'
      })
    }

    if (slaMetrics.responseCompliance < 85) {
      items.push({
        key: 'sla-response',
        title: 'Improve first response SLA',
        description: `Response compliance is ${slaMetrics.responseCompliance.toFixed(1)}%. Investigate helpdesk backlog.`,
        type: 'sla',
        priority: 'medium',
        cta: 'Open Support Dashboard'
      })
    }

    const upcomingForecast = revenueForecast.find(point => point.actual == null)
    if (upcomingForecast) {
      items.push({
        key: `forecast-${upcomingForecast.period}`,
        title: `Prepare for ${upcomingForecast.period}`,
        description: `Projected sales ${formatCurrency(upcomingForecast.forecast)}. Confirm marketing and supply readiness.`,
        type: 'forecast',
        priority: 'medium',
        cta: 'Review Forecast Plan'
      })
    }

    return items
      .slice(0, 5)
  }, [formatCurrency, operationsScore, revenueForecast, slaMetrics.responseCompliance, upcomingInventoryRisks.topRisks])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    const storedTarget = window.localStorage.getItem('magflow_dashboard_sales_target')
    if (storedTarget) {
      const parsed = Number(storedTarget)
      if (Number.isFinite(parsed) && parsed > 0) {
        setSalesTarget(parsed)
        setEditingTarget(parsed)
      }
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    window.localStorage.setItem('magflow_dashboard_sales_target', salesTarget.toString())
  }, [salesTarget])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)

      // Fetch dashboard data from API
      const response = await api.get('/admin/dashboard')
      setData(mergeDashboardData(response.data?.data))
      setLastRefreshTime(new Date())

      notificationApi.success({
        message: 'Dashboard Updated',
        description: 'Latest data loaded successfully',
      })
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      notificationApi.error({
        message: 'Dashboard Error',
        description: 'Failed to load dashboard data',
      })

      // Use enhanced mock data for development
      setData(mergeDashboardData({
        totalSales: 45670.89,
        totalOrders: 234,
        totalCustomers: 89,
        emagProducts: 1275,
        inventoryValue: 123400.50,
        syncStatus: 'success',
        salesGrowth: 12.5,
        ordersGrowth: 8.3,
        customersGrowth: 15.2,
        emagGrowth: 23.1,
        systemHealth: {
          database: 'healthy',
          api: 'healthy',
          emag: 'healthy'
        },
        realtimeMetrics: {
          activeUsers: 12,
          pendingOrders: 8,
          lowStockItems: 3,
          syncProgress: 85
        },
        recentOrders: [
          { id: 1, customer: 'John Doe', amount: 299.99, status: 'completed', date: '2024-01-15', priority: 'high' },
          { id: 2, customer: 'Jane Smith', amount: 149.50, status: 'processing', date: '2024-01-15', priority: 'medium' },
          { id: 3, customer: 'Bob Johnson', amount: 79.99, status: 'shipped', date: '2024-01-14', priority: 'low' },
          { id: 4, customer: 'Alice Brown', amount: 459.99, status: 'pending', date: '2024-01-15', priority: 'high' },
          { id: 5, customer: 'Charlie Wilson', amount: 199.99, status: 'completed', date: '2024-01-14', priority: 'medium' },
        ],
        salesData: [
          { name: 'Ian', sales: 4000, orders: 24, profit: 1200, growth: 5.2 },
          { name: 'Feb', sales: 3000, orders: 18, profit: 900, growth: -2.1 },
          { name: 'Mar', sales: 2000, orders: 12, profit: 600, growth: -8.5 },
          { name: 'Apr', sales: 2780, orders: 15, profit: 834, growth: 12.3 },
          { name: 'Mai', sales: 1890, orders: 11, profit: 567, growth: -15.2 },
          { name: 'Iun', sales: 2390, orders: 16, profit: 717, growth: 18.7 },
          { name: 'Iul', sales: 3200, orders: 22, profit: 960, growth: 25.1 },
        ],
        salesDataByRange: {
          '7d': [
            { name: 'Day 1', sales: 5200, orders: 28, profit: 1430, growth: 4.8 },
            { name: 'Day 2', sales: 4980, orders: 25, profit: 1350, growth: 3.1 },
            { name: 'Day 3', sales: 4670, orders: 24, profit: 1260, growth: 2.4 },
            { name: 'Day 4', sales: 4890, orders: 27, profit: 1320, growth: 3.9 },
            { name: 'Day 5', sales: 5100, orders: 29, profit: 1390, growth: 5.2 },
            { name: 'Day 6', sales: 5300, orders: 30, profit: 1475, growth: 6.4 },
            { name: 'Day 7', sales: 5480, orders: 32, profit: 1540, growth: 7.1 }
          ],
          '30d': [
            { name: 'Week 1', sales: 18900, orders: 112, profit: 4800, growth: 8.6 },
            { name: 'Week 2', sales: 17250, orders: 98, profit: 4280, growth: 5.2 },
            { name: 'Week 3', sales: 19560, orders: 123, profit: 5020, growth: 9.3 },
            { name: 'Week 4', sales: 21030, orders: 135, profit: 5360, growth: 11.4 }
          ],
          '12m': [
            { name: 'Aug', sales: 256000, orders: 1340, profit: 65750, growth: 12.4 },
            { name: 'Sep', sales: 243500, orders: 1260, profit: 62980, growth: 8.2 },
            { name: 'Oct', sales: 265890, orders: 1420, profit: 67840, growth: 14.7 },
            { name: 'Nov', sales: 301230, orders: 1580, profit: 74520, growth: 18.6 },
            { name: 'Dec', sales: 328890, orders: 1690, profit: 78950, growth: 22.1 },
            { name: 'Jan', sales: 298700, orders: 1520, profit: 71230, growth: 10.8 },
            { name: 'Feb', sales: 275430, orders: 1435, profit: 68420, growth: 9.5 },
            { name: 'Mar', sales: 289870, orders: 1490, profit: 69870, growth: 11.6 },
            { name: 'Apr', sales: 305120, orders: 1560, profit: 73210, growth: 13.8 },
            { name: 'May', sales: 322560, orders: 1650, profit: 76840, growth: 16.4 },
            { name: 'Jun', sales: 334120, orders: 1725, profit: 79560, growth: 18.9 },
            { name: 'Jul', sales: 348760, orders: 1810, profit: 82640, growth: 21.5 }
          ]
        },
        topProducts: [
          { name: 'iPhone 15', value: 35, sales: 15420, stock: 45, trend: 'up' },
          { name: 'MacBook Pro', value: 25, sales: 28900, stock: 23, trend: 'up' },
          { name: 'iPad Air', value: 20, sales: 8750, stock: 67, trend: 'stable' },
          { name: 'AirPods Pro', value: 20, sales: 3240, stock: 12, trend: 'down' },
        ],
        performanceData: [
          { name: 'Response Time', value: 95, target: 98 },
          { name: 'Uptime', value: 99.9, target: 99.5 },
          { name: 'Error Rate', value: 0.1, target: 0.5 },
          { name: 'Throughput', value: 87, target: 85 },
        ],
        inventoryStatus: [
          { category: 'Electronics', inStock: 245, lowStock: 12, outOfStock: 3 },
          { category: 'Clothing', inStock: 189, lowStock: 8, outOfStock: 1 },
          { category: 'Books', inStock: 567, lowStock: 23, outOfStock: 5 },
          { category: 'Home & Garden', inStock: 123, lowStock: 7, outOfStock: 2 },
        ]
      }))
      setLastRefreshTime(new Date())
    } finally {
      setLoading(false)
    }
  }

  const handleSyncEmag = async () => {
    try {
      await api.post('/emag/sync')
      notificationApi.success({
        message: 'eMAG Sync Started',
        description: 'Synchronization process initiated',
      })
    } catch (error) {
      notificationApi.error({
        message: 'Sync Failed',
        description: 'Failed to start eMAG synchronization',
      })
    }
  }

  // Real-time data refresh
  const refreshRealTimeData = useCallback(async () => {
    setRealTimeLoading(true)
    try {
      // Simulate real-time data fetch
      await new Promise(resolve => setTimeout(resolve, 1000))
      setData(prev => ({
        ...prev,
        realtimeMetrics: {
          activeUsers: Math.floor(Math.random() * 20) + 5,
          pendingOrders: Math.floor(Math.random() * 15) + 3,
          lowStockItems: Math.floor(Math.random() * 8) + 1,
          syncProgress: Math.min(100, prev.realtimeMetrics.syncProgress + Math.floor(Math.random() * 10))
        }
      }))
      setLastRefreshTime(new Date())
    } finally {
      setRealTimeLoading(false)
    }
  }, [])

  // Auto-refresh real-time data every 30 seconds
  useEffect(() => {
    if (!autoRefreshEnabled) {
      return
    }

    refreshRealTimeData()
    const interval = setInterval(refreshRealTimeData, 30000)
    return () => clearInterval(interval)
  }, [autoRefreshEnabled, refreshRealTimeData])

  const lastRefreshLabel = lastRefreshTime
    ? `Updated ${formatDistanceToNow(lastRefreshTime, { addSuffix: true })}`
    : 'Awaiting first refresh'

  const orderStatusOptions = useMemo(() => {
    const statusCounts = data.recentOrders.reduce<Record<string, number>>((acc, order) => {
      const normalized = typeof order?.status === 'string' ? order.status.toLowerCase() : 'unknown'
      acc[normalized] = (acc[normalized] ?? 0) + 1
      return acc
    }, {})

    const buildLabel = (status: string, count: number) => {
      if (status === 'unknown') {
        return `Unknown (${count})`
      }
      return `${status.charAt(0).toUpperCase()}${status.slice(1)} (${count})`
    }

    const orderedStatuses = ['pending', 'processing', 'shipped', 'completed', 'cancelled']
    const options = [
      {
        label: `All (${data.recentOrders.length})`,
        value: 'all'
      }
    ]

    orderedStatuses.forEach(status => {
      if (statusCounts[status]) {
        options.push({ label: buildLabel(status, statusCounts[status]), value: status })
        delete statusCounts[status]
      }
    })

    Object.entries(statusCounts).forEach(([status, count]) => {
      options.push({ label: buildLabel(status, count), value: status })
    })

    return options
  }, [data.recentOrders])

  const filteredRecentOrders = useMemo(() => {
    if (orderStatusFilter === 'all') {
      return data.recentOrders
    }

    return data.recentOrders.filter(order => {
      const normalized = typeof order?.status === 'string' ? order.status.toLowerCase() : 'unknown'
      return normalized === orderStatusFilter
    })
  }, [data.recentOrders, orderStatusFilter])

  const salesChartData = useMemo(() => {
    const dataset = data.salesDataByRange[selectedSalesRange]
    return dataset && dataset.length ? dataset : data.salesData
  }, [data.salesDataByRange, data.salesData, selectedSalesRange])

  const salesTargetProgress = useMemo(() => {
    const target = salesTarget > 0 ? salesTarget : 1
    const percentRaw = (data.totalSales / target) * 100
    const percent = Math.max(0, Math.min(200, Number.isFinite(percentRaw) ? percentRaw : 0))
    const variance = data.totalSales - target
    const varianceRatio = variance / target
    let status: 'ahead' | 'ontrack' | 'behind' = 'ontrack'

    if (varianceRatio >= 0.1) {
      status = 'ahead'
    } else if (varianceRatio <= -0.1) {
      status = 'behind'
    }

    return {
      percent,
      variance,
      status
    }
  }, [data.totalSales, salesTarget])

  const openTargetModal = useCallback(() => {
    setEditingTarget(salesTarget)
    setIsTargetModalOpen(true)
  }, [salesTarget])

  const handleTargetModalClose = useCallback(() => {
    setIsTargetModalOpen(false)
  }, [])

  const handleTargetSave = useCallback(() => {
    setSalesTarget(editingTarget)
    setIsTargetModalOpen(false)
    notificationApi.success({
      message: 'Sales Target Updated',
      description: `New monthly target set to ${formatCurrency(editingTarget)}`
    })
  }, [editingTarget, formatCurrency, notificationApi])

  const averageOrderValue = useMemo(() => {
    const numericOrders = data.recentOrders.filter(order => typeof order?.amount === 'number')
    if (!numericOrders.length) {
      return 0
    }

    const totalAmount = numericOrders.reduce((sum, order) => sum + (order?.amount as number), 0)
    return totalAmount / numericOrders.length
  }, [data.recentOrders])

  const operationalInsights = useMemo<InsightItem[]>(() => {
    const insights: InsightItem[] = []

    const salesGrowth = Number.isFinite(data.salesGrowth) ? data.salesGrowth : 0
    if (salesGrowth >= 15) {
      insights.push({
        key: 'sales-growth-positive',
        title: 'Sales momentum is strong',
        description: `Sales grew by ${salesGrowth.toFixed(1)}% compared to last month. Consider scheduling a marketing push to sustain the momentum.`,
        tone: 'positive'
      })
    } else if (salesGrowth <= 0) {
      insights.push({
        key: 'sales-growth-negative',
        title: 'Sales growth is cooling down',
        description: `Sales slipped ${Math.abs(salesGrowth).toFixed(1)}% versus last month. Review conversion funnels for potential bottlenecks.`,
        tone: 'negative'
      })
    } else {
      insights.push({
        key: 'sales-growth-neutral',
        title: 'Sales growth is steady',
        description: `Sales are up ${salesGrowth.toFixed(1)}% month-over-month. Explore targeted campaigns to lift results further.`,
        tone: 'neutral'
      })
    }

    const pendingOrders = data.realtimeMetrics?.pendingOrders ?? 0
    if (pendingOrders >= 12) {
      insights.push({
        key: 'pending-orders-warning',
        title: 'Order fulfillment backlog',
        description: `${pendingOrders} orders are awaiting processing. Prioritize fulfillment to prevent SLA breaches.`,
        tone: 'warning'
      })
    } else {
      insights.push({
        key: 'pending-orders-healthy',
        title: 'Order queue is healthy',
        description: `Only ${pendingOrders} orders are waiting. Continue monitoring fulfillment speed to maintain customer satisfaction.`,
        tone: 'positive'
      })
    }

    const lowStockItems = data.realtimeMetrics?.lowStockItems ?? 0
    if (lowStockItems > 0) {
      insights.push({
        key: 'low-stock-alert',
        title: 'Inventory attention required',
        description: `${lowStockItems} products are in low stock. Reorder soon to avoid stockouts on high-demand items.`,
        tone: lowStockItems > 5 ? 'warning' : 'neutral'
      })
    }

    const topProduct = data.topProducts?.reduce((best, product) => {
      if (!product) {
        return best
      }
      if (!best) {
        return product
      }
      return (product.sales ?? product.value ?? 0) > (best.sales ?? best.value ?? 0) ? product : best
    }, undefined as any)

    if (topProduct?.name) {
      const topProductSales = topProduct.sales ?? topProduct.value ?? 0
      insights.push({
        key: 'top-product-highlight',
        title: `${topProduct.name} leads product performance`,
        description: `${topProduct.name} generated ${topProductSales.toLocaleString()} RON in recent sales. Promote complementary products to boost average basket size.`,
        tone: 'positive'
      })
    }

    if (averageOrderValue > 0) {
      insights.push({
        key: 'aov-trend',
        title: 'Average order value update',
        description: `Average order value is ${averageOrderValue.toFixed(2)} RON. Experiment with bundles or upsells to push this metric higher.`,
        tone: 'neutral'
      })
    }

    return insights
  }, [averageOrderValue, data.realtimeMetrics, data.salesGrowth, data.topProducts])

  const getInsightToneMeta = useCallback((tone: InsightTone) => {
    switch (tone) {
      case 'positive':
        return {
          icon: <RiseOutlined style={{ color: '#52c41a', fontSize: 18 }} />,
          tagColor: 'green',
          tagLabel: 'Opportunity'
        }
      case 'warning':
        return {
          icon: <AlertOutlined style={{ color: '#faad14', fontSize: 18 }} />,
          tagColor: 'orange',
          tagLabel: 'Action Needed'
        }
      case 'negative':
        return {
          icon: <FallOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />,
          tagColor: 'red',
          tagLabel: 'At Risk'
        }
      default:
        return {
          icon: <BulbOutlined style={{ color: '#1890ff', fontSize: 18 }} />,
          tagColor: 'blue',
          tagLabel: 'Insight'
        }
    }
  }, [])

  const inventoryRiskItems = useMemo<InventoryRiskItem[]>(() => {
    return (data.inventoryStatus ?? [])
      .map((status, index) => {
        const lowStock = Number(status?.lowStock ?? 0)
        const outOfStock = Number(status?.outOfStock ?? 0)
        const inStock = Number(status?.inStock ?? 0)
        const total = lowStock + outOfStock + inStock

        if (total <= 0) {
          return null
        }

        const riskPercent = total ? ((lowStock + outOfStock) / total) * 100 : 0
        let severity: InventoryRiskItem['severity'] = 'low'

        if (riskPercent >= 40 || outOfStock >= 5) {
          severity = 'high'
        } else if (riskPercent >= 20 || outOfStock > 0) {
          severity = 'medium'
        }

        return {
          key: status?.category ?? `category-${index}`,
          category: status?.category ?? 'Unknown Category',
          lowStock,
          outOfStock,
          riskPercent,
          total,
          severity
        }
      })
      .filter((item): item is InventoryRiskItem => item !== null)
      .sort((a, b) => b.riskPercent - a.riskPercent)
  }, [data.inventoryStatus])

  const getInventorySeverityMeta = useCallback((severity: InventoryRiskItem['severity']) => {
    switch (severity) {
      case 'high':
        return {
          color: '#ff4d4f',
          tagColor: 'red',
          label: 'Critical',
          icon: <AlertOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />
        }
      case 'medium':
        return {
          color: '#faad14',
          tagColor: 'orange',
          label: 'Monitor',
          icon: <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 18 }} />
        }
      default:
        return {
          color: '#52c41a',
          tagColor: 'green',
          label: 'Stable',
          icon: <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
        }
    }
  }, [])

  const exportOrdersToCsv = (orders: DashboardData['recentOrders']) => {
    const headers = ['Order ID', 'Customer', 'Amount (RON)', 'Status', 'Priority', 'Date']
    const rows = orders.map(order => [
      order?.id ? `#${order.id.toString().padStart(6, '0')}` : 'N/A',
      order?.customer ?? 'N/A',
      typeof order?.amount === 'number' ? order.amount.toFixed(2) : order?.amount ?? 'N/A',
      order?.status ? order.status.toString() : 'N/A',
      order?.priority ? order.priority.toString() : 'N/A',
      order?.date ?? 'N/A'
    ])

    const csvContent = [headers, ...rows]
      .map(row => row
        .map(field => {
          if (field == null) {
            return ''
          }
          const fieldStr = field.toString().replace(/"/g, '""')
          return fieldStr.includes(',') || fieldStr.includes('\n') ? `"${fieldStr}"` : fieldStr
        })
        .join(','))
      .join('\n')

    return csvContent
  }

  const handleExportRecentOrders = () => {
    if (!data.recentOrders.length) {
      notificationApi.info({
        message: 'No Orders to Export',
        description: 'There are no recent orders available for export right now.'
      })
      return
    }

    const csv = exportOrdersToCsv(data.recentOrders)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().replace(/[:]/g, '-').split('.')[0]

    link.href = url
    link.setAttribute('download', `magflow_recent_orders_${timestamp}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    notificationApi.success({
      message: 'Export Started',
      description: 'Recent orders are being downloaded as a CSV file.'
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
      case 'error': return <ClockCircleOutlined />
      default: return <ClockCircleOutlined />
    }
  }

  return (
    <div className="dashboard">
      {contextHolder}
      <Spin spinning={loading}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <Title level={2} style={{ margin: 0 }}>Dashboard</Title>
              <p style={{ color: '#666', margin: 0 }}>Welcome to MagFlow ERP Admin Dashboard</p>
            </div>
            <Space>
              <Tag icon={<ClockCircleOutlined />} color="default">
                {lastRefreshLabel}
              </Tag>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={refreshRealTimeData}
                loading={realTimeLoading}
              >
                Refresh
              </Button>
              <Button type="primary" icon={<EyeOutlined />}>
                View Reports
              </Button>
            </Space>
          </div>

          {/* System Health Status */}
          <Alert
            message="System Status"
            description={
              <Space size="large">
                <Space>
                  {getHealthIcon(data.systemHealth.database)}
                  <span style={{ color: getHealthColor(data.systemHealth.database) }}>
                    Database: {data.systemHealth.database}
                  </span>
                </Space>
                <Space>
                  {getHealthIcon(data.systemHealth.api)}
                  <span style={{ color: getHealthColor(data.systemHealth.api) }}>
                    API: {data.systemHealth.api}
                  </span>
                </Space>
                <Space>
                  {getHealthIcon(data.systemHealth.emag)}
                  <span style={{ color: getHealthColor(data.systemHealth.emag) }}>
                    eMAG: {data.systemHealth.emag}
                  </span>
                </Space>
              </Space>
            }
            type="success"
            showIcon
            style={{ marginBottom: 24 }}
          />
        </div>

        {/* Real-time Metrics */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Active Users"
                value={data.realtimeMetrics.activeUsers}
                prefix={<FireOutlined style={{ color: '#ff4d4f' }} />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Pending Orders"
                value={data.realtimeMetrics.pendingOrders}
                prefix={<ClockCircleOutlined style={{ color: '#faad14' }} />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Low Stock Items"
                value={data.realtimeMetrics.lowStockItems}
                prefix={<ExclamationCircleOutlined style={{ color: '#ff7a45' }} />}
                valueStyle={{ color: '#ff7a45' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <div style={{ marginBottom: 8, color: '#666', fontSize: '14px' }}>Sync Progress</div>
                <Progress
                  type="circle"
                  percent={data.realtimeMetrics.syncProgress}
                  size={60}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Avg Order Value"
                value={averageOrderValue}
                precision={2}
                prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
                suffix="RON"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24}>
            <Card
              title="Operations Health Score"
              extra={(
                <Tag color={operationsScore.color} icon={
                  operationsScore.grade === 'Excellent'
                    ? <SafetyOutlined />
                    : operationsScore.grade === 'Good'
                      ? <WarningOutlined />
                      : <CloseCircleOutlined />
                }>
                  {operationsScore.grade}
                </Tag>
              )}
            >
              <Row gutter={[16, 16]} align="middle">
                <Col xs={24} md={6}>
                  <Progress
                    type="dashboard"
                    percent={operationsScore.score}
                    strokeColor={operationsScore.color === 'green' ? '#52c41a' : operationsScore.color === 'blue' ? '#1890ff' : '#ff4d4f'}
                    size={180}
                  />
                </Col>
                <Col xs={24} md={18}>
                  <List
                    size="small"
                    dataSource={operationsScore.breakdown}
                    renderItem={item => (
                      <List.Item key={item.key} style={{ paddingLeft: 0, paddingRight: 0 }}>
                        <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Space>
                            <Tag color={
                              item.status === 'positive'
                                ? 'green'
                                : item.status === 'warning'
                                  ? 'orange'
                                  : 'red'
                            }>
                              {item.label}
                            </Tag>
                            <span style={{ color: '#595959' }}>{item.description}</span>
                          </Space>
                        </Space>
                      </List.Item>
                    )}
                  />
                </Col>
              </Row>
            </Card>
          </Col>
          <Col xs={24}>
            <Card
              title="Predictive Replenishment Planner"
              extra={<Tag color={upcomingInventoryRisks.topRisks.length ? 'orange' : 'green'}>{upcomingInventoryRisks.topRisks.length ? `${upcomingInventoryRisks.topRisks.length} categories at risk` : 'All categories stable'}</Tag>}
            >
              {upcomingInventoryRisks.topRisks.length ? (
                <List
                  itemLayout="vertical"
                  dataSource={upcomingInventoryRisks.topRisks}
                  renderItem={item => (
                    <List.Item key={item.category}
                      actions={[
                        <Button key="replenish" type="primary" size="small">Create Purchase Order</Button>,
                        <Button key="simulate" size="small" type="link">Simulate Impact</Button>
                      ]}
                    >
                      <List.Item.Meta
                        title={item.category}
                        description={`${item.depletionRate.toFixed(1)}% depletion rate • ${item.lowStock} low • ${item.outOfStock} OOS`}
                      />
                      <Row gutter={[16, 16]}>
                        <Col xs={24} md={8}>
                          <Statistic
                            title="Reorder Suggestion"
                            value={Math.max(0, Math.round(item.total * 0.3))}
                            suffix="units"
                          />
                        </Col>
                        <Col xs={24} md={8}>
                          <Statistic
                            title="Projected Coverage"
                            value={Math.max(3, Math.round(14 - (item.depletionRate / 10)))}
                            suffix="days"
                            valueStyle={{ color: item.depletionRate >= 40 ? '#ff4d4f' : '#faad14' }}
                          />
                        </Col>
                        <Col xs={24} md={8}>
                          <Statistic
                            title="Priority"
                            value={item.depletionRate >= 40 ? 'Critical' : 'Warning'}
                            valueStyle={{ color: item.depletionRate >= 40 ? '#ff4d4f' : '#faad14' }}
                          />
                        </Col>
                      </Row>
                      <Divider />
                    </List.Item>
                  )}
                />
              ) : (
                <Alert
                  type="success"
                  message="Inventory levels stable"
                  description="No categories are currently trending toward stock-out."
                  showIcon
                />
              )}
            </Card>
          </Col>
          <Col xs={24}>
            <Card
              title="Strategic Action Center"
              extra={<Tag color={actionCenterItems.length ? 'processing' : 'green'}>{actionCenterItems.length ? `${actionCenterItems.length} action items` : 'All clear'}</Tag>}
            >
              {actionCenterItems.length ? (
                <List
                  itemLayout="horizontal"
                  dataSource={actionCenterItems}
                  renderItem={item => (
                    <List.Item
                      key={item.key}
                      actions={[
                        <Button key="action" type={item.priority === 'high' ? 'primary' : 'default'} size="small">
                          {item.cta}
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'blue'}>{item.type.toUpperCase()}</Tag>}
                        title={item.title}
                        description={item.description}
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Alert type="success" message="No pending strategic actions" showIcon />
              )}
            </Card>
          </Col>
        </Row>

        {/* Enhanced Key Metrics Cards */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card className="dashboard-card" hoverable>
              <Statistic
                title="Total Sales"
                value={data.totalSales}
                prefix={<DollarOutlined />}
                suffix="RON"
                valueStyle={{ color: '#3f8600' }}
              />
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center' }}>
                {data.salesGrowth > 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 4 }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 4 }} />
                )}
                <span style={{ 
                  color: data.salesGrowth > 0 ? '#3f8600' : '#cf1322',
                  fontSize: '12px'
                }}>
                  {data.salesGrowth > 0 ? '+' : ''}{data.salesGrowth}% vs last month
                </span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="dashboard-card" hoverable>
              <Statistic
                title="Total Orders"
                value={data.totalOrders}
                prefix={<ShoppingCartOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center' }}>
                {data.ordersGrowth > 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 4 }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 4 }} />
                )}
                <span style={{ 
                  color: data.ordersGrowth > 0 ? '#3f8600' : '#cf1322',
                  fontSize: '12px'
                }}>
                  {data.ordersGrowth > 0 ? '+' : ''}{data.ordersGrowth}% vs last month
                </span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="dashboard-card" hoverable>
              <Statistic
                title="Customers"
                value={data.totalCustomers}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center' }}>
                {data.customersGrowth > 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 4 }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 4 }} />
                )}
                <span style={{ 
                  color: data.customersGrowth > 0 ? '#3f8600' : '#cf1322',
                  fontSize: '12px'
                }}>
                  {data.customersGrowth > 0 ? '+' : ''}{data.customersGrowth}% vs last month
                </span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="dashboard-card" hoverable>
              <Statistic
                title="eMAG Products"
                value={data.emagProducts}
                prefix={<LinkOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center' }}>
                {data.emagGrowth > 0 ? (
                  <RiseOutlined style={{ color: '#3f8600', marginRight: 4 }} />
                ) : (
                  <FallOutlined style={{ color: '#cf1322', marginRight: 4 }} />
                )}
                <span style={{ 
                  color: data.emagGrowth > 0 ? '#3f8600' : '#cf1322',
                  fontSize: '12px'
                }}>
                  {data.emagGrowth > 0 ? '+' : ''}{data.emagGrowth}% vs last month
                </span>
              </div>
            </Card>
          </Col>
        </Row>

        {/* Sales Target Tracker */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} lg={12}>
            <Card
              title="Sales Target Tracker"
              extra={(() => {
                const statusMeta = salesTargetProgress.status === 'ahead'
                  ? { color: 'green', text: 'Ahead of target' }
                  : salesTargetProgress.status === 'behind'
                    ? { color: 'red', text: 'Behind target' }
                    : { color: 'blue', text: 'On track' }

                return (
                  <Space>
                    <Tag color={statusMeta.color}>{statusMeta.text}</Tag>
                    <Button size="small" icon={<AimOutlined />} onClick={openTargetModal}>
                      Adjust Target
                    </Button>
                  </Space>
                )
              })()}
            >
              <Row gutter={[16, 16]} align="middle">
                <Col xs={24} md={12}>
                  <Progress
                    type="dashboard"
                    percent={Math.round(Math.min(200, Math.max(0, salesTargetProgress.percent)))}
                    strokeColor={
                      salesTargetProgress.status === 'ahead'
                        ? '#52c41a'
                        : salesTargetProgress.status === 'behind'
                          ? '#ff4d4f'
                          : '#1890ff'
                    }
                  />
                  <div style={{ textAlign: 'center', marginTop: 12 }}>
                    <Text type="secondary">Progress against monthly goal</Text>
                  </div>
                </Col>
                <Col xs={24} md={12}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Statistic
                      title="Current Sales"
                      value={data.totalSales}
                      precision={0}
                      suffix="RON"
                      valueStyle={{ color: '#1890ff' }}
                    />
                    <Statistic
                      title="Sales Target"
                      value={salesTarget}
                      precision={0}
                      suffix="RON"
                      valueStyle={{ color: '#722ed1' }}
                    />
                    <Statistic
                      title={salesTargetProgress.variance >= 0 ? 'Ahead of target by' : 'Remaining to target'}
                      value={Math.abs(Math.round(salesTargetProgress.variance))}
                      precision={0}
                      suffix="RON"
                      valueStyle={{ color: salesTargetProgress.variance >= 0 ? '#52c41a' : '#ff4d4f' }}
                    />
                  </Space>
                </Col>
              </Row>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              title="Revenue Forecast"
              extra={(
                <Space>
                  {upcomingForecast ? (
                    <Tag color={upcomingForecast.growth >= 5 ? 'green' : upcomingForecast.growth >= 0 ? 'blue' : 'red'}>
                      Next: {formatCurrency(upcomingForecast.nextPoint.forecast)} ({upcomingForecast.growth >= 0 ? '+' : ''}{upcomingForecast.growth.toFixed(1)}%)
                    </Tag>
                  ) : (
                    <Tag color="default">Forecast up to date</Tag>
                  )}
                  <Button size="small" type="link" onClick={toggleForecastDetails}>
                    {showForecastDetails ? 'Hide Detail' : 'View Detail'}
                  </Button>
                </Space>
              )}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24}>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={revenueForecast}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <Tooltip formatter={(value) => `${Number(value).toLocaleString('ro-RO')} RON`} />
                      <Legend />
                      <Line type="monotone" dataKey="actual" stroke="#1890ff" name="Actual" dot />
                      <Line type="monotone" dataKey="forecast" stroke="#52c41a" name="Forecast" strokeDasharray="5 5" />
                    </LineChart>
                  </ResponsiveContainer>
                </Col>
              </Row>
              <Divider style={{ margin: '16px 0' }} />
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Statistic
                    title="Average Forecast"
                    value={Math.round(forecastSummary.average)}
                    prefix={<DollarOutlined />}
                    suffix="RON"
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Col>
                <Col xs={24} md={12}>
                  <Statistic
                    title="Volatility"
                    value={Math.round(forecastSummary.deviation)}
                    prefix={<ThunderboltOutlined />}
                    suffix="RON"
                    valueStyle={{ color: '#faad14' }}
                  />
                </Col>
              </Row>
              {showForecastDetails && (
                <div style={{ marginTop: 16 }}>
                  <Divider orientation="left" plain>Projection Detail</Divider>
                  <Table
                    size="small"
                    pagination={false}
                    rowKey={record => record.period}
                    dataSource={revenueForecast}
                    columns={[
                      {
                        title: 'Period',
                        dataIndex: 'period'
                      },
                      {
                        title: 'Actual',
                        dataIndex: 'actual',
                        render: (value) => value != null ? formatCurrency(value) : '–'
                      },
                      {
                        title: 'Forecast',
                        dataIndex: 'forecast',
                        render: value => formatCurrency(value)
                      }
                    ]}
                  />
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24}>
            <Card
              title="SLA Compliance"
              extra={<Tag color={slaMetrics.fulfillmentCompliance >= 90 ? 'green' : slaMetrics.fulfillmentCompliance >= 75 ? 'blue' : 'red'}>{slaMetrics.fulfillmentCompliance.toFixed(1)}% Fulfillment</Tag>}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                  <Statistic
                    title="Avg Fulfillment"
                    value={slaMetrics.averageFulfillmentHours}
                    precision={1}
                    suffix="h"
                    valueStyle={{ color: slaMetrics.fulfillmentCompliance >= 90 ? '#52c41a' : '#faad14' }}
                  />
                  <Statistic
                    title="Compliance"
                    value={slaMetrics.fulfillmentCompliance}
                    precision={1}
                    suffix="%"
                    valueStyle={{ color: slaMetrics.fulfillmentCompliance >= 90 ? '#52c41a' : slaMetrics.fulfillmentCompliance >= 75 ? '#1890ff' : '#ff4d4f' }}
                  />
                </Col>
                <Col xs={24} md={8}>
                  <Statistic
                    title="Avg First Response"
                    value={slaMetrics.averageResponseMinutes}
                    precision={0}
                    suffix="min"
                    valueStyle={{ color: slaMetrics.responseCompliance >= 90 ? '#52c41a' : '#faad14' }}
                  />
                  <Statistic
                    title="Response Compliance"
                    value={slaMetrics.responseCompliance}
                    precision={1}
                    suffix="%"
                    valueStyle={{ color: slaMetrics.responseCompliance >= 90 ? '#52c41a' : slaMetrics.responseCompliance >= 75 ? '#1890ff' : '#ff4d4f' }}
                  />
                </Col>
                <Col xs={24} md={8}>
                  <Statistic
                    title="Avg Resolution"
                    value={slaMetrics.averageResolutionHours}
                    precision={1}
                    suffix="h"
                    valueStyle={{ color: slaMetrics.resolutionCompliance >= 90 ? '#52c41a' : '#faad14' }}
                  />
                  <Statistic
                    title="Resolution Compliance"
                    value={slaMetrics.resolutionCompliance}
                    precision={1}
                    suffix="%"
                    valueStyle={{ color: slaMetrics.resolutionCompliance >= 90 ? '#52c41a' : slaMetrics.resolutionCompliance >= 75 ? '#1890ff' : '#ff4d4f' }}
                  />
                </Col>
              </Row>
              <Divider style={{ margin: '16px 0' }} />
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Alert
                    type={slaMetrics.fulfillmentCompliance >= 90 ? 'success' : 'warning'}
                    showIcon
                    message="Fulfillment Insight"
                    description={`Average fulfillment time is ${slaMetrics.averageFulfillmentHours.toFixed(1)}h (target ${slaTargets.fulfillmentTimeHours}h).`}
                  />
                </Col>
                <Col xs={24} md={12}>
                  <Alert
                    type={slaMetrics.responseCompliance >= 90 ? 'success' : 'warning'}
                    showIcon
                    message="Response Insight"
                    description={`Avg first response is ${slaMetrics.averageResponseMinutes.toFixed(0)} minutes (target ${slaTargets.firstResponseMinutes} minutes).`}
                  />
                </Col>
              </Row>
              <Divider orientation="left" plain style={{ marginTop: 16 }}>Recent Tickets</Divider>
              <Table
                size="small"
                pagination={false}
                rowKey="id"
                dataSource={slaMetrics.recentTickets}
                columns={[
                  {
                    title: 'Ticket',
                    dataIndex: 'id'
                  },
                  {
                    title: 'Created',
                    dataIndex: 'createdAt'
                  },
                  {
                    title: 'First Response',
                    dataIndex: 'firstResponseAt'
                  },
                  {
                    title: 'Resolved',
                    dataIndex: 'resolvedAt'
                  }
                ]}
              />
            </Card>
          </Col>
        </Row>

        {/* Operational Insights & Inventory Risk */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} lg={12}>
            <Card
              title="Operational Insights"
              extra={<Tag color="blue" icon={<InfoCircleOutlined />}>Updated in real-time</Tag>}
            >
              <List
                dataSource={operationalInsights}
                split
                locale={{ emptyText: 'No insights available yet. Data will populate as soon as events stream in.' }}
                renderItem={item => {
                  const meta = getInsightToneMeta(item.tone)
                  return (
                    <List.Item key={item.key} style={{ paddingLeft: 0, paddingRight: 0 }}>
                      <Space align="start" style={{ width: '100%' }}>
                        <div style={{ paddingTop: 2 }}>{meta.icon}</div>
                        <div style={{ flex: 1 }}>
                          <Space size="small" style={{ marginBottom: 4 }}>
                            <strong style={{ fontSize: 14 }}>{item.title}</strong>
                            <Tag color={meta.tagColor}>{meta.tagLabel}</Tag>
                          </Space>
                          <div style={{ color: '#595959', fontSize: 13 }}>{item.description}</div>
                        </div>
                      </Space>
                    </List.Item>
                  )
                }}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              title="Inventory Risk Monitor"
              extra={(() => {
                if (!inventoryRiskItems.length) {
                  return <Tag color="green" icon={<CheckCircleOutlined />}>All categories stable</Tag>
                }
                const highestRisk = inventoryRiskItems[0]
                const meta = getInventorySeverityMeta(highestRisk.severity)
                return (
                  <Tag color={meta.tagColor} icon={meta.icon}>
                    {meta.label}: {highestRisk.riskPercent.toFixed(1)}%
                  </Tag>
                )
              })()}
            >
              <List
                dataSource={inventoryRiskItems}
                split
                locale={{ emptyText: 'Inventory looks healthy. No risk indicators detected.' }}
                renderItem={item => {
                  const meta = getInventorySeverityMeta(item.severity)
                  return (
                    <List.Item key={item.key} style={{ paddingLeft: 0, paddingRight: 0 }}>
                      <Space align="start" style={{ width: '100%' }}>
                        <div style={{ paddingTop: 2 }}>{meta.icon}</div>
                        <div style={{ flex: 1 }}>
                          <Space align="baseline" style={{ width: '100%', justifyContent: 'space-between', marginBottom: 4 }}>
                            <strong style={{ fontSize: 14 }}>{item.category}</strong>
                            <Tag color={meta.tagColor}>{meta.label}</Tag>
                          </Space>
                          <div style={{ color: meta.color, fontWeight: 500, fontSize: 13 }}>
                            Risk score: {item.riskPercent.toFixed(1)}% ({item.lowStock} low / {item.outOfStock} out of stock)
                          </div>
                          <Progress
                            percent={Math.min(100, Math.round(item.riskPercent))}
                            size="small"
                            strokeColor={meta.color}
                            showInfo={false}
                            style={{ marginTop: 8 }}
                          />
                          <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 4 }}>
                            Total SKUs tracked: {item.total}
                          </div>
                        </div>
                      </Space>
                    </List.Item>
                  )
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* Enhanced Charts Section */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {/* Sales & Profit Chart */}
          <Col xs={24} lg={16}>
            <Card
              title="Sales & Profit Analytics"
              extra={
                <Space>
                  <Segmented
                    size="small"
                    value={selectedSalesRange}
                    onChange={value => setSelectedSalesRange(value as SalesRange)}
                    options={[
                      { label: '7 Days', value: '7d' },
                      { label: '30 Days', value: '30d' },
                      { label: '12 Months', value: '12m' }
                    ]}
                  />
                  <Button type="primary" size="small" onClick={handleSyncEmag}>
                    <SyncOutlined /> Sync eMAG
                  </Button>
                  <Button
                    size="small"
                    icon={<ThunderboltOutlined />}
                    type={autoRefreshEnabled ? 'primary' : 'default'}
                    onClick={() => setAutoRefreshEnabled(prev => !prev)}
                  >
                    {autoRefreshEnabled ? 'Auto Refresh On' : 'Auto Refresh Off'}
                  </Button>
                </Space>
              }
            >
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={salesChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip 
                    formatter={(value, name) => [
                      name === 'sales' ? `${value} RON` : `${value} RON`,
                      name === 'sales' ? 'Sales' : 'Profit'
                    ]}
                  />
                  <Area 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="sales" 
                    stroke="#1890ff" 
                    fill="#1890ff" 
                    fillOpacity={0.3} 
                  />
                  <Area 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="profit" 
                    stroke="#52c41a" 
                    fill="#52c41a" 
                    fillOpacity={0.2} 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>

          {/* Performance Metrics */}
          <Col xs={24} lg={8}>
            <Card title="System Performance" style={{ height: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {data.performanceData.map((metric, index) => (
                  <div key={index}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: '12px' }}>{metric.name}</span>
                      <span style={{ fontSize: '12px', fontWeight: 'bold' }}>
                        {metric.value}%
                      </span>
                    </div>
                    <Progress 
                      percent={metric.value} 
                      size="small"
                      strokeColor={metric.value >= metric.target ? '#52c41a' : '#faad14'}
                      showInfo={false}
                    />
                  </div>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>

        {/* Product Distribution & Inventory Status */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} lg={12}>
            <Card title="Top Products Distribution">
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
                    {data.topProducts.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="Inventory Status by Category">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.inventoryStatus}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="inStock" stackId="a" fill="#52c41a" name="In Stock" />
                  <Bar dataKey="lowStock" stackId="a" fill="#faad14" name="Low Stock" />
                  <Bar dataKey="outOfStock" stackId="a" fill="#ff4d4f" name="Out of Stock" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        {/* Enhanced Recent Orders Table */}
        <Row>
          <Col xs={24}>
            <Card 
              title="Recent Orders" 
              extra={
                <Space>
                  <Tag color="processing">{data.realtimeMetrics.pendingOrders} Pending</Tag>
                  <Segmented
                    size="small"
                    value={orderStatusFilter}
                    onChange={value => setOrderStatusFilter(value as string)}
                    options={orderStatusOptions}
                  />
                  <Button size="small" icon={<DownloadOutlined />} onClick={handleExportRecentOrders}>
                    Export CSV
                  </Button>
                  <Button size="small" type="link">View All Orders</Button>
                </Space>
              }
            >
              <Table
                rowKey="id"
                dataSource={filteredRecentOrders}
                columns={[
                  {
                    title: 'Order ID',
                    dataIndex: 'id',
                    key: 'id',
                    render: (id) => `#${id.toString().padStart(6, '0')}`,
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
                    render: (amount) => `${amount} RON`,
                    sorter: (a, b) => a.amount - b.amount,
                  },
                  {
                    title: 'Priority',
                    dataIndex: 'priority',
                    key: 'priority',
                    render: (priority) => {
                      const normalized = typeof priority === 'string' ? priority.toLowerCase() : undefined
                      const label = normalized ? normalized.toUpperCase() : 'N/A'
                      const color = normalized === 'high'
                        ? 'red'
                        : normalized === 'medium'
                          ? 'orange'
                          : normalized === 'low'
                            ? 'green'
                            : 'default'

                      return (
                        <Tag color={color}>
                          {label}
                        </Tag>
                      )
                    },
                  },
                  {
                    title: 'Status',
                    dataIndex: 'status',
                    key: 'status',
                    render: (status) => {
                      const normalized = typeof status === 'string' ? status.toLowerCase() : undefined
                      const label = normalized ? normalized.toUpperCase() : 'UNKNOWN'
                      let color: string = 'default'

                      switch (normalized) {
                        case 'completed':
                          color = 'success'
                          break
                        case 'processing':
                          color = 'processing'
                          break
                        case 'shipped':
                          color = 'blue'
                          break
                        case 'pending':
                          color = 'warning'
                          break
                        default:
                          color = 'default'
                      }

                      return (
                        <Tag color={color}>
                          {label}
                        </Tag>
                      )
                    },
                  },
                  {
                    title: 'Date',
                    dataIndex: 'date',
                    key: 'date',
                    sorter: (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
                  },
                ]}
                pagination={{ pageSize: 5, showSizeChanger: false }}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      <Modal
        title="Adjust Sales Target"
        open={isTargetModalOpen}
        onOk={handleTargetSave}
        onCancel={handleTargetModalClose}
        okText="Save Target"
        cancelText="Cancel"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Slider
            min={10000}
            max={200000}
            step={1000}
            value={Math.min(200000, Math.max(10000, editingTarget))}
            onChange={value => {
              if (typeof value === 'number') {
                setEditingTarget(value)
              }
            }}
            tooltip={{ formatter: value => `${value?.toLocaleString('ro-RO')} RON` }}
            marks={{
              10000: '10k',
              60000: '60k',
              120000: '120k',
              200000: '200k'
            }}
          />
          <InputNumber
            style={{ width: '100%' }}
            min={1000}
            max={500000}
            step={500}
            value={editingTarget}
            onChange={value => {
              if (typeof value === 'number') {
                setEditingTarget(value)
              }
            }}
            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={value => Number(value?.replace(/,/g, ''))}
            addonAfter="RON"
          />
          <Alert
            type="info"
            showIcon
            message="Tip"
            description="Adjust the slider or input to set your monthly sales target. This value is stored locally for each admin user."
          />
        </Space>
      </Modal>
    </div>
  )
}

export default Dashboard
