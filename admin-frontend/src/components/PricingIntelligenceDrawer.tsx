import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Card,
  Statistic,
  Alert,
  Button,
  Space,
  Spin,
  Divider,
  Tag,
  Typography,
  Row,
  Col,
  Progress,
  List,
  Empty,
  Badge
} from 'antd';
import {
  DollarOutlined,
  PercentageOutlined,
  ThunderboltOutlined,
  RiseOutlined,
  FallOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  StarOutlined,
  TrophyOutlined
} from '@ant-design/icons';
import api from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface PricingIntelligenceDrawerProps {
  visible: boolean;
  onClose: () => void;
  productId: number | null;
  productName?: string;
  currentPrice?: number;
  accountType?: string;
}

interface CommissionData {
  product_id: number;
  commission_value: number | null;
  commission_percentage: number | null;
  created: string | null;
  end_date: string | null;
  error: string | null;
}

interface SmartDealsData {
  product_id: number;
  current_price: number | null;
  target_price: number | null;
  discount_required: number | null;
  is_eligible: boolean;
  message: string | null;
  error: string | null;
}

interface PricingRecommendation {
  product_id: number;
  current_price: number;
  recommended_price: number | null;
  commission_estimate: number | null;
  smart_deals_eligible: boolean;
  smart_deals_target_price: number | null;
  potential_savings: number | null;
  recommendations: string[];
}

