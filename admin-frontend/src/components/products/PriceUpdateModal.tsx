/**
 * Price Update Modal Component
 * 
 * Modal for updating product prices on eMAG FBE account
 * Includes min/max price validation and automatic VAT calculation
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  InputNumber,
  Button,
  Space,
  Alert,
  Statistic,
  Row,
  Col,
  Divider,
  Typography,
  Spin,
  message,
} from 'antd';
import {
  DollarOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import api from '../../services/api';

const { Text, Title } = Typography;

interface PriceUpdateModalProps {
  visible: boolean;
  productId: number | null;
  productName?: string;
  currentSKU?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

interface PriceInfo {
  product_id: number;
  name: string;
  sku: string;
  base_price: number;
  base_price_with_vat: number;
  has_fbe_offer: boolean;
  emag_offer_id?: string;
  min_sale_price?: number;
  max_sale_price?: number;
  recommended_price?: number;
  min_sale_price_with_vat?: number;
  max_sale_price_with_vat?: number;
  recommended_price_with_vat?: number;
}

const PriceUpdateModal: React.FC<PriceUpdateModalProps> = ({
  visible,
  productId,
  productName,
  currentSKU,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [priceInfo, setPriceInfo] = useState<PriceInfo | null>(null);
  const [calculatedPriceExVat, setCalculatedPriceExVat] = useState<number | null>(null);
  const displayName = priceInfo?.name ?? productName;
  const displaySKU = priceInfo?.sku ?? currentSKU;

  // Load price info when modal opens
  useEffect(() => {
    if (visible && productId) {
      loadPriceInfo();
    } else {
      // Reset when modal closes
      setPriceInfo(null);
      form.resetFields();
      setCalculatedPriceExVat(null);
    }
  }, [visible, productId]);

  const loadPriceInfo = async () => {
    if (!productId) return;

    try {
      setLoadingInfo(true);
      const response = await api.get(`/emag/price/product/${productId}/info`);
      const info = response.data;
      setPriceInfo(info);

      // Pre-populate form with current prices if available
      if (info.has_fbe_offer) {
        form.setFieldsValue({
          sale_price_with_vat: info.base_price_with_vat,
          min_sale_price_with_vat: info.min_sale_price_with_vat,
          max_sale_price_with_vat: info.max_sale_price_with_vat,
        });
        
        // Calculate ex-VAT price for display
        if (info.base_price_with_vat) {
          setCalculatedPriceExVat(info.base_price);
        }
      }
    } catch (error: any) {
      console.error('Error loading price info:', error);
      message.error(
        error.response?.data?.detail || 'Failed to load price information'
      );
    } finally {
      setLoadingInfo(false);
    }
  };

  const handlePriceChange = (value: number | null) => {
    if (value) {
      // Calculate ex-VAT price (21% VAT for Romania)
      const exVat = value / 1.21;
      setCalculatedPriceExVat(exVat);
    } else {
      setCalculatedPriceExVat(null);
    }
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields();
      const values = form.getFieldsValue();

      if (!productId) {
        message.error('Product ID is missing');
        return;
      }

      setLoading(true);

      const payload = {
        product_id: productId,
        sale_price_with_vat: values.sale_price_with_vat,
        min_sale_price_with_vat: values.min_sale_price_with_vat || null,
        max_sale_price_with_vat: values.max_sale_price_with_vat || null,
        vat_rate: 21.0, // Romania VAT rate
      };

      await api.post('/emag/price/update', payload);

      message.success(
        `Preț actualizat cu succes! Noul preț: ${values.sale_price_with_vat} RON (cu TVA)`
      );

      if (onSuccess) {
        onSuccess();
      }

      onClose();
    } catch (error: any) {
      console.error('Error updating price:', error);
      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        'Failed to update price';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <DollarOutlined style={{ color: '#52c41a', fontSize: '20px' }} />
          <Title level={4} style={{ margin: 0 }}>
            Actualizare Preț eMAG FBE
          </Title>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="cancel" onClick={onClose} size="large">
          Anulează
        </Button>,
        <Button
          key="submit"
          type="primary"
          icon={<CheckCircleOutlined />}
          onClick={handleSubmit}
          loading={loading}
          size="large"
        >
          Actualizează Preț
        </Button>,
      ]}
    >
      {loadingInfo ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">Se încarcă informațiile despre preț...</Text>
          </div>
        </div>
      ) : (
        <>
          {/* Product Info */}
          {(priceInfo || displayName || displaySKU) && (
            <Alert
              message={
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  {displayName && (
                    <Text strong style={{ fontSize: '16px' }}>
                      {displayName}
                    </Text>
                  )}
                  {displaySKU && <Text type="secondary">SKU: {displaySKU}</Text>}
                  {priceInfo &&
                    (priceInfo.has_fbe_offer ? (
                      <Text type="success">
                        ✓ Produs publicat pe eMAG FBE (ID: {priceInfo.emag_offer_id})
                      </Text>
                    ) : (
                      <Text type="warning">
                        ⚠ Produsul nu este publicat pe eMAG FBE
                      </Text>
                    ))}
                </Space>
              }
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
              style={{ marginBottom: 24 }}
            />
          )}

          {/* Warning if product not on FBE */}
          {priceInfo && !priceInfo.has_fbe_offer && (
            <Alert
              message="Produsul nu este publicat pe eMAG FBE"
              description="Pentru a actualiza prețul, produsul trebuie să fie mai întâi publicat pe eMAG FBE. Rulează 'Sincronizare FBE' sau 'Sincronizare AMBELE' pentru a publica produsul."
              type="error"
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}

          {/* Price Form */}
          <Form
            form={form}
            layout="vertical"
            disabled={!priceInfo?.has_fbe_offer}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="Preț Vânzare (cu TVA)"
                  name="sale_price_with_vat"
                  rules={[
                    { required: true, message: 'Prețul este obligatoriu' },
                    {
                      type: 'number',
                      min: 0.01,
                      message: 'Prețul trebuie să fie mai mare de 0',
                    },
                  ]}
                  extra="Prețul final afișat pe eMAG (include TVA 21%)"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.01}
                    step={0.01}
                    precision={2}
                    addonAfter="RON"
                    placeholder="Ex: 30.00"
                    onChange={handlePriceChange}
                  />
                </Form.Item>
              </Col>

              <Col span={12}>
                <div style={{ marginTop: 30 }}>
                  <Statistic
                    title="Preț fără TVA (trimis la eMAG)"
                    value={calculatedPriceExVat?.toFixed(4) || '—'}
                    suffix="RON"
                    valueStyle={{ color: '#1890ff', fontSize: '20px' }}
                  />
                </div>
              </Col>
            </Row>

            

            

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="Preț Minim (cu TVA)"
                  name="min_sale_price_with_vat"
                  extra="Preț minim permis de eMAG"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.01}
                    step={0.01}
                    precision={2}
                    addonAfter="RON"
                    placeholder="Ex: 25.00"
                  />
                </Form.Item>
              </Col>

              <Col span={12}>
                <Form.Item
                  label="Preț Maxim (cu TVA)"
                  name="max_sale_price_with_vat"
                  extra="Preț maxim permis de eMAG"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.01}
                    step={0.01}
                    precision={2}
                    addonAfter="RON"
                    placeholder="Ex: 50.00"
                  />
                </Form.Item>
              </Col>
            </Row>

            {/* Current Prices Display */}
            {priceInfo?.has_fbe_offer && (
              <>
                <Divider>Prețuri Curente</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="Preț Curent"
                      value={priceInfo.base_price_with_vat?.toFixed(2) || '—'}
                      suffix="RON"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                  {priceInfo.min_sale_price_with_vat && (
                    <Col span={8}>
                      <Statistic
                        title="Preț Minim"
                        value={priceInfo.min_sale_price_with_vat.toFixed(2)}
                        suffix="RON"
                        valueStyle={{ fontSize: '16px', color: '#ff4d4f' }}
                      />
                    </Col>
                  )}
                  {priceInfo.max_sale_price_with_vat && (
                    <Col span={8}>
                      <Statistic
                        title="Preț Maxim"
                        value={priceInfo.max_sale_price_with_vat.toFixed(2)}
                        suffix="RON"
                        valueStyle={{ fontSize: '16px', color: '#52c41a' }}
                      />
                    </Col>
                  )}
                </Row>
              </>
            )}
          </Form>
        </>
      )}
    </Modal>
  );
};

export default PriceUpdateModal;
