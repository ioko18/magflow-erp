import React, { useState } from 'react';
import {
  Card,
  Alert,
  Button,
  Collapse,
  Tag,
  Space,
  Divider,
  Typography,
  List,
  Badge,
  Spin,
  Modal,
  Descriptions,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  BugOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Panel } = Collapse;
const { Title, Text } = Typography;

interface ValidationResult {
  is_valid: boolean;
  error_count: number;
  warning_count: number;
  errors: string[];
  warnings: string[];
  severity: 'error' | 'warning' | 'success';
}

interface ProductValidationProps {
  productData?: any;
  visible?: boolean;
  onClose?: () => void;
  onValidationComplete?: (result: ValidationResult) => void;
}

const ProductValidation: React.FC<ProductValidationProps> = ({
  productData,
  visible = false,
  onClose,
  onValidationComplete,
}) => {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(visible);

  React.useEffect(() => {
    setShowModal(visible);
  }, [visible]);

  React.useEffect(() => {
    if (productData && visible) {
      validateProduct();
    }
  }, [productData, visible]);

  const validateProduct = async () => {
    if (!productData) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        '/api/v1/emag/v449/products/validate',
        {
          product_data: productData,
          category_template: null, // Can be provided if available
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const result = response.data.validation;
      setValidationResult(result);
      
      if (onValidationComplete) {
        onValidationComplete(result);
      }
    } catch (error: any) {
      console.error('Validation error:', error);
      setValidationResult({
        is_valid: false,
        error_count: 1,
        warning_count: 0,
        errors: [error.response?.data?.detail || 'Validation failed'],
        warnings: [],
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setShowModal(false);
    if (onClose) {
      onClose();
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14', fontSize: 24 }} />;
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 24 }} />;
    }
  };

  // Removed unused getSeverityColor function

  const renderValidationSummary = () => {
    if (!validationResult) return null;

    return (
      <Card
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: 24 }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Space align="center" size="large">
            {getSeverityIcon(validationResult.severity)}
            <div>
              <Title level={4} style={{ margin: 0 }}>
                {validationResult.is_valid ? 'Validation Passed' : 'Validation Failed'}
              </Title>
              <Text type="secondary">
                {validationResult.is_valid
                  ? 'Product is ready for publication'
                  : 'Please fix the errors below before publishing'}
              </Text>
            </div>
          </Space>

          <Space size="large">
            <Badge
              count={validationResult.error_count}
              showZero
              style={{ backgroundColor: '#ff4d4f' }}
            >
              <Tag icon={<CloseCircleOutlined />} color="error">
                Errors
              </Tag>
            </Badge>
            <Badge
              count={validationResult.warning_count}
              showZero
              style={{ backgroundColor: '#faad14' }}
            >
              <Tag icon={<WarningOutlined />} color="warning">
                Warnings
              </Tag>
            </Badge>
          </Space>
        </Space>
      </Card>
    );
  };

  const renderErrorsList = () => {
    if (!validationResult || validationResult.errors.length === 0) return null;

    return (
      <Card
        title={
          <Space>
            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            <span>Errors ({validationResult.errors.length})</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <List
          dataSource={validationResult.errors}
          renderItem={(error, index) => (
            <List.Item key={index}>
              <Space>
                <BugOutlined style={{ color: '#ff4d4f' }} />
                <Text>{error}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    );
  };

  const renderWarningsList = () => {
    if (!validationResult || validationResult.warnings.length === 0) return null;

    return (
      <Card
        title={
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            <span>Warnings ({validationResult.warnings.length})</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <List
          dataSource={validationResult.warnings}
          renderItem={(warning, index) => (
            <List.Item key={index}>
              <Space>
                <InfoCircleOutlined style={{ color: '#faad14' }} />
                <Text type="warning">{warning}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    );
  };

  const renderValidationDetails = () => {
    if (!validationResult) return null;

    return (
      <Collapse defaultActiveKey={validationResult.errors.length > 0 ? ['errors'] : []}>
        {validationResult.errors.length > 0 && (
          <Panel
            header={
              <Space>
                <Badge count={validationResult.errors.length} style={{ backgroundColor: '#ff4d4f' }}>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
                </Badge>
                <Text strong>Critical Errors</Text>
              </Space>
            }
            key="errors"
          >
            {renderErrorsList()}
          </Panel>
        )}

        {validationResult.warnings.length > 0 && (
          <Panel
            header={
              <Space>
                <Badge count={validationResult.warnings.length} style={{ backgroundColor: '#faad14' }}>
                  <WarningOutlined style={{ color: '#faad14', fontSize: 16 }} />
                </Badge>
                <Text strong>Warnings</Text>
              </Space>
            }
            key="warnings"
          >
            {renderWarningsList()}
          </Panel>
        )}

        {validationResult.is_valid && (
          <Panel
            header={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                <Text strong>Validation Passed</Text>
              </Space>
            }
            key="success"
          >
            <Alert
              message="Product Ready for Publication"
              description="All validation checks passed successfully. You can now publish this product to eMAG."
              type="success"
              showIcon
              icon={<SafetyOutlined />}
            />
          </Panel>
        )}
      </Collapse>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <SafetyOutlined />
          <span>Product Validation</span>
        </Space>
      }
      open={showModal}
      onCancel={handleClose}
      footer={[
        <Button key="close" onClick={handleClose}>
          Close
        </Button>,
        <Button
          key="revalidate"
          type="primary"
          onClick={validateProduct}
          loading={loading}
          disabled={!productData}
        >
          Re-validate
        </Button>,
      ]}
      width={800}
    >
      <Spin spinning={loading} tip="Validating product...">
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {productData && (
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="Product Name">
                {productData.name || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="SKU">
                {productData.part_number || productData.sku || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Brand">
                {productData.brand || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                {productData.category_id || 'N/A'}
              </Descriptions.Item>
            </Descriptions>
          )}

          <Divider />

          {validationResult ? (
            <>
              {renderValidationSummary()}
              {renderValidationDetails()}
            </>
          ) : (
            <Alert
              message="No Validation Results"
              description="Click 'Re-validate' to validate this product."
              type="info"
              showIcon
            />
          )}
        </Space>
      </Spin>
    </Modal>
  );
};

export default ProductValidation;
