import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, Table, Tag, Typography, Space, Button, message, Statistic, Select, DatePicker } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import api from '../services/api';

type OrderStatus = string;

type FulfillmentChannel = 'main' | 'fbe' | 'other';

interface OrderRecord {
  id: number;
  orderNumber: string;
  customerName: string;
  channel: FulfillmentChannel;
  status: OrderStatus;
  totalAmount: number;
  currency: string;
  orderDate?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  itemsCount: number;
}

interface OrdersSummary {
  totalValue: number;
  statusBreakdown: Record<string, number>;
  channelBreakdown: Record<string, number>;
}

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

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
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [summary, setSummary] = useState<OrdersSummary>(defaultSummary);
  const [messageApi, contextHolder] = message.useMessage();

  const fetchOrders = useCallback(
    async (page: number, pageSize: number, showFeedback = false) => {
      setLoading(true);
      try {
        const response = await api.get('/admin/emag-orders', {
          params: {
            skip: (page - 1) * pageSize,
            limit: pageSize,
            status: statusFilter !== 'all' ? statusFilter : undefined,
            start_date: dateRange?.[0]?.toISOString(),
            end_date: dateRange?.[1]?.toISOString(),
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
                  id: Number(order?.id ?? 0),
                  orderNumber: order?.order_number ?? `EM-${order?.id ?? 'N/A'}`,
                  customerName: order?.customer?.name ?? '—',
                  channel: normalizedChannel,
                  status: statusValue,
                  totalAmount: parseNumber(order?.total_amount ?? order?.line_total_sum),
                  currency: order?.currency ?? 'RON',
                  orderDate: order?.order_date ?? order?.created_at ?? null,
                  createdAt: order?.created_at ?? null,
                  updatedAt: order?.updated_at ?? null,
                  itemsCount: Number(order?.items_count ?? order?.items?.length ?? 0),
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
    [messageApi, statusFilter, dateRange]
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

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
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

  const columns: ColumnsType<OrderRecord> = useMemo(
    () => [
      {
        title: 'Număr comandă',
        dataIndex: 'orderNumber',
        key: 'orderNumber',
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
        render: (status: OrderStatus) => (
          <Tag color={statusColorMap[status] ?? 'default'}>
            {statusLabelMap[status] ?? status.toUpperCase()}
          </Tag>
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
              Comenzi eMAG
            </Title>
            <Text type="secondary">
              Vizualizează comenzile sincronizate din marketplace și statusul lor curent.
            </Text>
          </div>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            Reîmprospătează
          </Button>
        </div>

        <Card
          title="Ultimele comenzi eMAG"
          extra={
            <Space size="middle" wrap>
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
              <RangePicker
                allowClear
                value={dateRange ?? undefined}
                onChange={handleDateRangeChange}
                disabled={loading}
                placeholder={["Data început", "Data sfârșit"]}
              />
            </Space>
          }
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space size="large" wrap>
              <Statistic
                title="Valoare totală"
                value={summary.totalValue}
                precision={2}
                suffix="RON"
              />
              <div>
                <Typography.Text strong>Statusuri</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  {renderBreakdown(summary.statusBreakdown, statusLabelMap)}
                </div>
              </div>
              <div>
                <Typography.Text strong>Canale</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  {renderBreakdown(summary.channelBreakdown, channelLabelMap, channelColorMap)}
                </div>
              </div>
            </Space>

            <Table<OrderRecord>
              rowKey="id"
              columns={columns}
              dataSource={orders}
              loading={loading}
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
