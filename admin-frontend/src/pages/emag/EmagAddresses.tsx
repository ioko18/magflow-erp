import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  message,
  Alert,
  Tabs,
  Descriptions,
  Badge,
  Typography,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  EnvironmentOutlined,
  HomeOutlined,
  ShopOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface Address {
  address_id: string;
  country_id: number;
  country_code: string;
  address_type_id: number;
  locality_id: number;
  suburb: string;
  city: string;
  address: string;
  zipcode: string;
  quarter?: string;
  floor?: string;
  is_default: boolean;
}

interface AddressesResponse {
  success: boolean;
  addresses: Address[];
  total: number;
  page: number;
  items_per_page: number;
  message?: string;
}

const EmagAddresses: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [mainAddresses, setMainAddresses] = useState<Address[]>([]);
  const [fbeAddresses, setFbeAddresses] = useState<Address[]>([]);
  const [activeTab, setActiveTab] = useState('main');

  // Fetch addresses for an account
  const fetchAddresses = async (accountType: string) => {
    setLoading(true);
    try {
      const response = await api.get<AddressesResponse>(
        `/api/v1/emag/addresses/list?account_type=${accountType}`
      );

      if (response.data.success) {
        if (accountType === 'main') {
          setMainAddresses(response.data.addresses);
        } else {
          setFbeAddresses(response.data.addresses);
        }
        message.success(response.data.message || `Loaded ${response.data.total} addresses`);
      }
    } catch (error: any) {
      message.error(`Failed to load addresses: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load addresses on mount
  useEffect(() => {
    fetchAddresses('main');
    fetchAddresses('fbe');
  }, []);

  // Get address type label
  const getAddressTypeLabel = (typeId: number): { text: string; color: string; icon: React.ReactNode } => {
    switch (typeId) {
      case 1:
        return { text: 'Return', color: 'orange', icon: <HomeOutlined /> };
      case 2:
        return { text: 'Pickup', color: 'blue', icon: <ShopOutlined /> };
      case 3:
        return { text: 'Invoice (HQ)', color: 'green', icon: <EnvironmentOutlined /> };
      case 4:
        return { text: 'Delivery Estimates', color: 'purple', icon: <InfoCircleOutlined /> };
      default:
        return { text: 'Unknown', color: 'default', icon: <InfoCircleOutlined /> };
    }
  };

  // Table columns
  const columns: ColumnsType<Address> = [
    {
      title: 'Address ID',
      dataIndex: 'address_id',
      key: 'address_id',
      width: 120,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'address_type_id',
      key: 'address_type_id',
      width: 150,
      render: (typeId: number) => {
        const { text, color, icon } = getAddressTypeLabel(typeId);
        return (
          <Tag color={color} icon={icon}>
            {text}
          </Tag>
        );
      },
      filters: [
        { text: 'Return', value: 1 },
        { text: 'Pickup', value: 2 },
        { text: 'Invoice (HQ)', value: 3 },
        { text: 'Delivery Estimates', value: 4 },
      ],
      onFilter: (value, record) => record.address_type_id === value,
    },
    {
      title: 'Location',
      key: 'location',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{record.city}</Text>
          <Text type="secondary">{record.suburb}</Text>
          <Text>{record.address}</Text>
          {record.zipcode && <Text type="secondary">ZIP: {record.zipcode}</Text>}
        </Space>
      ),
    },
    {
      title: 'Country',
      dataIndex: 'country_code',
      key: 'country_code',
      width: 100,
      render: (code: string) => <Tag>{code}</Tag>,
    },
    {
      title: 'Details',
      key: 'details',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.quarter && <Text type="secondary">Quarter: {record.quarter}</Text>}
          {record.floor && <Text type="secondary">Floor: {record.floor}</Text>}
          <Text type="secondary">Locality ID: {record.locality_id}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_default',
      key: 'is_default',
      width: 100,
      render: (isDefault: boolean) =>
        isDefault ? (
          <Badge status="success" text="Default" />
        ) : (
          <Badge status="default" text="Standard" />
        ),
      filters: [
        { text: 'Default', value: true },
        { text: 'Standard', value: false },
      ],
      onFilter: (value, record) => record.is_default === value,
    },
  ];

  // Render address statistics
  const renderStatistics = (addresses: Address[]) => {
    const pickupCount = addresses.filter((a) => a.address_type_id === 2).length;
    const returnCount = addresses.filter((a) => a.address_type_id === 1).length;
    const defaultCount = addresses.filter((a) => a.is_default).length;

    return (
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Addresses"
              value={addresses.length}
              prefix={<EnvironmentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Pickup Addresses"
              value={pickupCount}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Return Addresses"
              value={returnCount}
              prefix={<HomeOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Default Addresses"
              value={defaultCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  // Render address table
  const renderAddressTable = (addresses: Address[], accountType: string) => (
    <div>
      {renderStatistics(addresses)}
      <Card
        title={
          <Space>
            <EnvironmentOutlined />
            <span>{accountType.toUpperCase()} Account Addresses</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchAddresses(accountType)}
            loading={loading}
          >
            Refresh
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={addresses}
          rowKey="address_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} addresses`,
          }}
          expandable={{
            expandedRowRender: (record) => (
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="Address ID">{record.address_id}</Descriptions.Item>
                <Descriptions.Item label="Country ID">{record.country_id}</Descriptions.Item>
                <Descriptions.Item label="Locality ID">{record.locality_id}</Descriptions.Item>
                <Descriptions.Item label="Country Code">{record.country_code}</Descriptions.Item>
                <Descriptions.Item label="Suburb">{record.suburb}</Descriptions.Item>
                <Descriptions.Item label="City">{record.city}</Descriptions.Item>
                <Descriptions.Item label="Address" span={2}>
                  {record.address}
                </Descriptions.Item>
                <Descriptions.Item label="Zipcode">{record.zipcode || 'N/A'}</Descriptions.Item>
                <Descriptions.Item label="Quarter">{record.quarter || 'N/A'}</Descriptions.Item>
                <Descriptions.Item label="Floor">{record.floor || 'N/A'}</Descriptions.Item>
                <Descriptions.Item label="Default">
                  {record.is_default ? (
                    <Tag color="success">Yes</Tag>
                  ) : (
                    <Tag>No</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            ),
          }}
        />
      </Card>
    </div>
  );

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <EnvironmentOutlined /> eMAG Saved Addresses
      </Title>
      <Alert
        message="NEW in eMAG API v4.4.9"
        description="Manage your saved pickup and return addresses. These addresses can be used when creating AWBs (Air Waybills) for orders and returns, simplifying the shipping process."
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 24 }}
      />

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <span>
                <ShopOutlined />
                MAIN Account
              </span>
            }
            key="main"
          >
            {renderAddressTable(mainAddresses, 'main')}
          </TabPane>
          <TabPane
            tab={
              <span>
                <HomeOutlined />
                FBE Account
              </span>
            }
            key="fbe"
          >
            {renderAddressTable(fbeAddresses, 'fbe')}
          </TabPane>
        </Tabs>
      </Card>

      <Card style={{ marginTop: 24 }} title="Address Types Reference">
        <Descriptions bordered column={1}>
          <Descriptions.Item label={<Tag color="blue" icon={<ShopOutlined />}>Pickup (Type 2)</Tag>}>
            Address used as sender location when creating AWBs for customer orders
          </Descriptions.Item>
          <Descriptions.Item label={<Tag color="orange" icon={<HomeOutlined />}>Return (Type 1)</Tag>}>
            Address used as receiver location when creating AWBs for product returns (RMA)
          </Descriptions.Item>
          <Descriptions.Item label={<Tag color="green" icon={<EnvironmentOutlined />}>Invoice HQ (Type 3)</Tag>}>
            Company headquarters address for invoicing purposes
          </Descriptions.Item>
          <Descriptions.Item label={<Tag color="purple" icon={<InfoCircleOutlined />}>Delivery Estimates (Type 4)</Tag>}>
            Address used for calculating delivery time estimates
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default EmagAddresses;
