import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Modal,
  Descriptions,
  Alert,
  Progress,
  Tabs,
  App,
  Typography,
  Input,
  Checkbox,
  Divider,
} from 'antd';
import {
  CloudUploadOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  GoogleOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const { Text } = Typography;
const { Search } = Input;

// Interfaces
interface ProductStatistics {
  total_products: number;
  active_products: number;
  inactive_products: number;
  priced_products: number;
  unpriced_products: number;
}

interface Product {
  id: number;
  sku: string;
  name: string;
  base_price: number;
  currency: string;
  is_active: boolean;
  display_order: number | null;
  image_url: string | null;
  brand: string | null;
  ean: string | null;
  weight_kg: number | null;
  manufacturer: string | null;
}

interface ProductChange {
  field: string;
  old_value: string | null;
  new_value: string | null;
}

interface PreviewProduct {
  sku: string;
  name: string;
  price?: number;
  changes?: ProductChange[];
}

interface ImportPreview {
  total_rows: number;
  new_products: PreviewProduct[];
  updated_products: PreviewProduct[];
  unchanged_products: PreviewProduct[];
  errors: any[];
}

interface ImportLog {
  id: number;
  import_type: string;
  source_name: string;
  total_rows: number;
  successful_imports: number;
  failed_imports: number;
  skipped_rows: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  initiated_by: string | null;
}

interface ImportResponse {
  import_id: number;
  status: string;
  total_rows: number;
  successful_imports: number;
  failed_imports: number;
  auto_mapped_main: number;
  auto_mapped_fbe: number;
  unmapped_products: number;
  duration_seconds: number | null;
  error_message: string | null;
}

interface ProductSupplier {
  id: number;
  sku: string;
  supplier_name: string;
  price_cny: number;
  calculated_price_ron: number | null;
  exchange_rate_cny_ron: number | null;
  supplier_contact: string | null;
  supplier_url: string | null;
  supplier_notes: string | null;
  is_preferred: boolean;
  is_verified: boolean;
  last_imported_at: string | null;
}

interface SupplierStatistics {
  total_supplier_entries: number;
  unique_skus_with_suppliers: number;
  unique_supplier_names: number;
  avg_suppliers_per_sku: number;
}

const ProductImport: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { message: messageApi, modal } = App.useApp();
  
  // State
  const [statistics, setStatistics] = useState<ProductStatistics | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [importHistory, setImportHistory] = useState<ImportLog[]>([]);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [activeOnly, setActiveOnly] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'connected' | 'error'>('unknown');
  const [updateExisting, setUpdateExisting] = useState(true);
  const [createNew, setCreateNew] = useState(true);
  const [importSuppliers, setImportSuppliers] = useState(true);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [suppliersModalVisible, setSuppliersModalVisible] = useState(false);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);
  const [suppliers, setSuppliers] = useState<ProductSupplier[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [supplierStats, setSupplierStats] = useState<SupplierStatistics | null>(null);
  const [productsSource, setProductsSource] = useState<'google_sheets' | 'local_db' | null>(null);
  const [importProgress, setImportProgress] = useState<number>(0);
  const [importStatus, setImportStatus] = useState<string>('');

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      testConnection();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && searchTerm !== undefined) {
      loadProducts();
    }
  }, [searchTerm, activeOnly, isAuthenticated]);

  const loadData = async () => {
    await Promise.all([
      loadStatistics(),
      loadProducts(),
      loadImportHistory(),
      loadSupplierStatistics(),
    ]);
  };

  const loadStatistics = async () => {
    try {
      const response = await api.get('/products/update/statistics');
      setStatistics(response.data);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  const loadProducts = async () => {
    setLoading(true);
    try {
      // First try to load from Google Sheets directly
      try {
        const sheetsResponse = await api.get('/products/update/google-sheets-products', {
          params: { limit: 100 }
        });
        if (sheetsResponse.data && sheetsResponse.data.length > 0) {
          // Transform Google Sheets data to match Product interface
          const transformedProducts = sheetsResponse.data.map((p: any) => ({
            id: p.row_number,
            sku: p.sku,
            name: p.romanian_name,
            base_price: p.emag_fbe_ro_price_ron || 0,
            currency: 'RON',
            is_active: true,
            display_order: null,
            image_url: null,
            brand: null,
            ean: null,
            weight_kg: null,
            manufacturer: null,
          }));
          setProducts(transformedProducts);
          setProductsSource('google_sheets');
          return;
        }
      } catch (sheetsError) {
        console.warn('Could not load from Google Sheets, falling back to local products:', sheetsError);
      }

      // Fallback to local database products
      const params: any = { limit: 100 };
      if (searchTerm) {
        params.search = searchTerm;
      }
      if (activeOnly) {
        params.active_only = true;
      }
      const response = await api.get('/products/update/products', { params });
      setProducts(response.data);
      setProductsSource('local_db');
    } catch (error) {
      console.error('Failed to load products:', error);
      setProductsSource(null);
    } finally {
      setLoading(false);
    }
  };

  const loadImportHistory = async () => {
    try {
      const response = await api.get('/products/update/history', {
        params: { limit: 10 }
      });
      setImportHistory(response.data);
    } catch (error) {
      console.error('Failed to load import history:', error);
    }
  };

  const loadSupplierStatistics = async () => {
    try {
      const response = await api.get('/products/import/suppliers-statistics');
      setSupplierStats(response.data);
    } catch (error) {
      console.error('Failed to load supplier statistics:', error);
    }
  };

  const loadSuppliersForSku = async (sku: string) => {
    setLoadingSuppliers(true);
    try {
      const response = await api.get(`/products/import/suppliers/${sku}`);
      setSuppliers(response.data);
      setSelectedSku(sku);
      setSuppliersModalVisible(true);
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || 'Failed to load suppliers');
    } finally {
      setLoadingSuppliers(false);
    }
  };

  const testConnection = async () => {
    try {
      const response = await api.get('/products/update/test-connection');
      if (response.data.status === 'connected') {
        setConnectionStatus('connected');
        messageApi.success('Google Sheets connection successful');
      }
    } catch (error: any) {
      setConnectionStatus('error');
      
      // Show specific error message based on status code
      if (error.response?.status === 401) {
        messageApi.error('Authentication required. Please login first.');
      } else if (error.response?.status === 500) {
        messageApi.error('Google Sheets connection failed. Check service_account.json configuration.');
      } else {
        messageApi.error(error.response?.data?.detail || 'Connection test failed');
      }
      
      console.error('Connection test failed:', error);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      const response = await api.get<ImportPreview>('/products/update/preview');
      setPreview(response.data);
      setPreviewVisible(true);
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || 'Preview failed');
    } finally {
      setPreviewing(false);
    }
  };

  const handleImport = async () => {
    modal.confirm({
      title: 'Import Products from Google Sheets',
      content: (
        <div>
          <p>This will import products from Google Sheets and update your local database.</p>
          <Space direction="vertical" style={{ marginTop: 16, width: '100%' }}>
            <Checkbox checked={updateExisting} onChange={(e) => setUpdateExisting(e.target.checked)}>
              Update existing products
            </Checkbox>
            <Checkbox checked={createNew} onChange={(e) => setCreateNew(e.target.checked)}>
              Create new products
            </Checkbox>
            <Divider style={{ margin: '12px 0' }} />
            <Checkbox 
              checked={importSuppliers} 
              onChange={(e) => setImportSuppliers(e.target.checked)}
              style={{ fontWeight: 'bold' }}
            >
              Import suppliers from "Product_Suppliers" sheet
            </Checkbox>
            <Alert
              message="Includes: prices, Chinese names, specifications, URLs"
              type="info"
              showIcon
              style={{ marginTop: 8 }}
            />
          </Space>
          <Alert
            message="Make sure service_account.json is configured"
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        </div>
      ),
      okText: 'Start Import',
      cancelText: 'Cancel',
      onOk: async () => {
        setImporting(true);
        setImportProgress(0);
        setImportStatus('Connecting to Google Sheets...');
        
        try {
          // Show progress message
          messageApi.loading({ content: 'Starting import...', key: 'import', duration: 0 });
          
          setImportStatus('Fetching products from Google Sheets...');
          setImportProgress(10);
          
          const response = await api.post<ImportResponse>('/products/import/google-sheets', {
            auto_map: true,
            import_suppliers: importSuppliers
          });
          
          setImportProgress(100);
          setImportStatus('Import completed!');
          messageApi.destroy('import');
          
          const result = response.data;
          
          modal.success({
            title: '✅ Import Completed Successfully',
            width: 600,
            content: (
              <div>
                <Alert
                  message="Import Summary"
                  description={
                    <Descriptions column={2} size="small" style={{ marginTop: 12 }}>
                      <Descriptions.Item label="Total Rows" span={2}>{result.total_rows}</Descriptions.Item>
                      <Descriptions.Item label="✅ Successful">{result.successful_imports}</Descriptions.Item>
                      <Descriptions.Item label="❌ Failed">{result.failed_imports}</Descriptions.Item>
                      <Descriptions.Item label="🆕 Created">{result.auto_mapped_main || 0}</Descriptions.Item>
                      <Descriptions.Item label="🔄 Updated">{result.auto_mapped_fbe || 0}</Descriptions.Item>
                      {result.duration_seconds && (
                        <Descriptions.Item label="⏱️ Duration" span={2}>
                          {result.duration_seconds.toFixed(2)} seconds
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  }
                  type="success"
                  showIcon
                />
                {result.failed_imports > 0 && (
                  <Alert
                    message="Some products failed to import"
                    description="Check the logs for details about failed imports."
                    type="warning"
                    showIcon
                    style={{ marginTop: 16 }}
                  />
                )}
              </div>
            ),
          });
          
          await loadData();
        } catch (error: any) {
          messageApi.destroy('import');
          setImportProgress(0);
          setImportStatus('');
          
          const errorMessage = error.response?.data?.detail || error.message || 'Import failed';
          const errorTitle = '❌ Import Failed';
          
          modal.error({
            title: errorTitle,
            content: (
              <div>
                <p style={{ marginBottom: '12px', color: '#ff4d4f' }}>
                  <strong>Error:</strong> {errorMessage}
                </p>
                {error.response?.status && (
                  <p style={{ fontSize: '12px', color: '#8c8c8c' }}>
                    Status Code: {error.response.status}
                  </p>
                )}
                <p style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '8px' }}>
                  Please check the console logs for more details or contact support if the issue persists.
                </p>
              </div>
            ),
          });
          
          // Also show a brief message notification
          messageApi.error(`Import failed: ${errorMessage.substring(0, 100)}${errorMessage.length > 100 ? '...' : ''}`);
        } finally {
          setImporting(false);
        }
      },
    });
  };

  const productColumns: ColumnsType<Product> = [
    {
      title: 'Ordine',
      dataIndex: 'display_order',
      key: 'display_order',
      width: 80,
      sorter: (a, b) => {
        if (a.display_order === null && b.display_order === null) return 0;
        if (a.display_order === null) return 1;
        if (b.display_order === null) return -1;
        return a.display_order - b.display_order;
      },
      render: (order) => order !== null ? <Tag color="blue">{order}</Tag> : <Tag>-</Tag>,
    },
    {
      title: 'Imagine',
      dataIndex: 'image_url',
      key: 'image_url',
      width: 80,
      render: (url) => url ? (
        <img 
          src={url} 
          alt="Product" 
          style={{ width: 50, height: 50, objectFit: 'cover', borderRadius: 4 }}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      fixed: 'left',
      width: 120,
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Product Name',
      dataIndex: 'name',
      key: 'name',
      width: 400,
      ellipsis: true,
    },
    {
      title: 'Price',
      dataIndex: 'base_price',
      key: 'base_price',
      width: 120,
      render: (price, record) => `${price.toFixed(2)} ${record.currency}`,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Brand',
      dataIndex: 'brand',
      key: 'brand',
      width: 150,
      render: (brand) => brand || '-',
    },
    {
      title: 'EAN',
      dataIndex: 'ean',
      key: 'ean',
      width: 140,
      render: (ean) => ean ? <Text code>{ean}</Text> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Greutate',
      dataIndex: 'weight_kg',
      key: 'weight_kg',
      width: 100,
      render: (weight) => weight !== null ? `${weight} kg` : <Text type="secondary">-</Text>,
    },
    {
      title: 'Furnizori',
      key: 'suppliers',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => loadSuppliersForSku(record.sku)}
          loading={loadingSuppliers && selectedSku === record.sku}
        >
          Vezi furnizori
        </Button>
      ),
    },
  ];

  const historyColumns: ColumnsType<ImportLog> = [
    {
      title: 'Date',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: 'Source',
      dataIndex: 'source_name',
      key: 'source_name',
    },
    {
      title: 'Total',
      dataIndex: 'total_rows',
      key: 'total_rows',
    },
    {
      title: 'Success',
      dataIndex: 'successful_imports',
      key: 'successful_imports',
      render: (value) => <Tag color="success">{value}</Tag>,
    },
    {
      title: 'Failed',
      dataIndex: 'failed_imports',
      key: 'failed_imports',
      render: (value) => value > 0 ? <Tag color="error">{value}</Tag> : <Tag>{value}</Tag>,
    },
    {
      title: 'Skipped',
      dataIndex: 'skipped_rows',
      key: 'skipped_rows',
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (seconds) => seconds ? `${seconds.toFixed(2)}s` : '-',
    },
  ];

  if (!isAuthenticated) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="Authentication Required"
          description="Please log in to access the Product Import feature."
          type="warning"
          showIcon
        />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1>
          <GoogleOutlined style={{ marginRight: '8px' }} />
          Product Import from Google Sheets
        </h1>
        <p style={{ color: '#666' }}>
          Import and update products from Google Sheets to your local database
        </p>
      </div>

      {/* Connection Status */}
      <Alert
        message={
          connectionStatus === 'connected' ? 'Google Sheets Connected' :
          connectionStatus === 'error' ? 'Connection Error' :
          'Connection Status Unknown'
        }
        description={
          connectionStatus === 'connected' ? 'Successfully connected to Google Sheets API' :
          connectionStatus === 'error' ? 'Failed to connect. Check service_account.json configuration' :
          'Testing connection...'
        }
        type={connectionStatus === 'connected' ? 'success' : connectionStatus === 'error' ? 'error' : 'info'}
        showIcon
        style={{ marginBottom: '24px' }}
        action={
          <Button size="small" onClick={testConnection}>
            <SyncOutlined /> Test Again
          </Button>
        }
      />

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        {statistics && (
          <>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Total Products"
                  value={statistics.total_products}
                  prefix={<DatabaseOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Active Products"
                  value={statistics.active_products}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
                <Progress
                  percent={statistics.total_products > 0 ? (statistics.active_products / statistics.total_products * 100) : 0}
                  size="small"
                  status="active"
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Priced Products"
                  value={statistics.priced_products}
                  prefix={<InfoCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Unpriced Products"
                  value={statistics.unpriced_products}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
          </>
        )}
      </Row>

      {/* Supplier Statistics */}
      {supplierStats && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Suppliers"
                value={supplierStats.total_supplier_entries}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="SKUs with Suppliers"
                value={supplierStats.unique_skus_with_suppliers}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unique Supplier Names"
                value={supplierStats.unique_supplier_names}
                prefix={<InfoCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Avg Suppliers/SKU"
                value={supplierStats.avg_suppliers_per_sku}
                precision={2}
                prefix={<InfoCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Import Actions */}
      <Card style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Button
              type="default"
              size="large"
              icon={<EyeOutlined />}
              onClick={handlePreview}
              loading={previewing}
              disabled={connectionStatus !== 'connected' || importing}
            >
              Preview Changes
            </Button>
            <Button
              type="primary"
              size="large"
              icon={<CloudUploadOutlined />}
              onClick={handleImport}
              loading={importing}
              disabled={connectionStatus !== 'connected'}
            >
              Import Products & Suppliers
            </Button>
            <Button
              icon={<SyncOutlined />}
              onClick={loadData}
              loading={loading}
              disabled={importing}
            >
              Refresh
            </Button>
          </Space>
          {importing && (
            <div style={{ width: '100%' }}>
              <Progress 
                percent={importProgress} 
                status="active"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              {importStatus && (
                <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
                  {importStatus}
                </Text>
              )}
            </div>
          )}
        </Space>
      </Card>

      {/* Tabs */}
      <Tabs
        defaultActiveKey="products"
        type="card"
        items={[
          {
            key: 'products',
            label: (
              <span>
                <DatabaseOutlined />
                <span style={{ marginLeft: 8 }}>Products</span>
              </span>
            ),
            children: (
              <Card>
                <Space style={{ marginBottom: '16px', width: '100%' }} direction="vertical">
                  <Space>
                    <Search
                      placeholder="Search by SKU or name"
                      allowClear
                      style={{ width: 300 }}
                      onSearch={setSearchTerm}
                      onChange={(e) => !e.target.value && setSearchTerm('')}
                    />
                    <Checkbox
                      checked={activeOnly}
                      onChange={(e) => setActiveOnly(e.target.checked)}
                    >
                      Active only
                    </Checkbox>
                  </Space>
                  {productsSource && (
                    <Alert
                      message={
                        productsSource === 'google_sheets' 
                          ? 'Showing products from Google Sheets (not yet imported)'
                          : 'Showing products from local database'
                      }
                      type={productsSource === 'google_sheets' ? 'info' : 'success'}
                      showIcon
                      closable
                    />
                  )}
                </Space>

                <Table
                  columns={productColumns}
                  dataSource={products}
                  rowKey="id"
                  loading={loading}
                  scroll={{ x: 1000 }}
                  pagination={{
                    pageSize: 50,
                    showSizeChanger: true,
                    showTotal: (total) => `Total ${total} products`,
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'history',
            label: (
              <span>
                <HistoryOutlined />
                <span style={{ marginLeft: 8 }}>Import History</span>
              </span>
            ),
            children: (
              <Card>
                <Table
                  columns={historyColumns}
                  dataSource={importHistory}
                  rowKey="id"
                  pagination={false}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Preview Modal */}
      <Modal
        title="Import Preview"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Close
          </Button>,
          <Button
            key="import"
            type="primary"
            icon={<CloudUploadOutlined />}
            onClick={() => {
              setPreviewVisible(false);
              handleImport();
            }}
          >
            Proceed with Import
          </Button>,
        ]}
      >
        {preview && (
          <div>
            <Alert
              message={`Total: ${preview.total_rows} rows from Google Sheets`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Divider>Summary</Divider>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="New Products"
                  value={preview.new_products.length}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="To Update"
                  value={preview.updated_products.length}
                  prefix={<InfoCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Unchanged"
                  value={preview.unchanged_products.length}
                  prefix={<CheckCircleOutlined />}
                />
              </Col>
            </Row>

            {preview.errors.length > 0 && (
              <>
                <Divider>Warnings & Errors</Divider>
                <Alert
                  message={`${preview.errors.length} issue(s) found`}
                  description={
                    <ul style={{ marginBottom: 0 }}>
                      {preview.errors.slice(0, 10).map((err, idx) => (
                        <li key={idx}>
                          {err.sku && <strong>[{err.sku}]</strong>} Row {err.row}: {err.error}
                        </li>
                      ))}
                      {preview.errors.length > 10 && <li>... and {preview.errors.length - 10} more</li>}
                    </ul>
                  }
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Note: Products with long names will be automatically truncated to 255 characters during import.
                </Text>
              </>
            )}

            {preview.new_products.length > 0 && (
              <>
                <Divider>New Products (showing first 5)</Divider>
                <Table
                  size="small"
                  dataSource={preview.new_products.slice(0, 5)}
                  rowKey="sku"
                  pagination={false}
                  columns={[
                    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
                    { title: 'Name', dataIndex: 'name', key: 'name' },
                    { title: 'Price', dataIndex: 'price', key: 'price', render: (p) => p ? `${p.toFixed(2)} RON` : '-' },
                  ]}
                />
              </>
            )}

            {preview.updated_products.length > 0 && (
              <>
                <Divider>Products to Update (showing first 5)</Divider>
                <Table
                  size="small"
                  dataSource={preview.updated_products.slice(0, 5)}
                  rowKey="sku"
                  pagination={false}
                  columns={[
                    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
                    { title: 'Name', dataIndex: 'name', key: 'name' },
                    {
                      title: 'Changes',
                      dataIndex: 'changes',
                      key: 'changes',
                      render: (changes: ProductChange[]) => (
                        <Space direction="vertical" size="small">
                          {changes?.map((change, idx) => (
                            <Text key={idx} type="secondary" style={{ fontSize: 12 }}>
                              {change.field}: {change.old_value} → {change.new_value}
                            </Text>
                          ))}
                        </Space>
                      ),
                    },
                  ]}
                />
              </>
            )}
          </div>
        )}
      </Modal>

      {/* Suppliers Modal */}
      <Modal
        title={`Furnizori pentru SKU: ${selectedSku}`}
        open={suppliersModalVisible}
        onCancel={() => setSuppliersModalVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setSuppliersModalVisible(false)}>
            Close
          </Button>,
        ]}
      >
        {suppliers.length > 0 ? (
          <Table
            dataSource={suppliers}
            rowKey="id"
            pagination={false}
            size="small"
            columns={[
              {
                title: 'Supplier',
                dataIndex: 'supplier_name',
                key: 'supplier_name',
                render: (name, record) => (
                  <div>
                    <strong>{name}</strong>
                    {record.is_preferred && <Tag color="gold" style={{ marginLeft: 8 }}>Preferred</Tag>}
                    {record.is_verified && <Tag color="green" style={{ marginLeft: 8 }}>Verified</Tag>}
                  </div>
                ),
              },
              {
                title: 'Price (CNY)',
                dataIndex: 'price_cny',
                key: 'price_cny',
                render: (price) => `¥${price.toFixed(2)}`,
                sorter: (a, b) => a.price_cny - b.price_cny,
              },
              {
                title: 'Price (RON)',
                dataIndex: 'calculated_price_ron',
                key: 'calculated_price_ron',
                render: (price, record) => {
                  if (price) {
                    return (
                      <div>
                        <div>{price.toFixed(2)} RON</div>
                        {record.exchange_rate_cny_ron && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            Rate: {record.exchange_rate_cny_ron.toFixed(4)}
                          </Text>
                        )}
                      </div>
                    );
                  }
                  return <Text type="secondary">-</Text>;
                },
              },
              {
                title: 'Contact',
                dataIndex: 'supplier_contact',
                key: 'supplier_contact',
                render: (contact) => contact || <Text type="secondary">-</Text>,
              },
              {
                title: 'URL',
                dataIndex: 'supplier_url',
                key: 'supplier_url',
                render: (url) => url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    Link
                  </a>
                ) : <Text type="secondary">-</Text>,
              },
              {
                title: 'Last Updated',
                dataIndex: 'last_imported_at',
                key: 'last_imported_at',
                render: (date) => date ? new Date(date).toLocaleDateString() : '-',
              },
            ]}
            expandable={{
              expandedRowRender: (record) => (
                <div style={{ padding: '8px 16px' }}>
                  {record.supplier_notes && (
                    <div>
                      <strong>Notes:</strong>
                      <p style={{ marginTop: 4 }}>{record.supplier_notes}</p>
                    </div>
                  )}
                  {!record.supplier_notes && (
                    <Text type="secondary">No additional notes</Text>
                  )}
                </div>
              ),
              rowExpandable: (record) => !!record.supplier_notes,
            }}
          />
        ) : (
          <Alert
            message="No suppliers found"
            description={
              <div>
                <p>This product doesn't have any suppliers configured in Google Sheets.</p>
                <p style={{ marginTop: 8, marginBottom: 0 }}>
                  <strong>To add suppliers:</strong>
                </p>
                <ol style={{ marginTop: 4, paddingLeft: 20 }}>
                  <li>Open Google Sheets "Product_Suppliers" tab</li>
                  <li>Add row with: SKU, Supplier_Name, Price_CNY</li>
                  <li>Run import again</li>
                </ol>
              </div>
            }
            type="info"
            showIcon
          />
        )}
      </Modal>
    </div>
  );
};

export default ProductImport;
