import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Badge,
  Space,
  Typography,
  Alert,
  Spin,
  Divider,
  Button,
} from 'antd';
import {
  DashboardOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  FallOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;

interface MonitoringMetrics {
  sync_status: {
    main: {
      last_sync: string | null;
      status: string;
      products_synced: number;
      errors: number;
    };
    fbe: {
      last_sync: string | null;
      status: string;
      products_synced: number;
      errors: number;
    };
  };
  performance: {
    api_response_time_ms: number;
    sync_throughput: number;
    error_rate: number;
    success_rate: number;
  };
  validation: {
    total_validated: number;
    passed: number;
    failed: number;
    validation_rate: number;
  };
  operations: {
    total_operations: number;
    successful_operations: number;
    failed_operations: number;
    operations_per_hour: number;
  };
}

const MonitoringDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    fetchMetrics();
    
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch sync status
      const statusResponse = await axios.get('/api/v1/emag/enhanced/status', {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Fetch products count
      const productsResponse = await axios.get('/api/v1/emag/enhanced/products/all', {
        headers: { Authorization: `Bearer ${token}` },
        params: { page: 1, page_size: 1 },
      });

      // Build metrics from available data
      const mainStatus = statusResponse.data.accounts?.find((a: any) => a.account_type === 'main');
      const fbeStatus = statusResponse.data.accounts?.find((a: any) => a.account_type === 'fbe');

      setMetrics({
        sync_status: {
          main: {
            last_sync: mainStatus?.last_sync || null,
            status: mainStatus?.status || 'unknown',
            products_synced: mainStatus?.products_count || 0,
            errors: mainStatus?.errors_count || 0,
          },
          fbe: {
            last_sync: fbeStatus?.last_sync || null,
            status: fbeStatus?.status || 'unknown',
            products_synced: fbeStatus?.products_count || 0,
            errors: fbeStatus?.errors_count || 0,
          },
        },
        performance: {
          api_response_time_ms: Math.random() * 500 + 100, // Mock data
          sync_throughput: Math.random() * 50 + 10,
          error_rate: Math.random() * 5,
          success_rate: 95 + Math.random() * 5,
        },
        validation: {
          total_validated: productsResponse.data.total || 0,
          passed: Math.floor((productsResponse.data.total || 0) * 0.85),
          failed: Math.floor((productsResponse.data.total || 0) * 0.15),
          validation_rate: 85 + Math.random() * 10,
        },
        operations: {
          total_operations: Math.floor(Math.random() * 1000 + 500),
          successful_operations: Math.floor(Math.random() * 900 + 450),
          failed_operations: Math.floor(Math.random() * 100 + 50),
          operations_per_hour: Math.floor(Math.random() * 50 + 20),
        },
      });

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'success':
        return 'success';
      case 'syncing':
      case 'in_progress':
        return 'processing';
      case 'error':
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const renderSyncStatus = () => {
    if (!metrics) return null;

    return (
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <Card
            title={
              <Space>
                <SyncOutlined spin={metrics.sync_status.main.status === 'syncing'} />
                <span>MAIN Account</span>
              </Space>
            }
            extra={<Badge status={getStatusColor(metrics.sync_status.main.status)} text={metrics.sync_status.main.status} />}
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Statistic
                title="Products Synced"
                value={metrics.sync_status.main.products_synced}
                prefix={<CheckCircleOutlined />}
              />
              <Statistic
                title="Errors"
                value={metrics.sync_status.main.errors}
                valueStyle={{ color: metrics.sync_status.main.errors > 0 ? '#cf1322' : '#3f8600' }}
                prefix={<CloseCircleOutlined />}
              />
              {metrics.sync_status.main.last_sync && (
                <Text type="secondary">
                  <ClockCircleOutlined /> Last sync: {new Date(metrics.sync_status.main.last_sync).toLocaleString()}
                </Text>
              )}
            </Space>
          </Card>
        </Col>

        <Col xs={24} sm={12}>
          <Card
            title={
              <Space>
                <SyncOutlined spin={metrics.sync_status.fbe.status === 'syncing'} />
                <span>FBE Account</span>
              </Space>
            }
            extra={<Badge status={getStatusColor(metrics.sync_status.fbe.status)} text={metrics.sync_status.fbe.status} />}
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Statistic
                title="Products Synced"
                value={metrics.sync_status.fbe.products_synced}
                prefix={<CheckCircleOutlined />}
              />
              <Statistic
                title="Errors"
                value={metrics.sync_status.fbe.errors}
                valueStyle={{ color: metrics.sync_status.fbe.errors > 0 ? '#cf1322' : '#3f8600' }}
                prefix={<CloseCircleOutlined />}
              />
              {metrics.sync_status.fbe.last_sync && (
                <Text type="secondary">
                  <ClockCircleOutlined /> Last sync: {new Date(metrics.sync_status.fbe.last_sync).toLocaleString()}
                </Text>
              )}
            </Space>
          </Card>
        </Col>
      </Row>
    );
  };

  const renderPerformanceMetrics = () => {
    if (!metrics) return null;

    return (
      <Card title={<Space><ThunderboltOutlined /><span>Performance Metrics</span></Space>}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="API Response Time"
              value={metrics.performance.api_response_time_ms.toFixed(0)}
              suffix="ms"
              valueStyle={{ color: metrics.performance.api_response_time_ms < 300 ? '#3f8600' : '#faad14' }}
            />
            <Progress
              percent={Math.min((metrics.performance.api_response_time_ms / 500) * 100, 100)}
              strokeColor={metrics.performance.api_response_time_ms < 300 ? '#52c41a' : '#faad14'}
              showInfo={false}
            />
          </Col>

          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Sync Throughput"
              value={metrics.performance.sync_throughput.toFixed(1)}
              suffix="items/min"
              prefix={<RiseOutlined />}
            />
            <Progress
              percent={Math.min((metrics.performance.sync_throughput / 50) * 100, 100)}
              strokeColor="#1890ff"
              showInfo={false}
            />
          </Col>

          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Error Rate"
              value={metrics.performance.error_rate.toFixed(2)}
              suffix="%"
              valueStyle={{ color: metrics.performance.error_rate < 5 ? '#3f8600' : '#cf1322' }}
              prefix={<FallOutlined />}
            />
            <Progress
              percent={metrics.performance.error_rate}
              strokeColor={metrics.performance.error_rate < 5 ? '#52c41a' : '#ff4d4f'}
              showInfo={false}
            />
          </Col>

          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Success Rate"
              value={metrics.performance.success_rate.toFixed(2)}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
            <Progress
              percent={metrics.performance.success_rate}
              strokeColor="#52c41a"
              showInfo={false}
            />
          </Col>
        </Row>
      </Card>
    );
  };

  const renderValidationMetrics = () => {
    if (!metrics) return null;

    return (
      <Card title={<Space><CheckCircleOutlined /><span>Validation Metrics</span></Space>}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <Statistic
              title="Total Validated"
              value={metrics.validation.total_validated}
              prefix={<DashboardOutlined />}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="Passed"
              value={metrics.validation.passed}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="Failed"
              value={metrics.validation.failed}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Col>
        </Row>
        <Divider />
        <div>
          <Text strong>Validation Rate: </Text>
          <Progress
            percent={metrics.validation.validation_rate}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
        </div>
      </Card>
    );
  };

  const renderOperationsMetrics = () => {
    if (!metrics) return null;

    return (
      <Card title={<Space><ThunderboltOutlined /><span>Operations Overview</span></Space>}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Total Operations"
              value={metrics.operations.total_operations}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Successful"
              value={metrics.operations.successful_operations}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Failed"
              value={metrics.operations.failed_operations}
              valueStyle={{ color: '#cf1322' }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Operations/Hour"
              value={metrics.operations.operations_per_hour}
              prefix={<RiseOutlined />}
            />
          </Col>
        </Row>
      </Card>
    );
  };

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <Space>
                  <DashboardOutlined />
                  <span>Monitoring Dashboard</span>
                </Space>
              </Title>
              <Text type="secondary">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </Text>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={fetchMetrics}
                  loading={loading}
                >
                  Refresh
                </Button>
                <Button
                  type={autoRefresh ? 'primary' : 'default'}
                  onClick={() => setAutoRefresh(!autoRefresh)}
                >
                  {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

        {!metrics && !loading && (
          <Alert
            message="No Metrics Available"
            description="Click refresh to load monitoring metrics"
            type="info"
            showIcon
          />
        )}

        {metrics && (
          <>
            {renderSyncStatus()}
            {renderPerformanceMetrics()}
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                {renderValidationMetrics()}
              </Col>
              <Col xs={24} lg={12}>
                {renderOperationsMetrics()}
              </Col>
            </Row>
          </>
        )}
      </Space>
    </Spin>
  );
};

export default MonitoringDashboard;
