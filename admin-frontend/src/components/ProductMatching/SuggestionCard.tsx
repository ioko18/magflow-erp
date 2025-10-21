import { memo } from 'react';
import { Card, Row, Col, Image, Typography, Tag, Button, Space } from 'antd';
import { CheckCircleOutlined, CloseOutlined } from '@ant-design/icons';
import type { LocalProductSuggestion } from '../../hooks/useProductMatching';

const { Text } = Typography;

interface SuggestionCardProps {
  suggestion: LocalProductSuggestion;
  onConfirm: () => void;
  onRemove: () => void;
  loading?: boolean;
}

const getConfidenceColor = (score: number): string => {
  if (score >= 0.95) return '#52c41a'; // Verde închis - excelent
  if (score >= 0.9) return '#73d13d'; // Verde - foarte bun
  if (score >= 0.85) return '#95de64'; // Verde deschis - bun
  return '#faad14'; // Portocaliu - mediu
};

const getConfidenceLabel = (score: number): string => {
  if (score >= 0.95) return 'Excelent';
  if (score >= 0.9) return 'Foarte bun';
  if (score >= 0.85) return 'Bun';
  return 'Mediu';
};

export const SuggestionCard = memo<SuggestionCardProps>(
  ({ suggestion, onConfirm, onRemove, loading = false }) => {
    const confidenceColor = getConfidenceColor(suggestion.similarity_score);
    const confidenceLabel = getConfidenceLabel(suggestion.similarity_score);

    return (
      <Card
        size="small"
        style={{
          borderLeft: `4px solid ${confidenceColor}`,
        }}
      >
        <Row gutter={16} align="middle">
          <Col span={3}>
            {suggestion.local_product_image_url ? (
              <Image
                src={suggestion.local_product_image_url}
                alt={suggestion.local_product_name}
                width={60}
                height={60}
                style={{ objectFit: 'cover', borderRadius: '4px' }}
                fallback="/placeholder-product.png"
                preview={false}
              />
            ) : (
              <div
                style={{
                  width: 60,
                  height: 60,
                  background: '#f0f0f0',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Text type="secondary" style={{ fontSize: '10px' }}>
                  No Image
                </Text>
              </div>
            )}
          </Col>

          <Col span={13}>
            <div>
              <Text strong style={{ fontSize: '13px' }}>
                {suggestion.local_product_name}
              </Text>
              {suggestion.local_product_chinese_name && (
                <div style={{ fontSize: '12px', color: '#52c41a', marginTop: '2px' }}>
                  🇨🇳 {suggestion.local_product_chinese_name}
                </div>
              )}
              <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                <Text type="secondary">SKU: {suggestion.local_product_sku}</Text>
                {suggestion.local_product_brand && (
                  <Tag color="blue" style={{ marginLeft: '8px', fontSize: '10px' }}>
                    {suggestion.local_product_brand}
                  </Tag>
                )}
              </div>
              <div style={{ fontSize: '10px', color: '#999', marginTop: '4px' }}>
                Tokeni: {suggestion.common_tokens.slice(0, 5).join(', ')}
                {suggestion.common_tokens.length > 5 && '...'}
              </div>
            </div>
          </Col>

          <Col span={4} style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: '8px' }}>
              <div
                style={{
                  fontSize: '20px',
                  fontWeight: 'bold',
                  color: confidenceColor,
                }}
              >
                {Math.round(suggestion.similarity_percent)}%
              </div>
              <Tag color={confidenceColor} style={{ fontSize: '10px' }}>
                {confidenceLabel}
              </Tag>
            </div>
          </Col>

          <Col span={4} style={{ textAlign: 'right' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={onConfirm}
                size="small"
                block
                loading={loading}
              >
                Confirmă
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                onClick={onRemove}
                size="small"
                block
                loading={loading}
              >
                Elimină
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>
    );
  }
);

SuggestionCard.displayName = 'SuggestionCard';
