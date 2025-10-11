import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Image,
  Typography,
  Tag,
  Button,
  Space,
  Statistic,
  Tooltip,
  Modal,
  Descriptions,
  List,
  Avatar,
  Badge,
  Divider,
  Spin,
  Empty,
  Tabs,
  Table,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  ShoppingOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  PercentageOutlined,
  ZoomInOutlined,
  SwapOutlined,
  LinkOutlined,
  BarChartOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

interface Product {
  product_id: number;
  supplier_id: number;
  supplier_name: string;
  price_cny: number;
  product_url: string;
  chinese_name: string;
  english_name?: string;
  image_url: string;
}

interface PriceComparison {
  group_id: number;
  group_name: string;
  product_count: number;
  best_price_cny: number;
  worst_price_cny: number;
  avg_price_cny: number;
  savings_cny: number;
  savings_percent: number;
  products: Product[];
}

interface MatchingGroup {
  id: number;
  group_name: string;
  group_name_en?: string;
  product_count: number;
  min_price_cny?: number;
  max_price_cny?: number;
  avg_price_cny?: number;
  confidence_score: number;
  matching_method: string;
  status: string;
  representative_image_url?: string;
  created_at: string;
}

interface MatchingGroupCardProps {
  group: MatchingGroup;
  onConfirm: (groupId: number) => void;
  onReject: (groupId: number) => void;
  onViewDetails: (groupId: number) => Promise<PriceComparison>;
}

