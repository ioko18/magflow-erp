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
  Form,
  InputNumber,
  Switch,
  Divider,
  App as AntApp,
  Popconfirm,
  Image
} from 'antd';
import {
  ShoppingOutlined,
  SearchOutlined,
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DollarOutlined,
  InboxOutlined,
  BarChartOutlined,
  FilterOutlined,
  EyeOutlined,
  MenuOutlined,
  SaveOutlined,
  SortAscendingOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { logError } from '../../utils/errorLogger';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface Supplier {
  id: number;
  name: string;
  country?: string;
  is_active: boolean;
  supplier_price?: number;
  supplier_currency?: string;
}

interface Product {
  id: number;
  name: string;
  chinese_name?: string;
  image_url?: string;
  sku: string;
  emag_part_number_key?: string;
  ean?: string;
  brand?: string;
  manufacturer?: string;
  base_price: number;
  recommended_price?: number;
  currency: string;
  weight_kg?: number;
  is_active: boolean;
  is_discontinued: boolean;
  description?: string;
  short_description?: string;
  display_order?: number;
  suppliers?: Supplier[];
  created_at: string;
  updated_at: string;
}

interface Statistics {
  total_products: number;
  active_products: number;
  inactive_products: number;
  in_stock: number;
  out_of_stock: number;
  average_price: number;
}

interface ProductFormData {
  name: string;
  chinese_name?: string;
  image_url?: string;
  sku: string;
  ean?: string;
  brand?: string;
  manufacturer?: string;
  base_price: number;
  recommended_price?: number;
  currency: string;
  weight_kg?: number;
  description?: string;
  short_description?: string;
  is_active: boolean;
  is_discontinued: boolean;
}

const ProductsPage: React.FC = () => {
  const { message, modal } = AntApp.useApp();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [draggedProduct, setDraggedProduct] = useState<Product | null>(null);
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [tempOrderValue, setTempOrderValue] = useState<number | undefined>();

  useEffect(() => {
    loadProducts();
    loadStatistics();
  }, [pagination.current, pagination.pageSize, statusFilter, searchText]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const skip = (pagination.current - 1) * pagination.pageSize;
      
      // Build params object with proper status_filter
      const params: any = {
        skip,
        limit: pagination.pageSize,
      };
      
      // Add status_filter if not 'all'
      if (statusFilter && statusFilter !== 'all') {
        params.status_filter = statusFilter;
      }
      
      // Add search if present
      if (searchText) {
        params.search = searchText;
      }
      
      const response = await api.get('/products', { params });

      const data = response.data?.data;
      setProducts(data?.products || []);
      setPagination(prev => ({
        ...prev,
        total: data?.pagination?.total || 0,
      }));
    } catch (error) {
      logError(error as Error, { component: 'Products', action: 'loadProducts', page: pagination.current });
      message.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await api.get('/products/statistics');
      setStatistics(response.data?.data || null);
    } catch (error) {
      logError(error as Error, { component: 'Products', action: 'loadStatistics' });
    }
  };

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current,
      pageSize: newPagination.pageSize,
      total: pagination.total,
    });
  };

  const handleCreateProduct = () => {
    setSelectedProduct(null);
    form.resetFields();
    form.setFieldsValue({
      currency: 'RON',
      is_active: true,
      is_discontinued: false,
    });
    setFormVisible(true);
  };

  const handleEditProduct = (product: Product) => {
    setSelectedProduct(product);
    form.setFieldsValue({
      name: product.name,
      chinese_name: product.chinese_name,
      image_url: product.image_url,
      sku: product.sku,
      ean: product.ean,
      brand: product.brand,
      manufacturer: product.manufacturer,
      base_price: product.base_price,
      recommended_price: product.recommended_price,
      currency: product.currency,
      weight_kg: product.weight_kg,
      description: product.description,
      short_description: product.short_description,
      is_active: product.is_active,
      is_discontinued: product.is_discontinued,
    });
    setFormVisible(true);
  };

  const handleDeleteProduct = (product: Product) => {
    modal.confirm({
      title: 'Șterge produs',
      icon: <DeleteOutlined />,
      content: `Ești sigur că vrei să ștergi produsul "${product.name}"?`,
      okText: 'Da, șterge',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.delete(`/products/${product.id}`);
          message.success('Produs șters cu succes');
          await loadProducts();
          await loadStatistics();
        } catch (error) {
          message.error('Failed to delete product');
        }
      }
    });
  };

  const handleFormSubmit = async (values: ProductFormData) => {
    try {
      if (selectedProduct) {
        await api.put(`/products/${selectedProduct.id}`, values);
        message.success('Produs actualizat cu succes');
      } else {
        await api.post('/products', values);
        message.success('Produs creat cu succes');
      }
      setFormVisible(false);
      await loadProducts();
      await loadStatistics();
    } catch (error) {
      message.error('Failed to save product');
    }
  };

  const viewProductDetails = (product: Product) => {
    setSelectedProduct(product);
    setDetailModalVisible(true);
  };

  const handleDragStart = (product: Product) => {
    setDraggedProduct(product);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (targetProduct: Product) => {
    if (!draggedProduct || draggedProduct.id === targetProduct.id) {
      setDraggedProduct(null);
      return;
    }

    try {
      setLoading(true);
      
      // Calculate new position based on target's display_order
      const targetOrder = targetProduct.display_order !== undefined 
        ? targetProduct.display_order 
        : (pagination.current - 1) * pagination.pageSize + products.findIndex(p => p.id === targetProduct.id);

      // Update just the dragged product's position
      await api.post(`/products/${draggedProduct.id}/display-order`, {
        display_order: targetOrder,
        auto_adjust: true
      });

      message.success(`Produs mutat la poziția ${targetOrder}`);
      
      // Reload to get correct order from backend
      await loadProducts();
    } catch (error) {
      logError(error as Error, { component: 'Products', action: 'handleDrop', fromId: draggedProduct?.id, toId: targetProduct?.id });
      message.error('Eroare la reordonarea produselor');
    } finally {
      setDraggedProduct(null);
      setLoading(false);
    }
  };

  const handleOrderEdit = (product: Product) => {
    setEditingOrderId(product.id);
    // Set to current display_order or calculate position
    const currentOrder = product.display_order !== undefined 
      ? product.display_order 
      : (pagination.current - 1) * pagination.pageSize + products.findIndex(p => p.id === product.id);
    setTempOrderValue(currentOrder);
  };

  const handleOrderSave = async (productId: number) => {
    if (tempOrderValue === undefined || tempOrderValue === null) {
      setEditingOrderId(null);
      return;
    }

    try {
      setLoading(true);
      
      // Save to backend first
      await api.post(`/products/${productId}/display-order`, {
        display_order: tempOrderValue,
        auto_adjust: true
      });

      message.success(`Produs mutat la poziția ${tempOrderValue}`);
      setEditingOrderId(null);
      setTempOrderValue(undefined);
      
      // Force reload to get correct order from backend
      await loadProducts();
    } catch (error: any) {
      logError(error as Error, { component: 'Products', action: 'handleOrderSave', productId: editingOrderId, newOrder: tempOrderValue });
      const errorMsg = error?.response?.data?.detail || 'Eroare la actualizarea ordinii';
      message.error(errorMsg);
      setEditingOrderId(null);
    } finally {
      setLoading(false);
    }
  };

  const handleInitializeOrder = async () => {
    modal.confirm({
      title: 'Inițializează Ordine Produse',
      content: 'Aceasta va seta automat o ordine pentru toate produsele din baza de date. Continuați?',
      okText: 'Da, inițializează',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          setLoading(true);
          
          // Get all products (without pagination)
          const response = await api.get('/products', { 
            params: { skip: 0, limit: 10000 } 
          });
          
          const allProducts = response.data?.data?.products || [];
          
          // Create reorder payload with sequential order
          const reorderData = allProducts.map((product: Product, index: number) => ({
            product_id: product.id,
            display_order: index
          }));

          // Send bulk reorder
          await api.post('/products/reorder', {
            product_orders: reorderData
          });

          message.success(`Ordine inițializată pentru ${allProducts.length} produse`);
          await loadProducts();
        } catch (error) {
          logError(error as Error, { component: 'Products', action: 'initializeOrder' });
          message.error('Eroare la inițializarea ordinii');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const columns: ColumnsType<Product> = [
    {
      title: '',
      key: 'drag',
      width: 50,
      fixed: 'left',
      render: (_, record) => (
        <MenuOutlined
          style={{ cursor: 'grab', color: '#999', fontSize: '16px' }}
          draggable
          onDragStart={() => handleDragStart(record)}
        />
      ),
    },
    {
      title: (
        <Tooltip title="Click pe număr pentru a edita poziția. Produsele sunt sortate automat după această coloană.">
          <Space>
            <Text strong>Ordine</Text>
            <Text type="secondary" style={{ fontSize: '10px' }}></Text>
          </Space>
        </Tooltip>
      ),
      key: 'display_order',
      width: 90,
      fixed: 'left',
      defaultSortOrder: 'ascend',
      sorter: (a, b) => {
        // Products with display_order come first, sorted by order
        if (a.display_order !== undefined && b.display_order !== undefined) {
          return a.display_order - b.display_order;
        }
        if (a.display_order !== undefined) return -1;
        if (b.display_order !== undefined) return 1;
        return 0;
      },
      render: (_, record, index) => {
        const actualPosition = record.display_order !== undefined 
          ? record.display_order 
          : (pagination.current - 1) * pagination.pageSize + index;
        
        return editingOrderId === record.id ? (
          <Space.Compact style={{ width: '100%' }}>
            <InputNumber
              size="small"
              min={0}
              max={9999}
              value={tempOrderValue}
              onChange={(value) => setTempOrderValue(value || 0)}
              style={{ width: '70px' }}
              autoFocus
              onPressEnter={() => handleOrderSave(record.id)}
              placeholder="Poziție"
            />
            <Button
              size="small"
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => handleOrderSave(record.id)}
              title="Salvează"
            />
          </Space.Compact>
        ) : (
          <Tooltip title={`Click pentru a muta la altă poziție${record.display_order === undefined ? ' (nesetat)' : ''}`}>
            <div
              onClick={() => handleOrderEdit(record)}
              style={{
                cursor: 'pointer',
                padding: '6px 10px',
                borderRadius: '4px',
                background: record.display_order !== undefined ? '#e6f7ff' : '#f5f5f5',
                border: record.display_order !== undefined ? '1px solid #91d5ff' : '1px dashed #d9d9d9',
                textAlign: 'center',
                fontWeight: record.display_order !== undefined ? 'bold' : 'normal',
                color: record.display_order !== undefined ? '#1890ff' : '#999',
                transition: 'all 0.2s'
              }}
            >
              {actualPosition}
              {record.display_order === undefined && (
                <Text type="secondary" style={{ fontSize: '10px', display: 'block' }}>auto</Text>
              )}
            </div>
          </Tooltip>
        );
      },
    },
    {
      title: 'Imagine',
      key: 'image',
      width: 165,
      fixed: 'left',
      render: (_, record) => (
        record.image_url ? (
          <Image
            src={record.image_url}
            alt={record.name}
            width={150}
            height={150}
            style={{ objectFit: 'cover', borderRadius: '4px' }}
            fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='12'%3ENo Image%3C/text%3E%3C/svg%3E"
            preview={{
              mask: <EyeOutlined />
            }}
          />
        ) : (
          <div style={{
            width: 150,
            height: 150,
            background: '#f0f0f0',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            color: '#999'
          }}>
            No Image
          </div>
        )
      ),
    },
    {
      title: 'Produs',
      key: 'product',
      width: 500,
      render: (_, record) => (
        <Space direction="vertical" size={10}>
          <Text strong style={{ fontSize: '15px' }}>
            {record.name}
          </Text>
          <Space size={24}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              SKU: {record.sku}
            </Text>
            {record.ean && (
              <Tag color="blue" style={{ fontSize: '11px' }}>
                EAN: {record.ean}
              </Tag>
            )}
          
            {record.brand && (
              <Tag color="purple" style={{ fontSize: '11px' }}>
                {record.brand}
              </Tag>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: 'Preț',
      key: 'price',
      width: 120,
      sorter: (a, b) => a.base_price - b.base_price,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1890ff', fontSize: '16px' }}>
            {record.base_price.toFixed(2)} {record.currency}
          </Text>
          {record.recommended_price && (
            <Text type="secondary" style={{ fontSize: '13px' }}>
              Rec: {record.recommended_price.toFixed(2)} {record.currency}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Furnizori',
      key: 'suppliers',
      width: 100,
      render: (_, record) => {
        // Deduplicare furnizori (măsură de siguranță)
        const uniqueSuppliers = record.suppliers 
          ? Array.from(
              new Map(record.suppliers.map(s => [s.id, s])).values()
            )
          : [];
        
        return uniqueSuppliers.length > 0 ? (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            {uniqueSuppliers.slice(0, 3).map((supplier) => (
              <Tag 
                key={supplier.id}
                color={supplier.is_active ? 'orange' : 'default'}
                style={{ 
                  fontSize: '11px',
                  marginRight: 0,
                  width: '100%',
                  textAlign: 'center'
                }}
              >
                {supplier.name}
                
              </Tag>
            ))}
            {uniqueSuppliers.length > 3 && (
              <Text type="secondary" style={{ fontSize: '10px' }}>
                +{uniqueSuppliers.length - 3} furnizori
              </Text>
            )}
          </Space>
        ) : (
          <Text type="secondary" style={{ fontSize: '12px' }}>Fără furnizori</Text>
        );
      },
    },
    {
      title: 'Greutate',
      dataIndex: 'weight_kg',
      key: 'weight',
      width: 80,
      render: (weight: number) => (
        weight ? (
          <Text style={{ fontSize: '13px' }}>{weight} kg</Text>
        ) : (
          <Text type="secondary" style={{ fontSize: '12px' }}>-</Text>
        )
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 90,
      filters: [
        { text: 'Activ', value: 'active' },
        { text: 'Inactiv', value: 'inactive' },
        { text: 'Discontinuat', value: 'discontinued' },
      ],
      onFilter: (value, record) => {
        if (value === 'active') return record.is_active && !record.is_discontinued;
        if (value === 'inactive') return !record.is_active;
        if (value === 'discontinued') return record.is_discontinued;
        return true;
      },
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          <Tag 
            color={record.is_active ? 'green' : 'default'}
            icon={record.is_active ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          >
            {record.is_active ? 'Activ' : 'Inactiv'}
          </Tag>
          {record.is_discontinued && (
            <Tag color="red" style={{ fontSize: '11px' }}>Discontinuat</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      fixed: 'right',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Vezi detalii">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => viewProductDetails(record)}
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          <Tooltip title="Editează">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditProduct(record)}
              style={{ color: '#52c41a' }}
            />
          </Tooltip>
          <Tooltip title="Șterge">
            <Popconfirm
              title="Șterge produs"
              description="Ești sigur că vrei să ștergi acest produs?"
              onConfirm={() => handleDeleteProduct(record)}
              okText="Da"
              cancelText="Nu"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </Tooltip>
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
                <ShoppingOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Management Produse
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Gestionează catalogul complet de produse din baza de date locală
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadProducts}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
              <Button 
                icon={<SortAscendingOutlined />}
                onClick={handleInitializeOrder}
                size="large"
                style={{ marginRight: '8px' }}
              >
                Inițializează Ordine
              </Button>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={handleCreateProduct}
                size="large"
              >
                Produs Nou
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Statistics Cards */}
      {statistics && (
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
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Produse Active</span>}
                value={statistics.active_products}
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
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>În Stoc</span>}
                value={statistics.in_stock}
                prefix={<InboxOutlined />}
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
                title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Preț Mediu</span>}
                value={statistics.average_price}
                precision={2}
                suffix={<span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>RON</span>}
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
              placeholder="Caută după nume, SKU, EAN, brand..."
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
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: '100%', borderRadius: '6px' }}
              suffixIcon={<FilterOutlined />}
            >
              <Option value="all">📋 Toate produsele</Option>
              <Option value="active">✅ Doar active</Option>
              <Option value="inactive">❌ Doar inactive</Option>
              <Option value="discontinued">🚫 Doar discontinuate</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Button 
              size="large"
              onClick={() => { setSearchText(''); setStatusFilter('all'); }}
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
        <Table
          columns={columns}
          dataSource={products}
          rowKey="id"
          loading={loading}
          onRow={(record) => ({
            onDragOver: handleDragOver,
            onDrop: () => handleDrop(record),
            style: {
              cursor: draggedProduct ? 'move' : 'default',
              background: draggedProduct?.id === record.id ? '#e6f7ff' : undefined
            }
          })}
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
                    <Text type="secondary">Nu există produse</Text>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateProduct}>
                      Adaugă primul produs
                    </Button>
                  </Space>
                }
              />
            )
          }}
        />
      </Card>

      {/* Product Form Modal */}
      <Modal
        title={
          <Space>
            <ShoppingOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>
              {selectedProduct ? 'Editează Produs' : 'Produs Nou'}
            </Text>
          </Space>
        }
        open={formVisible}
        onCancel={() => setFormVisible(false)}
        onOk={() => form.submit()}
        width={900}
        okText={selectedProduct ? 'Actualizează' : 'Creează'}
        cancelText="Anulează"
        okButtonProps={{ size: 'large' }}
        cancelButtonProps={{ size: 'large' }}
      >
        <Divider />
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFormSubmit}
          size="large"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={<Text strong>Nume Produs</Text>}
                rules={[{ required: true, message: 'Numele este obligatoriu' }]}
              >
                <Input placeholder="ex: Amplificator audio YUDI" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="sku"
                label={<Text strong>SKU</Text>}
                rules={[{ required: true, message: 'SKU este obligatoriu' }]}
              >
                <Input placeholder="ex: SKU-YUDI-123" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="chinese_name"
                label={
                  <Space>
                    <Text strong>Nume Chinezesc</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      (opțional - pentru matching cu produse furnizori)
                    </Text>
                  </Space>
                }
              >
                <Input 
                  placeholder="ex: 电子音频放大器" 
                  style={{ fontSize: '14px' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="image_url"
                label={
                  <Space>
                    <Text strong>URL Imagine Produs</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      (opțional - imagine principală)
                    </Text>
                  </Space>
                }
              >
                <Input 
                  placeholder="ex: https://example.com/image.jpg" 
                  type="url"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="ean"
                label={<Text strong>EAN</Text>}
              >
                <Input placeholder="ex: 1234567890123" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="brand"
                label={<Text strong>Brand</Text>}
              >
                <Input placeholder="ex: YUDI" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="manufacturer"
                label={<Text strong>Producător</Text>}
              >
                <Input placeholder="ex: Shenzhen Electronics" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Prețuri și Specificații</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="base_price"
                label={<Text strong>Preț Bază</Text>}
                rules={[{ required: true, message: 'Prețul este obligatoriu' }]}
              >
                <InputNumber 
                  min={0} 
                  step={0.01} 
                  style={{ width: '100%' }}
                  prefix="RON"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="recommended_price"
                label={<Text strong>Preț Recomandat</Text>}
              >
                <InputNumber 
                  min={0} 
                  step={0.01} 
                  style={{ width: '100%' }}
                  prefix="RON"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="weight_kg"
                label={<Text strong>Greutate (kg)</Text>}
              >
                <InputNumber 
                  min={0} 
                  step={0.01} 
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="short_description"
            label={<Text strong>Descriere Scurtă</Text>}
          >
            <Input placeholder="Descriere scurtă a produsului" />
          </Form.Item>

          <Form.Item
            name="description"
            label={<Text strong>Descriere Completă</Text>}
          >
            <TextArea 
              rows={4} 
              placeholder="Descriere detaliată a produsului" 
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Divider orientation="left">Status Produs</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label={<Text strong>Status Activ</Text>}
                valuePropName="checked"
              >
                <Switch 
                  checkedChildren="Activ" 
                  unCheckedChildren="Inactiv"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_discontinued"
                label={
                  <Space>
                    <Text strong>Status Discontinuat</Text>
                    <Tooltip title="Marchează produsul ca fiind discontinuat (nu mai este disponibil de la furnizor)">
                      <Text type="secondary" style={{ fontSize: '12px' }}>(ℹ️)</Text>
                    </Tooltip>
                  </Space>
                }
                valuePropName="checked"
              >
                <Switch 
                  checkedChildren="Discontinuat" 
                  unCheckedChildren="Disponibil"
                  style={{ backgroundColor: Form.useWatch('is_discontinued', form) ? '#ff4d4f' : undefined }}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Product Details Modal */}
      <Modal
        title={
          <Space>
            <BarChartOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>Detalii Produs</Text>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)} size="large">
            Închide
          </Button>
        ]}
      >
        {selectedProduct && (
          <div>
            {/* Product Image */}
            {selectedProduct.image_url && (
              <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                <Image
                  src={selectedProduct.image_url}
                  alt={selectedProduct.name}
                  width={200}
                  height={200}
                  style={{ objectFit: 'cover', borderRadius: '8px' }}
                  fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='16'%3ENo Image%3C/text%3E%3C/svg%3E"
                />
              </div>
            )}

            <Card title="Informații Generale" size="small" style={{ marginBottom: '16px' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Text strong>Nume:</Text>
                  <div style={{ marginBottom: '8px' }}>{selectedProduct.name}</div>
                  
                  {selectedProduct.chinese_name && (
                    <>
                      <Text strong>Nume Chinezesc:</Text>
                      <div style={{ marginBottom: '8px', color: '#1890ff', fontSize: '14px' }}>
                        {selectedProduct.chinese_name}
                      </div>
                    </>
                  )}
                  
                  <Text strong>SKU:</Text>
                  <div style={{ marginBottom: '8px' }}>{selectedProduct.sku}</div>
                  
                  {selectedProduct.ean && (
                    <>
                      <Text strong>EAN:</Text>
                      <div style={{ marginBottom: '8px' }}>{selectedProduct.ean}</div>
                    </>
                  )}
                </Col>
                <Col span={12}>
                  {selectedProduct.brand && (
                    <>
                      <Text strong>Brand:</Text>
                      <div style={{ marginBottom: '8px' }}>{selectedProduct.brand}</div>
                    </>
                  )}
                  
                  {selectedProduct.manufacturer && (
                    <>
                      <Text strong>Producător:</Text>
                      <div style={{ marginBottom: '8px' }}>{selectedProduct.manufacturer}</div>
                    </>
                  )}
                  
                  {selectedProduct.weight_kg && (
                    <>
                      <Text strong>Greutate:</Text>
                      <div style={{ marginBottom: '8px' }}>{selectedProduct.weight_kg} kg</div>
                    </>
                  )}
                </Col>
              </Row>
            </Card>

            <Card title="Prețuri" size="small" style={{ marginBottom: '16px' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="Preț Bază"
                    value={selectedProduct.base_price}
                    precision={2}
                    suffix={selectedProduct.currency}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                {selectedProduct.recommended_price && (
                  <Col span={12}>
                    <Statistic
                      title="Preț Recomandat"
                      value={selectedProduct.recommended_price}
                      precision={2}
                      suffix={selectedProduct.currency}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                )}
              </Row>
            </Card>

            {selectedProduct.description && (
              <Card title="Descriere" size="small" style={{ marginBottom: '16px' }}>
                <Text>{selectedProduct.description}</Text>
              </Card>
            )}

            <Card title="Status și Date" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Text strong>Status:</Text>
                  <div style={{ marginTop: '8px' }}>
                    <Space direction="vertical" size={4}>
                      <Tag 
                        color={selectedProduct.is_active ? 'green' : 'default'}
                        icon={selectedProduct.is_active ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                      >
                        {selectedProduct.is_active ? 'Activ' : 'Inactiv'}
                      </Tag>
                      {selectedProduct.is_discontinued && (
                        <Tag color="red" style={{ fontSize: '11px' }}>Discontinuat</Tag>
                      )}
                    </Space>
                  </div>
                </Col>
                <Col span={8}>
                  <Text strong>Data Creare:</Text>
                  <div style={{ marginTop: '8px' }}>
                    {new Date(selectedProduct.created_at).toLocaleDateString('ro-RO')}
                  </div>
                </Col>
                <Col span={8}>
                  <Text strong>Ultima Actualizare:</Text>
                  <div style={{ marginTop: '8px' }}>
                    {new Date(selectedProduct.updated_at).toLocaleDateString('ro-RO')}
                  </div>
                </Col>
              </Row>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ProductsPage;
