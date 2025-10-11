/**
 * Modern Purchase Order List Component
 * Enhanced version with dashboard metrics, advanced filtering, and improved UX
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Input,
  Select,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Tag,
  Dropdown,
  message,
  Empty,
  DatePicker,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DownloadOutlined,
  ReloadOutlined,
  FilterOutlined,
  EyeOutlined,
  EditOutlined,
  SendOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  MoreOutlined,
  ShoppingCartOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  TruckOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';
import dayjs from 'dayjs';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import PurchaseOrderStatusBadge from './PurchaseOrderStatusBadge';
import type { PurchaseOrder, PurchaseOrderStatus, PurchaseOrderListParams } from '../../types/purchaseOrder';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface StatusMetrics {
  draft: number;
  sent: number;
  confirmed: number;
  partially_received: number;
  received: number;
  cancelled: number;
  total: number;
  totalValue: number;
}

export const PurchaseOrderListModern: React.FC = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // Filters
  const [filters, setFilters] = useState<PurchaseOrderListParams>({
    skip: 0,
    limit: 20,
  });

  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<PurchaseOrderStatus | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  useEffect(() => {
    loadOrders();
  }, [filters]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const response = await purchaseOrdersApi.list(filters);
      
      if (response.status === 'success' && response.data) {
        setOrders(response.data.orders);
        setPagination({
          current: Math.floor((filters.skip || 0) / (filters.limit || 20)) + 1,
          pageSize: filters.limit || 20,
          total: response.data.pagination.total,
        });
      }
    } catch (err: any) {
      message.error(err.response?.data?.message || 'Failed to load purchase orders');
      console.error('Error loading purchase orders:', err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate metrics from orders
  const metrics = useMemo<StatusMetrics>(() => {
    const stats: StatusMetrics = {
      draft: 0,
      sent: 0,
      confirmed: 0,
      partially_received: 0,
      received: 0,
      cancelled: 0,
      total: orders.length,
      totalValue: 0,
    };

    orders.forEach(order => {
      stats[order.status as keyof Omit<StatusMetrics, 'total' | 'totalValue'>]++;
      stats.totalValue += order.total_amount || 0;
    });

    return stats;
  }, [orders]);

  const handleTableChange = (newPagination: any) => {
    const newSkip = (newPagination.current - 1) * newPagination.pageSize;
    setFilters({
      ...filters,
      skip: newSkip,
      limit: newPagination.pageSize,
    });
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    setFilters({ ...filters, search: value, skip: 0 });
  };

  const handleStatusFilter = (status: PurchaseOrderStatus | undefined) => {
    setStatusFilter(status);
    setFilters({ ...filters, status, skip: 0 });
  };

  const handleDateRangeChange = (dates: any) => {
    setDateRange(dates);
    if (dates) {
      // Note: Backend API might need date_from/date_to parameters
      // For now, we'll just reset to trigger a reload
      setFilters({
        ...filters,
        skip: 0,
      });
    } else {
      setFilters({ ...filters, skip: 0 });
    }
  };

  const handleClearFilters = () => {
    setSearchText('');
    setStatusFilter(undefined);
    setDateRange(null);
    setFilters({ skip: 0, limit: 20 });
  };

  const handleExport = async () => {
    try {
      message.info('Export functionality coming soon!');
      // TODO: Implement export to Excel
    } catch (err) {
      message.error('Failed to export orders');
    }
  };

  const handleBulkAction = (action: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('Please select at least one order');
      return;
    }
    message.info(`Bulk ${action} for ${selectedRowKeys.length} orders - Coming soon!`);
    // TODO: Implement bulk actions
  };

  const getActionMenuItems = (record: PurchaseOrder): MenuProps['items'] => {
    const items: MenuProps['items'] = [
      {
        key: 'view',
        label: 'View Details',
        icon: <EyeOutlined />,
        onClick: () => navigate(`/purchase-orders/${record.id}`),
      },
    ];

    if (record.status === 'draft') {
      items.push(
        {
          key: 'edit',
          label: 'Edit',
          icon: <EditOutlined />,
          onClick: () => navigate(`/purchase-orders/${record.id}/edit`),
        },
        {
          key: 'send',
          label: 'Send to Supplier',
          icon: <SendOutlined />,
          onClick: () => message.info('Send to supplier - Coming soon!'),
        }
      );
    }

    if (record.status === 'confirmed') {
      items.push({
        key: 'receive',
        label: 'Mark as Received',
        icon: <CheckCircleOutlined />,
        onClick: () => navigate(`/purchase-orders/${record.id}/receive`),
      });
    }

    if (['draft', 'sent'].includes(record.status)) {
      items.push({
        type: 'divider',
      }, {
        key: 'cancel',
        label: 'Cancel Order',
        icon: <CloseCircleOutlined />,
        danger: true,
        onClick: () => message.info('Cancel order - Coming soon!'),
      });
    }

    return items;
  };

  const columns: ColumnsType<PurchaseOrder> = [
    {
      title: 'Order Number',
      dataIndex: 'order_number',
      key: 'order_number',
      fixed: 'left',
      width: 150,
      render: (text: string, record: PurchaseOrder) => (
        <Button
          type="link"
          onClick={() => navigate(`/purchase-orders/${record.id}`)}
          style={{ padding: 0, fontWeight: 600 }}
        >
          {text}
        </Button>
      ),
    },
    {
      title: 'Supplier',
      dataIndex: ['supplier', 'name'],
      key: 'supplier',
      width: 200,
      render: (text: string) => text || '-',
    },
    {
      title: 'Order Date',
      dataIndex: 'order_date',
      key: 'order_date',
      width: 120,
      render: (date: string) => date ? dayjs(date).format('DD/MM/YYYY') : '-',
      sorter: (a, b) => dayjs(a.order_date).unix() - dayjs(b.order_date).unix(),
    },
    {
      title: 'Expected Delivery',
      dataIndex: 'expected_delivery_date',
      key: 'expected_delivery',
      width: 140,
      render: (date: string) => {
        if (!date) return '-';
        const deliveryDate = dayjs(date);
        const isOverdue = deliveryDate.isBefore(dayjs()) && !['received', 'cancelled'].includes(orders.find(o => o.expected_delivery_date === date)?.status || '');
        return (
          <span style={{ color: isOverdue ? '#ef4444' : undefined }}>
            {deliveryDate.format('DD/MM/YYYY')}
            {isOverdue && <Tag color="red" style={{ marginLeft: 8 }}>Overdue</Tag>}
          </span>
        );
      },
    },
    {
      title: 'Total Amount',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 150,
      render: (amount: number, record: PurchaseOrder) => (
        <span style={{ fontWeight: 600 }}>
          {new Intl.NumberFormat('ro-RO', {
            style: 'currency',
            currency: record.currency || 'RON',
          }).format(amount || 0)}
        </span>
      ),
      sorter: (a, b) => (a.total_amount || 0) - (b.total_amount || 0),
    },
    {
      title: 'Currency',
      dataIndex: 'currency',
      key: 'currency',
      width: 100,
      render: (currency: string) => (
        <Tag color={currency === 'CNY' ? 'orange' : 'blue'}>{currency || 'RON'}</Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status: PurchaseOrderStatus) => <PurchaseOrderStatusBadge status={status} />,
      filters: [
        { text: 'Draft', value: 'draft' },
        { text: 'Sent', value: 'sent' },
        { text: 'Confirmed', value: 'confirmed' },
        { text: 'Partially Received', value: 'partially_received' },
        { text: 'Received', value: 'received' },
        { text: 'Cancelled', value: 'cancelled' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 100,
      render: (_, record: PurchaseOrder) => (
        <Dropdown menu={{ items: getActionMenuItems(record) }} trigger={['click']}>
          <Button icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0, marginBottom: 4 }}>Purchase Orders</h1>
          <p style={{ color: '#6b7280', margin: 0 }}>Manage and track all purchase orders</p>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadOrders}>
            Refresh
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            Export
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/purchase-orders/new')}
          >
            New Purchase Order
          </Button>
        </Space>
      </div>

      {/* Metrics Dashboard */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Orders"
              value={metrics.total}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending"
              value={metrics.draft + metrics.sent}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#f59e0b' }}
              suffix={
                <span style={{ fontSize: 14, color: '#6b7280' }}>
                  / {metrics.total}
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="In Transit"
              value={metrics.confirmed + metrics.partially_received}
              prefix={<TruckOutlined />}
              valueStyle={{ color: '#8b5cf6' }}
              suffix={
                <span style={{ fontSize: 14, color: '#6b7280' }}>
                  / {metrics.total}
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Value"
              value={metrics.totalValue}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: '#10b981' }}
              suffix="RON"
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Row gutter={16}>
            <Col xs={24} sm={12} md={8}>
              <Input
                placeholder="Search by order number or supplier..."
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => handleSearch(e.target.value)}
                allowClear
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Select
                placeholder="Filter by status"
                style={{ width: '100%' }}
                value={statusFilter}
                onChange={handleStatusFilter}
                allowClear
              >
                <Option value="draft">Draft</Option>
                <Option value="sent">Sent</Option>
                <Option value="confirmed">Confirmed</Option>
                <Option value="partially_received">Partially Received</Option>
                <Option value="received">Received</Option>
                <Option value="cancelled">Cancelled</Option>
              </Select>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <RangePicker
                style={{ width: '100%' }}
                value={dateRange}
                onChange={handleDateRangeChange}
                format="DD/MM/YYYY"
              />
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Button
                icon={<FilterOutlined />}
                onClick={handleClearFilters}
                block
              >
                Clear Filters
              </Button>
            </Col>
          </Row>

          {/* Bulk Actions */}
          {selectedRowKeys.length > 0 && (
            <div style={{ 
              padding: '12px 16px', 
              background: '#eff6ff', 
              borderRadius: 8,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{ fontWeight: 500 }}>
                {selectedRowKeys.length} order(s) selected
              </span>
              <Space>
                <Button size="small" onClick={() => handleBulkAction('export')}>
                  Export Selected
                </Button>
                <Button size="small" onClick={() => handleBulkAction('send')}>
                  Send to Suppliers
                </Button>
                <Button size="small" danger onClick={() => setSelectedRowKeys([])}>
                  Clear Selection
                </Button>
              </Space>
            </div>
          )}
        </Space>
      </Card>

      {/* Orders Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
          rowSelection={rowSelection}
          scroll={{ x: 1200 }}
          locale={{
            emptyText: (
              <Empty
                description="No purchase orders found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => navigate('/purchase-orders/new')}
                >
                  Create First Order
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>
    </div>
  );
};

export default PurchaseOrderListModern;
