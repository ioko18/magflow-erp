import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Table, Button, Space, Tag, Typography, Select, Statistic,
  Empty, message as antMessage, Badge, Progress
} from 'antd';
import {
  WarningOutlined, DownloadOutlined, ReloadOutlined, InboxOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ShoppingCartOutlined,
  DashboardOutlined, FilterOutlined, ClearOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface LowStockProduct {
  id: string;
  part_number_key: string;
  name: string;
  account_type: string;
  stock_quantity: number;
  main_stock?: number;
  fbe_stock?: number;
  price: number;
  currency: string;
  stock_status: string;
  reorder_quantity: number;
  sale_price?: number;
  recommended_price?: number;
  vat_id?: number;
  ean?: string;
  brand?: string;
  category_name?: string;
}

interface Statistics {
  total_items: number;
  out_of_stock: number;
  critical: number;
  low_stock: number;
  in_stock: number;
  needs_reorder: number;
  total_value: number;
  stock_health_percentage: number;
}

const InventoryPage: React.FC = () => {
  const [products, setProducts] = useState<LowStockProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [accountFilter, setAccountFilter] = useState<string>('all');
  const [groupBySku, setGroupBySku] = useState<boolean>(true);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  useEffect(() => {
    loadProducts();
    loadStatistics();
  }, [pagination.current, pagination.pageSize, statusFilter, accountFilter, groupBySku]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      const params: any = { skip, limit: pagination.pageSize, group_by_sku: groupBySku };
      
      // Only add status filter if it's not 'all'
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      // Add account filter - send uppercase but backend will normalize
      if (accountFilter && accountFilter !== 'all') {
        params.account_type = accountFilter;
      }
      
      // Use eMAG inventory endpoint for real data
      const response = await api.get('/emag-inventory/low-stock', { params });
      const data = response.data?.data;
      
      if (!data?.products || data.products.length === 0) {
        if (accountFilter !== 'all' || statusFilter !== 'all') {
          antMessage.info('No products found with current filters. Try adjusting your filters.');
        }
      }
      
      setProducts(data?.products || []);
      setPagination(prev => ({ ...prev, total: data?.pagination?.total || 0 }));
    } catch (error: any) {
      console.error('Error loading products:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to load inventory data';
      antMessage.error(`Error loading inventory: ${errorMsg}`);
      setProducts([]);
      setPagination(prev => ({ ...prev, total: 0 }));
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const params: any = {};
      
      // Add account filter to statistics as well
      if (accountFilter && accountFilter !== 'all') {
        params.account_type = accountFilter;
      }
      
      // Use eMAG inventory endpoint for real data
      const response = await api.get('/emag-inventory/statistics', { params });
      setStatistics(response.data?.data || null);
    } catch (error) {
      console.error('Error loading statistics:', error);
      // Don't show error message for statistics - it's not critical
    }
  };

  const resetFilters = () => {
    setStatusFilter('all');
    setAccountFilter('all');
    setGroupBySku(true);
    setPagination({ current: 1, pageSize: 20, total: 0 });
    antMessage.success('Filters reset successfully');
  };

  const handleExportExcel = async () => {
    try {
      setExporting(true);
      
      const params: any = {};
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      // Use eMAG inventory endpoint for real data
      const response = await api.get('/emag-inventory/export/low-stock-excel', {
        params,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `low_stock_products_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      antMessage.success('Excel file downloaded successfully!');
    } catch (error) {
      console.error('Error exporting Excel:', error);
      antMessage.error('Failed to export Excel file');
    } finally {
      setExporting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'out_of_stock': return 'red';
      case 'critical': return 'orange';
      case 'low_stock': return 'gold';
      case 'in_stock': return 'green';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'out_of_stock': return <CloseCircleOutlined />;
      case 'critical': return <WarningOutlined />;
      case 'low_stock': return <WarningOutlined />;
      case 'in_stock': return <CheckCircleOutlined />;
      default: return <InboxOutlined />;
    }
  };

  const columns: ColumnsType<LowStockProduct> = [
    {
      title: 'Part Number',
      dataIndex: 'part_number_key',
      key: 'part_number_key',
      width: 150,
      fixed: 'left',
      render: (pnk: string) => <Text strong style={{ color: '#1890ff' }}>{pnk}</Text>
    },
    {
      title: 'Product',
      key: 'product',
      width: 350,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.name}</Text>
          {record.brand && (
            <Text type="secondary" style={{ fontSize: '12px' }}>Brand: {record.brand}</Text>
          )}
          {record.category_name && (
            <Text type="secondary" style={{ fontSize: '11px' }}>{record.category_name}</Text>
          )}
        </Space>
      )
    },
    {
      title: 'Account',
      dataIndex: 'account_type',
      key: 'account',
      width: 100,
      render: (account: string) => (
        <Tag color={account === 'MAIN' ? 'blue' : 'green'}>{account}</Tag>
      )
    },
    {
      title: 'Stock',
      key: 'stock',
      width: 220,
      render: (_, record) => {
        const hasMultiAccount = (record.main_stock !== undefined && record.fbe_stock !== undefined) && 
                                (record.main_stock > 0 || record.fbe_stock > 0);
        const totalStock = hasMultiAccount ? (record.main_stock || 0) + (record.fbe_stock || 0) : (record.stock_quantity || 0);
        
        return (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            {hasMultiAccount ? (
              <>
                <Text>Total: <Text strong style={{ color: '#1890ff' }}>{totalStock}</Text></Text>
                <Space size={8}>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    MAIN: <Text strong>{record.main_stock || 0}</Text>
                  </Text>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    FBE: <Text strong>{record.fbe_stock || 0}</Text>
                  </Text>
                </Space>
              </>
            ) : (
              <Text>Current: <Text strong>{record.stock_quantity || 0}</Text></Text>
            )}
            <Progress
              percent={Math.min(100, (totalStock / 20) * 100)}
              size="small"
              status={totalStock <= 10 ? 'exception' : 'normal'}
              showInfo={false}
            />
            <Text type="secondary" style={{ fontSize: '11px' }}>
              Target: 20+ units
            </Text>
          </Space>
        );
      }
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      filters: [
        { text: 'Out of Stock', value: 'out_of_stock' },
        { text: 'Critical', value: 'critical' },
        { text: 'Low Stock', value: 'low_stock' },
      ],
      render: (_, record) => (
        <Tag
          color={getStatusColor(record.stock_status)}
          icon={getStatusIcon(record.stock_status)}
        >
          {(record.stock_status || 'unknown').toUpperCase().replace('_', ' ')}
        </Tag>
      )
    },
    {
      title: 'Reorder',
      key: 'reorder',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#52c41a', fontSize: '16px' }}>
            {record.reorder_quantity || 0} units
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Cost: {((record.price || 0) * (record.reorder_quantity || 0)).toFixed(2)} {record.currency || 'RON'}
          </Text>
        </Space>
      )
    },
    {
      title: 'Price',
      key: 'price',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{(record.price || 0).toFixed(2)} {record.currency || 'RON'}</Text>
          {record.sale_price && record.sale_price !== record.price && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              Sale: {(record.sale_price || 0).toFixed(2)}
            </Text>
          )}
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <Card variant="borderless" style={{ marginBottom: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                <DashboardOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Inventory Management
                {(accountFilter !== 'all' || statusFilter !== 'all') && (
                  <Badge 
                    count="Filtered" 
                    style={{ backgroundColor: '#52c41a', marginLeft: '12px' }} 
                  />
                )}
              </Title>
              <Text type="secondary">
                Monitor stock levels and generate supplier orders
                {accountFilter !== 'all' && (
                  <Text type="secondary" style={{ marginLeft: '8px' }}>
                    • Showing {accountFilter} account only
                  </Text>
                )}
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button 
                icon={<ReloadOutlined />} 
                onClick={() => {
                  loadProducts();
                  loadStatistics();
                  antMessage.success('Data refreshed successfully');
                }} 
                loading={loading} 
                size="large"
              >
                Refresh
              </Button>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleExportExcel}
                loading={exporting}
                size="large"
              >
                Export to Excel
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {statistics && (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="borderless" style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Total Items</span>}
                value={statistics.total_items}
                prefix={<InboxOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="borderless" style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Needs Reorder</span>}
                value={statistics.needs_reorder}
                prefix={<ShoppingCartOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="borderless" style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Stock Health</span>}
                value={statistics.stock_health_percentage}
                suffix="%"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card variant="borderless" style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' }}>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Inventory Value</span>}
                value={statistics.total_value}
                precision={2}
                suffix="RON"
                valueStyle={{ color: '#fff', fontSize: '28px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card variant="borderless" style={{ marginBottom: '16px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={6}>
            <Select
              size="large"
              placeholder="Filter by status"
              value={statusFilter}
              onChange={(value) => {
                setStatusFilter(value);
                setPagination(prev => ({ ...prev, current: 1 }));
              }}
              style={{ width: '100%' }}
              suffixIcon={<FilterOutlined />}
              loading={loading}
            >
              <Option value="all">📦 All Products</Option>
              <Option value="out_of_stock">🔴 Out of Stock</Option>
              <Option value="critical">🟠 Critical</Option>
              <Option value="low_stock">🟡 Low Stock</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Select
              size="large"
              placeholder="Filter by account"
              value={accountFilter}
              onChange={(value) => {
                setAccountFilter(value);
                setPagination(prev => ({ ...prev, current: 1 }));
              }}
              style={{ width: '100%' }}
              loading={loading}
            >
              <Option value="all">🏢 All Accounts</Option>
              <Option value="MAIN">🔵 MAIN Account</Option>
              <Option value="FBE">🟢 FBE Account</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Button
              size="large"
              type={groupBySku ? 'primary' : 'default'}
              onClick={() => setGroupBySku(!groupBySku)}
              style={{ width: '100%' }}
            >
              {groupBySku ? '✅ Grouped by SKU' : '📋 Show All'}
            </Button>
          </Col>
          <Col xs={24} md={6}>
            <Button
              size="large"
              icon={<ClearOutlined />}
              onClick={resetFilters}
              style={{ width: '100%' }}
              disabled={statusFilter === 'all' && accountFilter === 'all' && groupBySku === true}
            >
              Reset Filters
            </Button>
          </Col>
          <Col xs={24} md={24} style={{ marginTop: '16px' }}>
            <Space wrap size="large">
              <Badge count={statistics?.out_of_stock || 0} style={{ backgroundColor: '#ff4d4f' }}>
                <Tag color="red" style={{ fontSize: '14px', padding: '4px 12px' }}>🔴 Out of Stock</Tag>
              </Badge>
              <Badge count={statistics?.critical || 0} style={{ backgroundColor: '#ff7a45' }}>
                <Tag color="orange" style={{ fontSize: '14px', padding: '4px 12px' }}>🟠 Critical</Tag>
              </Badge>
              <Badge count={statistics?.low_stock || 0} style={{ backgroundColor: '#faad14' }}>
                <Tag color="gold" style={{ fontSize: '14px', padding: '4px 12px' }}>🟡 Low Stock</Tag>
              </Badge>
              <Badge count={statistics?.in_stock || 0} style={{ backgroundColor: '#52c41a' }}>
                <Tag color="green" style={{ fontSize: '14px', padding: '4px 12px' }}>✅ In Stock</Tag>
              </Badge>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card variant="borderless" style={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <Table
          columns={columns}
          dataSource={products}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => <Text strong>{range[0]}-{range[1]} of {total} products</Text>,
            pageSizeOptions: ['10', '20', '50', '100'],
            onChange: (page, pageSize) => setPagination({ ...pagination, current: page, pageSize })
          }}
          scroll={{ x: 1400 }}
          size="middle"
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Space direction="vertical" size="small">
                    <Text type="secondary">
                      {(accountFilter !== 'all' || statusFilter !== 'all') 
                        ? 'No products found with current filters'
                        : 'No low stock products found'}
                    </Text>
                    {(accountFilter !== 'all' || statusFilter !== 'all') && (
                      <Button type="link" onClick={resetFilters}>
                        Clear all filters
                      </Button>
                    )}
                  </Space>
                }
              />
            )
          }}
        />
      </Card>
    </div>
  );
};

export default InventoryPage;
