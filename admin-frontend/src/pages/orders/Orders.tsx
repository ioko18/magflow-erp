import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Select,
  DatePicker,
  Descriptions,
  Badge,
  Statistic,
  Row,
  Col,
  Typography,
  Segmented,
  Alert,
  Divider,
  notification,
  message,
} from 'antd';
import { 
  ReloadOutlined, UndoOutlined, ShoppingCartOutlined, DatabaseOutlined,
  SyncOutlined, CheckCircleOutlined, ClockCircleOutlined,
  DollarOutlined, CalendarOutlined, TagOutlined
} from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import api from '../../services/api';

type OrderStatus = string;

type FulfillmentChannel = 'main' | 'fbe' | 'other';

interface OrderRecord {
  id: number;
  orderNumber: string;
  customerName: string;
  customerEmail?: string | null;
  customerPhone?: string | null;
  customerCity?: string | null;
  channel: FulfillmentChannel;
  status: OrderStatus;
  totalAmount: number;
  currency: string;
  orderDate?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  itemsCount: number;
  notes?: string | null;
  // eMAG specific fields
  emagOrderId?: string;
  emagStatus?: string;
  paymentMethod?: string;
  paymentStatus?: 'paid' | 'not_paid';
  deliveryMethod?: string;
  trackingNumber?: string;
  emagSyncStatus?: 'synced' | 'pending' | 'failed' | 'never_synced';
  lastSyncAt?: string | null;
  syncError?: string | null;
  fulfillmentType?: 'FBE' | 'FBS';
  cancellationReason?: number;
  customerAddress?: {
    street?: string;
    city?: string;
    county?: string;
    postalCode?: string;
    country?: string;
  };
  orderItems?: {
    id: string;
    sku: string;
    name: string;
    quantity: number;
    price: number;
    total: number;
  }[];
}

interface OrdersSummary {
  totalValue: number;
  statusBreakdown: Record<string, number>;
  channelBreakdown: Record<string, number>;
  emagSyncStats: {
    synced: number;
    pending: number;
    failed: number;
    never_synced: number;
  };
  recentActivity: {
    newOrders24h: number;
    syncedToday: number;
    pendingSync: number;
  };
}

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;

const statusColorMap: Record<string, string> = {
  pending: 'warning',
  processing: 'processing',
  completed: 'success',
  cancelled: 'error',
  confirmed: 'blue',
  shipped: 'geekblue',
  delivered: 'green',
  returned: 'magenta',
};

const statusLabelMap: Record<string, string> = {
  pending: 'În așteptare',
  processing: 'În procesare',
  completed: 'Finalizată',
  cancelled: 'Anulată',
  confirmed: 'Confirmată',
  shipped: 'Expediată',
  delivered: 'Livrată',
  returned: 'Returnată',
};

const channelLabelMap: Record<FulfillmentChannel, string> = {
  main: 'MAIN',
  fbe: 'FBE',
  other: 'OTHER',
};

const channelColorMap: Record<FulfillmentChannel, string> = {
  main: 'blue',
  fbe: 'green',
  other: 'orange',
};

const knownStatuses = ['pending', 'processing', 'completed', 'cancelled', 'confirmed', 'shipped', 'delivered', 'returned'];

const defaultSummary: OrdersSummary = {
  totalValue: 0,
  statusBreakdown: {},
  channelBreakdown: {},
  emagSyncStats: {
    synced: 0,
    pending: 0,
    failed: 0,
    never_synced: 0,
  },
  recentActivity: {
    newOrders24h: 0,
    syncedToday: 0,
    pendingSync: 0,
  },
};

