import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Skeleton,
  Result,
  Button,
  message,
  Row,
  Col,
  Statistic,
  Form,
  DatePicker,
  Input,
  InputNumber,
  Alert,
  Space,
  Typography,
  Divider,
  Tag,
} from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import type { PurchaseOrder, PurchaseOrderLine } from '../../types/purchaseOrder';

type LineFormState = {
  line: PurchaseOrderLine;
  pendingQuantity: number;
};

const ReceivePurchaseOrderPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [receiptDate, setReceiptDate] = useState<Dayjs>(dayjs());
  const [generalNotes, setGeneralNotes] = useState('');
  const [lineStates, setLineStates] = useState<Record<number, { receive: number; notes: string }>>({});
  const [submitting, setSubmitting] = useState(false);

  const loadOrder = async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError(null);
      const response = await purchaseOrdersApi.get(Number(id));

      if (response.status === 'success' && response.data) {
        const respData = response.data as any;
        const fetchedOrder = (respData.purchase_order ?? respData) as PurchaseOrder;
        setOrder(fetchedOrder);
        const initialStates: Record<number, { receive: number; notes: string }> = {};
        fetchedOrder.lines.forEach((line) => {
          if (!line.id) return;
          const pending = (line.quantity ?? 0) - (line.received_quantity ?? 0);
          initialStates[line.id] = {
            receive: pending > 0 ? pending : 0,
            notes: '',
          };
        });
        setLineStates(initialStates);
      } else {
        setError(response.message || 'Unable to load purchase order');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load purchase order');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadOrder();
  }, [id]);

  const refresh = async () => {
    await loadOrder();
  };

  const handleSubmit = async () => {
    if (!order) {
      return;
    }

    const receiptLines = order.lines
      .filter((line) => line.id)
      .map((line) => {
        const state = lineStates[line.id!];
        const receiveQty = state?.receive ?? 0;
        return {
          line,
          pending: (line.quantity ?? 0) - (line.received_quantity ?? 0),
          receiveQty,
          note: state?.notes ?? '',
        };
      })
      .filter((entry) => entry.receiveQty > 0);

    if (receiptLines.length === 0) {
      message.warning('Please enter at least one quantity to receive');
      return;
    }

    for (const entry of receiptLines) {
      if (entry.receiveQty < 0) {
        message.error('Received quantity cannot be negative');
        return;
      }
      if (entry.receiveQty > entry.pending) {
        message.error('Received quantity cannot exceed pending amount');
        return;
      }
    }

    try {
      setSubmitting(true);
      await purchaseOrdersApi.receive(order.id!, {
        receipt_date: receiptDate.format('YYYY-MM-DD'),
        notes: generalNotes || undefined,
        lines: receiptLines.map((entry) => ({
          purchase_order_line_id: entry.line.id!,
          received_quantity: entry.receiveQty,
          notes: entry.note || undefined,
        })),
      });

      message.success('Items received successfully');
      navigate(`/purchase-orders/${order.id}`);
    } catch (err: any) {
      const apiError = err.response?.data?.message || 'Failed to receive purchase order';
      setError(apiError);
      message.error(apiError);
    } finally {
      setSubmitting(false);
    }
  };

  const lineSummaries = useMemo<LineFormState[]>(() => {
    if (!order) {
      return [];
    }
    return order.lines
      .filter((line) => line.id)
      .map((line) => {
        const pendingQuantity = (line.quantity ?? 0) - (line.received_quantity ?? 0);
        return {
          line,
          pendingQuantity,
        };
      });
  }, [order]);

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Card>
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      </div>
    );
  }

  if (error && !order) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="error"
          title="Unable to load purchase order"
          subTitle={error}
          extra={[
            <Button key="back" onClick={() => navigate('/purchase-orders')}>
              Back to list
            </Button>,
            <Button key="retry" type="primary" onClick={() => void loadOrder()}>
              Retry
            </Button>,
          ]}
        />
      </div>
    );
  }

  if (!order) {
    return null;
  }

  const totalPending = lineSummaries.reduce((sum, entry) => sum + entry.pendingQuantity, 0);
  const totalReceiving = lineSummaries.reduce((sum, entry) => {
    const state = lineStates[entry.line.id!];
    return sum + (state?.receive ?? 0);
  }, 0);

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 24 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
          <Space align="start" size="middle">
            <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/purchase-orders/${order.id}`)} style={{ padding: 0 }}>
              Back to order
            </Button>
            <Space direction="vertical" size={0}>
              <Typography.Title level={3} style={{ margin: 0 }}>
                Receive Purchase Order
              </Typography.Title>
              <Typography.Text type="secondary">Order #{order.order_number}</Typography.Text>
            </Space>
          </Space>
          <Button icon={<ReloadOutlined />} onClick={() => void refresh()}>
            Refresh
          </Button>
        </Space>
      </Card>

      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          style={{ marginBottom: 24 }}
          action={
            <Button size="small" onClick={() => setError(null)}>
              Dismiss
            </Button>
          }
        />
      )}

      <Row gutter={24}>
        <Col xs={24} lg={16}>
          <Card title="Products to Receive" style={{ marginBottom: 24 }}>
            <Form layout="vertical">
              {lineSummaries.map(({ line, pendingQuantity }) => {
                const state = lineStates[line.id!];
                const receivingQty = state?.receive ?? 0;
                const remainingQty = pendingQuantity - receivingQty;
                return (
                  <Card key={line.id} type="inner" style={{ marginBottom: 16 }}>
                    <Row gutter={[16, 16]}>
                      <Col xs={24} md={16}>
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          <Typography.Text strong>{line.product?.name || `Product ${line.product_id}`}</Typography.Text>
                          {line.product?.sku && (
                            <Typography.Text type="secondary">SKU: {line.product.sku}</Typography.Text>
                          )}
                          <Space size="large">
                            <Typography.Text type="secondary">Ordered: {line.quantity}</Typography.Text>
                            <Typography.Text type="secondary">Received: {line.received_quantity ?? 0}</Typography.Text>
                            <Tag color={pendingQuantity === 0 ? 'green' : 'orange'}>
                              Pending {pendingQuantity}
                            </Tag>
                          </Space>
                        </Space>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Receive quantity" required>
                          <InputNumber
                            min={0}
                            max={pendingQuantity}
                            style={{ width: '100%' }}
                            value={receivingQty}
                            onChange={(value) =>
                              setLineStates((prev) => ({
                                ...prev,
                                [line.id!]: {
                                  receive: value ?? 0,
                                  notes: prev[line.id!]?.notes ?? '',
                                },
                              }))
                            }
                            disabled={pendingQuantity === 0}
                          />
                        </Form.Item>
                        {pendingQuantity > 0 && receivingQty < pendingQuantity && receivingQty > 0 && (
                          <Typography.Text type="warning" style={{ display: 'block' }}>
                            <WarningOutlined style={{ marginRight: 4 }} />
                            Remaining pending: {remainingQty}
                          </Typography.Text>
                        )}
                      </Col>
                      <Col span={24}>
                        <Form.Item label="Line notes">
                          <Input
                            value={state?.notes ?? ''}
                            onChange={(e) =>
                              setLineStates((prev) => ({
                                ...prev,
                                [line.id!]: {
                                  receive: prev[line.id!]?.receive ?? 0,
                                  notes: e.target.value,
                                },
                              }))
                            }
                            placeholder="Optional notes about this product"
                            disabled={pendingQuantity === 0}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                );
              })}
            </Form>
          </Card>

          <Card title="General notes" style={{ marginBottom: 24 }}>
            <Input.TextArea
              rows={4}
              value={generalNotes}
              onChange={(e) => setGeneralNotes(e.target.value)}
              placeholder="Add general notes about this receipt (optional)"
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card style={{ marginBottom: 24 }}>
            <Statistic title="Order number" value={order.order_number} />
            <Divider />
            <Form layout="vertical">
              <Form.Item label="Receipt date" required>
                <DatePicker
                  value={receiptDate}
                  onChange={(value) => value && setReceiptDate(value)}
                  style={{ width: '100%' }}
                  format="DD/MM/YYYY"
                />
              </Form.Item>
            </Form>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Typography.Text type="secondary">Total pending</Typography.Text>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {totalPending}
                </Typography.Title>
              </div>
              <div>
                <Typography.Text type="secondary">Receiving now</Typography.Text>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {totalReceiving}
                </Typography.Title>
              </div>
              <div>
                <Typography.Text type="secondary">Will remain pending</Typography.Text>
                <Typography.Title level={4} style={{ margin: 0, color: '#f59e0b' }}>
                  {Math.max(totalPending - totalReceiving, 0)}
                </Typography.Title>
              </div>
            </Space>
          </Card>

          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Typography.Text type="secondary">
                Review the quantities and confirm the receipt to update the purchase order status and inventory tracking.
              </Typography.Text>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={() => navigate(`/purchase-orders/${order.id}`)}>
                  Cancel
                </Button>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => void handleSubmit()}
                  loading={submitting}
                  disabled={totalReceiving === 0}
                >
                  Receive Items
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ReceivePurchaseOrderPage;
