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
  Select,
  Statistic,
  Tooltip,
  Empty,
  Modal,
  Form,
  Divider,
  Progress,
  Image,
  Alert,
  App as AntApp
} from 'antd';
import {
  LinkOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  ShoppingOutlined,
  TeamOutlined,
  GlobalOutlined,
  BarChartOutlined,
  SyncOutlined,
  WarningOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface LocalProduct {
  id: number;
  name: string;
  chinese_name?: string;
  sku: string;
  brand?: string;
}

interface SupplierProduct {
  id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_product_name: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  confidence_score: number;
  manual_confirmed: boolean;
  local_product_id?: number;
  local_product?: LocalProduct;
  is_active: boolean;
  created_at: string;
}

interface Statistics {
  total_unmatched: number;
  total_matched: number;
  pending_confirmation: number;
  confirmed_matches: number;
  average_confidence: number;
}

const SupplierMatchingPage: React.FC = () => {
  const { message } = AntApp.useApp();
  const [unmatchedProducts, setUnmatchedProducts] = useState<SupplierProduct[]>([]);
  const [localProducts, setLocalProducts] = useState<LocalProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<number | null>(null);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<SupplierProduct | null>(null);
  const [matchModalVisible, setMatchModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  useEffect(() => {
    loadSuppliers();
    loadLocalProducts();
  }, []);

  useEffect(() => {
    if (selectedSupplier) {
      loadUnmatchedProducts();
      loadStatistics();
    }
  }, [selectedSupplier, pagination.current, pagination.pageSize]);

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

  const loadUnmatchedProducts = async () => {
    if (!selectedSupplier) return;

    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      const response = await api.get(`/suppliers/${selectedSupplier}/products/unmatched`, {
        params: {
          skip,
          limit: pagination.pageSize,
        }
      });

      const data = response.data?.data;
      setUnmatchedProducts(data?.products || []);
      setPagination(prev => ({
        ...prev,
        total: data?.pagination?.total || 0,
      }));
    } catch (error) {
      console.error('Error loading unmatched products:', error);
      message.error('Failed to load unmatched products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    if (!selectedSupplier) return;

    try {
      const response = await api.get(`/suppliers/${selectedSupplier}/matching/statistics`);
      setStatistics(response.data?.data || null);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const handleAutoMatch = async () => {
    if (!selectedSupplier) return;

    try {
      setLoading(true);
      const response = await api.post(`/suppliers/${selectedSupplier}/products/auto-match`);
      
      message.success(`Auto-matched ${response.data?.data?.matched_count || 0} products`);
      await loadUnmatchedProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Auto-match failed');
    } finally {
      setLoading(false);
    }
  };

  const handleManualMatch = (supplierProduct: SupplierProduct) => {
    setSelectedProduct(supplierProduct);
    form.resetFields();
    setMatchModalVisible(true);
  };

  const handleConfirmMatch = async (values: { local_product_id: number }) => {
    if (!selectedProduct) return;

    try {
      await api.post(`/suppliers/${selectedProduct.supplier_id}/products/${selectedProduct.id}/match`, {
        local_product_id: values.local_product_id,
        confidence_score: 1.0,
        manual_confirmed: true
      });

      message.success('Match confirmed successfully');
      setMatchModalVisible(false);
      await loadUnmatchedProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Failed to confirm match');
    }
  };

  const handleConfirmPendingMatch = async (supplierProduct: SupplierProduct) => {
    if (!supplierProduct.local_product_id) return;

    try {
      await api.post(`/suppliers/${supplierProduct.supplier_id}/products/${supplierProduct.id}/match`, {
        local_product_id: supplierProduct.local_product_id,
        confidence_score: supplierProduct.confidence_score || 1.0,
        manual_confirmed: true
      });

      message.success('Match confirmat cu succes!');
      await loadUnmatchedProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la confirmarea match-ului');
    }
  };

  const handleUnmatch = async (supplierProduct: SupplierProduct) => {
    try {
      await api.delete(`/suppliers/${supplierProduct.supplier_id}/products/${supplierProduct.id}/match`);
      
      message.success('Match șters cu succes!');
      await loadUnmatchedProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la ștergerea match-ului');
    }
  };

  const handleReMatchAll = async () => {
    if (!selectedSupplier) return;

    Modal.confirm({
      title: 'Re-Match All Products',
      content: 'Aceasta va șterge toate match-urile pending (neconfirmate) și va rula din nou auto-match. Match-urile confirmate manual vor rămâne neschimbate. Continui?',
      okText: 'Da, Re-Match',
      cancelText: 'Anulează',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setLoading(true);
          
          // Get all pending matches and unmatch them
          const response = await api.get(`/suppliers/${selectedSupplier}/products`, {
            params: { limit: 1000 }
          });
          
          const pendingMatches = response.data?.data?.products?.filter(
            (p: SupplierProduct) => p.local_product_id && !p.manual_confirmed
          ) || [];
          
          // Unmatch all pending
          for (const product of pendingMatches) {
            await api.delete(`/suppliers/${selectedSupplier}/products/${product.id}/match`);
          }
          
          // Run auto-match again
          await api.post(`/suppliers/${selectedSupplier}/products/auto-match`);
          
          message.success(`Re-match complet! ${pendingMatches.length} match-uri pending șterse și re-matchate`);
          await loadUnmatchedProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la re-match');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const viewProductDetails = (product: SupplierProduct) => {
    setSelectedProduct(product);
    setDetailModalVisible(true);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const columns: ColumnsType<SupplierProduct> = [
    {
      title: 'Imagine',
      key: 'image',
      width: 80,
      render: (_, record) => (
        <Image
          src={record.supplier_image_url}
          alt={record.supplier_product_name}
          width={60}
          height={60}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="/placeholder-product.png"
          preview={false}
        />
      ),
    },
    {
      title: 'Produs Furnizor (Chinezește)',
      key: 'supplier_product',
      width: 300,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: '13px', color: '#1890ff' }}>
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
          <Text type="secondary" style={{ fontSize: '11px' }}>
            Furnizor: {record.supplier_name}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Preț',
      key: 'price',
      width: 120,
      render: (_, record) => (
        <Text strong style={{ color: '#1890ff', fontSize: '14px' }}>
          {record.supplier_price.toFixed(2)} {record.supplier_currency}
        </Text>
      ),
    },
    {
      title: 'Status Matching',
      key: 'status',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          {record.local_product_id ? (
            <>
              <Tag 
                color={record.manual_confirmed ? 'green' : 'orange'}
                icon={record.manual_confirmed ? <CheckCircleOutlined /> : <WarningOutlined />}
              >
                {record.manual_confirmed ? 'Confirmat' : 'Pending'}
              </Tag>
              {record.confidence_score && (
                <Progress 
                  percent={Math.round(record.confidence_score * 100)} 
                  size="small"
                  strokeColor={getConfidenceColor(record.confidence_score)}
                />
              )}
            </>
          ) : (
            <Tag color="red" icon={<CloseCircleOutlined />}>
              Nematchat
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Produs Local Asociat',
      key: 'local_product',
      width: 250,
      render: (_, record) => (
        record.local_product ? (
          <Space direction="vertical" size={0}>
            <Text strong style={{ fontSize: '13px' }}>
              {record.local_product.name}
            </Text>
            {record.local_product.chinese_name && (
              <Text type="secondary" style={{ fontSize: '12px', color: '#1890ff' }}>
                中文: {record.local_product.chinese_name}
              </Text>
            )}
            <Text type="secondary" style={{ fontSize: '11px' }}>
              SKU: {record.local_product.sku}
            </Text>
          </Space>
        ) : (
          <Text type="secondary">-</Text>
        )
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space size="small" direction="vertical">
          <Space size="small">
            <Tooltip title="Vezi detalii">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => viewProductDetails(record)}
                style={{ color: '#1890ff' }}
                size="small"
              />
            </Tooltip>
            {!record.local_product_id ? (
              <Tooltip title="Match manual">
                <Button
                  type="primary"
                  size="small"
                  icon={<LinkOutlined />}
                  onClick={() => handleManualMatch(record)}
                >
                  Match
                </Button>
              </Tooltip>
            ) : (
              <>
                {!record.manual_confirmed && (
                  <Tooltip title="Confirmă match-ul">
                    <Button
                      type="primary"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleConfirmPendingMatch(record)}
                      style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    >
                      Confirmă
                    </Button>
                  </Tooltip>
                )}
                <Tooltip title="Șterge match-ul">
                  <Button
                    danger
                    size="small"
                    icon={<CloseCircleOutlined />}
                    onClick={() => handleUnmatch(record)}
                  >
                    Unmatch
                  </Button>
                </Tooltip>
              </>
            )}
          </Space>
        </Space>
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
                <LinkOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Product Matching
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Asociază produsele furnizorilor cu produsele din catalogul local
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadUnmatchedProducts}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
              <Button 
                type="primary" 
                icon={<ThunderboltOutlined />} 
                onClick={handleAutoMatch}
                loading={loading}
                size="large"
              >
                Auto-Match
              </Button>
              <Tooltip title="Șterge match-urile pending și re-match după actualizarea numelor chinezești">
                <Button 
                  icon={<SyncOutlined />} 
                  onClick={handleReMatchAll}
                  loading={loading}
                  size="large"
                  style={{ borderColor: '#faad14', color: '#faad14' }}
                >
                  Re-Match All
                </Button>
              </Tooltip>
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
                onChange={setSelectedSupplier}
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
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Nematchate</span>}
                value={statistics.total_unmatched}
                prefix={<CloseCircleOutlined />}
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
                value={statistics.confirmed_matches}
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
                value={statistics.pending_confirmation}
                prefix={<WarningOutlined />}
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
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Alert Info */}
      <Alert
        message="Cum funcționează matching-ul?"
        description={
          <Space direction="vertical" size={4}>
            <Text>• <strong>Auto-Match:</strong> Sistemul caută automat potriviri bazate pe nume chinezești și alte criterii</Text>
            <Text>• <strong>Match Manual:</strong> Poți asocia manual produsele furnizorului cu produsele din catalog</Text>
            <Text>• <strong>Nume Chinezești:</strong> Adaugă nume în limba chineză la produsele locale pentru matching mai bun</Text>
          </Space>
        }
        type="info"
        showIcon
        icon={<SyncOutlined />}
        style={{ marginBottom: '16px', borderRadius: '8px' }}
      />

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
            dataSource={unmatchedProducts}
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
            onChange={(newPagination) => setPagination({
              current: newPagination.current || 1,
              pageSize: newPagination.pageSize || 20,
              total: pagination.total,
            })}
            scroll={{ x: 1400 }}
            size="middle"
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical">
                      <Text type="secondary">Nu există produse nematchate</Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        Toate produsele au fost asociate cu produse locale
                      </Text>
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

      {/* Manual Match Modal */}
      <Modal
        title={
          <Space>
            <LinkOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>Match Manual Produs</Text>
          </Space>
        }
        open={matchModalVisible}
        onCancel={() => setMatchModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
        okText="Confirmă Match"
        cancelText="Anulează"
        okButtonProps={{ size: 'large', icon: <CheckCircleOutlined /> }}
        cancelButtonProps={{ size: 'large' }}
      >
        {selectedProduct && (
          <>
            <Alert
              message="Produs Furnizor"
              description={
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>{selectedProduct.supplier_product_name}</Text>
                  <Text type="secondary">Preț: {selectedProduct.supplier_price} {selectedProduct.supplier_currency}</Text>
                </Space>
              }
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />

            <Divider />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleConfirmMatch}
              size="large"
            >
              <Form.Item
                name="local_product_id"
                label={<Text strong>Selectează Produs Local</Text>}
                rules={[{ required: true, message: 'Selectează un produs local' }]}
              >
                <Select
                  showSearch
                  placeholder="Caută după nume sau SKU..."
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={localProducts.map(p => ({
                    value: p.id,
                    label: `${p.name} ${p.chinese_name ? `(${p.chinese_name})` : ''} - SKU: ${p.sku}`,
                    searchText: `${p.name} ${p.chinese_name || ''} ${p.sku}`.toLowerCase()
                  }))}
                  size="large"
                />
              </Form.Item>

              <Alert
                message="Notă"
                description="După confirmare, produsul furnizorului va fi asociat permanent cu produsul local selectat."
                type="warning"
                showIcon
              />
            </Form>
          </>
        )}
      </Modal>

      {/* Product Details Modal */}
      <Modal
        title={
          <Space>
            <ShoppingOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>Detalii Produs</Text>
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
                    <div style={{ fontSize: '14px', color: '#1890ff', marginTop: '4px' }}>
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
                      <div style={{ marginBottom: '8px' }}>
                        <Text strong style={{ fontSize: '16px' }}>
                          {selectedProduct.local_product.name}
                        </Text>
                      </div>
                      {selectedProduct.local_product.chinese_name && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Nume Chinezesc:</strong></Text>
                          <div style={{ fontSize: '14px', color: '#1890ff', marginTop: '4px' }}>
                            {selectedProduct.local_product.chinese_name}
                          </div>
                        </div>
                      )}
                      <div style={{ marginBottom: '8px' }}>
                        <Text><strong>SKU:</strong> {selectedProduct.local_product.sku}</Text>
                      </div>
                      {selectedProduct.local_product.brand && (
                        <div style={{ marginBottom: '8px' }}>
                          <Text><strong>Brand:</strong> {selectedProduct.local_product.brand}</Text>
                        </div>
                      )}
                    </>
                  ) : (
                    <Empty 
                      description="Nu există produs local asociat"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  )}
                </Card>
              </Col>
            </Row>

            {selectedProduct.confidence_score && (
              <>
                <Divider />
                <Card title="Informații Matching" size="small">
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic
                        title="Scor Potrivire"
                        value={Math.round(selectedProduct.confidence_score * 100)}
                        suffix="%"
                        valueStyle={{
                          color: getConfidenceColor(selectedProduct.confidence_score)
                        }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="Status"
                        value={selectedProduct.manual_confirmed ? 'Confirmat' : 'Pending'}
                        valueStyle={{
                          color: selectedProduct.manual_confirmed ? '#52c41a' : '#faad14'
                        }}
                      />
                    </Col>
                  </Row>
                </Card>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SupplierMatchingPage;
