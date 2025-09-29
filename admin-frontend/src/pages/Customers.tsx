import { useCallback, useEffect, useMemo, useState } from 'react';
import { 
  Card, Table, Tag, Typography, Space, Button, message, Statistic, Select,
  Row, Col, Badge, Divider
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { 
  ReloadOutlined, TeamOutlined, DownloadOutlined,
  UserOutlined, ShoppingOutlined, CalendarOutlined, DollarOutlined,
  CrownOutlined, StarOutlined, HeartOutlined, DatabaseOutlined
} from '@ant-design/icons';
import api from '../services/api';

type CustomerTier = 'bronze' | 'silver' | 'gold';

type CustomerStatus = 'active' | 'inactive' | 'blocked';

interface CustomerRecord {
  id: number;
  code?: string;
  name: string;
  email?: string;
  phone?: string;
  city?: string;
  tier: CustomerTier;
  status: CustomerStatus;
  totalOrders: number;
  totalSpent: number;
  lastOrderAt: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  // eMAG specific fields
  emagCustomerId?: string;
  emagOrdersCount?: number;
  emagTotalSpent?: number;
  preferredChannel?: 'main' | 'fbe' | 'mixed';
  averageOrderValue?: number;
  lastEmagOrderAt?: string | null;
  loyaltyScore?: number;
  riskLevel?: 'low' | 'medium' | 'high';
  address?: {
    street?: string;
    city?: string;
    county?: string;
    postalCode?: string;
    country?: string;
  };
  preferences?: {
    deliveryMethod?: string;
    paymentMethod?: string;
    communicationChannel?: string;
  };
}

interface CustomerStats {
  totalActive: number;
  totalInactive: number;
  totalSpent: number;
  emagCustomers: {
    total: number;
    active: number;
    vip: number;
    newThisMonth: number;
  };
  channelDistribution: {
    main: number;
    fbe: number;
    mixed: number;
  };
  loyaltyDistribution: {
    bronze: number;
    silver: number;
    gold: number;
  };
}

const { Title, Text } = Typography;

const statusOptions: { value: 'all' | 'active' | 'inactive'; label: string }[] = [
  { value: 'all', label: 'Toți clienții' },
  { value: 'active', label: 'Clienți activi' },
  { value: 'inactive', label: 'Clienți inactivi' },
];

const defaultStats: CustomerStats = {
  totalActive: 0,
  totalInactive: 0,
  totalSpent: 0,
  emagCustomers: {
    total: 0,
    active: 0,
    vip: 0,
    newThisMonth: 0,
  },
  channelDistribution: {
    main: 0,
    fbe: 0,
    mixed: 0,
  },
  loyaltyDistribution: {
    bronze: 0,
    silver: 0,
    gold: 0,
  },
};

const tierColorMap: Record<CustomerTier, string> = {
  bronze: 'volcano',
  silver: 'geekblue',
  gold: 'gold',
};

const tierLabelMap: Record<CustomerTier, string> = {
  bronze: 'Bronze',
  silver: 'Silver',
  gold: 'Gold',
};

const statusColorMap: Record<CustomerStatus, string> = {
  active: 'success',
  inactive: 'default',
  blocked: 'error',
};

const statusLabelMap: Record<CustomerStatus, string> = {
  active: 'Activ',
  inactive: 'Inactiv',
  blocked: 'Blocat',
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

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerRecord[]>([]);
  const [stats, setStats] = useState<CustomerStats>(defaultStats);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    total: 0,
    showSizeChanger: true,
  });
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [messageApi, contextHolder] = message.useMessage();

  const fetchCustomers = useCallback(
    async (page: number, pageSize: number, showFeedback = false) => {
      setLoading(true);
      try {
        const response = await api.get('/admin/emag-customers', {
          params: {
            skip: (page - 1) * pageSize,
            limit: pageSize,
            status: statusFilter === 'all' ? undefined : statusFilter,
          },
        });

        const payload = response.data;
        if (payload?.status === 'success' && payload.data) {
          const responseData = payload.data;
          const mappedCustomers: CustomerRecord[] = Array.isArray(responseData.customers)
            ? responseData.customers.map((customer: any) => {
                const tierValue = (customer?.tier ?? 'bronze').toString().toLowerCase();
                const normalizedTier: CustomerTier = ['gold', 'silver', 'bronze'].includes(tierValue)
                  ? (tierValue as CustomerTier)
                  : 'bronze';

                const statusValue = (customer?.status ?? 'active').toString().toLowerCase();
                const normalizedStatus: CustomerStatus = ['active', 'inactive', 'blocked'].includes(statusValue)
                  ? (statusValue as CustomerStatus)
                  : 'active';

                return {
                  id: Number(customer?.id ?? 0),
                  code: customer?.code ?? undefined,
                  name: customer?.name ?? '—',
                  email: customer?.email ?? undefined,
                  phone: customer?.phone ?? undefined,
                  city: customer?.city ?? undefined,
                  tier: normalizedTier,
                  status: normalizedStatus,
                  totalOrders: Number(customer?.total_orders ?? 0),
                  totalSpent: parseNumber(customer?.total_spent ?? 0),
                  lastOrderAt: customer?.last_order_at ?? null,
                  createdAt: customer?.created_at ?? null,
                  updatedAt: customer?.updated_at ?? null,
                };
              })
            : [];

          setCustomers(mappedCustomers);

          const paginationData = responseData.pagination ?? {};
          setPagination((prev) => ({
            ...prev,
            current: page,
            pageSize,
            total: typeof paginationData.total === 'number' ? paginationData.total : prev.total,
          }));

          const summaryData = responseData.summary ?? {};
          setStats({
            totalActive: summaryData.total_active ?? summaryData.totalActive ?? 0,
            totalInactive: summaryData.total_inactive ?? summaryData.totalInactive ?? 0,
            totalSpent: parseNumber(summaryData.total_spent ?? summaryData.totalSpent ?? 0),
            emagCustomers: summaryData.emag_customers ?? {
              total: 0,
              active: 0,
              vip: 0,
              newThisMonth: 0,
            },
            channelDistribution: summaryData.channel_distribution ?? {
              main: 0,
              fbe: 0,
              mixed: 0,
            },
            loyaltyDistribution: summaryData.loyalty_distribution ?? {
              bronze: 0,
              silver: 0,
              gold: 0,
            },
          });

          if (showFeedback) {
            messageApi.success('Clienții eMAG au fost reîmprospătați.');
          }
        } else {
          throw new Error('Invalid response from eMAG customers API');
        }
      } catch (error) {
        console.error('Error fetching eMAG customers:', error);
        messageApi.error('Eroare la încărcarea clienților eMAG.');
        setCustomers([]);
        setStats(defaultStats);
        setPagination((prev) => ({ ...prev, total: 0 }));
      } finally {
        setLoading(false);
      }
    },
    [messageApi, statusFilter]
  );

  useEffect(() => {
    fetchCustomers(pagination.current ?? 1, pagination.pageSize ?? 10);
  }, [fetchCustomers, pagination.current, pagination.pageSize]);

  const handleTableChange = (tablePagination: TablePaginationConfig) => {
    const current = tablePagination.current ?? 1;
    const pageSize = tablePagination.pageSize ?? pagination.pageSize ?? 10;

    setPagination((prev) => ({
      ...prev,
      current,
      pageSize,
    }));

    fetchCustomers(current, pageSize);
  };

  const handleRefresh = () => {
    const current = pagination.current ?? 1;
    const pageSize = pagination.pageSize ?? 10;
    fetchCustomers(current, pageSize, true);
  };

  const handleStatusFilterChange = (value: 'all' | 'active' | 'inactive') => {
    setStatusFilter(value);
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const buildCsvContent = useCallback(() => {
    if (customers.length === 0) {
      return '';
    }

    const headers = [
      'ID',
      'Cod',
      'Nume',
      'Email',
      'Telefon',
      'Oraș',
      'Nivel',
      'Status',
      'Total comenzi',
      'Total cheltuit (RON)',
      'Ultima comandă',
      'Creat la',
      'Actualizat la',
    ];

    const escapeCsvValue = (value: string | number | null | undefined) => {
      if (value === undefined || value === null) {
        return '';
      }

      const stringValue = value.toString();
      if (stringValue.includes('"')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      if (/[",\n]/.test(stringValue)) {
        return `"${stringValue}"`;
      }
      return stringValue;
    };

    const rows = customers.map((customer) => [
      customer.id,
      customer.code ?? '',
      customer.name,
      customer.email ?? '',
      customer.phone ?? '',
      customer.city ?? '',
      tierLabelMap[customer.tier],
      statusLabelMap[customer.status],
      customer.totalOrders,
      customer.totalSpent.toFixed(2),
      customer.lastOrderAt ?? '',
      customer.createdAt ?? '',
      customer.updatedAt ?? '',
    ]);

    const csvLines = [headers.join(','), ...rows.map((row) => row.map(escapeCsvValue).join(','))];
    return csvLines.join('\n');
  }, [customers]);

  const handleExportCsv = useCallback(() => {
    if (customers.length === 0) {
      messageApi.warning('Nu există clienți de exportat pentru filtrul curent.');
      return;
    }

    const csvContent = buildCsvContent();
    if (!csvContent) {
      messageApi.error('Nu s-a putut genera fișierul CSV.');
      return;
    }

    try {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:]/g, '-');
      link.href = url;
      link.setAttribute('download', `magflow_customers_${timestamp}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      messageApi.success('Export CSV generat cu succes.');
    } catch (error) {
      console.error('Error exporting customers CSV:', error);
      messageApi.error('Exportul CSV a eșuat.');
    }
  }, [buildCsvContent, customers.length, messageApi]);

  const columns: ColumnsType<CustomerRecord> = useMemo(
    () => [
      {
        title: 'Client',
        dataIndex: 'name',
        key: 'name',
        render: (value, record) => (
          <Space direction="vertical" size={0}>
            <span>{value}</span>
            {record.code && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {record.code}
              </Typography.Text>
            )}
          </Space>
        ),
      },
      {
        title: 'Email',
        dataIndex: 'email',
        key: 'email',
        render: (value?: string) => value ?? '—',
      },
      {
        title: 'Telefon',
        dataIndex: 'phone',
        key: 'phone',
        render: (value?: string) => value ?? '—',
      },
      {
        title: 'Oraș',
        dataIndex: 'city',
        key: 'city',
        render: (value?: string) => value ?? '—',
      },
      {
        title: 'Nivel',
        dataIndex: 'tier',
        key: 'tier',
        render: (tier: CustomerTier) => <Tag color={tierColorMap[tier]}>{tierLabelMap[tier]}</Tag>,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (status: CustomerStatus) => <Tag color={statusColorMap[status]}>{statusLabelMap[status]}</Tag>,
      },
      {
        title: 'Comenzi',
        dataIndex: 'totalOrders',
        key: 'totalOrders',
        align: 'center',
      },
      {
        title: 'Total cheltuit',
        dataIndex: 'totalSpent',
        key: 'totalSpent',
        align: 'right',
        render: (value: number) =>
          `${value.toLocaleString('ro-RO', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })} RON`,
      },
      {
        title: 'Ultima comandă',
        dataIndex: 'lastOrderAt',
        key: 'lastOrderAt',
        render: (value: string | null) =>
          value ? new Date(value).toLocaleString('ro-RO') : 'Fără comenzi',
      },
      {
        title: 'Creat la',
        dataIndex: 'createdAt',
        key: 'createdAt',
        render: (value?: string | null) => (value ? new Date(value).toLocaleDateString('ro-RO') : '—'),
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
              Contact
            </Button>
          </Space>
        ),
      },
    ],
    []
  );

  return (
    <>
      {contextHolder}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ marginBottom: 0 }}>
              <Space>
                <TeamOutlined style={{ color: '#1890ff' }} />
                Clienți eMAG
              </Space>
            </Title>
            <Text type="secondary">
              Gestionare avansată clienți eMAG cu analiză comportamentală și segmentare
            </Text>
          </div>
          <Space>
            <Badge
              count={stats.emagCustomers.vip}
              style={{ backgroundColor: '#faad14' }}
              title="Clienți VIP"
            />
            <Button icon={<DownloadOutlined />} onClick={handleExportCsv} disabled={loading || customers.length === 0}>
              Exportă CSV
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              Reîmprospătează
            </Button>
          </Space>
        </div>

        {/* Enhanced eMAG Customer Analytics Dashboard */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Total Clienți eMAG"
                value={stats.emagCustomers.total}
                prefix={<DatabaseOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Clienți Activi"
                value={stats.emagCustomers.active}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Clienți VIP"
                value={stats.emagCustomers.vip}
                prefix={<CrownOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <Statistic
                title="Noi Luna Aceasta"
                value={stats.emagCustomers.newThisMonth}
                prefix={<CalendarOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Customer Segmentation and Channel Analysis */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card size="small" title={<><StarOutlined /> Distribuție Loialitate</>}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Bronze:</span>
                  <Badge count={stats.loyaltyDistribution.bronze} style={{ backgroundColor: '#d4380d' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Silver:</span>
                  <Badge count={stats.loyaltyDistribution.silver} style={{ backgroundColor: '#722ed1' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Gold:</span>
                  <Badge count={stats.loyaltyDistribution.gold} style={{ backgroundColor: '#faad14' }} />
                </div>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title={<><ShoppingOutlined /> Canale Preferate</>}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>eMAG MAIN:</span>
                  <Badge count={stats.channelDistribution.main} style={{ backgroundColor: '#1890ff' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>eMAG FBE:</span>
                  <Badge count={stats.channelDistribution.fbe} style={{ backgroundColor: '#52c41a' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Mixt:</span>
                  <Badge count={stats.channelDistribution.mixed} style={{ backgroundColor: '#fa8c16' }} />
                </div>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title={<><HeartOutlined /> Valoare Cumulată</>}>
              <Statistic
                value={stats.totalSpent}
                precision={2}
                suffix="RON"
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#52c41a', fontSize: '20px' }}
              />
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ fontSize: '12px', color: '#666' }}>
                Valoare medie per client: {stats.emagCustomers.total > 0 ? (stats.totalSpent / stats.emagCustomers.total).toFixed(2) : '0.00'} RON
              </div>
            </Card>
          </Col>
        </Row>

        <Card
          title="Lista Clienți eMAG"
          extra={
            <Select<'all' | 'active' | 'inactive'>
              value={statusFilter}
              onChange={handleStatusFilterChange}
              style={{ minWidth: 200 }}
              disabled={loading}
            >
              {statusOptions.map((option) => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          }
        >
          <Table<CustomerRecord>
            rowKey="id"
            columns={columns}
            dataSource={customers}
            loading={loading}
            pagination={{
              ...pagination,
              showTotal: (total, range) => `${range[0]}-${range[1]} din ${total} clienți`,
            }}
            onChange={handleTableChange}
          />
        </Card>
      </Space>
    </>
  );
}
