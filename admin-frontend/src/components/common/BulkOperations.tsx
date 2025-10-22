import React, { useState } from 'react';
import {
  Card,
  Button,
  Space,
  Progress,
  Modal,
  Select,
  InputNumber,
  Form,
  message,
  Statistic,
  Row,
  Col,
  Alert,
  Tooltip,
  Badge,
} from 'antd';
import {
  ThunderboltOutlined,
  DollarOutlined,
  InboxOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;

// Define proper types for selected products (similar to EmagProductSync ProductRecord)
interface SelectedProduct {
  id: string | number;
  emag_id?: string | number;
  name: string;
  sku: string;
  price: number;
  brand?: string;
  category_id?: number;
  part_number?: string;
  images?: string[];
  ean?: string[];
}

interface BulkOperationsProps {
  selectedProducts: SelectedProduct[];
  onOperationComplete?: () => void;
}

interface OperationResult {
  total: number;
  successful: number;
  failed: number;
  errors: Array<{ product_id: string; error: string }>;
}

const BulkOperations: React.FC<BulkOperationsProps> = ({
  selectedProducts,
  onOperationComplete,
}) => {
  const [loading, setLoading] = useState(false);
  const [operation, setOperation] = useState<string>('');
  const [modalVisible, setModalVisible] = useState(false);
  const [operationResult, setOperationResult] = useState<OperationResult | null>(null);
  const [progress, setProgress] = useState(0);
  const [form] = Form.useForm();

  const operations = [
    {
      key: 'update_price',
      label: 'Update Prices',
      icon: <DollarOutlined />,
      color: 'blue',
      description: 'Bulk update sale prices for selected products',
    },
    {
      key: 'update_stock',
      label: 'Update Stock',
      icon: <InboxOutlined />,
      color: 'green',
      description: 'Bulk update stock quantities',
    },
    {
      key: 'sync_to_emag',
      label: 'Sync to eMAG',
      icon: <SyncOutlined />,
      color: 'purple',
      description: 'Synchronize products to eMAG marketplace',
    },
    {
      key: 'validate_products',
      label: 'Validate Products',
      icon: <CheckCircleOutlined />,
      color: 'orange',
      description: 'Validate products before publication',
    },
  ];

  const handleOperationClick = (operationKey: string) => {
    if (selectedProducts.length === 0) {
      message.warning('Please select at least one product');
      return;
    }
    setOperation(operationKey);
    setModalVisible(true);
    form.resetFields();
  };

  const executeOperation = async (values: {
    sale_price?: number;
    stock?: number;
    warehouse_id?: number;
    account_type?: string;
  }) => {
    setLoading(true);
    setProgress(0);

    try {
      const token = localStorage.getItem('access_token');
      let endpoint = '';
      let payload: Record<string, unknown> = {};

      switch (operation) {
        case 'update_price':
          endpoint = '/api/v1/emag/enhanced/bulk-update-prices';
          payload = {
            updates: selectedProducts.map((p) => ({
              id: p.emag_id || p.id,
              sale_price: values.sale_price,
            })),
            account_type: values.account_type || 'main',
          };
          break;

        case 'update_stock':
          endpoint = '/api/v1/emag/enhanced/bulk-update-stock';
          payload = {
            updates: selectedProducts.map((p) => ({
              id: p.emag_id || p.id,
              stock: values.stock,
              warehouse_id: values.warehouse_id || 1,
            })),
            account_type: values.account_type || 'main',
          };
          break;

        case 'sync_to_emag':
          endpoint = '/api/v1/emag/enhanced/sync/products';
          payload = {
            product_ids: selectedProducts.map((p) => p.id),
            account_type: values.account_type || 'main',
          };
          break;

        case 'validate_products':
          endpoint = '/api/v1/emag/v449/products/validate-bulk';
          payload = selectedProducts.map((p) => ({
            name: p.name,
            part_number: p.sku || p.part_number,
            brand: p.brand,
            category_id: p.category_id,
            sale_price: p.price,
            images: p.images || [],
            ean: p.ean || [],
          })) as unknown as Record<string, unknown>;
          break;

        default:
          throw new Error('Unknown operation');
      }

      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 500);

      const response = await axios.post(endpoint, payload, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      clearInterval(progressInterval);
      setProgress(100);

      const result = response.data;
      setOperationResult({
        total: result.summary?.total || selectedProducts.length,
        successful: result.summary?.valid || result.successful || 0,
        failed: result.summary?.invalid || result.failed || 0,
        errors: result.errors || [],
      });

      message.success(`Operation completed: ${result.successful || result.summary?.valid || 0} successful`);

      if (onOperationComplete) {
        onOperationComplete();
      }
    } catch (error: unknown) {
      console.error('Bulk operation error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Operation failed';
      message.error(errorMessage);
      setOperationResult({
        total: selectedProducts.length,
        successful: 0,
        failed: selectedProducts.length,
        errors: [{ product_id: 'all', error: errorMessage }],
      });
    } finally {
      setLoading(false);
    }
  };

  const renderOperationForm = () => {
    switch (operation) {
      case 'update_price':
        return (
          <>
            <Form.Item
              name="sale_price"
              label="New Sale Price"
              rules={[{ required: true, message: 'Please enter sale price' }]}
            >
              <InputNumber
                min={0.01}
                max={999999}
                precision={2}
                style={{ width: '100%' }}
                placeholder="Enter new price"
              />
            </Form.Item>
            <Form.Item name="account_type" label="Account Type" initialValue="main">
              <Select>
                <Option value="main">MAIN Account</Option>
                <Option value="fbe">FBE Account</Option>
              </Select>
            </Form.Item>
          </>
        );

      case 'update_stock':
        return (
          <>
            <Form.Item
              name="stock"
              label="New Stock Quantity"
              rules={[{ required: true, message: 'Please enter stock quantity' }]}
            >
              <InputNumber
                min={0}
                max={999999}
                style={{ width: '100%' }}
                placeholder="Enter stock quantity"
              />
            </Form.Item>
            <Form.Item name="warehouse_id" label="Warehouse ID" initialValue={1}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="account_type" label="Account Type" initialValue="main">
              <Select>
                <Option value="main">MAIN Account</Option>
                <Option value="fbe">FBE Account</Option>
              </Select>
            </Form.Item>
          </>
        );

      case 'sync_to_emag':
        return (
          <Form.Item name="account_type" label="Account Type" initialValue="main">
            <Select>
              <Option value="main">MAIN Account</Option>
              <Option value="fbe">FBE Account</Option>
            </Select>
          </Form.Item>
        );

      case 'validate_products':
        return (
          <Alert
            message="Product Validation"
            description="This will validate all selected products against eMAG requirements."
            type="info"
            showIcon
          />
        );

      default:
        return null;
    }
  };

  const renderResults = () => {
    if (!operationResult) return null;

    return (
      <Card style={{ marginTop: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="Total"
              value={operationResult.total}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Successful"
              value={operationResult.successful}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Failed"
              value={operationResult.failed}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Col>
        </Row>

        {operationResult.errors.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Alert
              message="Errors Encountered"
              description={
                <ul>
                  {operationResult.errors.slice(0, 5).map((err, idx) => (
                    <li key={idx}>
                      Product {err.product_id}: {err.error}
                    </li>
                  ))}
                  {operationResult.errors.length > 5 && (
                    <li>... and {operationResult.errors.length - 5} more errors</li>
                  )}
                </ul>
              }
              type="error"
              showIcon
            />
          </div>
        )}
      </Card>
    );
  };

  const currentOperation = operations.find((op) => op.key === operation);

  return (
    <>
      <Card
        title={
          <Space>
            <RocketOutlined />
            <span>Bulk Operations</span>
            <Badge count={selectedProducts.length} showZero />
          </Space>
        }
      >
        <Space wrap size="middle">
          {operations.map((op) => (
            <Tooltip key={op.key} title={op.description}>
              <Button
                type="primary"
                icon={op.icon}
                onClick={() => handleOperationClick(op.key)}
                disabled={selectedProducts.length === 0}
                style={{ backgroundColor: op.color }}
              >
                {op.label}
              </Button>
            </Tooltip>
          ))}
        </Space>

        {selectedProducts.length === 0 && (
          <Alert
            message="No Products Selected"
            description="Please select products from the table to perform bulk operations."
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Modal
        title={
          <Space>
            {currentOperation?.icon}
            <span>{currentOperation?.label}</span>
          </Space>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setOperationResult(null);
          setProgress(0);
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              setModalVisible(false);
              setOperationResult(null);
              setProgress(0);
            }}
          >
            Cancel
          </Button>,
          <Button
            key="execute"
            type="primary"
            loading={loading}
            onClick={() => form.submit()}
            disabled={operationResult !== null}
          >
            Execute
          </Button>,
        ]}
        width={600}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Alert
            message={`${selectedProducts.length} products selected`}
            description={currentOperation?.description}
            type="info"
            showIcon
          />

          {loading && (
            <Progress
              percent={progress}
              status={progress === 100 ? 'success' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          )}

          <Form form={form} layout="vertical" onFinish={executeOperation}>
            {renderOperationForm()}
          </Form>

          {renderResults()}
        </Space>
      </Modal>
    </>
  );
};

export default BulkOperations;
