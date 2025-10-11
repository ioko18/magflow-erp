import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  message,
  Statistic,
  Row,
  Col,
  Descriptions,
  Alert,
  Spin,
  Typography,
  Divider,
  Badge,
  Tooltip,
  Select,
} from 'antd';
import {
  FileTextOutlined,
  FilePdfOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  DownloadOutlined,
  SendOutlined,
  EyeOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface Order {
  id: string;
  emag_order_id: number;
  status: number;
  status_name: string;
  customer_name: string;
  customer_email: string;
  total_amount: number;
  currency: string;
  order_date: string;
  invoice_url?: string;
  invoice_uploaded_at?: string;
  account_type: string;
  products: any[];
}

interface InvoiceData {
  invoice_number: string;
  invoice_date: string;
  order_id: number;
  order_date?: string;
  seller: any;
  customer: any;
  products: any[];
  subtotal: number;
  vat_amount: number;
  shipping?: number;
  total: number;
  currency: string;
}

interface InvoiceStats {
  total_orders: number;
  pending_invoice: number;
  generated_today: number;
  total_value: number;
}

const EmagInvoices: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<InvoiceStats>({
    total_orders: 0,
    pending_invoice: 0,
    generated_today: 0,
    total_value: 0,
  });
  const [loading, setLoading] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [invoiceData, setInvoiceData] = useState<InvoiceData | null>(null);
  const [accountType, setAccountType] = useState<string>('main');
  const [customInvoiceUrl, setCustomInvoiceUrl] = useState<string>('');
  const [form] = Form.useForm();

  useEffect(() => {
    loadOrders();
  }, [accountType]);

  const loadOrders = async () => {
    setLoading(true);
    try {
      // Load finalized orders (status 4)
      const response = await api.get(`/emag/orders/list`, {
        params: {
          account_type: accountType,
          status: 4, // Finalized orders
          page: 1,
          items_per_page: 100,
        },
      });

      if (response.data.success) {
        const ordersList = response.data.orders || [];
        setOrders(ordersList);
        
        // Calculate stats
        const pending = ordersList.filter((o: Order) => !o.invoice_url).length;
        const withInvoice = ordersList.filter((o: Order) => o.invoice_url).length;
        const totalValue = ordersList.reduce((sum: number, o: Order) => sum + o.total_amount, 0);
        
        setStats({
          total_orders: ordersList.length,
          pending_invoice: pending,
          generated_today: withInvoice,
          total_value: totalValue,
        });
      }
    } catch (error: any) {
      console.error('Failed to load orders:', error);
      message.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const loadInvoiceData = async (orderId: number) => {
    setLoading(true);
    try {
      const response = await api.get(`/emag/phase2/invoice/${orderId}/data`, {
        params: { account_type: accountType },
      });

      if (response.data.success) {
        setInvoiceData(response.data.invoice_data);
        return response.data.invoice_data;
      }
    } catch (error: any) {
      console.error('Failed to load invoice data:', error);
      message.error('Failed to load invoice data');
    } finally {
      setLoading(false);
    }
    return null;
  };

  const handlePreviewInvoice = async (order: Order) => {
    setSelectedOrder(order);
    const data = await loadInvoiceData(order.emag_order_id);
    if (data) {
      setPreviewModalVisible(true);
    }
  };

  const handleGenerateInvoice = async () => {
    if (!selectedOrder) return;

    setLoading(true);
    try {
      const response = await api.post(
        `/emag/phase2/invoice/${selectedOrder.emag_order_id}/generate`,
        {
          account_type: accountType,
          invoice_url: customInvoiceUrl || null,
        }
      );

      if (response.data.success) {
        message.success(
          `Invoice ${response.data.invoice_number} generated and attached successfully!`
        );
        setGenerateModalVisible(false);
        setCustomInvoiceUrl('');
        form.resetFields();
        loadOrders();
      }
    } catch (error: any) {
      console.error('Failed to generate invoice:', error);
      message.error(error.response?.data?.detail || 'Failed to generate invoice');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkGenerate = async () => {
    const pendingOrders = orders.filter(o => !o.invoice_url);
    
    if (pendingOrders.length === 0) {
      message.warning('No orders pending invoice generation');
      return;
    }

    Modal.confirm({
      title: 'Bulk Generate Invoices',
      content: `Generate invoices for ${pendingOrders.length} orders?`,
      onOk: async () => {
        setLoading(true);
        try {
          const response = await api.post('/emag/phase2/invoice/bulk-generate', {
            account_type: accountType,
            order_ids: pendingOrders.map(o => o.emag_order_id),
          });

          if (response.data.success) {
            message.success(
              `Generated ${response.data.success_count} invoices successfully!`
            );
            if (response.data.failed_count > 0) {
              message.warning(`${response.data.failed_count} invoices failed`);
            }
            loadOrders();
          }
        } catch (error: any) {
          console.error('Bulk invoice generation failed:', error);
          message.error('Failed to generate invoices');
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
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Amount',
      key: 'amount',
      width: 120,
      render: (_, record) => (
        <Text strong style={{ color: '#52c41a' }}>
          {record.total_amount.toFixed(2)} {record.currency}
        </Text>
      ),
    },
    {
      title: 'Products',
      dataIndex: 'products',
      key: 'products',
      width: 100,
      render: (products: any[]) => (
        <Badge count={products?.length || 0} showZero style={{ backgroundColor: '#1890ff' }} />
      ),
    },
    {
      title: 'Invoice Status',
      key: 'invoice_status',
      width: 150,
      render: (_, record) => (
        record.invoice_url ? (
          <Space direction="vertical" size="small">
            <Tag color="green" icon={<CheckCircleOutlined />}>
              Generated
            </Tag>
            {record.invoice_uploaded_at && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {new Date(record.invoice_uploaded_at).toLocaleDateString()}
              </Text>
            )}
          </Space>
        ) : (
          <Tag color="orange" icon={<ClockCircleOutlined />}>
            Pending
          </Tag>
        )
      ),
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
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Preview Invoice Data">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreviewInvoice(record)}
            />
          </Tooltip>
          
          {!record.invoice_url ? (
            <Tooltip title="Generate Invoice">
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
          ) : (
            <Tooltip title="Download Invoice">
              <Button
                size="small"
                icon={<DownloadOutlined />}
                href={record.invoice_url}
                target="_blank"
              >
                Download
              </Button>
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
          <FilePdfOutlined /> Invoice Management
        </Title>
        <Text type="secondary">
          Generate and manage invoices for finalized eMAG orders
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
              title="Pending Invoice"
              value={stats.pending_invoice}
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
              title="Total Value"
              value={stats.total_value.toFixed(2)}
              prefix={<DollarOutlined />}
              suffix="RON"
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
            <Badge count={stats.pending_invoice} showZero>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleBulkGenerate}
                disabled={stats.pending_invoice === 0}
              >
                Bulk Generate Invoices
              </Button>
            </Badge>
          </Space>
        </Space>

        {stats.pending_invoice > 0 && (
          <Alert
            message={`${stats.pending_invoice} orders are ready for invoice generation`}
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
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Generate Invoice Modal */}
      <Modal
        title={
          <Space>
            <FilePdfOutlined />
            <span>Generate Invoice for Order #{selectedOrder?.emag_order_id}</span>
          </Space>
        }
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false);
          setCustomInvoiceUrl('');
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
                  <Descriptions.Item label="Email">
                    {selectedOrder.customer_email}
                  </Descriptions.Item>
                  <Descriptions.Item label="Total Amount">
                    <Text strong style={{ color: '#52c41a' }}>
                      {selectedOrder.total_amount} {selectedOrder.currency}
                    </Text>
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
              onFinish={handleGenerateInvoice}
            >
              <Alert
                message="Invoice Generation Options"
                description="Leave URL empty to auto-generate invoice PDF, or provide a custom invoice URL"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                name="invoice_url"
                label="Custom Invoice URL (Optional)"
              >
                <Input
                  placeholder="https://your-storage.com/invoices/invoice.pdf"
                  value={customInvoiceUrl}
                  onChange={(e) => setCustomInvoiceUrl(e.target.value)}
                  prefix={<FilePdfOutlined />}
                />
              </Form.Item>

              <Divider />

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setGenerateModalVisible(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    icon={<SendOutlined />}
                  >
                    Generate & Attach Invoice
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* Preview Invoice Data Modal */}
      <Modal
        title={
          <Space>
            <EyeOutlined />
            <span>Invoice Preview - Order #{selectedOrder?.emag_order_id}</span>
          </Space>
        }
        open={previewModalVisible}
        onCancel={() => {
          setPreviewModalVisible(false);
          setInvoiceData(null);
        }}
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            Close
          </Button>,
          <Button
            key="generate"
            type="primary"
            icon={<SendOutlined />}
            onClick={() => {
              setPreviewModalVisible(false);
              setGenerateModalVisible(true);
            }}
          >
            Generate Invoice
          </Button>,
        ]}
        width={800}
      >
        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        )}

        {!loading && invoiceData && (
          <div>
            <Descriptions title="Invoice Details" column={2} bordered size="small">
              <Descriptions.Item label="Invoice Number" span={2}>
                <Text strong code>{invoiceData.invoice_number}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Invoice Date">
                {invoiceData.invoice_date}
              </Descriptions.Item>
              <Descriptions.Item label="Order Date">
                {invoiceData.order_date}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">Seller Information</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Company">
                {invoiceData.seller.name}
              </Descriptions.Item>
              <Descriptions.Item label="CUI">
                {invoiceData.seller.cui}
              </Descriptions.Item>
              <Descriptions.Item label="Address">
                {invoiceData.seller.address}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">Customer Information</Divider>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Name">
                {invoiceData.customer.name}
              </Descriptions.Item>
              <Descriptions.Item label="Email">
                {invoiceData.customer.email}
              </Descriptions.Item>
              <Descriptions.Item label="Phone">
                {invoiceData.customer.phone}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">Products</Divider>
            <Table
              size="small"
              dataSource={invoiceData.products}
              pagination={false}
              columns={[
                {
                  title: '#',
                  dataIndex: 'line_number',
                  width: 50,
                },
                {
                  title: 'Product',
                  dataIndex: 'name',
                },
                {
                  title: 'SKU',
                  dataIndex: 'sku',
                  width: 100,
                },
                {
                  title: 'Qty',
                  dataIndex: 'quantity',
                  width: 60,
                },
                {
                  title: 'Price',
                  dataIndex: 'unit_price',
                  width: 100,
                  render: (price: number) => `${price.toFixed(2)} ${invoiceData.currency}`,
                },
                {
                  title: 'Total',
                  dataIndex: 'total',
                  width: 100,
                  render: (total: number) => (
                    <Text strong>{total.toFixed(2)} {invoiceData.currency}</Text>
                  ),
                },
              ]}
            />

            <Divider />

            <Row gutter={16}>
              <Col span={12} offset={12}>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text>Subtotal:</Text>
                      <Text>{invoiceData.subtotal.toFixed(2)} {invoiceData.currency}</Text>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text>VAT:</Text>
                      <Text>{invoiceData.vat_amount.toFixed(2)} {invoiceData.currency}</Text>
                    </div>
                    {invoiceData.shipping && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>Shipping:</Text>
                        <Text>{invoiceData.shipping.toFixed(2)} {invoiceData.currency}</Text>
                      </div>
                    )}
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text strong style={{ fontSize: 16 }}>Total:</Text>
                      <Text strong style={{ fontSize: 16, color: '#52c41a' }}>
                        {invoiceData.total.toFixed(2)} {invoiceData.currency}
                      </Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default EmagInvoices;