const MatchingGroupCard: React.FC<MatchingGroupCardProps> = ({
  group,
  onConfirm,
  onReject,
  onViewDetails,
}) => {
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [priceComparison, setPriceComparison] = useState<PriceComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [productImages, setProductImages] = useState<Product[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Load product images only when card is expanded (lazy loading)
  useEffect(() => {
    if (!expanded || productImages.length > 0) return;

    const loadProductImages = async () => {
      setImagesLoading(true);
      try {
        const data = await onViewDetails(group.id);
        // Already limited to 2 products by backend, but ensure it here as well
        const limitedProducts = (data.products || []).slice(0, 2);
        setProductImages(limitedProducts);
      } catch (error) {
        console.error('Error loading product images:', error);
        setProductImages([]);
      } finally {
        setImagesLoading(false);
      }
    };
    loadProductImages();
  }, [expanded, group.id, onViewDetails, productImages.length]);

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      auto_matched: 'processing',
      manual_matched: 'success',
      rejected: 'error',
      needs_review: 'warning',
      pending: 'default',
    };
    return colors[status] || 'default';
  };

  const getMethodColor = (method: string): string => {
    const colors: Record<string, string> = {
      hybrid: 'blue',
      text: 'green',
      image: 'orange',
    };
    return colors[method] || 'default';
  };

  const handleViewDetails = async () => {
    setLoading(true);
    try {
      const data = await onViewDetails(group.id);
      setPriceComparison(data);
      setDetailsVisible(true);
    } catch (error) {
      console.error('Error loading details:', error);
    } finally {
      setLoading(false);
    }
  };

  const savings = group.max_price_cny && group.min_price_cny
    ? group.max_price_cny - group.min_price_cny
    : 0;
  const savingsPercent = group.max_price_cny
    ? (savings / group.max_price_cny * 100)
    : 0;

  return (
    <>
      <Card
        hoverable
        style={{
          marginBottom: 24,
          borderRadius: 16,
          boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          border: '1px solid #f0f0f0',
          overflow: 'hidden',
        }}
        styles={{ body: { padding: 0 } }}
      >
        {/* Header Section */}
        <div style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
          padding: '20px 24px',
          color: 'white'
        }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={4} style={{ margin: 0, color: 'white', marginBottom: 8 }}>
                {group.group_name}
              </Title>
              {group.group_name_en && (
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 13 }}>
                  {group.group_name_en}
                </Text>
              )}
            </Col>
            <Col>
              <Space size="large">
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: 'white' }}>
                    {Math.round(group.confidence_score * 100)}%
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12 }}>Confidence</Text>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: 'white' }}>
                    {group.product_count}
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12 }}>Products</Text>
                </div>
              </Space>
            </Col>
          </Row>
          <div style={{ marginTop: 12 }}>
            <Space wrap>
              <Tag color={getStatusColor(group.status)} style={{ borderRadius: 12, padding: '4px 12px' }}>
                {group.status.replace('_', ' ').toUpperCase()}
              </Tag>
              <Tag color={getMethodColor(group.matching_method)} icon={<ThunderboltOutlined />} style={{ borderRadius: 12, padding: '4px 12px' }}>
                {group.matching_method.toUpperCase()}
              </Tag>
            </Space>
          </div>
        </div>

        {/* Products Comparison Section - Collapsible */}
        <div style={{ padding: 24 }}>
          {!expanded ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Button 
                type="dashed" 
                block 
                size="large"
                onClick={() => setExpanded(true)}
                icon={<EyeOutlined />}
                style={{ borderRadius: 8 }}
              >
                Click to Load Product Preview
              </Button>
            </div>
          ) : imagesLoading ? (
            <div style={{ textAlign: 'center', padding: '60px' }}>
              <Spin size="large" spinning tip="Loading products..." />
            </div>
          ) : productImages.length === 0 ? (
            <Empty 
              description="No product images available" 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ padding: '40px' }}
            />
          ) : (
            <Row gutter={24}>
              {productImages.map((product, index) => (
                <Col xs={24} sm={12} key={product.product_id}>
                  <Card
                    style={{
                      borderRadius: 12,
                      border: index === 0 ? '2px solid #52c41a' : '1px solid #f0f0f0',
                      boxShadow: index === 0 ? '0 4px 12px rgba(82, 196, 26, 0.2)' : '0 2px 8px rgba(0,0,0,0.06)',
                      height: '100%',
                    }}
                    bodyStyle={{ padding: 16 }}
                  >
                    {/* Product Image */}
                    <div style={{ position: 'relative', marginBottom: 16 }}>
                      <Image
                        src={product.image_url}
                        alt={product.chinese_name}
                        fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='240'%3E%3Crect fill='%23f0f0f0' width='300' height='240'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='16'%3ENo Image%3C/text%3E%3C/svg%3E"
                        style={{
                          width: '100%',
                          height: 240,
                          objectFit: 'cover',
                          borderRadius: 8,
                        }}
                        preview={{
                          mask: (
                            <Space direction="vertical" align="center">
                              <ZoomInOutlined style={{ fontSize: 24 }} />
                              <Text style={{ color: 'white', fontSize: 14 }}>View Full Size</Text>
                            </Space>
                          ),
                        }}
                      />
                      {index === 0 && (
                        <Tag
                          color="success"
                          icon={<DollarOutlined />}
                          style={{
                            position: 'absolute',
                            top: 12,
                            right: 12,
                            fontSize: 12,
                            fontWeight: 'bold',
                            padding: '6px 12px',
                            borderRadius: 8,
                            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                          }}
                        >
                          BEST PRICE
                        </Tag>
                      )}
                    </div>

                    {/* Product Info */}
                    <Space direction="vertical" style={{ width: '100%' }} size={12}>
                      {/* Price */}
                      <div style={{ 
                        background: index === 0 ? 'linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%)' : 'linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%)',
                        padding: '12px 16px',
                        borderRadius: 8,
                        textAlign: 'center'
                      }}>
                        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                          Price
                        </Text>
                        <Text strong style={{ 
                          color: index === 0 ? '#52c41a' : '#1890ff', 
                          fontSize: 28,
                          fontWeight: 'bold'
                        }}>
                          ¥{product.price_cny.toFixed(2)}
                        </Text>
                      </div>

                      {/* Product Name */}
                      <div>
                        <Tooltip title={product.chinese_name}>
                          <Paragraph
                            ellipsis={{ rows: 2 }}
                            strong
                            style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}
                          >
                            {product.chinese_name}
                          </Paragraph>
                        </Tooltip>
                        {product.english_name && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {product.english_name}
                          </Text>
                        )}
                      </div>

                      {/* Supplier */}
                      <div>
                        <Tag color="blue" icon={<TeamOutlined />} style={{ borderRadius: 6, padding: '4px 12px' }}>
                          {product.supplier_name}
                        </Tag>
                      </div>

                      {/* View Link */}
                      <Button
                        type={index === 0 ? 'primary' : 'default'}
                        block
                        href={product.product_url}
                        target="_blank"
                        icon={<LinkOutlined />}
                        style={{ borderRadius: 8 }}
                      >
                        View on Supplier Website
                      </Button>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}

          {/* Price Savings Summary */}
          {productImages.length === 2 && savings > 0 && (
            <Card
              style={{
                marginTop: 24,
                background: 'linear-gradient(135deg, #fff7e6 0%, #ffe7ba 100%)',
                border: '1px solid #ffd591',
                borderRadius: 12,
              }}
              bodyStyle={{ padding: 16 }}
            >
              <Row gutter={16} align="middle">
                <Col flex="auto">
                  <Space size="large">
                    <Statistic
                      title="Best Price"
                      value={group.min_price_cny || 0}
                      precision={2}
                      prefix="¥"
                      valueStyle={{ color: '#52c41a', fontSize: 20, fontWeight: 'bold' }}
                    />
                    <Statistic
                      title="Highest Price"
                      value={group.max_price_cny || 0}
                      precision={2}
                      prefix="¥"
                      valueStyle={{ color: '#ff4d4f', fontSize: 20, fontWeight: 'bold' }}
                    />
                    <Statistic
                      title="Potential Savings"
                      value={savings}
                      precision={2}
                      prefix="¥"
                      suffix={`(${savingsPercent.toFixed(1)}%)`}
                      valueStyle={{ color: '#fa8c16', fontSize: 20, fontWeight: 'bold' }}
                    />
                  </Space>
                </Col>
              </Row>
            </Card>
          )}
        </div>

        {/* Actions Footer */}
        <div style={{ 
          borderTop: '1px solid #f0f0f0', 
          padding: '16px 24px',
          background: '#fafafa'
        }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Button
                type="primary"
                icon={<EyeOutlined />}
                onClick={handleViewDetails}
                loading={loading}
                size="large"
                style={{ borderRadius: 8 }}
              >
                View All Products
              </Button>
            </Col>
            {group.status === 'auto_matched' && (
              <Col>
                <Space size="middle">
                  <Tooltip title="Confirm this matching group">
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={() => onConfirm(group.id)}
                      size="large"
                      style={{ 
                        backgroundColor: '#52c41a', 
                        borderColor: '#52c41a',
                        borderRadius: 8
                      }}
                    >
                      Confirm Match
                    </Button>
                  </Tooltip>
                  <Tooltip title="Reject this matching group">
                    <Button
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={() => onReject(group.id)}
                      size="large"
                      style={{ borderRadius: 8 }}
                    >
                      Reject
                    </Button>
                  </Tooltip>
                </Space>
              </Col>
            )}
          </Row>
        </div>
      </Card>

      {/* Details Modal */}
      <Modal
        title={
          <Space>
            <DollarOutlined style={{ color: '#52c41a' }} />
            <span>Price Comparison - {priceComparison?.group_name}</span>
          </Space>
        }
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            Close
          </Button>,
          group.status === 'auto_matched' && (
            <Button
              key="confirm"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                onConfirm(group.id);
                setDetailsVisible(false);
              }}
              style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
            >
              Confirm Match
            </Button>
          ),
        ]}
      >
        {priceComparison && (
          <>
            {/* Summary Stats */}
            <Card style={{ marginBottom: 16 }} bordered={false}>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="Products" span={2}>
                  <Badge count={priceComparison.product_count} showZero style={{ backgroundColor: '#52c41a' }} />
                </Descriptions.Item>
                <Descriptions.Item label="Best Price">
                  <Text strong style={{ color: '#52c41a', fontSize: 16 }}>
                    ¥{priceComparison.best_price_cny.toFixed(2)}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Worst Price">
                  <Text strong style={{ color: '#ff4d4f', fontSize: 16 }}>
                    ¥{priceComparison.worst_price_cny.toFixed(2)}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Average Price" span={2}>
                  <Text strong style={{ fontSize: 16 }}>
                    ¥{priceComparison.avg_price_cny.toFixed(2)}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Potential Savings" span={2}>
                  <Space>
                    <Text strong style={{ color: '#52c41a', fontSize: 18 }}>
                      ¥{priceComparison.savings_cny.toFixed(2)}
                    </Text>
                    <Tag color="success" style={{ fontSize: 14 }} icon={<PercentageOutlined />}>
                      {priceComparison.savings_percent.toFixed(1)}% OFF
                    </Tag>
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* Enhanced Products Display with Tabs */}
            <Tabs
              defaultActiveKey="gallery"
              items={[
                {
                  key: 'gallery',
                  label: (
                    <span>
                      <ShoppingOutlined /> Gallery View
                    </span>
                  ),
                  children: (
                    <List
                      grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 3 }}
                      dataSource={priceComparison.products}
                      renderItem={(product: Product, index: number) => (
                        <List.Item>
                          <Card
                            hoverable
                            cover={
                      <Image
                        alt={product.chinese_name}
                        src={product.image_url}
                        style={{ height: 200, objectFit: 'cover' }}
                        fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect fill='%23f0f0f0' width='200' height='200'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3ENo Image%3C/text%3E%3C/svg%3E"
                            />
                          }
                          actions={[
                            <Tooltip title="View on supplier website">
                              <Button
                                type="link"
                                href={product.product_url}
                                target="_blank"
                                icon={<LinkOutlined />}
                                size="small"
                              >
                                View Source
                              </Button>
                            </Tooltip>,
                          ]}
                        >
                          <Card.Meta
                            avatar={
                              index === 0 ? (
                                <Avatar style={{ backgroundColor: '#52c41a' }} icon={<DollarOutlined />} />
                              ) : (
                                <Avatar style={{ backgroundColor: '#1890ff' }} icon={<ShoppingOutlined />} />
                              )
                            }
                            title={
                              <Space direction="vertical" size={0}>
                                <Text strong style={{ fontSize: 16, color: index === 0 ? '#52c41a' : '#1890ff' }}>
                                  ¥{product.price_cny.toFixed(2)}
                                </Text>
                                {index === 0 && (
                                  <Tag color="success" icon={<DollarOutlined />} style={{ fontSize: 10 }}>
                                    BEST PRICE
                                  </Tag>
                                )}
                              </Space>
                            }
                            description={
                              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                <Tooltip title={product.chinese_name}>
                                  <Paragraph
                                    ellipsis={{ rows: 2 }}
                                    style={{ margin: 0, fontSize: 12, fontWeight: 500 }}
                                  >
                                    {product.chinese_name}
                                  </Paragraph>
                                </Tooltip>
                                {product.english_name && (
                                  <Text type="secondary" style={{ fontSize: 11 }}>
                                    {product.english_name}
                                  </Text>
                                )}
                                <Tag color="blue" style={{ fontSize: 10 }}>
                                  {product.supplier_name}
                                </Tag>
                              </Space>
                            }
                          />
                        </Card>
                      </List.Item>
                    )}
                  />
                  ),
                },
                {
                  key: 'comparison',
                  label: (
                    <span>
                      <SwapOutlined /> Side-by-Side
                    </span>
                  ),
                  children: (
                    <Row gutter={[16, 16]}>
                      {priceComparison.products.map((product: Product, index: number) => (
                        <Col xs={24} sm={12} md={8} key={product.product_id}>
                          <Card
                            bordered
                            style={{
                              borderColor: index === 0 ? '#52c41a' : '#d9d9d9',
                              borderWidth: index === 0 ? 2 : 1,
                            }}
                          >
                            <Space direction="vertical" size={12} style={{ width: '100%' }}>
                              <div style={{ position: 'relative' }}>
                                <Image
                                  src={product.image_url}
                                  alt={product.chinese_name}
                                  style={{ width: '100%', height: 180, objectFit: 'cover', borderRadius: 8 }}
                                  fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='180'%3E%3Crect fill='%23f0f0f0' width='200' height='180'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3ENo Image%3C/text%3E%3C/svg%3E"
                                />
                                {index === 0 && (
                                  <Tag
                                    color="success"
                                    icon={<DollarOutlined />}
                                    style={{
                                      position: 'absolute',
                                      top: 8,
                                      right: 8,
                                      fontWeight: 'bold',
                                    }}
                                  >
                                    BEST
                                  </Tag>
                                )}
                              </div>
                              <Statistic
                                title="Price"
                                value={product.price_cny}
                                precision={2}
                                prefix="¥"
                                valueStyle={{ color: index === 0 ? '#52c41a' : '#1890ff', fontSize: 20 }}
                              />
                              <Divider style={{ margin: '8px 0' }} />
                              <div>
                                <Text strong style={{ fontSize: 13 }}>
                                  {product.chinese_name}
                                </Text>
                                {product.english_name && (
                                  <div style={{ marginTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                      {product.english_name}
                                    </Text>
                                  </div>
                                )}
                              </div>
                              <Tag color="blue" icon={<TeamOutlined />}>
                                {product.supplier_name}
                              </Tag>
                              <Button
                                type="primary"
                                block
                                href={product.product_url}
                                target="_blank"
                                icon={<LinkOutlined />}
                                size="small"
                              >
                                View on Website
                              </Button>
                            </Space>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  ),
                },
                {
                  key: 'table',
                  label: (
                    <span>
                      <BarChartOutlined /> Table View
                    </span>
                  ),
                  children: (
                    <Table
                      dataSource={priceComparison.products}
                      rowKey="product_id"
                      pagination={false}
                      size="small"
                      columns={[
                        {
                          title: 'Image',
                          dataIndex: 'image_url',
                          key: 'image_url',
                          width: 100,
                          render: (url: string, record: Product) => (
                            <Image
                              src={url}
                              alt={record.chinese_name}
                              width={80}
                              height={60}
                              style={{ objectFit: 'cover', borderRadius: 4 }}
                              fallback="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='60'%3E%3Crect fill='%23f0f0f0' width='80' height='60'/%3E%3C/svg%3E"
                            />
                          ),
                        },
                        {
                          title: 'Product Name',
                          dataIndex: 'chinese_name',
                          key: 'chinese_name',
                          ellipsis: true,
                          render: (text: string, record: Product) => (
                            <Space direction="vertical" size={2}>
                              <Text strong style={{ fontSize: 13 }}>{text}</Text>
                              {record.english_name && (
                                <Text type="secondary" style={{ fontSize: 11 }}>
                                  {record.english_name}
                                </Text>
                              )}
                            </Space>
                          ),
                        },
                        {
                          title: 'Supplier',
                          dataIndex: 'supplier_name',
                          key: 'supplier_name',
                          width: 150,
                          render: (text: string) => <Tag color="blue">{text}</Tag>,
                        },
                        {
                          title: 'Price (CNY)',
                          dataIndex: 'price_cny',
                          key: 'price_cny',
                          width: 120,
                          sorter: (a: Product, b: Product) => a.price_cny - b.price_cny,
                          render: (price: number, _: Product, index: number) => (
                            <Space>
                              <Text strong style={{ color: index === 0 ? '#52c41a' : '#1890ff', fontSize: 15 }}>
                                ¥{price.toFixed(2)}
                              </Text>
                              {index === 0 && <Tag color="success">BEST</Tag>}
                            </Space>
                          ),
                        },
                        {
                          title: 'Actions',
                          key: 'actions',
                          width: 100,
                          render: (_, record: Product) => (
                            <Button
                              type="link"
                              href={record.product_url}
                              target="_blank"
                              icon={<LinkOutlined />}
                              size="small"
                            >
                              View
                            </Button>
                          ),
                        },
                      ]}
                    />
                  ),
                },
              ]}
            />
          </>
        )}
      </Modal>
    </>
  );
};

export default MatchingGroupCard;
