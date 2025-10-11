import React, { useState, useEffect } from 'react';
import {
  Space,
  Button,
  Input,
  Tag,
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Select,
  Modal,
  Form,
  InputNumber,
  Tooltip,
  Badge,
  Divider,
  Rate,
  Switch,
  App as AntApp
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  GlobalOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  ShopOutlined,
  PhoneOutlined,
  MailOutlined,
  StarOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UserOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import DraggableSuppliersTable from '../../components/suppliers/DraggableSuppliersTable';

const { Title, Text } = Typography;
const { Option } = Select;

interface Supplier {
  id: number;
  name: string;
  country: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  lead_time_days: number;
  min_order_value?: number;
  min_order_qty?: number;
  currency?: string;
  payment_terms?: string;
  rating: number;
  is_active: boolean;
  total_orders: number;
  display_order?: number;
  notes?: string;
  created_at?: string;
}

interface SupplierFormData {
  name: string;
  country: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  lead_time_days: number;
  min_order_value: number;
  min_order_qty: number;
  currency: string;
  payment_terms: string;
  notes?: string;
  is_active?: boolean;
}

interface Statistics {
  total_suppliers: number;
  active_suppliers: number;
  chinese_suppliers: number;
  average_rating: number;
}

const SuppliersPage: React.FC = () => {
  const { message, modal } = AntApp.useApp();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [countryFilter, setCountryFilter] = useState<string>('all');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [statistics, setStatistics] = useState<Statistics>({
    total_suppliers: 0,
    active_suppliers: 0,
    chinese_suppliers: 0,
    average_rating: 0
  });

  const [form] = Form.useForm();

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/suppliers', {
        params: { limit: 1000, active_only: false }
      });
      
      // Backend returns { status, data: { suppliers, pagination } }
      const suppliersData = response.data?.data?.suppliers || response.data?.suppliers || response.data || [];
      setSuppliers(suppliersData);
      
      // Calculate statistics
      setStatistics({
        total_suppliers: suppliersData.length,
        active_suppliers: suppliersData.filter((s: Supplier) => s.is_active).length,
        chinese_suppliers: suppliersData.filter((s: Supplier) => s.country === 'China').length,
        average_rating: suppliersData.length > 0 
          ? suppliersData.reduce((sum: number, s: Supplier) => sum + s.rating, 0) / suppliersData.length 
          : 0
      });
    } catch (error) {
      console.error('Error loading suppliers:', error);
      message.error('Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSupplier = () => {
    setSelectedSupplier(null);
    form.resetFields();
    setFormVisible(true);
  };

  const handleEditSupplier = async (supplier: Supplier) => {
    setSelectedSupplier(supplier);
    
    // Fetch full supplier details to get all fields including currency
    try {
      const response = await api.get(`/suppliers/${supplier.id}`);
      const fullSupplier = response.data?.data?.supplier || supplier;
      
      form.setFieldsValue({
        name: fullSupplier.name,
        country: fullSupplier.country,
        contact_person: fullSupplier.contact_person,
        email: fullSupplier.email,
        phone: fullSupplier.phone,
        lead_time_days: fullSupplier.lead_time_days,
        min_order_value: fullSupplier.min_order_value,
        min_order_qty: fullSupplier.min_order_qty,
        currency: fullSupplier.currency,
        payment_terms: fullSupplier.payment_terms,
        notes: fullSupplier.notes,
        is_active: fullSupplier.is_active
      });
    } catch (error) {
      console.error('Error loading supplier details:', error);
      // Fallback to basic supplier data
      form.setFieldsValue({
        ...supplier,
        is_active: supplier.is_active
      });
    }
    
    setFormVisible(true);
  };

  const handleReorder = async (reorderedSuppliers: Supplier[]) => {
    try {
      // Prepare data for API
      const suppliersOrder = reorderedSuppliers.map(s => ({
        id: s.id,
        display_order: s.display_order
      }));

      // Update local state immediately for smooth UX
      setSuppliers(reorderedSuppliers);

      // Send to backend
      await api.patch('/suppliers/batch-update-order', {
        suppliers: suppliersOrder
      });

      message.success('Ordinea furnizorilor a fost actualizată');
    } catch (error: any) {
      message.error('Eroare la actualizarea ordinii');
      // Reload to restore correct order
      await loadSuppliers();
    }
  };

  const handleDeleteSupplier = async (supplier: Supplier) => {
    const hasOrders = supplier.total_orders > 0;
    
    // Get product count for this supplier
    let productCount = 0;
    try {
      const statsResponse = await api.get(`/suppliers/${supplier.id}/products/statistics`);
      productCount = statsResponse.data?.data?.total_products || 0;
    } catch (error) {
      console.error('Error getting product count:', error);
    }
    
    if (hasOrders) {
      // Supplier has orders - only soft delete allowed
      modal.confirm({
        title: 'Dezactivează furnizor',
        icon: <ExclamationCircleOutlined />,
        content: `Furnizorul "${supplier.name}" are ${supplier.total_orders} comenzi. Poți doar să-l dezactivezi.`,
        okText: 'Dezactivează',
        okType: 'danger',
        cancelText: 'Anulează',
        onOk: async () => {
          try {
            await api.delete(`/suppliers/${supplier.id}`);
            message.success('Furnizor dezactivat cu succes');
            await loadSuppliers();
          } catch (error) {
            message.error('Eroare la dezactivare');
          }
        }
      });
    } else {
      // No orders - offer both soft and hard delete
      modal.confirm({
        title: 'Șterge furnizor',
        icon: <ExclamationCircleOutlined />,
        content: (
          <div>
            <p>Furnizorul "{supplier.name}" nu are comenzi.</p>
            {productCount > 0 && (
              <p style={{ color: '#fa8c16' }}>
                <strong>⚠️ Atenție:</strong> Furnizorul are {productCount} produse care vor fi șterse împreună cu furnizorul.
              </p>
            )}
            <p><strong>Cum vrei să ștergi furnizorul?</strong></p>
            <ul style={{ marginTop: '10px' }}>
              <li><strong>Dezactivează</strong> - furnizorul rămâne în baza de date dar devine inactiv</li>
              <li><strong>Șterge permanent</strong> - furnizorul {productCount > 0 ? `și toate cele ${productCount} produse sunt eliminate` : 'este eliminat'} complet din baza de date</li>
            </ul>
          </div>
        ),
        okText: 'Șterge Permanent',
        okType: 'danger',
        cancelText: 'Anulează',
        onOk: async () => {
          try {
            await api.delete(`/suppliers/${supplier.id}?permanent=true`);
            message.success(`Furnizor ${productCount > 0 ? `și ${productCount} produse șterse` : 'șters'} permanent`);
            await loadSuppliers();
          } catch (error: any) {
            message.error(error.response?.data?.detail || 'Eroare la ștergere permanentă');
          }
        },
        onCancel: () => {
          // Show second modal for soft delete option
          modal.confirm({
            title: 'Dezactivează furnizor',
            icon: <ExclamationCircleOutlined />,
            content: `Vrei să dezactivezi furnizorul "${supplier.name}" în loc să-l ștergi permanent?`,
            okText: 'Da, dezactivează',
            okType: 'default',
            cancelText: 'Nu',
            onOk: async () => {
              try {
                await api.delete(`/suppliers/${supplier.id}`);
                message.success('Furnizor dezactivat cu succes');
                await loadSuppliers();
              } catch (error) {
                message.error('Eroare la dezactivare');
              }
            }
          });
        }
      });
    }
  };

  const handleFormSubmit = async (values: SupplierFormData) => {
    try {
      if (selectedSupplier) {
        // Update
        await api.put(`/suppliers/${selectedSupplier.id}`, values);
        message.success('Furnizor actualizat cu succes');
      } else {
        // Create
        await api.post('/suppliers', values);
        message.success('Furnizor creat cu succes');
      }
      setFormVisible(false);
      form.resetFields();
      setSelectedSupplier(null);
      await loadSuppliers(); // Reload from backend
    } catch (error: any) {
      console.error('Error saving supplier:', error);
      message.error(error.response?.data?.detail || 'Failed to save supplier');
    }
  };

  const handleBulkActivate = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Selectează cel puțin un furnizor');
      return;
    }

    try {
      await api.post('/suppliers/bulk-update-status', {
        supplier_ids: selectedRowKeys,
        is_active: true
      });
      message.success(`${selectedRowKeys.length} furnizori activați cu succes`);
      setSelectedRowKeys([]);
      await loadSuppliers();
    } catch (error) {
      message.error('Eroare la activarea furnizorilor');
    }
  };

  const handleBulkDeactivate = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Selectează cel puțin un furnizor');
      return;
    }

    modal.confirm({
      title: 'Dezactivează furnizori',
      icon: <ExclamationCircleOutlined />,
      content: `Ești sigur că vrei să dezactivezi ${selectedRowKeys.length} furnizori?`,
      okText: 'Da, dezactivează',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.post('/suppliers/bulk-update-status', {
            supplier_ids: selectedRowKeys,
            is_active: false
          });
          message.success(`${selectedRowKeys.length} furnizori dezactivați cu succes`);
          setSelectedRowKeys([]);
          await loadSuppliers();
        } catch (error) {
          message.error('Eroare la dezactivarea furnizorilor');
        }
      }
    });
  };

  const filteredSuppliers = suppliers.filter(supplier => {
    const matchesSearch = !searchText || 
      supplier.name.toLowerCase().includes(searchText.toLowerCase()) ||
      supplier.contact_person?.toLowerCase().includes(searchText.toLowerCase()) ||
      supplier.email?.toLowerCase().includes(searchText.toLowerCase());
    
    const matchesCountry = countryFilter === 'all' || supplier.country === countryFilter;
    
    return matchesSearch && matchesCountry;
  });

  // Columns definition (kept for reference, now using DraggableSuppliersTable)
  // @ts-ignore - kept for reference
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _columns: ColumnsType<Supplier> = [
    {
      title: 'Furnizor',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left',
      width: 110,
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (text: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: '14px' }}>
            <ShopOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
            {text}
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <GlobalOutlined style={{ marginRight: '4px' }} />
            {record.country}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Contact',
      key: 'contact',
      width: 160,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.contact_person && (
            <Text style={{ fontSize: '13px' }}>
              <UserOutlined style={{ marginRight: '6px', color: '#52c41a' }} />
              {record.contact_person}
            </Text>
          )}
          {record.email && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <MailOutlined style={{ marginRight: '6px' }} />
              {record.email}
            </Text>
          )}
          {record.phone && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <PhoneOutlined style={{ marginRight: '6px' }} />
              {record.phone}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Lead Time',
      dataIndex: 'lead_time_days',
      key: 'lead_time',
      width: 100,
      sorter: (a, b) => a.lead_time_days - b.lead_time_days,
      render: (days: number) => (
        <Tag 
          icon={<ClockCircleOutlined />}
          color={days <= 25 ? 'green' : days <= 35 ? 'orange' : 'red'}
        >
          {days} zile
        </Tag>
      ),
    },
    {
      title: 'Rating',
      dataIndex: 'rating',
      key: 'rating',
      width: 130,
      sorter: (a, b) => a.rating - b.rating,
      render: (rating: number) => (
        <Space>
          <Rate disabled value={rating} allowHalf style={{ fontSize: '14px' }} />
          <Text type="secondary">({rating.toFixed(1)})</Text>
        </Space>
      ),
    },
    {
      title: 'Monedă',
      dataIndex: 'currency',
      key: 'currency',
      width: 80,
      filters: [
        { text: 'USD', value: 'USD' },
        { text: 'CNY', value: 'CNY' },
        { text: 'EUR', value: 'EUR' },
      ],
      onFilter: (value, record) => record.currency === value,
      render: (currency: string) => {
        const currencyIcons: Record<string, string> = {
          'USD': '💵',
          'CNY': '💴',
          'EUR': '💶',
          'GBP': '💷',
          'JPY': '💴'
        };
        return (
          <Tag color="blue">
            {currencyIcons[currency] || '💰'} {currency || 'USD'}
          </Tag>
        );
      },
    },
    {
      title: 'Comenzi',
      dataIndex: 'total_orders',
      key: 'total_orders',
      width: 80,
      sorter: (a, b) => a.total_orders - b.total_orders,
      render: (orders: number) => (
        <Badge 
          count={orders} 
          showZero 
          style={{ backgroundColor: orders > 30 ? '#52c41a' : '#1890ff' }} 
        />
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 70,
      filters: [
        { text: 'Activ', value: true },
        { text: 'Inactiv', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
      render: (active: boolean) => (
        <Tag 
          icon={active ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
          color={active ? 'success' : 'default'}
        >
          {active ? 'Activ' : 'Inactiv'}
        </Tag>
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      fixed: 'right',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Editează">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditSupplier(record)}
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          <Tooltip title="Șterge">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteSupplier(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header Modern */}
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
                <TeamOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                Management Furnizori
              </Title>
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Gestionează furnizorii și relațiile comerciale pentru reaprovizionare
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button 
                icon={<ReloadOutlined />} 
                onClick={loadSuppliers}
                loading={loading}
                size="large"
              >
                Refresh
              </Button>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={handleCreateSupplier}
                size="large"
              >
                Furnizor Nou
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Statistics Cards Modern */}
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
              title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Total Furnizori</span>}
              value={statistics.total_suppliers}
              prefix={<TeamOutlined />}
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
              title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Furnizori Activi</span>}
              value={statistics.active_suppliers}
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
              title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Furnizori Chinezi</span>}
              value={statistics.chinese_suppliers}
              prefix={<GlobalOutlined />}
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
              title={<span style={{ color: 'rgba(255,255,255,0.9)' }}>Rating Mediu</span>}
              value={statistics.average_rating}
              precision={1}
              suffix={<span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>/5</span>}
              prefix={<StarOutlined />}
              valueStyle={{ color: '#fff', fontSize: '32px', fontWeight: 'bold' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters Card Modern */}
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
              placeholder="Caută după nume, contact, email..."
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
              placeholder="Filtrează după țară"
              value={countryFilter}
              onChange={setCountryFilter}
              style={{ width: '100%', borderRadius: '6px' }}
              suffixIcon={<GlobalOutlined />}
            >
              <Option value="all">🌍 Toate țările</Option>
              <Option value="China">🇨🇳 China</Option>
              <Option value="Taiwan">🇹🇼 Taiwan</Option>
              <Option value="Vietnam">🇻🇳 Vietnam</Option>
            </Select>
          </Col>
          <Col xs={24} md={6}>
            <Space>
              <Button 
                size="large"
                onClick={() => { setSearchText(''); setCountryFilter('all'); }}
                style={{ borderRadius: '6px' }}
              >
                Resetează Filtre
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Bulk Actions Card */}
      {selectedRowKeys.length > 0 && (
        <Card 
          variant="borderless"
          style={{ 
            marginBottom: '16px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            background: '#e6f7ff'
          }}
        >
          <Row justify="space-between" align="middle">
            <Col>
              <Text strong style={{ fontSize: '14px' }}>
                {selectedRowKeys.length} furnizori selectați
              </Text>
            </Col>
            <Col>
              <Space>
                <Button 
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={handleBulkActivate}
                  style={{ borderRadius: '6px' }}
                >
                  Activează
                </Button>
                <Button 
                  danger
                  icon={<ExclamationCircleOutlined />}
                  onClick={handleBulkDeactivate}
                  style={{ borderRadius: '6px' }}
                >
                  Dezactivează
                </Button>
                <Button 
                  onClick={() => setSelectedRowKeys([])}
                  style={{ borderRadius: '6px' }}
                >
                  Anulează selecția
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* Table Card Modern */}
      <Card 
        variant="borderless"
        style={{ 
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <DraggableSuppliersTable
          suppliers={filteredSuppliers}
          loading={loading}
          onEdit={handleEditSupplier}
          onDelete={(id: number) => {
            const supplier = suppliers.find(s => s.id === id);
            if (supplier) handleDeleteSupplier(supplier);
          }}
          onReorder={handleReorder}
        />
      </Card>

      {/* Form Modal Modern */}
      <Modal
        title={
          <Space>
            <ShopOutlined style={{ color: '#1890ff', fontSize: '20px' }} />
            <Text strong style={{ fontSize: '18px' }}>
              {selectedSupplier ? 'Editează Furnizor' : 'Furnizor Nou'}
            </Text>
          </Space>
        }
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          form.resetFields();
          setSelectedSupplier(null);
        }}
        onOk={() => form.submit()}
        width={900}
        destroyOnHidden
        okText={selectedSupplier ? 'Actualizează' : 'Creează'}
        cancelText="Anulează"
        okButtonProps={{ size: 'large' }}
        cancelButtonProps={{ size: 'large' }}
      >
        <Divider />
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFormSubmit}
          initialValues={{
            country: 'China',
            currency: 'USD',
            lead_time_days: 30,
            min_order_value: 0,
            min_order_qty: 1,
            payment_terms: '30 days',
            is_active: true,
          }}
          size="large"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={<Text strong>Nume Furnizor</Text>}
                rules={[{ required: true, message: 'Numele este obligatoriu' }]}
              >
                <Input 
                  prefix={<ShopOutlined />}
                  placeholder="ex: Shenzhen Electronics Co." 
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="country"
                label={<Text strong>Țară</Text>}
                rules={[{ required: true, message: 'Țara este obligatorie' }]}
              >
                <Select 
                  placeholder="Selectează țara" 
                  suffixIcon={<GlobalOutlined />}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.children?.toString() ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                >
                  <Option value="China">🇨🇳 China</Option>
                  <Option value="Taiwan">🇹🇼 Taiwan</Option>
                  <Option value="Vietnam">🇻🇳 Vietnam</Option>
                  <Option value="South Korea">🇰🇷 Coreea de Sud</Option>
                  <Option value="Japan">🇯🇵 Japonia</Option>
                  <Option value="Thailand">🇹🇭 Thailanda</Option>
                  <Option value="India">🇮🇳 India</Option>
                  <Option value="Turkey">🇹🇷 Turcia</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="contact_person" label={<Text strong>Persoană Contact</Text>}>
                <Input prefix={<UserOutlined />} placeholder="ex: Li Wei" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="email" label={<Text strong>Email</Text>}>
                <Input prefix={<MailOutlined />} type="email" placeholder="email@furnizor.com" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="phone" label={<Text strong>Telefon</Text>}>
                <Input prefix={<PhoneOutlined />} placeholder="+86 123 456 7890" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Termeni Comerciali</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="lead_time_days" label={<Text strong>Lead Time (zile)</Text>}>
                <InputNumber 
                  min={1} 
                  max={90} 
                  style={{ width: '100%' }}
                  prefix={<ClockCircleOutlined />}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="min_order_value" label={<Text strong>Valoare Minimă Comandă</Text>}>
                <InputNumber 
                  min={0} 
                  step={0.01} 
                  style={{ width: '100%' }}
                  prefix="$"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="currency" label={<Text strong>Monedă</Text>}>
                <Select placeholder="Selectează moneda">
                  <Option value="USD">💵 USD - Dolar American</Option>
                  <Option value="CNY">💴 CNY - Yuan Chinezesc</Option>
                  <Option value="EUR">💶 EUR - Euro</Option>
                  <Option value="GBP">💷 GBP - Liră Sterlină</Option>
                  <Option value="JPY">💴 JPY - Yen Japonez</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="min_order_qty" label={<Text strong>Cantitate Minimă</Text>}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="payment_terms" label={<Text strong>Termeni Plată</Text>}>
                <Input placeholder="ex: 30 days, T/T, L/C" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label={<Text strong>Note și Observații</Text>}>
            <Input.TextArea 
              rows={3} 
              placeholder="Observații suplimentare despre furnizor, condiții speciale, etc." 
              showCount
              maxLength={500}
            />
          </Form.Item>

          {selectedSupplier && (
            <>
              <Divider orientation="left">Status Furnizor</Divider>
              <Form.Item 
                name="is_active" 
                label={<Text strong>Status Activ</Text>}
                valuePropName="checked"
              >
                <Switch 
                  checkedChildren="Activ" 
                  unCheckedChildren="Inactiv"
                  defaultChecked={selectedSupplier?.is_active}
                />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      <style>{`
        .row-disabled {
          opacity: 0.6;
          background-color: #fafafa;
        }
        .ant-table-thead > tr > th {
          background: #fafafa !important;
          font-weight: 600 !important;
        }
      `}</style>
    </div>
  );
};

export default SuppliersPage;
