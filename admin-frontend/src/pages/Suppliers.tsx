import React, { useState, useEffect } from 'react';
import {
  Table,
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
  Empty,
  Divider,
  Rate,
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
import api from '../services/api';

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
  rating: number;
  is_active: boolean;
  total_orders: number;
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

  const handleEditSupplier = (supplier: Supplier) => {
    setSelectedSupplier(supplier);
    form.setFieldsValue(supplier);
    setFormVisible(true);
  };

  const handleDeleteSupplier = (supplier: Supplier) => {
    modal.confirm({
      title: 'Șterge furnizor',
      icon: <ExclamationCircleOutlined />,
      content: `Ești sigur că vrei să ștergi furnizorul "${supplier.name}"?`,
      okText: 'Da, șterge',
      okType: 'danger',
      cancelText: 'Anulează',
      onOk: async () => {
        try {
          await api.delete(`/suppliers/${supplier.id}`);
          message.success('Furnizor șters cu succes');
          await loadSuppliers(); // Reload from backend
        } catch (error) {
          message.error('Failed to delete supplier');
        }
      }
    });
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
      await loadSuppliers(); // Reload from backend
    } catch (error) {
      message.error('Failed to save supplier');
    }
  };

  const filteredSuppliers = suppliers.filter(supplier => {
    const matchesSearch = !searchText || 
      supplier.name.toLowerCase().includes(searchText.toLowerCase()) ||
      supplier.contact_person?.toLowerCase().includes(searchText.toLowerCase()) ||
      supplier.email?.toLowerCase().includes(searchText.toLowerCase());
    
    const matchesCountry = countryFilter === 'all' || supplier.country === countryFilter;
    
    return matchesSearch && matchesCountry;
  });

  const columns: ColumnsType<Supplier> = [
    {
      title: 'Furnizor',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left',
      width: 250,
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
      width: 220,
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
      width: 130,
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
      width: 150,
      sorter: (a, b) => a.rating - b.rating,
      render: (rating: number) => (
        <Space>
          <Rate disabled value={rating} allowHalf style={{ fontSize: '14px' }} />
          <Text type="secondary">({rating.toFixed(1)})</Text>
        </Space>
      ),
    },
    {
      title: 'Comenzi',
      dataIndex: 'total_orders',
      key: 'total_orders',
      width: 100,
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
      width: 100,
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

      {/* Table Card Modern */}
      <Card 
        variant="borderless"
        style={{ 
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}
      >
        <Table
          columns={columns}
          dataSource={filteredSuppliers}
          rowKey="id"
          loading={loading}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Space direction="vertical">
                    <Text type="secondary">Nu există furnizori</Text>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSupplier}>
                      Adaugă primul furnizor
                    </Button>
                  </Space>
                }
              />
            )
          }}
          pagination={{
            total: filteredSuppliers.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => (
              <Text strong>
                {range[0]}-{range[1]} din {total} furnizori
              </Text>
            ),
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          scroll={{ x: 1200 }}
          size="middle"
          rowClassName={(record) => !record.is_active ? 'row-disabled' : ''}
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
        onCancel={() => setFormVisible(false)}
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
                <Select placeholder="Selectează țara" suffixIcon={<GlobalOutlined />}>
                  <Option value="China">🇨🇳 China</Option>
                  <Option value="Taiwan">🇹🇼 Taiwan</Option>
                  <Option value="Vietnam">🇻🇳 Vietnam</Option>
                  <Option value="South Korea">🇰🇷 Coreea de Sud</Option>
                  <Option value="Japan">🇯🇵 Japonia</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Informații Contact</Divider>

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
                <Select>
                  <Option value="USD">💵 USD</Option>
                  <Option value="CNY">💴 CNY</Option>
                  <Option value="EUR">💶 EUR</Option>
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
