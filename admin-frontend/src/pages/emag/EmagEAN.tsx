import React, { useState } from 'react';
import {
  Card,
  Input,
  Button,
  Space,
  Tag,
  message,
  Row,
  Col,
  Descriptions,
  Alert,
  Spin,
  Typography,
  Steps,
  Empty,
  List,
  Image,
  Tooltip,
  Statistic,
  Divider,
  Badge,
} from 'antd';
import { 
  SearchOutlined, 
  BarcodeOutlined, 
  CheckCircleOutlined, 
  InfoCircleOutlined, 
  ShoppingOutlined, 
  PlusOutlined, 
  LinkOutlined, 
  FireOutlined 
} from '@ant-design/icons';
import api from '../../services/api';
import { logError } from '../../utils/errorLogger';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Step } = Steps;

interface EANSearchResult {
  ean: string;
  products: any[];
  count: number;
  account_type: string;
}

interface MatchResult {
  ean: string;
  match_found: boolean;
  recommendation: string;
  action: string;
  emag_product?: any;
  local_product?: any;
  details: any;
}

interface EANValidation {
  valid: boolean;
  ean: string;
  format?: string;
  error?: string;
}

const EmagEAN: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [eanInput, setEanInput] = useState('');
  const [bulkEans, setBulkEans] = useState('');
  const [accountType] = useState<string>('main');
  const [searchResult, setSearchResult] = useState<EANSearchResult | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [validationResult, setValidationResult] = useState<EANValidation | null>(null);
  const [bulkResults, setBulkResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'single' | 'bulk' | 'match'>('single');

  const validateEAN = async (ean: string) => {
    if (!ean || ean.trim().length === 0) {
      message.warning('Please enter an EAN code');
      return;
    }

    setLoading(true);
    try {
      const response = await api.get(`/emag/phase2/ean/validate/${ean}`, {
        params: { account_type: accountType },
      });

      setValidationResult(response.data);
      
      if (response.data.valid) {
        message.success(`Valid ${response.data.format} barcode`);
      } else {
        message.error(response.data.error || 'Invalid EAN code');
      }
    } catch (error: any) {
      logError(error, { component: 'EmagEAN', action: 'validateEAN', ean: eanInput });
      message.error('Failed to validate EAN');
    } finally {
      setLoading(false);
    }
  };

  const searchByEAN = async () => {
    if (!eanInput || eanInput.trim().length === 0) {
      message.warning('Please enter an EAN code');
      return;
    }

    setLoading(true);
    setSearchResult(null);
    
    try {
      // First validate
      await validateEAN(eanInput);

      // Then search
      const response = await api.post('/emag/phase2/ean/search', {
        account_type: accountType,
        ean: eanInput.trim(),
      });

      if (response.data.success) {
        setSearchResult(response.data);
        
        if (response.data.count === 0) {
          message.info('No products found with this EAN on eMAG');
        } else {
          message.success(`Found ${response.data.count} product(s) on eMAG`);
        }
      }
    } catch (error: any) {
      logError(error, { component: 'EmagEAN', action: 'searchByEAN', ean: eanInput });
      message.error(error.response?.data?.detail || 'Failed to search EAN');
    } finally {
      setLoading(false);
    }
  };

  const bulkSearchEANs = async () => {
    const eans = bulkEans
      .split('\n')
      .map(e => e.trim())
      .filter(e => e.length > 0);

    if (eans.length === 0) {
      message.warning('Please enter at least one EAN code');
      return;
    }

    if (eans.length > 100) {
      message.warning('Maximum 100 EANs per request');
      return;
    }

    setLoading(true);
    setBulkResults(null);

    try {
      const response = await api.post('/emag/phase2/ean/bulk-search', {
        account_type: accountType,
        eans: eans,
      });

      if (response.data.success) {
        setBulkResults(response.data);
        message.success(
          `Searched ${response.data.eans_searched} EANs, found ${response.data.products_found} products`
        );
      }
    } catch (error: any) {
      logError(error, { component: 'EmagEAN', action: 'bulkSearchEANs', eanCount: eans.length });
      message.error('Failed to search EANs');
    } finally {
      setLoading(false);
    }
  };

  const smartMatch = async () => {
    if (!eanInput || eanInput.trim().length === 0) {
      message.warning('Please enter an EAN code');
      return;
    }

    setLoading(true);
    setMatchResult(null);

    try {
      const response = await api.post('/emag/phase2/ean/match', {
        account_type: accountType,
        ean: eanInput.trim(),
        product_data: null,
      });

      if (response.data.success) {
        setMatchResult(response.data);
        
        const recommendations: Record<string, string> = {
          already_have_offer: 'You already have an offer for this product',
          can_add_offer: 'You can add your offer to this existing product',
          cannot_add_offer: 'Cannot add offer - contact eMAG support',
          create_new_product: 'Product not found - you can create a new listing',
        };
        
        message.info(recommendations[response.data.recommendation] || 'Match completed');
      }
    } catch (error: any) {
      logError(error, { component: 'EmagEAN', action: 'smartMatch', ean: eanInput });
      message.error('Failed to match product');
    } finally {
      setLoading(false);
    }
  };

  const renderRecommendation = (match: MatchResult) => {
    const actionSteps: Record<string, { steps: string[]; type: 'success' | 'warning' | 'error' | 'info' }> = {
      already_have_offer: {
        steps: [
          'Product exists on eMAG',
          'You already sell this product',
          'Update your existing offer if needed',
        ],
        type: 'success',
      },
      can_add_offer: {
        steps: [
          'Product exists on eMAG',
          'You can add your offer',
          'Use part_number_key to attach offer',
        ],
        type: 'info',
      },
      cannot_add_offer: {
        steps: [
          'Product exists on eMAG',
          'Category restrictions apply',
          'Contact eMAG support for access',
        ],
        type: 'warning',
      },
      create_new_product: {
        steps: [
          'Product not found on eMAG',
          'You can create a new listing',
          'Prepare product documentation',
        ],
        type: 'info',
      },
    };

    const config = actionSteps[match.recommendation] || actionSteps.create_new_product;

    return (
      <Alert
        message={`Recommendation: ${match.recommendation.replace(/_/g, ' ').toUpperCase()}`}
        description={
          <Steps direction="vertical" size="small" current={-1}>
            {config.steps.map((step, index) => (
              <Step key={index} title={step} />
            ))}
          </Steps>
        }
        type={config.type}
        showIcon
        style={{ marginTop: 16 }}
      />
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <BarcodeOutlined /> EAN Product Matching
        </Title>
        <Text type="secondary">
          Smart product matching using EAN codes - Find existing products or create new listings
        </Text>
      </div>

      {/* Tab Selection */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="large">
          <Button
            type={activeTab === 'single' ? 'primary' : 'default'}
            icon={<SearchOutlined />}
            onClick={() => setActiveTab('single')}
          >
            Single EAN Search
          </Button>
          <Button
            type={activeTab === 'bulk' ? 'primary' : 'default'}
            icon={<BarcodeOutlined />}
            onClick={() => setActiveTab('bulk')}
          >
            Bulk EAN Search
          </Button>
          <Button
            type={activeTab === 'match' ? 'primary' : 'default'}
            icon={<LinkOutlined />}
            onClick={() => setActiveTab('match')}
          >
            Smart Matching
          </Button>
        </Space>
      </Card>

      {/* Single EAN Search */}
      {activeTab === 'single' && (
        <Row gutter={16}>
          <Col span={12}>
            <Card title="Search by EAN">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Input
                  size="large"
                  placeholder="Enter EAN code (8, 12, 13, or 14 digits)"
                  prefix={<BarcodeOutlined />}
                  value={eanInput}
                  onChange={(e) => setEanInput(e.target.value)}
                  onPressEnter={searchByEAN}
                />
                
                <Space>
                  <Button
                    type="primary"
                    icon={<SearchOutlined />}
                    onClick={searchByEAN}
                    loading={loading}
                    size="large"
                  >
                    Search on eMAG
                  </Button>
                  <Button
                    icon={<CheckCircleOutlined />}
                    onClick={() => validateEAN(eanInput)}
                    loading={loading}
                  >
                    Validate EAN
                  </Button>
                </Space>

                {validationResult && (
                  <Alert
                    message={validationResult.valid ? 'Valid EAN Code' : 'Invalid EAN Code'}
                    description={
                      validationResult.valid
                        ? `Format: ${validationResult.format}`
                        : validationResult.error
                    }
                    type={validationResult.valid ? 'success' : 'error'}
                    showIcon
                    closable
                  />
                )}
              </Space>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Search Results">
              {loading && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text>Searching eMAG catalog...</Text>
                  </div>
                </div>
              )}

              {!loading && !searchResult && (
                <Empty description="Enter an EAN code to search" />
              )}

              {!loading && searchResult && searchResult.count === 0 && (
                <Empty
                  description="No products found with this EAN"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Button type="primary" icon={<PlusOutlined />}>
                    Create New Product
                  </Button>
                </Empty>
              )}

              {!loading && searchResult && searchResult.count > 0 && (
                <List
                  dataSource={searchResult.products}
                  renderItem={(product: any) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          product.product_image && (
                            <Image
                              width={60}
                              src={product.product_image}
                              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                            />
                          )
                        }
                        title={
                          <Space>
                            <Text strong>{product.product_name}</Text>
                            {product.hotness && (
                              <Tooltip title={`Hotness: ${product.hotness}`}>
                                <Tag color="red" icon={<FireOutlined />}>
                                  Hot
                                </Tag>
                              </Tooltip>
                            )}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size="small">
                            <Text type="secondary">{product.brand_name}</Text>
                            <Text type="secondary">{product.category_name}</Text>
                            <Space>
                              {product.vendor_has_offer && (
                                <Tag color="green">You have offer</Tag>
                              )}
                              {product.allow_to_add_offer && (
                                <Tag color="blue">Can add offer</Tag>
                              )}
                            </Space>
                            <Text code>{product.part_number_key}</Text>
                          </Space>
                        }
                      />
                      <Space direction="vertical">
                        {product.site_url && (
                          <Button
                            type="link"
                            icon={<LinkOutlined />}
                            href={product.site_url}
                            target="_blank"
                          >
                            View on eMAG
                          </Button>
                        )}
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* Bulk EAN Search */}
      {activeTab === 'bulk' && (
        <Row gutter={16}>
          <Col span={12}>
            <Card title="Bulk EAN Search">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  message="Enter multiple EAN codes"
                  description="One EAN per line, maximum 100 EANs per request"
                  type="info"
                  showIcon
                  icon={<InfoCircleOutlined />}
                />
                
                <TextArea
                  rows={12}
                  placeholder="Enter EAN codes, one per line&#10;Example:&#10;5901234123457&#10;4006381333931&#10;8712345678906"
                  value={bulkEans}
                  onChange={(e) => setBulkEans(e.target.value)}
                />
                
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={bulkSearchEANs}
                  loading={loading}
                  size="large"
                  block
                >
                  Search {bulkEans.split('\n').filter(e => e.trim()).length} EANs
                </Button>
              </Space>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Bulk Results">
              {loading && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text>Processing bulk search...</Text>
                  </div>
                </div>
              )}

              {!loading && !bulkResults && (
                <Empty description="Enter EAN codes to search" />
              )}

              {!loading && bulkResults && (
                <>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="EANs Searched"
                          value={bulkResults.eans_searched}
                          prefix={<BarcodeOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small">
                        <Statistic
                          title="Products Found"
                          value={bulkResults.products_found}
                          prefix={<ShoppingOutlined />}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Divider />

                  <List
                    size="small"
                    dataSource={bulkResults.products}
                    renderItem={(product: any) => (
                      <List.Item>
                        <List.Item.Meta
                          title={product.product_name}
                          description={
                            <Space>
                              <Text type="secondary">{product.brand_name}</Text>
                              {product.vendor_has_offer && (
                                <Tag color="green" icon={<CheckCircleOutlined />}>
                                  Your offer
                                </Tag>
                              )}
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                    pagination={{ pageSize: 10 }}
                  />
                </>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* Smart Matching */}
      {activeTab === 'match' && (
        <Row gutter={16}>
          <Col span={12}>
            <Card title="Smart Product Matching">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  message="Intelligent Product Matching"
                  description="Get recommendations on whether to create a new product or attach to existing one"
                  type="info"
                  showIcon
                />
                
                <Input
                  size="large"
                  placeholder="Enter EAN code"
                  prefix={<BarcodeOutlined />}
                  value={eanInput}
                  onChange={(e) => setEanInput(e.target.value)}
                  onPressEnter={smartMatch}
                />
                
                <Button
                  type="primary"
                  icon={<LinkOutlined />}
                  onClick={smartMatch}
                  loading={loading}
                  size="large"
                  block
                >
                  Smart Match
                </Button>
              </Space>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Match Results">
              {loading && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text>Analyzing product...</Text>
                  </div>
                </div>
              )}

              {!loading && !matchResult && (
                <Empty description="Enter an EAN to get smart recommendations" />
              )}

              {!loading && matchResult && (
                <>
                  <Badge.Ribbon
                    text={matchResult.match_found ? 'Match Found' : 'No Match'}
                    color={matchResult.match_found ? 'green' : 'orange'}
                  >
                    <Card size="small" style={{ marginBottom: 16 }}>
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="EAN">
                          <Text code>{matchResult.ean}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Action">
                          <Tag color="blue">{matchResult.action.replace(/_/g, ' ')}</Tag>
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Badge.Ribbon>

                  {renderRecommendation(matchResult)}

                  {matchResult.emag_product && (
                    <Card
                      size="small"
                      title="eMAG Product Details"
                      style={{ marginTop: 16 }}
                    >
                      <Descriptions column={1} size="small" bordered>
                        <Descriptions.Item label="Product">
                          {matchResult.details.product_name}
                        </Descriptions.Item>
                        <Descriptions.Item label="Brand">
                          {matchResult.details.brand_name}
                        </Descriptions.Item>
                        <Descriptions.Item label="Category">
                          {matchResult.details.category_name}
                        </Descriptions.Item>
                        <Descriptions.Item label="Part Number Key">
                          <Text code>{matchResult.details.part_number_key}</Text>
                        </Descriptions.Item>
                        {matchResult.details.hotness && (
                          <Descriptions.Item label="Hotness">
                            <Tag color="red" icon={<FireOutlined />}>
                              {matchResult.details.hotness}
                            </Tag>
                          </Descriptions.Item>
                        )}
                      </Descriptions>

                      {matchResult.details.site_url && (
                        <Button
                          type="link"
                          icon={<LinkOutlined />}
                          href={matchResult.details.site_url}
                          target="_blank"
                          style={{ marginTop: 8 }}
                        >
                          View on eMAG
                        </Button>
                      )}
                    </Card>
                  )}

                  {matchResult.details.required_fields && (
                    <Card
                      size="small"
                      title="Required for New Product"
                      style={{ marginTop: 16 }}
                    >
                      <List
                        size="small"
                        dataSource={matchResult.details.required_fields}
                        renderItem={(field: string) => (
                          <List.Item>
                            <CheckCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                            {field.replace(/_/g, ' ')}
                          </List.Item>
                        )}
                      />
                    </Card>
                  )}
                </>
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default EmagEAN;
