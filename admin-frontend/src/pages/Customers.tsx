import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, Table, Tag, Typography, Space, Button, message, Statistic, Select } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, TeamOutlined, TrophyOutlined, DownloadOutlined } from '@ant-design/icons';
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
}

interface CustomerStats {
  totalActive: number;
  totalInactive: number;
  totalSpent: number;
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
              Clienți eMAG
            </Title>
            <Text type="secondary">
              Monitorizează clienții și nivelul lor de fidelitate pentru marketplace.
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExportCsv} disabled={loading || customers.length === 0}>
              Exportă CSV
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              Reîmprospătează
            </Button>
          </Space>
        </div>

        <Card
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
          <Space size="large" wrap>
            <Statistic
              title="Clienți activi"
              value={stats.totalActive}
              prefix={<TeamOutlined />}
            />
            <Statistic
              title="Clienți inactivi"
              value={stats.totalInactive}
              prefix={<TeamOutlined />}
            />
            <Statistic
              title="Valoare cumulată"
              value={stats.totalSpent}
              precision={2}
              suffix="RON"
              prefix={<TrophyOutlined />}
            />
          </Space>
        </Card>

        <Card title="Top clienți eMAG">
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