const parseNumber = (value: unknown): number => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    total: 0,
    showSizeChanger: true,
  });
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [channelFilter, setChannelFilter] = useState<FulfillmentChannel | 'all'>('all');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [summary, setSummary] = useState<OrdersSummary>(defaultSummary);
  const [messageApi, contextHolder] = message.useMessage();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInput, setSearchInput] = useState(''); // Separate state for input value

  const hasActiveFilters = useMemo(
    () =>
      statusFilter !== 'all' ||
      channelFilter !== 'all' ||
      Boolean(dateRange?.[0] || dateRange?.[1]) ||
      Boolean(searchTerm.trim()),
    [channelFilter, dateRange, searchTerm, statusFilter]
  );

  const fetchOrders = useCallback(
    async (page: number, pageSize: number, showFeedback = false) => {
      setLoading(true);
      try {
        const response = await api.get('/admin/emag-orders', {
          params: {
            skip: (page - 1) * pageSize,
            limit: pageSize,
            status: statusFilter !== 'all' ? statusFilter : undefined,
            channel: channelFilter !== 'all' ? channelFilter : undefined,
            start_date: dateRange?.[0]?.toISOString(),
            end_date: dateRange?.[1]?.toISOString(),
            search: searchTerm.trim() || undefined,  // Added search parameter
          },
        });

        const payload = response.data;
        if (payload?.status === 'success' && payload.data) {
          const responseData = payload.data;
          const mappedOrders: OrderRecord[] = Array.isArray(responseData.orders)
            ? responseData.orders.map((order: any) => {
                const channelValue = (order?.channel ?? 'main').toString().toLowerCase();
                const normalizedChannel: FulfillmentChannel = channelValue === 'fbe'
                  ? 'fbe'
                  : channelValue === 'main'
                    ? 'main'
                    : 'other';

                const statusValue = (order?.status ?? 'pending').toString().toLowerCase();

                return {
                  id: order?.id ?? order?.emag_order_id ?? 0,  // Use UUID or emag_order_id
                  orderNumber: order?.order_number ?? `EM-${order?.emag_order_id ?? 'N/A'}`,
                  customerName: order?.customer?.name ?? '—',
                  customerEmail: order?.customer?.email ?? null,
                  customerPhone: order?.customer?.phone ?? null,
                  customerCity: order?.customer?.city ?? null,
                  channel: normalizedChannel,
                  status: statusValue,
                  totalAmount: parseNumber(order?.total_amount ?? order?.line_total_sum),
                  currency: order?.currency ?? 'RON',
                  orderDate: order?.order_date ?? order?.created_at ?? null,
                  createdAt: order?.created_at ?? null,
                  updatedAt: order?.updated_at ?? null,
                  itemsCount: Number(order?.items_count ?? order?.items?.length ?? 0),
                  notes: order?.notes ?? null,
                  // eMAG specific fields
                  emagOrderId: order?.emag_order_id,
                  paymentMethod: order?.payment_method,
                  deliveryMethod: order?.delivery_mode,
                  emagSyncStatus: order?.sync_status,
                  lastSyncAt: order?.last_synced_at,
                };
              })
            : [];

          setOrders(mappedOrders);

          const paginationData = responseData.pagination ?? {};
          setPagination((prev) => ({
            ...prev,
            current: page,
            pageSize,
            total: typeof paginationData.total === 'number' ? paginationData.total : prev.total,
          }));

          const summaryData = responseData.summary ?? {};
          setSummary({
            totalValue: parseNumber(summaryData.total_value ?? summaryData.totalValue ?? 0),
            statusBreakdown: summaryData.status_breakdown ?? summaryData.statusBreakdown ?? {},
            channelBreakdown: summaryData.channel_breakdown ?? summaryData.channelBreakdown ?? {},
            emagSyncStats: summaryData.emag_sync_stats ?? {
              synced: 0,
              pending: 0,
              failed: 0,
              never_synced: 0,
            },
            recentActivity: summaryData.recent_activity ?? {
              newOrders24h: 0,
              syncedToday: 0,
              pendingSync: 0,
            },
          });

          if (showFeedback) {
            messageApi.success('Comenzile eMAG au fost reîmprospătate.');
          }
        } else {
          throw new Error('Invalid response from eMAG orders API');
        }
      } catch (error) {
        console.error('Error fetching eMAG orders:', error);
        messageApi.error('Eroare la încărcarea comenzilor eMAG.');
        setOrders([]);
        setPagination((prev) => ({ ...prev, total: 0 }));
        setSummary(defaultSummary);
      } finally {
        setLoading(false);
      }
    },
    [messageApi, statusFilter, channelFilter, dateRange, searchTerm]
  );

  useEffect(() => {
    fetchOrders(pagination.current ?? 1, pagination.pageSize ?? 10);
  }, [fetchOrders, pagination.current, pagination.pageSize]);

  const handleTableChange = (tablePagination: TablePaginationConfig) => {
    const current = tablePagination.current ?? 1;
    const pageSize = tablePagination.pageSize ?? pagination.pageSize ?? 10;

    setPagination((prev) => ({
      ...prev,
      current,
      pageSize,
    }));

    fetchOrders(current, pageSize);
  };

  const handleRefresh = () => {
    const current = pagination.current ?? 1;
    const pageSize = pagination.pageSize ?? 10;
    fetchOrders(current, pageSize, true);
  };

  const handleSyncOrders = async (syncMode: 'incremental' | 'full' = 'incremental') => {
    setLoading(true);
    try {
      const modeLabels = {
        incremental: 'Incrementală (ultimele 7 zile)',
        full: 'Completă (toate comenzile)'
      };
      
      notification.info({
        message: 'Sincronizare Pornită',
        description: `Se sincronizează comenzile din ambele conturi (MAIN + FBE). Mod: ${modeLabels[syncMode]}. Vă rugăm așteptați...`,
        duration: 5,
      });

      const response = await api.post('/emag/orders/sync', {
        account_type: 'both',
        status_filter: null, // All statuses
        max_pages: syncMode === 'incremental' ? 10 : 50,
        days_back: null,
        sync_mode: syncMode,
        start_date: null,
        end_date: null,
        auto_acknowledge: false
      });

      if (response.data.success) {
        const data = response.data.data;
        const totals = data.totals || {};
        
        notification.success({
          message: 'Sincronizare Completă!',
          description: `Sincronizare finalizată cu succes! Total: ${totals.synced || 0} comenzi (${totals.created || 0} noi, ${totals.updated || 0} actualizate)`,
          duration: 10,
        });

        // Refresh orders list
        const current = pagination.current ?? 1;
        const pageSize = pagination.pageSize ?? 10;
        fetchOrders(current, pageSize, false);
      }
    } catch (error: any) {
      notification.error({
        message: 'Eroare Sincronizare',
        description: error.response?.data?.detail || 'Nu s-a putut sincroniza comenzile',
        duration: 10,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  const handleChannelChange = (value: FulfillmentChannel | 'all') => {
    setChannelFilter(value);
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  const handleDateRangeChange = (value: [Dayjs | null, Dayjs | null] | null) => {
    setDateRange(value);
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  const handleResetFilters = () => {
    setStatusFilter('all');
    setChannelFilter('all');
    setDateRange(null);
    setSearchTerm('');
    setSearchInput('');
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    // Reset to page 1 when searching
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  const handleSearchSubmit = (value: string) => {
    setSearchTerm(value);
    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));
  };

  // Search is now handled on backend, no need for client-side filtering

  const columns: ColumnsType<OrderRecord> = useMemo(
    () => [
      {
        title: 'Număr comandă',
        dataIndex: 'orderNumber',
        key: 'orderNumber',
        render: (orderNumber: string, record: OrderRecord) => (
          <Space direction="vertical" size={0}>
            <span style={{ fontWeight: 500 }}>{orderNumber}</span>
            {record.emagOrderId && (
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                eMAG: {record.emagOrderId}
              </Typography.Text>
            )}
          </Space>
        ),
      },
      {
        title: 'Client',
        dataIndex: 'customerName',
        key: 'customerName',
      },
      {
        title: 'Canal',
        dataIndex: 'channel',
        key: 'channel',
        render: (channel: FulfillmentChannel) => (
          <Tag color={channelColorMap[channel] ?? 'default'}>
            {channelLabelMap[channel]}
          </Tag>
        ),
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (status: OrderStatus, record: OrderRecord) => (
          <Space direction="vertical" size={0}>
            <Tag color={statusColorMap[status] ?? 'default'}>
              {statusLabelMap[status] ?? status.toUpperCase()}
            </Tag>
            {record.emagSyncStatus && (
              <Tag
                color={
                  record.emagSyncStatus === 'synced'
                    ? 'success'
                    : record.emagSyncStatus === 'pending'
                    ? 'processing'
                    : record.emagSyncStatus === 'failed'
                    ? 'error'
                    : 'default'
                }
                style={{ fontSize: 10 }}
              >
                {record.emagSyncStatus === 'synced' && '✓ Synced'}
                {record.emagSyncStatus === 'pending' && '⏳ Pending'}
                {record.emagSyncStatus === 'failed' && '✗ Failed'}
                {record.emagSyncStatus === 'never_synced' && '○ Not Synced'}
              </Tag>
            )}
          </Space>
        ),
      },
      {
        title: 'Total',
        dataIndex: 'totalAmount',
        key: 'totalAmount',
        render: (value: number, record) =>
          `${value.toLocaleString('ro-RO', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })} ${record.currency ?? 'RON'}`,
        align: 'right',
      },
      {
        title: 'Produse',
        dataIndex: 'itemsCount',
        key: 'itemsCount',
        align: 'center',
      },
      {
        title: 'Creat la',
        dataIndex: 'createdAt',
        key: 'createdAt',
        render: (value?: string | null) =>
          value ? new Date(value).toLocaleString('ro-RO') : '—',
      },
      {
        title: 'Actualizat la',
        dataIndex: 'updatedAt',
        key: 'updatedAt',
        render: (value?: string | null) =>
          value ? new Date(value).toLocaleString('ro-RO') : '—',
      },
      {
        title: 'Acțiuni',
        key: 'actions',
        render: () => (
          <Space size="middle">
            <Button type="link" size="small" disabled>
              Detalii
            </Button>
            <Button type="link" size="small" disabled>
              Factură
            </Button>
          </Space>
        ),
      },
    ],
    []
  );

  const expandedRowRender = useCallback((record: OrderRecord) => {
    const formatDateTime = (value?: string | null) =>
      value ? new Date(value).toLocaleString('ro-RO') : '—';

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" title="Detalii client">
          <Descriptions.Item label="Email">
            {record.customerEmail ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Telefon">
            {record.customerPhone ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Oraș">
            {record.customerCity ?? '—'}
          </Descriptions.Item>
        </Descriptions>

        {/* eMAG Specific Details */}
        {(record.emagOrderId || record.paymentMethod || record.deliveryMethod || record.trackingNumber) && (
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" title="Detalii eMAG">
            {record.paymentMethod && (
              <Descriptions.Item label="Metodă plată">
                <Tag color="blue">{record.paymentMethod}</Tag>
                {record.paymentStatus && (
                  <Tag color={record.paymentStatus === 'paid' ? 'success' : 'warning'}>
                    {record.paymentStatus === 'paid' ? 'Plătit' : 'Neplătit'}
                  </Tag>
                )}
              </Descriptions.Item>
            )}
            {record.deliveryMethod && (
              <Descriptions.Item label="Metodă livrare">
                <Tag color="green">{record.deliveryMethod}</Tag>
              </Descriptions.Item>
            )}
            {record.trackingNumber && (
              <Descriptions.Item label="Tracking">
                <Typography.Text code copyable>{record.trackingNumber}</Typography.Text>
              </Descriptions.Item>
            )}
            {record.fulfillmentType && (
              <Descriptions.Item label="Fulfillment">
                <Tag color={record.fulfillmentType === 'FBE' ? 'purple' : 'orange'}>
                  {record.fulfillmentType}
                </Tag>
              </Descriptions.Item>
            )}
            {record.emagSyncStatus && record.lastSyncAt && (
              <Descriptions.Item label="Ultima sincronizare">
                {formatDateTime(record.lastSyncAt)}
              </Descriptions.Item>
            )}
            {record.syncError && (
              <Descriptions.Item label="Eroare sync" span={3}>
                <Alert
                  message={record.syncError}
                  type="error"
                  showIcon
                  closable
                  style={{ marginTop: 4 }}
                />
              </Descriptions.Item>
            )}
          </Descriptions>
        )}

        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" title="Metadate comandă">
          <Descriptions.Item label="Data comandă">
            {formatDateTime(record.orderDate)}
          </Descriptions.Item>
          <Descriptions.Item label="Creat la">
            {formatDateTime(record.createdAt)}
          </Descriptions.Item>
          <Descriptions.Item label="Actualizat la">
            {formatDateTime(record.updatedAt)}
          </Descriptions.Item>
          <Descriptions.Item label="Produse">
            {record.itemsCount}
          </Descriptions.Item>
          <Descriptions.Item label="Total">
            {`${record.totalAmount.toLocaleString('ro-RO', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} ${record.currency ?? 'RON'}`}
          </Descriptions.Item>
          <Descriptions.Item label="Notă">
            {record.notes?.trim() ? record.notes : '—'}
          </Descriptions.Item>
        </Descriptions>
      </Space>
    );
  }, []);

  const renderBreakdown = (
    breakdown: Record<string, number>,
    labels: Record<string, string>,
    colorMap?: Record<string, string>
  ) => {
    const entries = Object.entries(breakdown);

    if (!entries.length) {
      return <Typography.Text type="secondary">Nu există date</Typography.Text>;
    }

    return (
      <Space size={[8, 8]} wrap>
        {entries.map(([key, value]) => (
          <Tag key={key} color={colorMap?.[key as keyof typeof colorMap] ?? statusColorMap[key] ?? 'default'}>
            {(labels[key] ?? key.toUpperCase())}: {value}
          </Tag>
        ))}
      </Space>
    );
  };

  return (
    <>
      {contextHolder}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ marginBottom: 0 }}>
              <Space>
                <ShoppingCartOutlined style={{ color: '#1890ff' }} />
                Comenzi eMAG v2.0
              </Space>
            </Title>
            <Text type="secondary">
              Gestionare avansată comenzi eMAG cu sincronizare în timp real și tracking complet
            </Text>
          </div>
          <Space>
            <Badge
              status={summary.emagSyncStats.failed > 0 ? 'error' : summary.emagSyncStats.pending > 0 ? 'warning' : 'success'}
              text={`Sync Status: ${summary.emagSyncStats.synced} synced, ${summary.emagSyncStats.pending} pending`}
            />
            <Button icon={<SyncOutlined />} type="primary" onClick={() => handleSyncOrders('incremental')} loading={loading}>
              Sincronizare eMAG (Rapid)
            </Button>
            <Button icon={<SyncOutlined spin />} onClick={() => handleSyncOrders('full')} loading={loading}>
              Sincronizare Completă
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              Reîmprospătează
            </Button>
          </Space>
        </div>

        <Card
          title="Ultimele comenzi eMAG"
          extra={
            <Space size="middle" wrap>
              <Search
                allowClear
                placeholder="Caută după număr, client sau contact"
                style={{ width: 260 }}
                value={searchInput}
                onChange={(event) => handleSearchChange(event.target.value)}
                onSearch={handleSearchSubmit}
                disabled={loading && !orders.length}
                enterButton
              />
              <Select
                value={statusFilter}
                style={{ minWidth: 200 }}
                onChange={handleStatusChange}
                disabled={loading}
              >
                <Select.Option value="all">Toate statusurile</Select.Option>
                {knownStatuses.map((status) => (
                  <Select.Option key={status} value={status}>
                    {statusLabelMap[status] ?? status.toUpperCase()}
                  </Select.Option>
                ))}
              </Select>
              <Segmented
                value={channelFilter}
                onChange={(value) => handleChannelChange(value as FulfillmentChannel | 'all')}
                options={[
                  { label: 'Toate canalele', value: 'all' },
                  { label: channelLabelMap.main, value: 'main' },
                  { label: channelLabelMap.fbe, value: 'fbe' },
                  { label: channelLabelMap.other, value: 'other' },
                ]}
                disabled={loading}
              />
              <RangePicker
                allowClear
                allowEmpty={[true, true]}
                value={dateRange}
                onChange={handleDateRangeChange}
                disabled={loading}
                placeholder={["Data început", "Data sfârșit"]}
                style={{ minWidth: '250px' }}
              />
              <Button
                icon={<UndoOutlined />}
                onClick={handleResetFilters}
                disabled={!hasActiveFilters || loading}
              >
                Resetează filtrele
              </Button>
            </Space>
          }
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* Enhanced eMAG Statistics Dashboard */}
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="Valoare Totală"
                    value={summary.totalValue}
                    precision={2}
                    suffix="RON"
                    prefix={<DollarOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="Comenzi Noi (24h)"
                    value={summary.recentActivity.newOrders24h}
                    prefix={<CalendarOutlined />}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="Sincronizate Azi"
                    value={summary.recentActivity.syncedToday}
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="În Așteptare Sync"
                    value={summary.recentActivity.pendingSync}
                    prefix={<ClockCircleOutlined />}
                    valueStyle={{ color: summary.recentActivity.pendingSync > 0 ? '#faad14' : '#52c41a' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* Sync Status Overview */}
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card size="small" title={<><DatabaseOutlined /> Status Sincronizare eMAG</>}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Sincronizate:</span>
                      <Badge count={summary.emagSyncStats.synced} style={{ backgroundColor: '#52c41a' }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>În așteptare:</span>
                      <Badge count={summary.emagSyncStats.pending} style={{ backgroundColor: '#faad14' }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Eșuate:</span>
                      <Badge count={summary.emagSyncStats.failed} style={{ backgroundColor: '#ff4d4f' }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Niciodată sincronizate:</span>
                      <Badge count={summary.emagSyncStats.never_synced} style={{ backgroundColor: '#d9d9d9' }} />
                    </div>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card size="small" title={<><TagOutlined /> Distribuție Statusuri</>}>
                  <div style={{ marginTop: 8 }}>
                    {renderBreakdown(summary.statusBreakdown, statusLabelMap)}
                  </div>
                  <Divider style={{ margin: '12px 0' }} />
                  <div>
                    <Typography.Text strong>Canale de Vânzare</Typography.Text>
                    <div style={{ marginTop: 8 }}>
                      {renderBreakdown(summary.channelBreakdown, channelLabelMap, channelColorMap)}
                    </div>
                  </div>
                </Card>
              </Col>
            </Row>

            <Table<OrderRecord>
              rowKey="id"
              columns={columns}
              dataSource={orders}
              loading={loading}
              expandable={{ expandedRowRender }}
              pagination={{
                ...pagination,
                showTotal: (total, range) => `${range[0]}-${range[1]} din ${total} comenzi`,
              }}
              onChange={handleTableChange}
            />
          </Space>
        </Card>
      </Space>
    </>
  );
}
