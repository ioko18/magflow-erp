import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Timeline,
  Typography,
  Tag,
  Space,
  Spin,
  Empty,
  Descriptions,
  Alert,
  Button,
  message,
} from 'antd';
import {
  HistoryOutlined,
  UserOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import api from '../services/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Text, Paragraph } = Typography;

interface SKUHistoryEntry {
  id: number;
  product_id: number;
  old_sku: string;
  new_sku: string;
  changed_at: string;
  changed_by_email: string | null;
  change_reason: string | null;
  ip_address: string | null;
}

interface SKUHistoryDrawerProps {
  visible: boolean;
  onClose: () => void;
  productId: number | null;
  currentSKU?: string;
  productName?: string;
}

const SKUHistoryDrawer: React.FC<SKUHistoryDrawerProps> = ({
  visible,
  onClose,
  productId,
  currentSKU,
  productName,
}) => {
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<SKUHistoryEntry[]>([]);

  const fetchHistory = async () => {
    if (!productId) return;

    setLoading(true);
    try {
      const response = await api.get(`/products/${productId}/sku-history`);
      setHistory(response.data || []);
    } catch (error: any) {
      console.error('Error fetching SKU history:', error);
      message.error('Eroare la încărcarea istoricului SKU');
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible && productId) {
      fetchHistory();
    }
  }, [visible, productId]);

  const handleRefresh = () => {
    fetchHistory();
  };

  const renderTimelineItem = (entry: SKUHistoryEntry, index: number) => {
    const isFirst = index === 0;
    const color = isFirst ? 'green' : 'blue';

    return (
      <Timeline.Item
        key={entry.id}
        color={color}
        dot={
          isFirst ? (
            <HistoryOutlined style={{ fontSize: '16px' }} />
          ) : (
            <ClockCircleOutlined style={{ fontSize: '16px' }} />
          )
        }
      >
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {/* Change Header */}
          <Space>
            <Tag color="red">
              <Text delete>{entry.old_sku}</Text>
            </Tag>
            <Text>→</Text>
            <Tag color="green">
              <Text strong>{entry.new_sku}</Text>
            </Tag>
          </Space>

          {/* Metadata */}
          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item
              label={
                <Space>
                  <ClockCircleOutlined />
                  <Text>Data</Text>
                </Space>
              }
            >
              <Space direction="vertical" size={0}>
                <Text>{dayjs(entry.changed_at).format('DD.MM.YYYY HH:mm:ss')}</Text>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {dayjs(entry.changed_at).fromNow()}
                </Text>
              </Space>
            </Descriptions.Item>

            {entry.changed_by_email && (
              <Descriptions.Item
                label={
                  <Space>
                    <UserOutlined />
                    <Text>Modificat de</Text>
                  </Space>
                }
              >
                <Tag icon={<UserOutlined />}>{entry.changed_by_email}</Tag>
              </Descriptions.Item>
            )}

            {entry.change_reason && (
              <Descriptions.Item
                label={
                  <Space>
                    <InfoCircleOutlined />
                    <Text>Motiv</Text>
                  </Space>
                }
              >
                <Paragraph style={{ margin: 0 }}>{entry.change_reason}</Paragraph>
              </Descriptions.Item>
            )}

            {entry.ip_address && (
              <Descriptions.Item
                label={
                  <Space>
                    <GlobalOutlined />
                    <Text>IP</Text>
                  </Space>
                }
              >
                <Text code>{entry.ip_address}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Space>
      </Timeline.Item>
    );
  };

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined />
          <span>Istoric SKU</span>
        </Space>
      }
      placement="right"
      width={600}
      onClose={onClose}
      open={visible}
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={loading}
        >
          Reîmprospătează
        </Button>
      }
    >
      {/* Product Info */}
      {productName && (
        <Alert
          message="Produs"
          description={
            <Space direction="vertical" size={0}>
              <Text strong>{productName}</Text>
              {currentSKU && (
                <Text type="secondary">
                  SKU curent: <Tag color="blue">{currentSKU}</Tag>
                </Text>
              )}
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" tip="Se încarcă istoricul..." />
        </div>
      )}

      {/* Empty State */}
      {!loading && history.length === 0 && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical">
              <Text>Nu există istoric de modificări SKU</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                SKU-ul acestui produs nu a fost niciodată modificat
              </Text>
            </Space>
          }
        />
      )}

      {/* History Timeline */}
      {!loading && history.length > 0 && (
        <>
          <Alert
            message={`${history.length} modificări înregistrate`}
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Timeline mode="left">
            {history.map((entry, index) => renderTimelineItem(entry, index))}
          </Timeline>
        </>
      )}
    </Drawer>
  );
};

export default SKUHistoryDrawer;
