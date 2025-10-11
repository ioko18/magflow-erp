/**
 * Quick Offer Update Component
 * 
 * Provides rapid price and stock updates using eMAG Light Offer API (v4.4.9).
 * This component is optimized for quick updates without full product sync.
 */

import React, { useState } from 'react';
import { 
  InputNumber, 
  Button, 
  Space, 
  message, 
  Tooltip, 
  Modal,
  Form,
  Select,
  Divider,
  Alert
} from 'antd';
import { 
  ThunderboltOutlined, 
  DollarOutlined, 
  InboxOutlined,
  InfoCircleOutlined 
} from '@ant-design/icons';
import api from '../../services/api';

const { Option } = Select;

interface QuickOfferUpdateProps {
  productId: number;
  currentPrice?: number;
  currentStock?: number;
  accountType?: 'main' | 'fbe';
  onSuccess?: () => void;
}

const QuickOfferUpdate: React.FC<QuickOfferUpdateProps> = ({
  productId,
  currentPrice = 0,
  currentStock = 0,
  accountType = 'main',
  onSuccess
}) => {
  const [price, setPrice] = useState<number>(currentPrice);
  const [stock, setStock] = useState<number>(currentStock);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [updateType, setUpdateType] = useState<'price' | 'stock' | 'both'>('both');

  const handleQuickUpdate = async () => {
    if (updateType === 'price' && (!price || price <= 0)) {
      message.error('Prețul trebuie să fie mai mare decât 0');
      return;
    }

    if (updateType === 'stock' && stock < 0) {
      message.error('Stocul nu poate fi negativ');
      return;
    }

    setLoading(true);

    try {
      let response;

      if (updateType === 'price') {
        // Update only price
        response = await api.post('/emag/enhanced/light-offer/update-price', {
          product_id: productId,
          sale_price: price,
          account_type: accountType
        });
      } else if (updateType === 'stock') {
        // Update only stock
        response = await api.post('/emag/enhanced/light-offer/update-stock', {
          product_id: productId,
          stock: stock,
          account_type: accountType
        });
      } else {
        // Update both (not implemented yet, would need new endpoint)
        message.info('Update combinat va fi disponibil în curând');
        setLoading(false);
        return;
      }

      if (response.data.status === 'success') {
        message.success(`${updateType === 'price' ? 'Preț' : 'Stoc'} actualizat cu succes!`);
        setModalVisible(false);
        if (onSuccess) {
          onSuccess();
        }
      } else {
        message.error('Eroare la actualizare');
      }
    } catch (error: any) {
      console.error('Failed to update offer:', error);
      const errorMsg = error.response?.data?.detail || 'Eroare la actualizare ofertă';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const showModal = () => {
    setPrice(currentPrice);
    setStock(currentStock);
    setModalVisible(true);
  };

  return (
    <>
      <Tooltip title="Update rapid preț/stoc folosind Light Offer API">
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          onClick={showModal}
          size="small"
        >
          Quick Update
        </Button>
      </Tooltip>

      <Modal
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#1890ff' }} />
            Quick Offer Update
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            Anulează
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={loading}
            onClick={handleQuickUpdate}
            icon={<ThunderboltOutlined />}
          >
            Actualizează Rapid
          </Button>
        ]}
        width={500}
      >
        <Alert
          message="Light Offer API v4.4.9"
          description="Update rapid folosind noul API eMAG. Doar câmpurile modificate sunt trimise."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form layout="vertical">
          <Form.Item label="Tip actualizare">
            <Select
              value={updateType}
              onChange={(value) => setUpdateType(value)}
              style={{ width: '100%' }}
            >
              <Option value="price">
                <Space>
                  <DollarOutlined />
                  Doar Preț
                </Space>
              </Option>
              <Option value="stock">
                <Space>
                  <InboxOutlined />
                  Doar Stoc
                </Space>
              </Option>
              <Option value="both" disabled>
                <Space>
                  <ThunderboltOutlined />
                  Ambele (în curând)
                </Space>
              </Option>
            </Select>
          </Form.Item>

          <Divider />

          {(updateType === 'price' || updateType === 'both') && (
            <Form.Item
              label={
                <Space>
                  <DollarOutlined />
                  Preț (RON, fără TVA)
                  <Tooltip title="Prețul de vânzare fără TVA">
                    <InfoCircleOutlined style={{ color: '#999' }} />
                  </Tooltip>
                </Space>
              }
            >
              <InputNumber
                value={price}
                onChange={(value) => setPrice(value || 0)}
                prefix="RON"
                precision={2}
                min={0}
                step={0.01}
                style={{ width: '100%' }}
                size="large"
              />
              {currentPrice > 0 && price !== currentPrice && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  Preț curent: {currentPrice.toFixed(2)} RON
                  {price > currentPrice && (
                    <span style={{ color: '#52c41a', marginLeft: 8 }}>
                      (+{((price - currentPrice) / currentPrice * 100).toFixed(1)}%)
                    </span>
                  )}
                  {price < currentPrice && (
                    <span style={{ color: '#ff4d4f', marginLeft: 8 }}>
                      ({((price - currentPrice) / currentPrice * 100).toFixed(1)}%)
                    </span>
                  )}
                </div>
              )}
            </Form.Item>
          )}

          {(updateType === 'stock' || updateType === 'both') && (
            <Form.Item
              label={
                <Space>
                  <InboxOutlined />
                  Stoc (bucăți)
                  <Tooltip title="Cantitatea disponibilă în stoc">
                    <InfoCircleOutlined style={{ color: '#999' }} />
                  </Tooltip>
                </Space>
              }
            >
              <InputNumber
                value={stock}
                onChange={(value) => setStock(value || 0)}
                min={0}
                step={1}
                style={{ width: '100%' }}
                size="large"
              />
              {currentStock >= 0 && stock !== currentStock && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  Stoc curent: {currentStock} bucăți
                  {stock > currentStock && (
                    <span style={{ color: '#52c41a', marginLeft: 8 }}>
                      (+{stock - currentStock})
                    </span>
                  )}
                  {stock < currentStock && (
                    <span style={{ color: '#ff4d4f', marginLeft: 8 }}>
                      ({stock - currentStock})
                    </span>
                  )}
                </div>
              )}
            </Form.Item>
          )}

          <Alert
            message="Avantaje Light Offer API"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>⚡ 50% mai rapid decât API tradițional</li>
                <li>📦 Payload mai mic (doar câmpuri modificate)</li>
                <li>🎯 Optimal pentru update-uri frecvente</li>
                <li>✅ Conform eMAG API v4.4.9</li>
              </ul>
            }
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>
    </>
  );
};

export default QuickOfferUpdate;
