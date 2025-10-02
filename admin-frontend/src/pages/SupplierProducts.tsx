import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  Statistic,
  Tooltip,
  Empty,
  Modal,
  Divider,
  Image,
  App as AntApp,
  Upload,
  Alert
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DollarOutlined,
  TeamOutlined,
  CloudUploadOutlined,
  FileExcelOutlined,
  ShoppingOutlined,
  GlobalOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import api from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface LocalProduct {
  id: number;
  name: string;
  sku: string;
  brand?: string;
  category?: string;
  image_url?: string;
}

interface SupplierProduct {
  id: number;
  supplier_product_name: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  confidence_score: number;
  manual_confirmed: boolean;
  is_active: boolean;
  last_price_update?: string;
  created_at: string;
  local_product?: LocalProduct;
}

interface Supplier {
  id: number;
  name: string;
  country: string;
}

interface Statistics {
  total_products: number;
  confirmed_products: number;
  pending_products: number;
  active_products: number;
  average_confidence: number;
  confirmation_rate: number;
}

const SupplierProductsPage: React.FC = () => {
  const { message } = AntApp.useApp();
  const [products, setProducts] = useState<SupplierProduct[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [localProducts, setLocalProducts] = useState<LocalProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<number | null>(null);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [searchText, setSearchText] = useState('');
  const [confirmedFilter, setConfirmedFilter] = useState<string>('all');
  const [selectedProduct, setSelectedProduct] = useState<SupplierProduct | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedLocalProductId, setSelectedLocalProductId] = useState<number | null>(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  useEffect(() => {
    loadSuppliers();
  }, []);

  useEffect(() => {
    if (selectedSupplier) {
      loadProducts();
      loadStatistics();
    }
  }, [selectedSupplier, pagination.current, pagination.pageSize, confirmedFilter, searchText]);

  const loadSuppliers = async () => {
    try {
      const response = await api.get('/suppliers', {
        params: { limit: 1000, active_only: true }
      });
      const suppliersData = response.data?.data?.suppliers || [];
      setSuppliers(suppliersData);
      
      if (suppliersData.length > 0 && !selectedSupplier) {
        setSelectedSupplier(suppliersData[0].id);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
      message.error('Failed to load suppliers');
    }
  };

  const loadProducts = async () => {
    if (!selectedSupplier) return;

    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      const response = await api.get(`/suppliers/${selectedSupplier}/products`, {
        params: {
          skip,
          limit: pagination.pageSize,
          confirmed_only: confirmedFilter === 'confirmed',
          search: searchText || undefined,
        }
      });

      const data = response.data?.data;
      setProducts(data?.products || []);
      setPagination(prev => ({
        ...prev,
        total: data?.pagination?.total || 0,
      }));
    } catch (error) {
      console.error('Error loading products:', error);
      message.error('Failed to load supplier products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    if (!selectedSupplier) return;

    try {
      const response = await api.get(`/suppliers/${selectedSupplier}/products/statistics`);
      setStatistics(response.data?.data || null);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const loadLocalProducts = async () => {
    try {
      const response = await api.get('/products', {
        params: { limit: 1000, active_only: true }
      });
      setLocalProducts(response.data?.data?.products || []);
    } catch (error) {
      console.error('Error loading local products:', error);
    }
  };

  const handleMatchProduct = async () => {
    if (!selectedProduct || !selectedSupplier || !selectedLocalProductId) {
      message.error('Selectează un produs local');
      return;
    }

    try {
      setLoading(true);
      await api.post(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/match`, {
        local_product_id: selectedLocalProductId,
        confidence_score: 1.0,
        manual_confirmed: true
      });

      message.success('Match confirmat cu succes!');
      setDetailModalVisible(false);
      setSelectedLocalProductId(null);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la confirmarea match-ului');
    } finally {
      setLoading(false);
    }
  };

  const handleUnmatchProduct = async () => {
    if (!selectedProduct || !selectedSupplier) return;

    try {
      setLoading(true);
      await api.delete(`/suppliers/${selectedSupplier}/products/${selectedProduct.id}/match`);
      
      message.success('Match șters cu succes!');
      setDetailModalVisible(false);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la ștergerea match-ului');
    } finally {
      setLoading(false);
    }
  };

  const handleSupplierChange = (supplierId: number) => {
    setSelectedSupplier(supplierId);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current || 1,
      pageSize: newPagination.pageSize || 20,
      total: pagination.total,
    });
  };

  const handleExcelUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    
    if (!selectedSupplier) {
      message.error('Selectează un furnizor mai întâi');
      onError?.(new Error('No supplier selected'));
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file as File);

      const response = await api.post(
        `/suppliers/${selectedSupplier}/products/import-excel`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const data = response.data?.data;
      message.success(
        `Import reușit! ${data?.imported_count} produse importate, ${data?.skipped_count} sărite`
      );
      
      if (data?.errors && data.errors.length > 0) {
        Modal.warning({
          title: 'Atenție - Erori la import',
          content: (
            <div>
              <p>Unele rânduri au avut erori:</p>
              <ul style={{ maxHeight: '200px', overflow: 'auto' }}>
                {data.errors.map((error: string, index: number) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          ),
          width: 600,
        });
      }

      onSuccess?.(response.data);
      await loadProducts();
      await loadStatistics();
    } catch (error: any) {
      console.error('Error uploading Excel:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to upload Excel file';
      message.error(errorMsg);
      onError?.(error);
    }
  };

  const viewProductDetails = async (product: SupplierProduct) => {
    setSelectedProduct(product);
    setSelectedLocalProductId(product.local_product?.id || null);
    setDetailModalVisible(true);
    await loadLocalProducts();
  };
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'Foarte sigur';
    if (score >= 0.6) return 'Mediu';
    return 'Scăzut';
  };

  // Get selected supplier data for potential future use
  // const selectedSupplierData = suppliers.find(s => s.id === selectedSupplier);

  const columns: ColumnsType<SupplierProduct> = [
    {
      title: 'Imagine Furnizor',
      key: 'supplier_image',
      width: 180,
      render: (_, record) => (
        <Image
          src={record.supplier_image_url}
          alt={record.supplier_product_name}
          width={170}
          height={170}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='10'%3ENo Image%3C/text%3E%3C/svg%3E"
          preview={{
            mask: <EyeOutlined />
          }}
        />
      ),
    },
    {
      title: 'Produs Furnizor',
      key: 'supplier_product',
      width: 300,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: '13px' }}>
            {record.supplier_product_name}
          </Text>
          <a 
            href={record.supplier_product_url} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ fontSize: '12px' }}
          >
            <GlobalOutlined style={{ marginRight: 4 }} />
            Vezi pe 1688.com
          </a>
        </Space>
      ),
    },
    {
      title: 'Imagine Local',
      key: 'local_image',
      width: 180,
      render: (_, record) => (
        record.local_product?.image_url ? (
          <Image
            src={record.local_product.image_url}
            alt={record.local_product.name}
            width={170}
            height={170}
            style={{ objectFit: 'cover', borderRadius: '4px' }}
            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='10'%3ENo Image%3C/text%3E%3C/svg%3E"
            preview={{
              mask: <EyeOutlined />
            }}
          />
        ) : (
          <div style={{
            width: 170,
            height: 170,
            background: '#f5f5f5',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px dashed #d9d9d9'
          }}>
            <Text type="secondary" style={{ fontSize: '10px', textAlign: 'center' }}>
              No<br/>Image
            </Text>
          </div>
        )
      ),
    },
    {
      title: 'Produs Local',
      key: 'local_product',
      width: 250,
      render: (_, record) => (
        record.local_product ? (
          <Space direction="vertical" size={0}>
            <Text strong style={{ fontSize: '13px' }}>
              {record.local_product.name}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              SKU: {record.local_product.sku}
            </Text>
            {record.local_product.brand && (
              <Tag color="blue" style={{ fontSize: '11px' }}>
                {record.local_product.brand}
              </Tag>
            )}
          </Space>
        ) : (
          <Text type="secondary">-</Text>
        )
      ),
    },
    {
      title: 'Preț',
      key: 'price',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1890ff', fontSize: '14px' }}>
            {record.supplier_price.toFixed(2)} {record.supplier_currency}
          </Text>
          {record.last_price_update && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {new Date(record.last_price_update).toLocaleDateString('ro-RO')}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Scor Potrivire',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      width: 130,
      sorter: (a, b) => a.confidence_score - b.confidence_score,
      render: (score: number) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 'bold', color: getConfidenceColor(score) }}>
            {Math.round(score * 100)}%
          </div>
          <Tag color={getConfidenceColor(score)} style={{ fontSize: '11px' }}>
            {getConfidenceLabel(score)}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      filters: [
        { text: 'Confirmat', value: 'confirmed' },
        { text: 'În așteptare', value: 'pending' },
        { text: 'Activ', value: 'active' },
        { text: 'Inactiv', value: 'inactive' },
      ],
      onFilter: (value, record) => {
        if (value === 'confirmed') return record.manual_confirmed;
        if (value === 'pending') return !record.manual_confirmed;
        if (value === 'active') return record.is_active;
        if (value === 'inactive') return !record.is_active;
        return true;
      },
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          <Tag 
            color={record.manual_confirmed ? 'green' : 'orange'}
            icon={record.manual_confirmed ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
          >
            {record.manual_confirmed ? 'Confirmat' : 'În așteptare'}
          </Tag>
          {record.is_active && (
            <Tag color="blue" style={{ fontSize: '11px' }}>Activ</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Data',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 110,
      render: (date: string) => (
        <Text style={{ fontSize: '12px' }}>
          {new Date(date).toLocaleDateString('ro-RO')}
        </Text>
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      fixed: 'right',
      width: 80,
      render: (_, record) => (
        <Tooltip title="Vezi detalii">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => viewProductDetails(record)}
            style={{ color: '#1890ff' }}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '24px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                <ShoppingOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Produse Furnizori
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Vizualizează și gestionează produsele de la furnizori cu potriviri automate
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                customRequest={handleExcelUpload}
                disabled={!selectedSupplier}
              >
                <Tooltip title={!selectedSupplier ? "Selectează un furnizor mai întâi" : "Încarcă fișier Excel cu produse"}>
                  <Button 
                    icon={<CloudUploadOutlined />}
                    disabled={!selectedSupplier}
                    size="large"
                    type="primary"
                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                  >
                    Import Excel
                  </Button>
                </Tooltip>
              </Upload>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadProducts}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Supplier Selection */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '24px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong>Selectează Furnizor:</Text>
              <Select
                size="large"
                value={selectedSupplier}
                onChange={handleSupplierChange}
                style={{ width: '100%', maxWidth: '400px' }}
                suffixIcon={<TeamOutlined />}
                placeholder="Selectează un furnizor"
              >
                {suppliers.map(supplier => (
                  <Option key={supplier.id} value={supplier.id}>
                    <Space>
                      <TeamOutlined />
                      {supplier.name}
                      <Tag color="blue">{supplier.country}</Tag>
                    </Space>
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Excel Import Info */}
      {selectedSupplier && (
        <Alert
          message="Import Produse din Excel"
          description={
            <Space direction="vertical" size={4}>
              <Text>📄 <strong>Format așteptat:</strong> Fișier Excel (.xlsx) cu următoarele coloane:</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>url_image_scrapping</code> - URL imagine produs</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>url_product_scrapping</code> - URL pagină produs (1688.com)</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>chinese_name_scrapping</code> - Nume produs în chineză</Text>
              <Text style={{ marginLeft: '20px' }}>• <code>price_scrapping</code> - Preț (format: "CN ¥ 2.45")</Text>
              <Text>💡 <strong>Notă:</strong> Produsele existente (același URL) vor fi actualizate automat</Text>
            </Space>
          }
          type="info"
          showIcon
          icon={<FileExcelOutlined />}
          closable
          style={{ marginBottom: '16px', borderRadius: '8px' }}
        />
      )}

      {/* Statistics Cards */}
      {statistics && selectedSupplier && (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Total Produse</span>}
                value={statistics.total_products}
                prefix={<ShoppingOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Confirmate</span>}
                value={statistics.confirmed_products}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>În Așteptare</span>}
                value={statistics.pending_products}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card 
              variant="borderless"
              style={{ 
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
              }}
            >
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Scor Mediu</span>}
                value={Math.round(statistics.average_confidence * 100)}
                suffix={<span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>%</span>}
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card 
        variant="borderless"
        style={{ 
          marginBottom: '16px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={10}>
            <Input
              size="large"
              placeholder="Caută după nume produs..."
              prefix={<SearchOutlined style={{ color: '#1890ff' }} />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ borderRadius: '6px' }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Select
              size="large"
              placeholder="Filtrează după status"
              value={confirmedFilter}
              onChange={setConfirmedFilter}
              style={{ width: '100%', borderRadius: '6px' }}
              suffixIcon={<FilterOutlined />}
            >
              <Option value="all">📋 Toate produsele</Option>
              <Option value="confirmed">✅ Doar confirmate</Option>
              <Option value="pending">⏳ Doar în așteptare</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Button 
              size="large"
              onClick={() => { setSearchText(''); setConfirmedFilter('all'); }}
              style={{ borderRadius: '6px' }}
            >
              Resetează Filtre
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Products Table */}
      <Card 
        variant="borderless"
        style={{ 
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        {selectedSupplier ? (
          <Table
            columns={columns}
            dataSource={products}
            rowKey="id"
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => (
                <Text strong>
                  {range[0]}-{range[1]} din {total} produse
                </Text>
              ),
              pageSizeOptions: ['10', '20', '50', '100'],
            }}
            onChange={handleTableChange}
            scroll={{ x: 1400 }}
            size="middle"
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical">
                      <Text type="secondary">Nu există produse pentru acest furnizor</Text>
                    </Space>
                  }
                />
              )
            }}
          />
        ) : (
          <Empty
            description="Selectează un furnizor pentru a vedea produsele"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Card>

      {/* Product Details Modal */}
      <Modal
        title={
          <Space>
            <ShoppingOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>Detalii Produs Furnizor</Text>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)} size="large">
            Închide
          </Button>
        ]}
      >
        {selectedProduct && (
          <div>
            <Row gutter={24}>
              <Col span={12}>
                <Card title="Produs Furnizor (1688.com)" size="small">
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Image
                      src={selectedProduct.supplier_image_url}
                      alt={selectedProduct.supplier_product_name}
                      width={200}
                      height={200}
                      style={{ objectFit: 'cover', borderRadius: '8px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>Nume Chinezesc:</strong></Text>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      {selectedProduct.supplier_product_name}
                    </div>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>Preț:</strong> {selectedProduct.supplier_price} {selectedProduct.supplier_currency}</Text>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <a href={selectedProduct.supplier_product_url} target="_blank" rel="noopener noreferrer">
                      <GlobalOutlined style={{ marginRight: 4 }} />
                      Vezi pe 1688.com
                    </a>
                  </div>
                </Card>
              </Col>

              <Col span={12}>
                <Card title="Produs Local" size="small">
                  {selectedProduct.local_product ? (
                    <>
                      {selectedProduct.local_product.image_url && (
                        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                          <Image
                            src={selectedProduct.local_product.image_url}
                            alt={selectedProduct.local_product.name}
                            width={200}
                            height={200}
                            style={{ objectFit: 'cover', borderRadius: '8px' }}
                            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='16'%3ENo Image%3C/text%3E%3C/svg%3E"
                          />
                        </div>
                      )}
                      <div style={{ marginBottom: '8px' }}>
                        <Text strong style={{ fontSize: '16px' }}>
                          {selectedProduct.local_product.name}
                        </Text>
                      </div>
                      <div style={{ marginBottom: '8px' }}>
                        <Text><strong>SKU:</strong> {selectedProduct.local_product.sku}</Text>
                      </div>
                      {selectedProduct.local_product.brand && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Brand:</strong> {selectedProduct.local_product.brand}</Text>
                        </div>
                      )}
                      {selectedProduct.local_product.category && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Categorie:</strong> {selectedProduct.local_product.category}</Text>
                        </div>
                      )}
                      <Divider style={{ margin: '12px 0' }} />
                      {!selectedProduct.manual_confirmed && (
                        <Button
                          type="primary"
                          icon={<CheckCircleOutlined />}
                          onClick={handleMatchProduct}
                          loading={loading}
                          style={{ width: '100%', marginBottom: '8px', background: '#52c41a', borderColor: '#52c41a' }}
                        >
                          Confirmă Match
                        </Button>
                      )}
                      <Button
                        danger
                        icon={<CloseCircleOutlined />}
                        onClick={handleUnmatchProduct}
                        loading={loading}
                        style={{ width: '100%' }}
                      >
                        Șterge Match
                      </Button>
                    </>
                  ) : (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: '12px' }}>
                        Nu există produs local asociat
                      </Text>
                      <Divider style={{ margin: '12px 0' }} />
                      <div style={{ marginBottom: '12px' }}>
                        <Text strong>Asociază cu produs local:</Text>
                        <Select
                          showSearch
                          placeholder="Selectează produs local"
                          style={{ width: '100%', marginTop: '8px' }}
                          value={selectedLocalProductId}
                          onChange={setSelectedLocalProductId}
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={localProducts.map(p => ({
                            value: p.id,
                            label: `${p.name} (SKU: ${p.sku})`
                          }))}
                        />
                      </div>
                      <Button
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={handleMatchProduct}
                        loading={loading}
                        disabled={!selectedLocalProductId}
                        style={{ width: '100%' }}
                      >
                        Confirmă Match
                      </Button>
                    </>
                  )}
                </Card>
              </Col>
            </Row>

            <Divider />

            <Card title="Informații Potrivire" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Scor Potrivire"
                    value={Math.round(selectedProduct.confidence_score * 100)}
                    suffix="%"
                    valueStyle={{
                      color: getConfidenceColor(selectedProduct.confidence_score)
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Status Confirmare"
                    value={selectedProduct.manual_confirmed ? 'Confirmat' : 'În așteptare'}
                    valueStyle={{
                      color: selectedProduct.manual_confirmed ? '#52c41a' : '#faad14'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Data Creare"
                    value={new Date(selectedProduct.created_at).toLocaleDateString('ro-RO')}
                  />
                </Col>
              </Row>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SupplierProductsPage;
