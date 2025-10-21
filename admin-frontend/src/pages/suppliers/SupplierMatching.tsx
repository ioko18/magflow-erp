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
  App as AntApp,
  Input,
  InputNumber,
  Upload,
  Dropdown
} from 'antd';
import {
  LinkOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  ShoppingOutlined,
  TeamOutlined,
  GlobalOutlined,
  BarChartOutlined,
  SyncOutlined,
  WarningOutlined,
  SearchOutlined,
  InboxOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  UploadOutlined,
  FilterOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { logError } from '../../utils/errorLogger';

const { Title, Text } = Typography;
const { Option } = Select;
const { Dragger } = Upload;

// Constants for sizes and dimensions
const SIZES = {
  IMAGE_THUMBNAIL: 160,
  IMAGE_PREVIEW: 200,
  MODAL_WIDTH: 1000,
  MODAL_WIDTH_MATCH: 800,
  MODAL_TOP: 20,
  TABLE_SCROLL_X: 1330, // Optimized - price integrated in product column
  COLUMN_WIDTH: {
    IMAGE: 160,
    PRODUCT_NAME: 320,
    PRICE: 110,
    STATUS: 40,
    LOCAL_PRODUCT: 300,
    ACTIONS: 140,
  },
} as const;

interface Supplier {
  id: number;
  name: string;
  country: string;
  is_active: boolean;
  display_order?: number;
}

interface LocalProduct {
  id: number;
  name: string;
  chinese_name?: string;
  sku: string;
  brand?: string;
  image_url?: string;
}

interface SupplierProduct {
  id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_product_name: string;
  supplier_product_chinese_name?: string;
  supplier_product_specification?: string;
  supplier_product_url: string;
  supplier_image_url: string;
  supplier_price: number;
  supplier_currency: string;
  confidence_score: number;
  manual_confirmed: boolean;
  local_product_id?: number;
  local_product?: LocalProduct;
  is_active: boolean;
  import_source?: string;
  created_at: string;
  // Token analysis fields
  common_tokens?: string[];
  common_tokens_count?: number;
  search_tokens_count?: number;
  product_tokens_count?: number;
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
  const [products, setProducts] = useState<SupplierProduct[]>([]);
  const [localProducts, setLocalProducts] = useState<LocalProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [statisticsLoading, setStatisticsLoading] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<number | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<SupplierProduct | null>(null);
  const [matchModalVisible, setMatchModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'unmatched' | 'pending' | 'confirmed'>('all');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  
  // New states for improvements
  const [searchTerm, setSearchTerm] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 1000]);
  const [minConfidence, setMinConfidence] = useState(0);
  const [_priceComparisons, setPriceComparisons] = useState<Record<number, any>>({});

  useEffect(() => {
    loadSuppliers();
    loadLocalProducts();
  }, []);

  useEffect(() => {
    if (selectedSupplier) {
      loadProducts();
      loadStatistics();
    }
  }, [selectedSupplier, pagination.current, pagination.pageSize, statusFilter]);

  // Load price comparisons for matched products
  useEffect(() => {
    const loadPriceComparisons = async () => {
      const matchedProducts = products.filter(p => p.local_product_id);
      const uniqueLocalProductIds = [...new Set(matchedProducts.map(p => p.local_product_id))];
      
      const comparisons: Record<number, any> = {};
      
      for (const localProductId of uniqueLocalProductIds) {
        if (localProductId) {
          try {
            const response = await api.get(`/suppliers/products/${localProductId}/price-comparison`);
            if (response.data?.data) {
              comparisons[localProductId] = response.data.data;
            }
          } catch (error) {
            logError(error as Error, { component: 'SupplierMatching', action: 'loadPriceComparison', productId: localProductId });
          }
        }
      }
      
      setPriceComparisons(comparisons);
    };
    
    if (products.length > 0) {
      loadPriceComparisons();
    }
  }, [products]);

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
      logError(error as Error, { component: 'SupplierMatching', action: 'loadSuppliers' });
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
      logError(error as Error, { component: 'SupplierMatching', action: 'loadLocalProducts' });
    }
  };

  const loadProducts = async () => {
    if (!selectedSupplier) return;

    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      // Use server-side filtering for better performance with pagination
      const response = await api.get(`/suppliers/${selectedSupplier}/products`, {
        params: {
          skip,
          limit: pagination.pageSize,
          status: statusFilter === 'all' ? undefined : statusFilter, // Server-side filter
          include_tokens: true, // Request token analysis
        }
      });

      const data = response.data?.data;
      setProducts(data?.products || []);
      setPagination(prev => ({
        ...prev,
        total: data?.pagination?.total || 0,
      }));
    } catch (error) {
      logError(error as Error, { component: 'SupplierMatching', action: 'loadProducts', supplierId: selectedSupplier });
      message.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    if (!selectedSupplier) return;

    try {
      setStatisticsLoading(true);
      const response = await api.get(`/suppliers/${selectedSupplier}/matching/statistics`);
      setStatistics(response.data?.data || null);
    } catch (error) {
      logError(error as Error, { component: 'SupplierMatching', action: 'loadStatistics', supplierId: selectedSupplier });
    } finally {
      setStatisticsLoading(false);
    }
  };

  // Auto-match functionality has been disabled - only manual matching is allowed

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
      await loadProducts();
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
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la confirmarea match-ului');
    }
  };

  const handleUnmatch = async (supplierProduct: SupplierProduct) => {
    try {
      await api.delete(`/suppliers/${supplierProduct.supplier_id}/products/${supplierProduct.id}/match`);
      
      message.success('Match șters cu succes!');
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la ștergerea match-ului');
    }
  };

  const handleBulkConfirm = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Selectează cel puțin un produs');
      return;
    }

    const selectedProducts = products.filter((p: SupplierProduct) => 
      selectedRowKeys.includes(p.id) && p.local_product_id && !p.manual_confirmed
    );

    if (selectedProducts.length === 0) {
      message.warning('Niciun produs pending selectat');
      return;
    }

    if (!selectedSupplier) return;

    try {
      setLoading(true);
      
      // Use bulk endpoint for better performance
      await api.post(`/suppliers/${selectedSupplier}/products/bulk-confirm`, {
        product_ids: selectedProducts.map(p => p.id)
      });
      
      message.success(`${selectedProducts.length} match-uri confirmate cu succes!`);
      setSelectedRowKeys([]);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Eroare la confirmarea bulk');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkUnmatch = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Selectează cel puțin un produs');
      return;
    }

    const selectedProducts = products.filter((p: SupplierProduct) => 
      selectedRowKeys.includes(p.id) && p.local_product_id
    );

    if (selectedProducts.length === 0) {
      message.warning('Niciun produs matchat selectat');
      return;
    }

    if (!selectedSupplier) return;

    Modal.confirm({
      title: `Șterge ${selectedProducts.length} match-uri?`,
      content: 'Ești sigur că vrei să ștergi match-urile selectate?',
      okText: 'Da, șterge',
      cancelText: 'Anulează',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setLoading(true);
          
          // Use bulk endpoint for better performance
          await api.post(`/suppliers/${selectedSupplier}/products/bulk-unmatch`, {
            product_ids: selectedProducts.map(p => p.id)
          });
          
          message.success(`${selectedProducts.length} match-uri șterse cu succes!`);
          setSelectedRowKeys([]);
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la ștergerea bulk');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const handleUnmatchAllPending = async () => {
    if (!selectedSupplier) return;

    Modal.confirm({
      title: 'Șterge toate match-urile pending',
      content: 'Aceasta va șterge toate match-urile pending (neconfirmate). Match-urile confirmate manual vor rămâne neschimbate. Continui?',
      okText: 'Da, Șterge',
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
          
          message.success(`${pendingMatches.length} match-uri pending șterse cu succes`);
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Eroare la ștergerea match-urilor');
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

  // New functions for improvements
  const handleQuickSearch = async (value: string) => {
    if (!value || !value.trim()) {
      // Dacă căutarea e goală, reîncarcă toate produsele
      loadProducts();
      return;
    }
    
    if (!selectedSupplier) {
      message.warning('Selectează un furnizor mai întâi');
      return;
    }
    
    try {
      setSearchLoading(true);
      setLoading(true);
      
      const response = await api.post(`/suppliers/${selectedSupplier}/products/jieba-search`, {
        search_term: value,
        threshold: 0.3,
        limit: 50
      });
      
      if (response.data?.data?.matches && response.data.data.matches.length > 0) {
        // ACTUALIZEAZĂ TABELUL cu rezultatele găsite
        setProducts(response.data.data.matches);
        setPagination(prev => ({
          ...prev,
          total: response.data.data.matches.length,
        }));
        message.success(`Găsite ${response.data.data.matches.length} rezultate`);
      } else {
        // Niciun rezultat - arată tabel gol
        setProducts([]);
        setPagination(prev => ({
          ...prev,
          total: 0,
        }));
        message.info('Nu s-au găsit rezultate');
      }
    } catch (error) {
      logError(error as Error, { component: 'SupplierMatching', action: 'handleSearch', searchTerm });
      message.error('Eroare la căutare');
    } finally {
      setSearchLoading(false);
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!selectedSupplier) {
      message.error('Selectează un furnizor mai întâi');
      return false;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadLoading(true);
      const response = await api.post(
        `/suppliers/${selectedSupplier}/products/import-excel`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      message.success(`Import reușit! ${response.data?.data?.imported_count || 0} produse importate`);
      await loadProducts();
      await loadStatistics();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Eroare la import');
    } finally {
      setUploadLoading(false);
    }

    return false; // Prevent default upload behavior
  };

  const handleExport = async (format: 'csv' | 'excel') => {
    if (!selectedSupplier) {
      message.error('Selectează un furnizor mai întâi');
      return;
    }

    try {
      const response = await api.get(`/suppliers/${selectedSupplier}/products/export`, {
        params: {
          format,
          status: statusFilter === 'all' ? undefined : statusFilter,
          include_tokens: true
        },
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `products_${selectedSupplier}_${Date.now()}.${format === 'csv' ? 'csv' : 'xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.success('Export realizat cu succes!');
    } catch (error) {
      message.error('Eroare la export');
    }
  };

  const columns: ColumnsType<SupplierProduct> = [
    {
      title: 'Imagine',
      key: 'image',
      width: SIZES.COLUMN_WIDTH.IMAGE,
      render: (_, record) => (
        <Image
          src={record.supplier_image_url}
          alt={record.supplier_product_name}
          width={SIZES.IMAGE_THUMBNAIL}
          height={SIZES.IMAGE_THUMBNAIL}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="/placeholder-product.png"
          preview={{
            src: record.supplier_image_url,
          }}
        />
      ),
    },
    {
      title: 'Produs Furnizor (Chinezește)',
      key: 'supplier_product',
      width: SIZES.COLUMN_WIDTH.PRODUCT_NAME,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: '13px', color: '#1890ff' }}>
            {record.supplier_product_chinese_name || record.supplier_product_name}
          </Text>
          {record.supplier_product_specification && (
            <Tag color="green" style={{ fontSize: '11px' }}>
              {record.supplier_product_specification}
            </Tag>
          )}
          <a 
            href={record.supplier_product_url} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ fontSize: '12px' }}
          >
            <GlobalOutlined style={{ marginRight: 4 }} />
            Vezi pe 1688.com
          </a>
          <Text strong style={{ fontSize: '13px', color: '#52c41a' }}>
            Preț: {record.supplier_price.toFixed(2)} {record.supplier_currency}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Status Matching',
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {record.local_product_id ? (
            <>
              <Tag 
                color={record.manual_confirmed ? 'green' : 'orange'}
                icon={record.manual_confirmed ? <CheckCircleOutlined /> : <WarningOutlined />}
                style={{ width: '100%', textAlign: 'center' }}
              >
                {record.manual_confirmed ? 'Confirmat' : 'Pending'}
              </Tag>
              {record.confidence_score !== null && record.confidence_score !== undefined && (
                <div style={{ width: '100%' }}>
                  <Progress 
                    percent={Math.round(record.confidence_score * 100)} 
                    size="small"
                    strokeColor={getConfidenceColor(record.confidence_score)}
                    format={(percent) => `${percent}%`}
                  />
                </div>
              )}
            </>
          ) : (
            <Tag 
              color="red" 
              icon={<CloseCircleOutlined />}
              style={{ width: '100%', textAlign: 'center' }}
            >
              Nematchat
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Imagine Produs Local',
      key: 'local_product_image',
      width: 170,
      render: (_, record) => (
        record.local_product?.image_url ? (
          <Image
            src={record.local_product.image_url}
            alt={record.local_product.name}
            width={SIZES.IMAGE_THUMBNAIL}
            height={SIZES.IMAGE_THUMBNAIL}
            style={{ objectFit: 'cover', borderRadius: '4px' }}
            fallback="/placeholder-product.png"
            preview={{
              src: record.local_product.image_url,
            }}
          />
        ) : (
          <div style={{ 
            width: SIZES.IMAGE_THUMBNAIL, 
            height: SIZES.IMAGE_THUMBNAIL, 
            background: '#f0f0f0', 
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#999'
          }}>
            <Text type="secondary" style={{ fontSize: '10px' }}>No Image</Text>
          </div>
        )
      ),
    },
    {
      title: 'Produs Local Asociat',
      key: 'local_product',
      width: SIZES.COLUMN_WIDTH.LOCAL_PRODUCT,
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
      width: SIZES.COLUMN_WIDTH.ACTIONS,
      render: (_, record) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {/* Vezi detalii - întotdeauna vizibil */}
          <Tooltip title="Vezi detalii produs">
            <Button
              type="default"
              icon={<EyeOutlined />}
              onClick={() => viewProductDetails(record)}
              size="small"
              block
            >
              Vezi detalii
            </Button>
          </Tooltip>

          {/* Match manual - doar pentru produse nematchate */}
          {!record.local_product_id ? (
            <Tooltip title="Asociază cu produs local">
              <Button
                type="primary"
                size="small"
                icon={<LinkOutlined />}
                onClick={() => handleManualMatch(record)}
                block
              >
                Match Manual
              </Button>
            </Tooltip>
          ) : (
            <>
              {/* Confirmă - doar pentru produse pending */}
              {!record.manual_confirmed && (
                <Tooltip title="Confirmă match-ul automat">
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleConfirmPendingMatch(record)}
                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    block
                  >
                    Confirmă
                  </Button>
                </Tooltip>
              )}
              
              {/* Unmatch - pentru produse matchate */}
              <Tooltip title="Șterge asocierea">
                <Button
                  danger
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={() => handleUnmatch(record)}
                  block
                >
                  Unmatch
                </Button>
              </Tooltip>
            </>
          )}
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
            <Space size="middle" wrap>
              {/* Quick Search */}
              <Input.Search
                placeholder="Caută după nume chinezesc..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onSearch={handleQuickSearch}
                loading={searchLoading}
                style={{ width: 300 }}
                size="large"
                prefix={<SearchOutlined />}
                enterButton
                allowClear
                onClear={() => {
                  setSearchTerm('');
                  loadProducts();
                }}
              />
              
              {/* Export Dropdown */}
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'csv',
                      label: 'Export CSV',
                      icon: <FileExcelOutlined />,
                      onClick: () => handleExport('csv')
                    },
                    {
                      key: 'excel',
                      label: 'Export Excel',
                      icon: <FileExcelOutlined />,
                      onClick: () => handleExport('excel')
                    }
                  ]
                }}
              >
                <Button icon={<DownloadOutlined />} size="large">
                  Export
                </Button>
              </Dropdown>
              
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadProducts}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
              <Tooltip title="Șterge toate match-urile pending (neconfirmate)">
                <Button 
                  icon={<CloseCircleOutlined />} 
                  onClick={handleUnmatchAllPending}
                  loading={loading}
                  size="large"
                  danger
                >
                  Șterge Pending
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Supplier Selection & Filters */}
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
                    </Space>
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col>
            <Space direction="vertical" size={4}>
              <Text strong>Filtrează Status:</Text>
              <Select
                size="large"
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: 200 }}
              >
                <Option value="all">Toate</Option>
                <Option value="unmatched">Nematchate</Option>
                <Option value="pending">Pending</Option>
                <Option value="confirmed">Confirmate</Option>
              </Select>
            </Space>
          </Col>
        </Row>
        
        {/* Advanced Filters - Collapsible */}
        {selectedSupplier && (
          <div style={{ marginTop: '16px' }}>
            <Button
              icon={<FilterOutlined />}
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              style={{ marginBottom: showAdvancedFilters ? '12px' : 0 }}
            >
              {showAdvancedFilters ? 'Ascunde' : 'Arată'} Filtre Avansate
            </Button>
            
            {showAdvancedFilters && (
              <Card size="small" style={{ marginTop: '8px' }}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Space direction="vertical" style={{ width: '100%' }} size={4}>
                      <Text strong>Interval Preț (CNY):</Text>
                      <Space>
                        <InputNumber
                          min={0}
                          max={1000}
                          value={priceRange[0]}
                          onChange={(value) => setPriceRange([value || 0, priceRange[1]])}
                          placeholder="Min"
                        />
                        <Text>-</Text>
                        <InputNumber
                          min={0}
                          max={1000}
                          value={priceRange[1]}
                          onChange={(value) => setPriceRange([priceRange[0], value || 1000])}
                          placeholder="Max"
                        />
                      </Space>
                      <Text type="secondary" style={{ fontSize: '11px' }}>
                        {priceRange[0]} - {priceRange[1]} CNY
                      </Text>
                    </Space>
                  </Col>
                  
                  <Col span={8}>
                    <Space direction="vertical" style={{ width: '100%' }} size={4}>
                      <Text strong>Scor Minim Confidence:</Text>
                      <InputNumber
                        min={0}
                        max={100}
                        value={minConfidence}
                        onChange={(value) => setMinConfidence(value || 0)}
                        formatter={(value) => `${value}%`}
                        parser={(value) => value?.replace('%', '') as unknown as number}
                        style={{ width: '100%' }}
                      />
                      <Text type="secondary" style={{ fontSize: '11px' }}>
                        Minim: {minConfidence}%
                      </Text>
                    </Space>
                  </Col>
                  
                  <Col span={8}>
                    <Space direction="vertical" style={{ width: '100%' }} size={4}>
                      <Text strong>Acțiuni Rapide:</Text>
                      <Space wrap>
                        <Button 
                          size="small" 
                          onClick={() => {
                            setPriceRange([0, 100]);
                            setMinConfidence(70);
                          }}
                        >
                          Ieftine + Încredere Mare
                        </Button>
                        <Button 
                          size="small" 
                          onClick={() => {
                            setPriceRange([0, 1000]);
                            setMinConfidence(0);
                          }}
                        >
                          Reset Filtre
                        </Button>
                      </Space>
                    </Space>
                  </Col>
                </Row>
              </Card>
            )}
          </div>
        )}
      </Card>

      {/* Statistics Cards */}
      {selectedSupplier && (
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
                value={statistics?.total_unmatched}
                loading={statisticsLoading}
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
                value={statistics?.confirmed_matches}
                loading={statisticsLoading}
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
                value={statistics?.pending_confirmation}
                loading={statisticsLoading}
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
                value={statistics ? Math.round(statistics.average_confidence * 100) : 0}
                loading={statisticsLoading}
                suffix={<span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>%</span>}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Quick Import Drag & Drop */}
      {selectedSupplier && (
        <Card
          title={
            <Space>
              <UploadOutlined style={{ color: '#1890ff' }} />
              <Text strong>Import Rapid Excel</Text>
            </Space>
          }
          style={{ marginBottom: '16px', borderRadius: '8px' }}
        >
          <Dragger
            accept=".xlsx,.xls"
            beforeUpload={handleFileUpload}
            showUploadList={false}
            disabled={uploadLoading}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">
              {uploadLoading ? 'Se încarcă...' : 'Trage fișierul Excel aici sau click pentru selectare'}
            </p>
            <p className="ant-upload-hint">
              Suport pentru .xlsx și .xls (max 10MB). Produsele vor fi importate automat pentru furnizorul selectat.
            </p>
          </Dragger>
        </Card>
      )}

      {/* Alert Info */}
      <Alert
        message="Cum funcționează matching-ul?"
        description={
          <Space direction="vertical" size={4}>
            <Text>• <strong>Match Manual:</strong> Asociază manual produsele furnizorului cu produsele din catalog</Text>
            <Text>• <strong>Tokeni Comuni:</strong> Vezi exact ce cuvinte/caractere au fost găsite în comun între produse pentru transparență totală</Text>
            <Text>• <strong>Nume Chinezești:</strong> Adaugă nume în limba chineză la produsele locale pentru identificare mai ușoară</Text>
            <Text>• <strong>Confirmare Manuală:</strong> Toate match-urile trebuie confirmate manual pentru acuratețe maximă</Text>
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
          <>
            {/* Bulk Actions */}
            {selectedRowKeys.length > 0 && (
              <Alert
                message={`${selectedRowKeys.length} produse selectate`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                action={
                  <Space>
                    <Button
                      type="primary"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      onClick={handleBulkConfirm}
                      style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    >
                      Confirmă Selectate
                    </Button>
                    <Button
                      danger
                      size="small"
                      icon={<CloseCircleOutlined />}
                      onClick={handleBulkUnmatch}
                    >
                      Unmatch Selectate
                    </Button>
                  </Space>
                }
              />
            )}
            <Table
              columns={columns}
              dataSource={products}
              rowKey="id"
              loading={loading}
              rowSelection={{
                selectedRowKeys,
                onChange: setSelectedRowKeys,
                preserveSelectedRowKeys: true,
              }}
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
            scroll={{ x: SIZES.TABLE_SCROLL_X }}
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
          </>
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
        width={SIZES.MODAL_WIDTH_MATCH}
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
        width={SIZES.MODAL_WIDTH}
        style={{ top: SIZES.MODAL_TOP }}
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
                      width={SIZES.IMAGE_PREVIEW}
                      height={SIZES.IMAGE_PREVIEW}
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
                  
                  {/* Token Analysis Section */}
                  {selectedProduct.common_tokens && selectedProduct.common_tokens.length > 0 && (
                    <>
                      <Divider style={{ margin: '16px 0' }} />
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <div>
                          <Text strong style={{ fontSize: '14px' }}>Analiza Tokenilor:</Text>
                        </div>
                        
                        <Alert
                          type={
                            selectedProduct.confidence_score >= 0.7 ? 'success' :
                            selectedProduct.confidence_score >= 0.5 ? 'warning' : 'error'
                          }
                          message={
                            selectedProduct.confidence_score >= 0.7 ? 'Match de Încredere Înaltă' :
                            selectedProduct.confidence_score >= 0.5 ? 'Match de Încredere Medie' :
                            'Match de Încredere Scăzută'
                          }
                          description={
                            <Space direction="vertical" size={4}>
                              <Text style={{ fontSize: '12px' }}>
                                <strong>Formula de calcul:</strong>
                              </Text>
                              <Text style={{ fontSize: '12px' }}>
                                • Tokeni comuni găsiți: <Tag color="blue">{selectedProduct.common_tokens_count}</Tag>
                              </Text>
                              <Text style={{ fontSize: '12px' }}>
                                • Tokeni căutați (produs local): <Tag>{selectedProduct.search_tokens_count}</Tag>
                              </Text>
                              <Text style={{ fontSize: '12px' }}>
                                • Calcul: {selectedProduct.common_tokens_count} / {selectedProduct.search_tokens_count} = {Math.round(selectedProduct.confidence_score * 100)}%
                              </Text>
                              <Divider style={{ margin: '8px 0' }} />
                              <Text style={{ fontSize: '11px', color: '#666' }}>
                                {selectedProduct.confidence_score >= 0.7 
                                  ? '✅ Acest match este foarte probabil corect și poate fi confirmat automat.'
                                  : selectedProduct.confidence_score >= 0.5
                                  ? '⚠️ Acest match necesită verificare manuală înainte de confirmare.'
                                  : '❌ Acest match are probabilitate scăzută și ar trebui verificat cu atenție.'}
                              </Text>
                            </Space>
                          }
                          showIcon
                          style={{ marginBottom: '12px' }}
                        />
                        
                        <div>
                          <Text strong style={{ fontSize: '13px' }}>Tokeni Comuni Găsiți:</Text>
                          <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {selectedProduct.common_tokens.map((token, idx) => (
                              <Tag 
                                key={idx} 
                                color="green" 
                                style={{ fontSize: '13px', padding: '4px 8px' }}
                              >
                                {token}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      </Space>
                    </>
                  )}
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
