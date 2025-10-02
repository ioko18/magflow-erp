import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Select,
  message,
  Statistic,
  Row,
  Col,
  Descriptions,
  Alert,
  Tooltip,
  Badge,
  Typography,
  Divider,
} from 'antd';
import {
  TruckOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  SearchOutlined,
  BarcodeOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface Order {
  id: string;
  emag_order_id: number;
  status: number;
  status_name: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  total_amount: number;
  currency: string;
  order_date: string;
  awb_number?: string;
  courier_name?: string;
  account_type: string;
  products: any[];
  shipping_address: any;
}

interface CourierAccount {
  id: number;
  name: string;
  courier_name: string;
  is_active: boolean;
}

interface AWBStats {
  total_orders: number;
  pending_awb: number;
  generated_today: number;
  in_transit: number;
}

const EmagAWB: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [couriers, setCouriers] = useState<CourierAccount[]>([]);
  const [stats, setStats] = useState<AWBStats>({
    total_orders: 0,
    pending_awb: 0,
    generated_today: 0,
    in_transit: 0,
  });
  const [loading, setLoading] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [accountType, setAccountType] = useState<string>('main');
  const [form] = Form.useForm();

  useEffect(() => {
    loadCouriers();
    loadOrders();
  }, [accountType]);

  const loadCouriers = async () => {
    try {
      const response = await api.get(`/emag/phase2/awb/couriers`, {
        params: { account_type: accountType },
      });
      if (response.data.success) {
        setCouriers(response.data.couriers || []);
      }
    } catch (error: any) {
      console.error('Failed to load couriers:', error);
      message.error('Failed to load courier accounts');
    }
  };

  const loadOrders = async () => {
    setLoading(true);
    try {
      // Load orders from eMAG orders endpoint
      const response = await api.get(`/emag/orders/list`, {
        params: {
          account_type: accountType,
          status: 3, // Prepared orders ready for AWB
          page: 1,
          items_per_page: 100,
        },
      });

      if (response.data.success) {
        const ordersList = response.data.orders || [];
        setOrders(ordersList);
        
        // Calculate stats
        const pending = ordersList.filter((o: Order) => !o.awb_number).length;
        const withAwb = ordersList.filter((o: Order) => o.awb_number).length;
        
        setStats({
          total_orders: ordersList.length,
          pending_awb: pending,
          generated_today: withAwb,
          in_transit: withAwb,
        });
      }
    } catch (error: any) {
      console.error('Failed to load orders:', error);
      message.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAWB = async (values: any) => {
    if (!selectedOrder) return;

    setLoading(true);
    try {
      const response = await api.post(
        `/emag/phase2/awb/${selectedOrder.emag_order_id}/generate`,
        {
          account_type: accountType,
          courier_account_id: values.courier_account_id,
          packages: values.packages || null,
        }
      );

      if (response.data.success) {
        message.success(`AWB ${response.data.awb_number} generated successfully!`);
        setGenerateModalVisible(false);
        form.resetFields();
        loadOrders();
      }
    } catch (error: any) {
      console.error('Failed to generate AWB:', error);
      message.error(error.response?.data?.detail || 'Failed to generate AWB');
    } finally {
      setLoading(false);
    }
  };

  const handleTrackAWB = async (awbNumber: string) => {
    setLoading(true);
    try {
      const response = await api.get(`/emag/phase2/awb/${awbNumber}`, {
        params: { account_type: accountType },
      });

      if (response.data.success) {
        Modal.info({
          title: `AWB Tracking: ${awbNumber}`,
          width: 600,
          content: (
            <div>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="AWB Number">
                  {awbNumber}
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  <Tag color="blue">In Transit</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Courier">
                  {response.data.data?.courier_name || 'N/A'}
                </Descriptions.Item>
                <Descriptions.Item label="Last Update">
                  {new Date().toLocaleString()}
                </Descriptions.Item>
              </Descriptions>
            </div>
          ),
        });
      }
    } catch (error: any) {
      console.error('Failed to track AWB:', error);
      message.error('Failed to fetch AWB tracking details');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkGenerate = async () => {
    const pendingOrders = orders.filter(o => !o.awb_number && o.status === 3);
    
    if (pendingOrders.length === 0) {
      message.warning('No orders pending AWB generation');
      return;
    }

    Modal.confirm({
      title: 'Bulk Generate AWBs',
      content: `Generate AWBs for ${pendingOrders.length} orders?`,
      onOk: async () => {
        setLoading(true);
        try {
          const defaultCourier = couriers.find(c => c.is_active);
          if (!defaultCourier) {
            message.error('No active courier account found');
            return;
          }

          const response = await api.post('/emag/phase2/awb/bulk-generate', {
            account_type: accountType,
            courier_account_id: defaultCourier.id,
            orders: pendingOrders.map(o => ({ order_id: o.emag_order_id })),
          });

          if (response.data.success) {
            message.success(
              `Generated ${response.data.success_count} AWBs successfully!`
            );
            if (response.data.failed_count > 0) {
              message.warning(`${response.data.failed_count} AWBs failed`);
            }
            loadOrders();
          }
        } catch (error: any) {
          console.error('Bulk AWB generation failed:', error);
          message.error('Failed to generate AWBs');
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const columns: ColumnsType<Order> = [
    {
      title: 'Order ID',
      dataIndex: 'emag_order_id',
      key: 'emag_order_id',
      width: 100,
      render: (id: number) => <Text strong>#{id}</Text>,
    },
    {
      title: 'Customer',
      key: 'customer',
      width: 200,
      render: (_, record) => (
        <div>
          <div><Text strong>{record.customer_name}</Text></div>
          <div><Text type="secondary" style={{ fontSize: 12 }}>{record.customer_email}</Text></div>
        </div>
      ),
    },
    {
      title: 'Order Date',
      dataIndex: 'order_date',
      key: 'order_date',
      width: 150,
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Total',
      key: 'total',
      width: 120,
      render: (_, record) => (
        <Text strong>{record.total_amount} {record.currency}</Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status_name',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const statusConfig: Record<string, { color: string; icon: any }> = {
          prepared: { color: 'orange', icon: <ClockCircleOutlined /> },
          finalized: { color: 'green', icon: <CheckCircleOutlined /> },
          in_progress: { color: 'blue', icon: <ClockCircleOutlined /> },
        };
        const config = statusConfig[status] || { color: 'default', icon: null };
        return (
          <Tag color={config.color} icon={config.icon}>
            {status.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'AWB Number',
      dataIndex: 'awb_number',
      key: 'awb_number',
      width: 150,
      render: (awb: string) => (
        awb ? (
          <Space>
            <Tag color="green" icon={<BarcodeOutlined />}>{awb}</Tag>
            <Button
              type="link"
              size="small"
              icon={<SearchOutlined />}
              onClick={() => handleTrackAWB(awb)}
            >
              Track
            </Button>
          </Space>
        ) : (
          <Tag color="red">Pending</Tag>
        )
      ),
    },
    {
      title: 'Courier',
      dataIndex: 'courier_name',
      key: 'courier_name',
      width: 120,
      render: (courier: string) => courier || <Text type="secondary">-</Text>,
    },
    {
      title: 'Account',
      dataIndex: 'account_type',
      key: 'account_type',
      width: 80,
      render: (type: string) => (
        <Tag color={type === 'main' ? 'blue' : 'purple'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {!record.awb_number && record.status === 3 && (
            <Tooltip title="Generate AWB">
              <Button
                type="primary"
                size="small"
                icon={<SendOutlined />}
                onClick={() => {
                  setSelectedOrder(record);
                  setGenerateModalVisible(true);
                }}
              >
                Generate
              </Button>
            </Tooltip>
          )}
          {record.awb_number && (
            <Tooltip title="View Details">
              <Button
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => {
                  Modal.info({
                    title: 'Order Details',
                    width: 700,
                    content: (
                      <Descriptions column={2} bordered size="small">
                        <Descriptions.Item label="Order ID" span={2}>
                          #{record.emag_order_id}
                        </Descriptions.Item>
                        <Descriptions.Item label="Customer">
                          {record.customer_name}
                        </Descriptions.Item>
                        <Descriptions.Item label="Phone">
                          {record.customer_phone}
                        </Descriptions.Item>
                        <Descriptions.Item label="AWB" span={2}>
                          <Tag color="green">{record.awb_number}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="Courier" span={2}>
                          {record.courier_name}
                        </Descriptions.Item>
                        <Descriptions.Item label="Products" span={2}>
                          {record.products?.length || 0} items
                        </Descriptions.Item>
                      </Descriptions>
                    ),
                  });
                }}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <TruckOutlined /> AWB Management
        </Title>
        <Text type="secondary">
          Generate and manage Air Waybills for eMAG orders
        </Text>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Orders"
              value={stats.total_orders}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Pending AWB"
              value={stats.pending_awb}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Generated Today"
              value={stats.generated_today}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="In Transit"
              value={stats.in_transit}
              prefix={<TruckOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters and Actions */}
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Select
              value={accountType}
              onChange={setAccountType}
              style={{ width: 150 }}
            >
              <Option value="main">MAIN Account</Option>
              <Option value="fbe">FBE Account</Option>
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadOrders}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
          <Space>
            <Badge count={stats.pending_awb} showZero>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleBulkGenerate}
                disabled={stats.pending_awb === 0}
              >
                Bulk Generate AWBs
              </Button>
            </Badge>
          </Space>
        </Space>

        {stats.pending_awb > 0 && (
          <Alert
            message={`${stats.pending_awb} orders are ready for AWB generation`}
            type="warning"
            showIcon
            icon={<WarningOutlined />}
            closable
          />
        )}
      </Card>

      {/* Orders Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} orders`,
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* Generate AWB Modal */}
      <Modal
        title={
          <Space>
            <SendOutlined />
            <span>Generate AWB for Order #{selectedOrder?.emag_order_id}</span>
          </Space>
        }
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        {selectedOrder && (
          <>
            <Alert
              message="Order Information"
              description={
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Customer">
                    {selectedOrder.customer_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Address">
                    {selectedOrder.shipping_address?.address || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Products">
                    {selectedOrder.products?.length || 0} items
                  </Descriptions.Item>
                </Descriptions>
              }
              type="info"
              style={{ marginBottom: 16 }}
            />

            <Form
              form={form}
              layout="vertical"
              onFinish={handleGenerateAWB}
            >
              <Form.Item
                name="courier_account_id"
                label="Courier Service"
                rules={[{ required: true, message: 'Please select a courier' }]}
              >
                <Select
                  placeholder="Select courier service"
                  loading={couriers.length === 0}
                >
                  {couriers.map((courier) => (
                    <Option key={courier.id} value={courier.id}>
                      <Space>
                        <TruckOutlined />
                        {courier.courier_name}
                        {courier.is_active && <Tag color="green">Active</Tag>}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Divider />

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setGenerateModalVisible(false)}>
                    Cancel
                  </Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    Generate AWB
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </div>
  );
};

export default EmagAWB;