const PricingIntelligenceDrawer: React.FC<PricingIntelligenceDrawerProps> = ({
  visible,
  onClose,
  productId,
  productName,
  currentPrice,
  accountType = 'main'
}) => {
  const [loading, setLoading] = useState(false);
  const [commissionData, setCommissionData] = useState<CommissionData | null>(null);
  const [smartDealsData, setSmartDealsData] = useState<SmartDealsData | null>(null);
  const [recommendations, setRecommendations] = useState<PricingRecommendation | null>(null);

  useEffect(() => {
    if (visible && productId) {
      fetchPricingIntelligence();
    }
  }, [visible, productId, accountType]);

  const fetchPricingIntelligence = async () => {
    if (!productId) return;

    setLoading(true);
    try {
      // Fetch all pricing intelligence data in parallel
      const [commissionRes, smartDealsRes, recommendationsRes] = await Promise.allSettled([
        api.get(`/emag/pricing/commission/estimate/${productId}`, {
          params: { account_type: accountType }
        }),
        api.get(`/emag/pricing/smart-deals/check/${productId}`, {
          params: { account_type: accountType }
        }),
        currentPrice ? api.post('/emag/pricing/recommendations', {
          product_id: productId,
          current_price: currentPrice,
          account_type: accountType
        }) : Promise.reject('No current price')
      ]);

      if (commissionRes.status === 'fulfilled') {
        setCommissionData(commissionRes.value.data);
      }

      if (smartDealsRes.status === 'fulfilled') {
        setSmartDealsData(smartDealsRes.value.data);
      }

      if (recommendationsRes.status === 'fulfilled') {
        setRecommendations(recommendationsRes.value.data);
      }
    } catch (error) {
      console.error('Error fetching pricing intelligence:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderCommissionCard = () => {
    if (!commissionData) return null;

    if (commissionData.error) {
      return (
        <Card title={<><DollarOutlined /> Commission Estimate</>} size="small">
          <Alert
            message="Commission data unavailable"
            description={commissionData.error}
            type="warning"
            showIcon
          />
        </Card>
      );
    }

    const netRevenue = currentPrice && commissionData.commission_value
      ? currentPrice - commissionData.commission_value
      : null;

    const marginPercentage = netRevenue && currentPrice
      ? (netRevenue / currentPrice) * 100
      : null;

    return (
      <Card title={<><DollarOutlined /> Commission Estimate</>} size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="Commission"
              value={commissionData.commission_percentage || 0}
              precision={1}
              suffix="%"
              valueStyle={{ color: '#cf1322' }}
              prefix={<PercentageOutlined />}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="Commission Amount"
              value={commissionData.commission_value || 0}
              precision={2}
              suffix="RON"
              valueStyle={{ color: '#cf1322' }}
            />
          </Col>
        </Row>

        {netRevenue !== null && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Net Revenue"
                  value={netRevenue}
                  precision={2}
                  suffix="RON"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Profit Margin"
                  value={marginPercentage || 0}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
            </Row>
          </>
        )}
      </Card>
    );
  };

  const renderSmartDealsCard = () => {
    if (!smartDealsData) return null;

    if (smartDealsData.error) {
      return (
        <Card title={<><ThunderboltOutlined /> Smart Deals Eligibility</>} size="small">
          <Alert
            message="Smart Deals data unavailable"
            description={smartDealsData.error}
            type="warning"
            showIcon
          />
        </Card>
      );
    }

    const isEligible = smartDealsData.is_eligible;
    const discountNeeded = smartDealsData.discount_required;

    return (
      <Card
        title={<><ThunderboltOutlined /> Smart Deals Eligibility</>}
        size="small"
        extra={
          isEligible ? (
            <Badge status="success" text="Eligible" />
          ) : (
            <Badge status="default" text="Not Eligible" />
          )
        }
      >
        {isEligible ? (
          <Alert
            message={
              <Space>
                <CheckCircleOutlined />
                <Text strong>Product qualifies for Smart Deals badge!</Text>
              </Space>
            }
            description="Your product meets eMAG's competitive pricing criteria and will receive increased visibility."
            type="success"
            showIcon={false}
            icon={<TrophyOutlined />}
          />
        ) : (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Current Price"
                  value={smartDealsData.current_price || 0}
                  precision={2}
                  suffix="RON"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Target Price"
                  value={smartDealsData.target_price || 0}
                  precision={2}
                  suffix="RON"
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<StarOutlined />}
                />
              </Col>
            </Row>

            {discountNeeded !== null && discountNeeded > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Alert
                  message="Price Reduction Needed"
                  description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>
                        Reduce price by <Text strong>{discountNeeded.toFixed(1)}%</Text> to qualify for Smart Deals badge
                      </Text>
                      <Progress
                        percent={100 - discountNeeded}
                        status="active"
                        strokeColor={{
                          '0%': '#108ee9',
                          '100%': '#87d068',
                        }}
                      />
                    </Space>
                  }
                  type="info"
                  showIcon
                  icon={<FallOutlined />}
                />
              </>
            )}
          </>
        )}

        {smartDealsData.message && (
          <Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
            <InfoCircleOutlined /> {smartDealsData.message}
          </Paragraph>
        )}
      </Card>
    );
  };

  const renderRecommendations = () => {
    if (!recommendations || recommendations.recommendations.length === 0) {
      return null;
    }

    return (
      <Card title={<><RiseOutlined /> Pricing Recommendations</>} size="small">
        <List
          size="small"
          dataSource={recommendations.recommendations}
          renderItem={(item) => (
            <List.Item>
              <Text>{item}</Text>
            </List.Item>
          )}
        />

        {recommendations.recommended_price && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Alert
              message="Recommended Action"
              description={
                <Space direction="vertical">
                  <Text>
                    Set price to <Text strong>{recommendations.recommended_price.toFixed(2)} RON</Text>
                  </Text>
                  {recommendations.potential_savings && (
                    <Text type="secondary">
                      Potential savings: {recommendations.potential_savings.toFixed(2)} RON
                    </Text>
                  )}
                </Space>
              }
              type="info"
              showIcon
            />
          </>
        )}
      </Card>
    );
  };

  return (
    <Drawer
      title={
        <Space>
          <DollarOutlined />
          <span>Pricing Intelligence</span>
          {accountType && (
            <Tag color={accountType === 'main' ? 'blue' : 'green'}>
              {accountType.toUpperCase()}
            </Tag>
          )}
        </Space>
      }
      placement="right"
      width={600}
      onClose={onClose}
      open={visible}
      extra={
        <Button onClick={fetchPricingIntelligence} loading={loading} icon={<RiseOutlined />}>
          Refresh
        </Button>
      }
    >
      {productName && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Title level={5} style={{ margin: 0 }}>
            {productName}
          </Title>
          <Text type="secondary">Product ID: {productId}</Text>
          {currentPrice && (
            <div style={{ marginTop: 8 }}>
              <Text strong>Current Price: </Text>
              <Text style={{ fontSize: 18, color: '#1890ff' }}>
                {currentPrice.toFixed(2)} RON
              </Text>
            </div>
          )}
        </Card>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" tip="Loading pricing intelligence..." />
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {renderCommissionCard()}
          {renderSmartDealsCard()}
          {renderRecommendations()}

          {!commissionData && !smartDealsData && !recommendations && (
            <Empty
              description="No pricing intelligence data available"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Space>
      )}

      <Divider />

      <Alert
        message="About Pricing Intelligence"
        description={
          <Space direction="vertical" size="small">
            <Text>
              <strong>Commission Estimate:</strong> Shows the fee eMAG charges for selling your product.
            </Text>
            <Text>
              <strong>Smart Deals:</strong> eMAG's program highlighting competitively priced products with increased visibility.
            </Text>
            <Text type="secondary">
              Data is fetched in real-time from eMAG API v4.4.9
            </Text>
          </Space>
        }
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
      />
    </Drawer>
  );
};

export default PricingIntelligenceDrawer;
