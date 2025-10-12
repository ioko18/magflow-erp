/**
 * Order Details Modal Component
 *
 * Displays comprehensive information about a specific eMAG order
 * including customer details, products, payment info, and order history.
 */

import React from 'react';
import {
  Modal,
  Descriptions,
  Tag,
  Table,
  Divider,
  Typography,
  Space,
  Alert,
  Button,
  Row,
  Col,
  Card,
  Statistic,
  message,
} from 'antd';
import {
  ShoppingOutlined,
  UserOutlined,
  FileTextOutlined,
  DollarOutlined,
  CalendarOutlined,
  CopyOutlined,
  DownloadOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { EmagOrderDetails } from '../../types/api';

const { Text } = Typography;

interface OrderDetailsModalProps {
  visible: boolean;
  onClose: () => void;
  order: EmagOrderDetails | null;
  loading?: boolean;
}

const OrderDetailsModal: React.FC<OrderDetailsModalProps> = ({
  visible,
  onClose,
  order,
  loading = false,
}) => {
  console.log('🔍 OrderDetailsModal RENDER:', {
    visible,
    hasOrder: !!order,
    orderId: order?.emag_order_id,
    loading,
    timestamp: new Date().toISOString()
  });

  if (!order) {
    console.log('❌ OrderDetailsModal: No order data provided');
    return null;
  }

  // Validate order data structure
  if (!order.emag_order_id) {
    console.error('❌ OrderDetailsModal: Invalid order data - missing emag_order_id', order);
    return (
      <Modal
        title="Eroare Date Comandă"
        open={visible}
        onCancel={onClose}
        footer={[
          <Button key="close" onClick={onClose}>Închide</Button>
        ]}
      >
        <Alert
          message="Date comandă incomplete"
          description={`Comanda nu are ID eMAG valid. Date primite: ${order ? JSON.stringify(order, null, 2) : 'Order is null'}`}
          type="error"
          showIcon
        />
      </Modal>
    );
  }

  console.log('✅ OrderDetailsModal: Rendering modal with order:', order?.emag_order_id);
  console.log('📋 Full order data:', order ? JSON.stringify(order, null, 2) : 'Order is null');

  const formatCurrency = (amount: number, currency: string) => {
    console.log('💰 formatCurrency called:', { amount, currency });
    return `${amount?.toLocaleString?.('ro-RO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) || 0} ${currency || 'RON'}`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '—';
    try {
      return new Date(dateString).toLocaleString('ro-RO');
    } catch {
      return '—';
    }
  };

  const getStatusColor = (status: string) => {
    const statusColors: Record<string, string> = {
      new: 'blue',
      in_progress: 'processing',
      prepared: 'orange',
      finalized: 'success',
      returned: 'magenta',
      canceled: 'error',
    };
    return statusColors[status] || 'default';
  };

  const getSyncStatusColor = (status: string) => {
    const syncColors: Record<string, string> = {
      synced: 'success',
      pending: 'processing',
      failed: 'error',
      never_synced: 'default',
    };
    return syncColors[status] || 'default';
  };

  const productColumns = [
    {
      title: 'Produs',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name || record.name || 'N/A'}</Text>
          {(record.sku || record.sku) && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              SKU: {record.sku || record.sku}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Cantitate',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'center' as const,
      render: (quantity: number, record: any) => quantity || record.quantity || 1,
    },
    {
      title: 'Preț',
      dataIndex: 'sale_price',
      key: 'price',
      align: 'right' as const,
      render: (price: number, record: any) => {
        const displayPrice = price || record.sale_price || record.price || 0;
        return formatCurrency(displayPrice, order.currency);
      },
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      align: 'right' as const,
      render: (total: number, record: any) => {
        const calculatedTotal = total || (record.quantity || 1) * (record.sale_price || record.price || 0);
        return formatCurrency(calculatedTotal, order.currency);
      },
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <ShoppingOutlined />
          <span>Detalii Comandă eMAG</span>
          <Tag color="blue">{order?.emag_order_id || 'N/A'}</Tag>
          <Tag color={order?.account_type === 'main' ? 'blue' : 'green'}>
            {order?.account_type?.toUpperCase() || 'UNKNOWN'}
          </Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1000}
      style={{ top: 20 }}
      styles={{
        body: {
          maxHeight: '70vh',
          overflowY: 'auto'
        }
      }}
      footer={[
        <Button key="close" onClick={onClose}>
          Închide
        </Button>,
        order.invoice_url && (
          <Button
            key="invoice"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => {
              try {
                // Use noopener and noreferrer to prevent cross-origin access issues
                const newWindow = window.open(order?.invoice_url || '', '_blank', 'noopener,noreferrer');
                if (!newWindow) {
                  // Fallback if popup is blocked
                  console.warn('Popup blocked, cannot open invoice');
                  message.warning('Popup-ul a fost blocat. Te rugăm să permiteți popup-urile pentru acest site.');
                }
              } catch (error) {
                console.error('Error opening invoice:', error);
                message.error('Nu s-a putut deschide factura. Te rugăm să încerci din nou.');
              }
            }}
          >
            Vezi Factură
          </Button>
        ),
      ].filter(Boolean)}
      loading={loading}
      destroyOnHidden
    >
      <div style={{ padding: '16px' }}>
        <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: '#f0f0f0', borderRadius: '4px' }}>
          <strong>🔍 DEBUG INFO:</strong><br />
          Order ID: {order?.emag_order_id || 'N/A'}<br />
          Status: {order?.status_name || 'N/A'}<br />
          Total: {order?.total_amount || 0} {order?.currency || 'RON'}<br />
          Products: {order?.products?.length || 0} items<br />
          Customer: {order?.customer_name || 'N/A'}
        </div>

        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Order Overview */}
          <Card size="small">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Status Comandă"
                  value={order?.status_name || 'Unknown'}
                  valueStyle={{
                    color: getStatusColor(order?.status_name || 'unknown'),
                    textTransform: 'capitalize',
                  }}
                  prefix={<TagOutlined />}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Valoare Totală"
                  value={order?.total_amount || 0}
                  precision={2}
                  suffix={order?.currency || 'RON'}
                  prefix={<DollarOutlined />}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Data Comandă"
                  value={formatDate(order?.order_date || undefined)}
                  prefix={<CalendarOutlined />}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Status Sync"
                  value={order?.sync_status || 'unknown'}
                  valueStyle={{
                    color: getSyncStatusColor(order?.sync_status || 'unknown'),
                    textTransform: 'capitalize',
                  }}
                  prefix={<CopyOutlined />}
                />
              </Col>
            </Row>
          </Card>

          <Row gutter={[16, 16]}>
            {/* Customer Information */}
            <Col xs={24} lg={12}>
              <Card title={<><UserOutlined /> Informații Client</>} size="small">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Nume">
                    {order?.customer_name || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Email">
                    {order?.customer_email || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Telefon">
                    {order?.customer_phone || '—'}
                  </Descriptions.Item>
                </Descriptions>

                {order?.shipping_address && (
                  <>
                    <Divider style={{ margin: '12px 0' }} />
                    <Typography.Title level={5}>Adresă Livrare</Typography.Title>
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="Contact">
                        {order?.shipping_address?.contact || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Telefon">
                        {order?.shipping_address?.phone || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Țară">
                        {order?.shipping_address?.country || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Oraș">
                        {order?.shipping_address?.city || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Stradă">
                        {order?.shipping_address?.street || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Cod Poștal">
                        {order?.shipping_address?.postal_code || '—'}
                      </Descriptions.Item>
                    </Descriptions>
                  </>
                )}
              </Card>
            </Col>

            {/* Order Information */}
            <Col xs={24} lg={12}>
              <Card title={<><FileTextOutlined /> Detalii Comandă</>} size="small">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="ID Comandă">
                    {order?.emag_order_id || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Metodă Plată">
                    {order?.payment_method ? (
                      <Tag color="blue">{order.payment_method}</Tag>
                    ) : (
                      '—'
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="Status Plată">
                    {order?.payment_status ? (
                      <Tag color={order.payment_status === 1 ? 'success' : 'warning'}>
                        {order.payment_status === 1 ? 'Plătit' : 'Neplătit'}
                      </Tag>
                    ) : (
                      '—'
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="Mod Livrare">
                    {order?.delivery_mode ? (
                      <Tag color="green">{order.delivery_mode}</Tag>
                    ) : (
                      '—'
                    )}
                  </Descriptions.Item>
                  {order?.awb_number && (
                    <Descriptions.Item label="AWB">
                      <Text code copyable>{order.awb_number}</Text>
                    </Descriptions.Item>
                  )}
                </Descriptions>

                <Divider style={{ margin: '12px 0' }} />
                <Typography.Title level={5}>Timestamps</Typography.Title>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Data Comandă">
                    {formatDate(order?.order_date || undefined)}
                  </Descriptions.Item>
                  {order?.acknowledged_at && (
                    <Descriptions.Item label="Confirmată la">
                      {formatDate(order.acknowledged_at)}
                    </Descriptions.Item>
                  )}
                  {order?.finalized_at && (
                    <Descriptions.Item label="Finalizată la">
                      {formatDate(order.finalized_at)}
                    </Descriptions.Item>
                  )}
                  <Descriptions.Item label="Ultima Sincronizare">
                    {formatDate(order?.last_synced_at || undefined)}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          {/* Products */}
          <Card title={<><ShoppingOutlined /> Produse</>} size="small">
            <Table
              dataSource={order?.products || []}
              columns={productColumns}
              rowKey={(record) => `${record.id || record.sku || Math.random()}`}
              pagination={false}
              size="small"
              scroll={{ x: 600 }}
              summary={(pageData) => {
                const totalQuantity = pageData.reduce((sum, item) => sum + (item.quantity || 1), 0);
                const totalValue = pageData.reduce((sum, item) => {
                  const quantity = item.quantity || 1;
                  const price = item.sale_price || item.price || 0;
                  return sum + (quantity * price);
                }, 0);

                return (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0}>Total</Table.Summary.Cell>
                    <Table.Summary.Cell index={1} align="center">
                      <Text strong>{totalQuantity}</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2} />
                    <Table.Summary.Cell index={3} align="right">
                      <Text strong>{formatCurrency(totalValue, order?.currency)}</Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                );
              }}
            />
          </Card>

          {/* Additional Information */}
          {order?.vouchers && order.vouchers.length > 0 && (
            <Card title="Vouchere" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                {order.vouchers.map((voucher, index) => (
                  <Alert
                    key={index}
                    message={`Voucher aplicat: ${voucher.code || 'N/A'}`}
                    description={`Valoare: ${formatCurrency(voucher.amount || 0, order?.currency)}`}
                    type="info"
                    showIcon
                  />
                ))}
              </Space>
            </Card>
          )}
        </Space>
      </div>
    </Modal>
  );
};

export default OrderDetailsModal;
