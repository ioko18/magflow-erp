import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  App as AntApp,
  Descriptions,
  Modal,
  Alert,
  Divider,
  Select
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  ShoppingOutlined,
  DollarOutlined,
  TeamOutlined,
  GlobalOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UploadOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const { Title, Text, Link } = Typography;
const { Search } = Input;

interface SupplierProduct {
  id: number;
  sku: string;
  supplier_id: number | null;
  supplier_name: string;
  price_cny: number;
  calculated_price_ron: number;
  exchange_rate_cny_ron: number;
  supplier_contact: string | null;
  supplier_url: string | null;
  supplier_notes: string | null;
  is_active: boolean;
  is_preferred: boolean;
  is_verified: boolean;
  last_imported_at: string;
  created_at: string;
}

interface Supplier {
  id: number;
  name: string;
  country: string;
  is_active: boolean;
}

interface Statistics {
  total_supplier_entries: number;
  unique_skus_with_suppliers: number;
  unique_supplier_names: number;
  avg_suppliers_per_sku: number;
}

const SupplierProductsSheetPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { message, modal } = AntApp.useApp();
  
  const [products, setProducts] = useState<SupplierProduct[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [searchSku, setSearchSku] = useState('');
  const [searchSupplier, setSearchSupplier] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<SupplierProduct | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [supplierModalVisible, setSupplierModalVisible] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      loadStatistics();
      loadSuppliers();
    }
  }, [isAuthenticated, pagination.current, pagination.pageSize]);

  const loadData = async () => {
    setLoading(true);
    try {
      const skip = (pagination.current - 1) * pagination.pageSize;
      const response = await api.get('/products/import/supplier-products', {
        params: {
          skip,
          limit: pagination.pageSize,
          sku: searchSku || undefined,
          supplier_name: searchSupplier || undefined,
        },
      });

      setProducts(response.data.data || []);
      setPagination(prev => ({
        ...prev,
        total: response.data.total || 0,
      }));
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load supplier products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await api.get('/products/import/suppliers-statistics');
      setStatistics(response.data);
    } catch (error: any) {
      console.error('Failed to load statistics:', error);
    }
  };

  const loadSuppliers = async () => {
    try {
      const response = await api.get('/suppliers', {
        params: { limit: 1000, active_only: true }
      });
      setSuppliers(response.data?.data?.suppliers || []);
    } catch (error: any) {
      console.error('Failed to load suppliers:', error);
    }
  };

  const handleSearch = () => {
    setPagination(prev => ({ ...prev, current: 1 }));
    loadData();
  };

  const handleReset = () => {
    setSearchSku('');
    setSearchSupplier('');
    setPagination(prev => ({ ...prev, current: 1 }));
    setTimeout(loadData, 100);
  };

  const showProductDetails = (product: SupplierProduct) => {
    setSelectedProduct(product);
    setDetailModalVisible(true);
  };

  const handleSetSupplier = () => {
    setSupplierModalVisible(true);
    setSelectedSupplierId(selectedProduct?.supplier_id || null);
  };

  const handleSaveSupplier = async () => {
    if (!selectedProduct?.id || !selectedSupplierId) return;

    try {
      await api.post(
        `/suppliers/sheets/${selectedProduct.id}/set-supplier`,
        { supplier_id: selectedSupplierId }
      );

      message.success('Furnizor setat cu succes!');

      // Reload data
      await loadData();

      // Update selected product
      setSelectedProduct({
        ...selectedProduct,
        supplier_id: selectedSupplierId
      });

      setSupplierModalVisible(false);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la setare furnizor');
    }
  };

  const handlePromoteProduct = () => {
    if (!selectedProduct?.id) return;

    modal.confirm({
      title: 'Transformă în Produs Intern?',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Acest produs va fi transformat din Google Sheets în produs intern (1688).</p>
          <p><strong>Beneficii:</strong></p>
          <ul>
            <li>✅ Management mai bun și mai rapid</li>
            <li>✅ Integrare cu workflow-ul 1688</li>
            <li>✅ Editare simplificată</li>
            <li>✅ Tracking și history</li>
          </ul>
          <p><strong>⚠️ ATENȚIE:</strong> Produsul Google Sheets va fi <strong>ȘTERS DEFINITIV</strong> din baza de date după promovare.</p>
          <p>Toate datele vor fi copiate în produsul intern. Această acțiune nu poate fi anulată.</p>
        </div>
      ),
      okText: 'Transformă și Șterge',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.post(
            `/suppliers/sheets/${selectedProduct.id}/promote`,
            null,
            { params: { delete_sheet: true } }
          );

          message.success('Produs transformat cu succes și șters din Google Sheets!');

          // Reload data
          await loadData();
          await loadStatistics();

          // Close modal
          setDetailModalVisible(false);
        } catch (error: any) {
          message.error(error.response?.data?.detail || 'Eroare la transformare');
        }
      },
    });
  };

  const columns: ColumnsType<SupplierProduct> = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      fixed: 'left',
      render: (sku: string) => (
        <Text strong style={{ color: '#1890ff' }}>{sku}</Text>
      ),
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      width: 150,
      render: (name: string) => (
        <Tag color="blue">{name}</Tag>
      ),
    },
    {
      title: 'Price (CNY)',
      dataIndex: 'price_cny',
      key: 'price_cny',
      width: 120,
      align: 'right',
      render: (price: number) => (
        <Text strong>¥{price.toFixed(2)}</Text>
      ),
      sorter: (a, b) => a.price_cny - b.price_cny,
    },
    {
      title: 'Price (RON)',
      dataIndex: 'calculated_price_ron',
      key: 'calculated_price_ron',
      width: 120,
      align: 'right',
      render: (price: number) => (
        <Text type="success">{price.toFixed(2)} RON</Text>
      ),
      sorter: (a, b) => a.calculated_price_ron - b.calculated_price_ron,
    },
    {
      title: 'Exchange Rate',
      dataIndex: 'exchange_rate_cny_ron',
      key: 'exchange_rate',
      width: 120,
      align: 'center',
      render: (rate: number) => (
        <Text type="secondary">{rate}</Text>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 150,
      render: (_, record) => (
        <Space>
          {record.is_verified && (
            <Tag icon={<CheckCircleOutlined />} color="success">
              Verified
            </Tag>
          )}
          {record.is_preferred && (
            <Tag color="gold">Preferred</Tag>
          )}
          {!record.is_active && (
            <Tag icon={<CloseCircleOutlined />} color="error">
              Inactive
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'URL',
      dataIndex: 'supplier_url',
      key: 'supplier_url',
      width: 100,
      align: 'center',
      render: (url: string | null) => (
        url ? (
          <Link href={url} target="_blank" rel="noopener noreferrer">
            <GlobalOutlined style={{ fontSize: 18 }} />
          </Link>
        ) : (
          <Text type="secondary">-</Text>
        )
      ),
    },
    {
      title: 'Last Import',
      dataIndex: 'last_imported_at',
      key: 'last_imported_at',
      width: 150,
      render: (date: string) => (
        <Text type="secondary">
          {date ? new Date(date).toLocaleString() : '-'}
        </Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showProductDetails(record)}
        >
          Details
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <ShoppingOutlined /> Supplier Products from Google Sheets
      </Title>
      <Text type="secondary">
        View and manage supplier products imported from Google Sheets
      </Text>

      {/* Statistics Cards */}
      {statistics && (
        <Row gutter={16} style={{ marginTop: 24, marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Products"
                value={statistics.total_supplier_entries}
                prefix={<ShoppingOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unique SKUs"
                value={statistics.unique_skus_with_suppliers}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unique Suppliers"
                value={statistics.unique_supplier_names}
                prefix={<GlobalOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Avg Suppliers/SKU"
                value={statistics.avg_suppliers_per_sku}
                prefix={<DollarOutlined />}
                precision={2}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Search and Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="middle" wrap>
          <Search
            placeholder="Search by SKU"
            value={searchSku}
            onChange={(e) => setSearchSku(e.target.value)}
            onSearch={handleSearch}
            style={{ width: 200 }}
            prefix={<SearchOutlined />}
          />
          <Search
            placeholder="Search by Supplier"
            value={searchSupplier}
            onChange={(e) => setSearchSupplier(e.target.value)}
            onSearch={handleSearch}
            style={{ width: 200 }}
            prefix={<SearchOutlined />}
          />
          <Button onClick={handleSearch} type="primary" icon={<SearchOutlined />}>
            Search
          </Button>
          <Button onClick={handleReset} icon={<ReloadOutlined />}>
            Reset
          </Button>
          <Button onClick={loadData} icon={<ReloadOutlined />}>
            Refresh
          </Button>
        </Space>
      </Card>

      {/* Products Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={products}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} products`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({ ...prev, current: page, pageSize }));
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title={`Product Details: ${selectedProduct?.sku}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedProduct && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="SKU" span={2}>
              <Text strong style={{ fontSize: 16 }}>{selectedProduct.sku}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Supplier Name" span={2}>
              <Tag color="blue" style={{ fontSize: 14 }}>{selectedProduct.supplier_name}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Price (CNY)">
              <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
                ¥{selectedProduct.price_cny.toFixed(2)}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Price (RON)">
              <Text strong style={{ fontSize: 16, color: '#52c41a' }}>
                {selectedProduct.calculated_price_ron.toFixed(2)} RON
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Exchange Rate" span={2}>
              1 CNY = {selectedProduct.exchange_rate_cny_ron} RON
            </Descriptions.Item>
            <Descriptions.Item label="Supplier URL" span={2}>
              {selectedProduct.supplier_url ? (
                <Link href={selectedProduct.supplier_url} target="_blank" rel="noopener noreferrer">
                  {selectedProduct.supplier_url}
                </Link>
              ) : (
                <Text type="secondary">No URL provided</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Contact" span={2}>
              {selectedProduct.supplier_contact || <Text type="secondary">No contact provided</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Notes" span={2}>
              {selectedProduct.supplier_notes || <Text type="secondary">No notes</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Status" span={2}>
              <Space>
                {selectedProduct.is_active ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">Active</Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">Inactive</Tag>
                )}
                {selectedProduct.is_verified && (
                  <Tag icon={<CheckCircleOutlined />} color="success">Verified</Tag>
                )}
                {selectedProduct.is_preferred && (
                  <Tag color="gold">Preferred</Tag>
                )}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Last Imported">
              {new Date(selectedProduct.last_imported_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              {new Date(selectedProduct.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}

        {selectedProduct && (
          <>
            <Divider />
            
            {/* Promote Section */}
            {selectedProduct.supplier_id ? (
              <Alert
                message="Acest produs poate fi transformat în produs intern"
                description="Produsul are un furnizor asociat și poate fi promovat pentru management mai bun."
                type="info"
                showIcon
                action={
                  <Button
                    type="primary"
                    icon={<UploadOutlined />}
                    onClick={handlePromoteProduct}
                  >
                    Transformă în Produs Intern
                  </Button>
                }
              />
            ) : (
              <Alert
                message="Furnizor lipsă"
                description="Trebuie să setezi un furnizor înainte de a putea promova produsul."
                type="warning"
                showIcon
                action={
                  <Button
                    icon={<TeamOutlined />}
                    onClick={handleSetSupplier}
                  >
                    Setează Furnizor
                  </Button>
                }
              />
            )}
          </>
        )}
      </Modal>

      {/* Supplier Selection Modal */}
      <Modal
        title="Setează Furnizor"
        open={supplierModalVisible}
        onCancel={() => setSupplierModalVisible(false)}
        onOk={handleSaveSupplier}
        okText="Salvează"
        cancelText="Anulează"
      >
        <Select
          style={{ width: '100%' }}
          placeholder="Selectează furnizor"
          value={selectedSupplierId}
          onChange={setSelectedSupplierId}
          showSearch
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={suppliers.map(s => ({
            value: s.id,
            label: s.name
          }))}
        />
      </Modal>
    </div>
  );
};

export default SupplierProductsSheetPage;
