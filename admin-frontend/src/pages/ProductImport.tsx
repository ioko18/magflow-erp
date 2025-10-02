import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Descriptions,
  Alert,
  Progress,
  Tabs,
  App,
  Switch,
  Typography,
  Tooltip,
  Divider,
} from 'antd';
import {
  CloudUploadOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  GoogleOutlined,
  DatabaseOutlined,
  LinkOutlined,
  HistoryOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const { Option } = Select;
const { Text } = Typography;

interface MappingStatistics {
  total_products: number;
  fully_mapped: number;
  main_only: number;
  fbe_only: number;
  unmapped: number;
  mapping_percentage: number;
}

interface ProductMapping {
  id: number;
  local_sku: string;
  local_product_name: string;
  local_price: number | null;
  emag_main_id: number | null;
  emag_main_part_number: string | null;
  emag_main_status: string | null;
  emag_fbe_id: number | null;
  emag_fbe_part_number: string | null;
  emag_fbe_status: string | null;
  mapping_status: string;
  mapping_confidence: number | null;
  mapping_method: string | null;
  is_verified: boolean;
  has_conflicts: boolean;
  notes: string | null;
}

interface ImportLog {
  id: number;
  import_type: string;
  source_name: string;
  total_rows: number;
  successful_imports: number;
  failed_imports: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  initiated_by: string | null;
}

interface ImportResponse {
  import_id: number;
  status: string;
  total_rows: number;
  successful_imports: number;
  failed_imports: number;
  auto_mapped_main: number;
  auto_mapped_fbe: number;
  unmapped_products: number;
  duration_seconds: number | null;
  error_message: string | null;
}

interface RemapSummary {
  processed: number;
  updated: number;
  mapped_main: number;
  mapped_fbe: number;
  still_unmapped: number;
}

const ProductImport: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { message: messageApi } = App.useApp();
  const [statistics, setStatistics] = useState<MappingStatistics | null>(null);
  const [mappings, setMappings] = useState<ProductMapping[]>([]);
  const [importHistory, setImportHistory] = useState<ImportLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined);
  const [manualMappingVisible, setManualMappingVisible] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<ProductMapping | null>(null);
  const [form] = Form.useForm();
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'connected' | 'error'>('unknown');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupMatches, setLookupMatches] = useState<Record<string, any> | null>(null);
  const [remapLoading, setRemapLoading] = useState(false);
  const [remapSummary, setRemapSummary] = useState<RemapSummary | null>(null);
  const [remapDryRun, setRemapDryRun] = useState(true);
  const [remapLimit, setRemapLimit] = useState<number>(100);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      testConnection();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      loadMappings();
    }
  }, [filterStatus, isAuthenticated]);

  const loadData = async () => {
    await Promise.all([
      loadStatistics(),
      loadMappings(),
      loadImportHistory(),
    ]);
    setRemapSummary(null);
  };

  const loadStatistics = async () => {
    try {
      const response = await api.get('/products/mappings/statistics');
      setStatistics(response.data);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  const loadMappings = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (filterStatus) {
        params.filter_status = filterStatus;
      }
      const response = await api.get('/products/mappings', { params });
      setMappings(response.data);
    } catch (error) {
      console.error('Failed to load mappings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadImportHistory = async () => {
    try {
      const response = await api.get('/products/import/history', {
        params: { limit: 10 }
      });
      setImportHistory(response.data);
    } catch (error) {
      console.error('Failed to load import history:', error);
    }
  };

  const handleRemap = async () => {
    setRemapLoading(true);
    try {
      const response = await api.post<RemapSummary>('/products/mappings/remap', {
        limit: remapLimit,
        dry_run: remapDryRun,
      });
      setRemapSummary(response.data);
      messageApi.success(
        remapDryRun ? 'Dry-run completed. Review the summary below.' : 'Remap completed successfully.'
      );
      if (!remapDryRun) {
        await Promise.all([loadStatistics(), loadMappings()]);
      }
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || 'Failed to remap products');
    } finally {
      setRemapLoading(false);
    }
  };

  const testConnection = async () => {
    try {
      const response = await api.get('/products/sheets/test-connection');
      if (response.data.status === 'connected') {
        setConnectionStatus('connected');
        messageApi.success('Google Sheets connection successful');
      }
    } catch (error) {
      setConnectionStatus('error');
      console.error('Connection test failed:', error);
    }
  };

  const handleImport = async () => {
    Modal.confirm({
      title: 'Import Products from Google Sheets',
      content: (
        <div>
          <p>This will import all products from your Google Sheets and automatically map them to eMAG accounts by SKU.</p>
          <Alert
            message="Make sure service_account.json is configured"
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        </div>
      ),
      okText: 'Start Import',
      cancelText: 'Cancel',
      onOk: async () => {
        setImporting(true);
        try {
          const response = await api.post<ImportResponse>('/products/import/google-sheets', {
            auto_map: true
          });
          
          const result = response.data;
          
          Modal.success({
            title: 'Import Completed',
            content: (
              <div>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Total Rows">{result.total_rows}</Descriptions.Item>
                  <Descriptions.Item label="Successful">{result.successful_imports}</Descriptions.Item>
                  <Descriptions.Item label="Failed">{result.failed_imports}</Descriptions.Item>
                  <Descriptions.Item label="Mapped to MAIN">{result.auto_mapped_main}</Descriptions.Item>
                  <Descriptions.Item label="Mapped to FBE">{result.auto_mapped_fbe}</Descriptions.Item>
                  <Descriptions.Item label="Unmapped">{result.unmapped_products}</Descriptions.Item>
                  {result.duration_seconds && (
                    <Descriptions.Item label="Duration">
                      {result.duration_seconds.toFixed(2)}s
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </div>
            ),
          });
          
          await loadData();
        } catch (error: any) {
          messageApi.error(error.response?.data?.detail || 'Import failed');
        } finally {
          setImporting(false);
        }
      },
    });
  };

  const handleManualMapping = (mapping: ProductMapping) => {
    setSelectedMapping(mapping);
    form.setFieldsValue({
      local_sku: mapping.local_sku,
      emag_main_id: mapping.emag_main_id,
      emag_fbe_id: mapping.emag_fbe_id,
      notes: mapping.notes,
    });
    setLookupMatches(null);
    setLookupError(null);
    setManualMappingVisible(true);
  };

  useEffect(() => {
    const fetchLookup = async (sku: string) => {
      setLookupLoading(true);
      setLookupError(null);
      try {
        const response = await api.get('/products/mappings/lookup', {
          params: { sku },
        });
        setLookupMatches(response.data.matches);

        const { main, fbe } = response.data.matches ?? {};
        const currentValues = form.getFieldsValue();

        if (main?.emag_product_id && !currentValues.emag_main_id) {
          form.setFieldsValue({
            emag_main_id: main.emag_product_id,
            notes: currentValues.notes,
          });
        }

        if (fbe?.emag_product_id && !currentValues.emag_fbe_id) {
          form.setFieldsValue({
            emag_fbe_id: fbe.emag_product_id,
            notes: currentValues.notes,
          });
        }
      } catch (error: any) {
        setLookupError(error.response?.data?.detail || 'Failed to fetch eMAG matches');
        setLookupMatches(null);
      } finally {
        setLookupLoading(false);
      }
    };

    if (manualMappingVisible && selectedMapping?.local_sku) {
      fetchLookup(selectedMapping.local_sku);
    }
  }, [manualMappingVisible, selectedMapping, form]);

  const handleManualMappingSubmit = async () => {
    try {
      const values = await form.validateFields();
      await api.post('/products/mappings/manual', values);
      messageApi.success('Mapping updated successfully');
      setManualMappingVisible(false);
      await loadData();
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || 'Failed to update mapping');
    }
  };

  const getMappingStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      fully_mapped: { color: 'success', icon: <CheckCircleOutlined />, text: 'Fully Mapped' },
      partially_mapped: { color: 'warning', icon: <ExclamationCircleOutlined />, text: 'Partial' },
      unmapped: { color: 'error', icon: <CloseCircleOutlined />, text: 'Unmapped' },
      conflict: { color: 'error', icon: <ExclamationCircleOutlined />, text: 'Conflict' },
    };
    
    const config = statusConfig[status] || { color: 'default', icon: null, text: status };
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  const getAccountStatusTag = (status: string | null) => {
    if (!status) return <Tag>-</Tag>;
    
    const statusConfig: Record<string, { color: string; text: string }> = {
      mapped: { color: 'success', text: 'Mapped' },
      not_found: { color: 'default', text: 'Not Found' },
      conflict: { color: 'error', text: 'Conflict' },
    };
    
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ColumnsType<ProductMapping> = [
    {
      title: 'SKU',
      dataIndex: 'local_sku',
      key: 'local_sku',
      fixed: 'left',
      width: 120,
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Product Name',
      dataIndex: 'local_product_name',
      key: 'local_product_name',
      width: 300,
      ellipsis: true,
    },
    {
      title: 'Price',
      dataIndex: 'local_price',
      key: 'local_price',
      width: 100,
      render: (price) => price ? `${price.toFixed(2)} RON` : '-',
    },
    {
      title: 'MAIN Account',
      key: 'main',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {getAccountStatusTag(record.emag_main_status)}
          {record.emag_main_part_number && (
            <span style={{ fontSize: '12px', color: '#666' }}>
              {record.emag_main_part_number}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: 'FBE Account',
      key: 'fbe',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {getAccountStatusTag(record.emag_fbe_status)}
          {record.emag_fbe_part_number && (
            <span style={{ fontSize: '12px', color: '#666' }}>
              {record.emag_fbe_part_number}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'mapping_status',
      key: 'mapping_status',
      width: 130,
      render: (status) => getMappingStatusTag(status),
    },
    {
      title: 'Method',
      dataIndex: 'mapping_method',
      key: 'mapping_method',
      width: 100,
      render: (method) => method ? <Tag>{method}</Tag> : '-',
    },
    {
      title: 'Verified',
      dataIndex: 'is_verified',
      key: 'is_verified',
      width: 80,
      render: (verified) => verified ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          icon={<LinkOutlined />}
          onClick={() => handleManualMapping(record)}
        >
          Map
        </Button>
      ),
    },
  ];

  const historyColumns: ColumnsType<ImportLog> = [
    {
      title: 'Date',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: 'Source',
      dataIndex: 'source_name',
      key: 'source_name',
    },
    {
      title: 'Total',
      dataIndex: 'total_rows',
      key: 'total_rows',
    },
    {
      title: 'Success',
      dataIndex: 'successful_imports',
      key: 'successful_imports',
      render: (value) => <Tag color="success">{value}</Tag>,
    },
    {
      title: 'Failed',
      dataIndex: 'failed_imports',
      key: 'failed_imports',
      render: (value) => value > 0 ? <Tag color="error">{value}</Tag> : <Tag>{value}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (seconds) => seconds ? `${seconds.toFixed(2)}s` : '-',
    },
  ];

  if (!isAuthenticated) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="Authentication Required"
          description="Please log in to access the Product Import feature."
          type="warning"
          showIcon
        />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1>
          <GoogleOutlined style={{ marginRight: '8px' }} />
          Product Import from Google Sheets
        </h1>
        <p style={{ color: '#666' }}>
          Import products from Google Sheets and automatically map them to eMAG MAIN and FBE accounts
        </p>
      </div>

      {/* Connection Status */}
      <Alert
        message={
          connectionStatus === 'connected' ? 'Google Sheets Connected' :
          connectionStatus === 'error' ? 'Connection Error' :
          'Connection Status Unknown'
        }
        description={
          connectionStatus === 'connected' ? 'Successfully connected to Google Sheets API' :
          connectionStatus === 'error' ? 'Failed to connect. Check service_account.json configuration' :
          'Testing connection...'
        }
        type={connectionStatus === 'connected' ? 'success' : connectionStatus === 'error' ? 'error' : 'info'}
        showIcon
        style={{ marginBottom: '24px' }}
        action={
          <Button size="small" onClick={testConnection}>
            <SyncOutlined /> Test Again
          </Button>
        }
      />

      {/* Statistics */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Products"
                value={statistics.total_products}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Fully Mapped"
                value={statistics.fully_mapped}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
              <Progress
                percent={statistics.mapping_percentage}
                size="small"
                status="active"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Partially Mapped"
                value={statistics.main_only + statistics.fbe_only}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
              <div style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
                MAIN: {statistics.main_only} | FBE: {statistics.fbe_only}
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unmapped"
                value={statistics.unmapped}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Import Button */}
      <Card style={{ marginBottom: '24px' }}>
        <Space>
          <Button
            type="primary"
            size="large"
            icon={<CloudUploadOutlined />}
            onClick={handleImport}
            loading={importing}
            disabled={connectionStatus !== 'connected'}
          >
            Import from Google Sheets
          </Button>
          <Button
            icon={<SyncOutlined />}
            onClick={loadData}
            loading={loading}
          >
            Refresh
          </Button>
        </Space>
      </Card>

      {/* Remap Controls */}
      <Card style={{ marginBottom: '24px' }} title="Remap Existing Products">
        <Space size="large" wrap align="start">
          <Space direction="vertical" size={4}>
            <Text strong>Remap Limit</Text>
            <InputNumber
              min={1}
              max={1000}
              value={remapLimit}
              onChange={(value) => setRemapLimit(typeof value === 'number' ? value : 100)}
              style={{ width: 140 }}
              disabled={remapLoading}
            />
          </Space>
          <Space direction="vertical" size={4}>
            <Text strong>Mode</Text>
            <Tooltip title="Dry-run preview does not save changes. Disable to apply updates.">
              <Switch
                checkedChildren="Dry-Run"
                unCheckedChildren="Apply"
                checked={remapDryRun}
                onChange={(checked) => setRemapDryRun(checked)}
                disabled={remapLoading}
              />
            </Tooltip>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {remapDryRun ? 'Preview results without saving changes.' : 'Updates will be persisted immediately.'}
            </Text>
          </Space>
          <Space direction="vertical" size={4}>
            <Text strong>Actions</Text>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              loading={remapLoading}
              onClick={handleRemap}
            >
              {remapDryRun ? 'Preview Remap' : 'Run Remap'}
            </Button>
            <Button onClick={() => setRemapSummary(null)} disabled={remapLoading || !remapSummary}>
              Clear Summary
            </Button>
          </Space>
        </Space>

        {remapSummary && (
          <>
            <Divider />
            <Descriptions
              column={3}
              size="small"
              title={remapDryRun ? 'Dry-Run Summary' : 'Remap Summary'}
            >
              <Descriptions.Item label="Processed">{remapSummary.processed}</Descriptions.Item>
              <Descriptions.Item label="Updated">{remapSummary.updated}</Descriptions.Item>
              <Descriptions.Item label="MAIN Mapped">{remapSummary.mapped_main}</Descriptions.Item>
              <Descriptions.Item label="FBE Mapped">{remapSummary.mapped_fbe}</Descriptions.Item>
              <Descriptions.Item label="Still Unmapped">{remapSummary.still_unmapped}</Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Card>

      {/* Tabs */}
      <Tabs
        defaultActiveKey="mappings"
        type="card"
        items={[
          {
            key: 'mappings',
            label: (
              <span>
                <FilterOutlined />
                <span style={{ marginLeft: 8 }}>Mappings</span>
              </span>
            ),
            children: (
              <Card>
                <Space style={{ marginBottom: '16px' }}>
                  <Text strong>Filter by status</Text>
                  <Select
                    style={{ width: 200 }}
                    placeholder="Filter by status"
                    allowClear
                    value={filterStatus}
                    onChange={setFilterStatus}
                  >
                    <Option value="fully_mapped">Fully Mapped</Option>
                    <Option value="partially_mapped">Partially Mapped</Option>
                    <Option value="unmapped">Unmapped</Option>
                    <Option value="conflict">Conflicts</Option>
                  </Select>
                </Space>

                <Table
                  columns={columns}
                  dataSource={mappings}
                  rowKey="id"
                  loading={loading}
                  scroll={{ x: 1400 }}
                  pagination={{
                    pageSize: 50,
                    showSizeChanger: true,
                    showTotal: (total) => `Total ${total} products`,
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'history',
            label: (
              <span>
                <HistoryOutlined />
                <span style={{ marginLeft: 8 }}>Import History</span>
              </span>
            ),
            children: (
              <Card>
                <Table
                  columns={historyColumns}
                  dataSource={importHistory}
                  rowKey="id"
                  pagination={false}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Manual Mapping Modal */}
      <Modal
        title="Manual Product Mapping"
        open={manualMappingVisible}
        onOk={handleManualMappingSubmit}
        onCancel={() => setManualMappingVisible(false)}
        width={600}
      >
        {selectedMapping && (
          <>
            <Alert
              message={`Mapping product: ${selectedMapping.local_product_name}`}
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />
            {lookupError && (
              <Alert
                message="SKU Lookup Failed"
                description={lookupError}
                type="error"
                showIcon
                style={{ marginBottom: '16px' }}
              />
            )}
            {lookupLoading && (
              <Alert
                message="Searching eMAG for matches by SKU..."
                type="info"
                showIcon
                style={{ marginBottom: '16px' }}
              />
            )}
            {lookupMatches && (
              <Card size="small" style={{ marginBottom: '16px' }}>
                <Space direction="vertical">
                  <div><strong>eMAG Matches for SKU:</strong> {selectedMapping.local_sku}</div>
                  <div>
                    <strong>MAIN:</strong>{' '}
                    {lookupMatches.main ? (
                      <span>
                        #{lookupMatches.main.emag_product_id} — {lookupMatches.main.name || 'Unnamed'}
                        {lookupMatches.main.part_number_key ? ` (Key: ${lookupMatches.main.part_number_key})` : ''}
                      </span>
                    ) : (
                      'No match found'
                    )}
                  </div>
                  <div>
                    <strong>FBE:</strong>{' '}
                    {lookupMatches.fbe ? (
                      <span>
                        #{lookupMatches.fbe.emag_product_id} — {lookupMatches.fbe.name || 'Unnamed'}
                        {lookupMatches.fbe.part_number_key ? ` (Key: ${lookupMatches.fbe.part_number_key})` : ''}
                      </span>
                    ) : (
                      'No match found'
                    )}
                  </div>
                </Space>
              </Card>
            )}
            <Form form={form} layout="vertical">
              <Form.Item name="local_sku" label="Local SKU">
                <Input disabled />
              </Form.Item>
              <Form.Item name="emag_main_id" label="eMAG MAIN Product ID">
                <Input type="number" placeholder="Enter eMAG MAIN product ID" />
              </Form.Item>
              <Form.Item name="emag_fbe_id" label="eMAG FBE Product ID">
                <Input type="number" placeholder="Enter eMAG FBE product ID" />
              </Form.Item>
              <Form.Item name="notes" label="Notes">
                <Input.TextArea rows={3} placeholder="Optional notes about this mapping" />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </div>
  );
};

export default ProductImport;
