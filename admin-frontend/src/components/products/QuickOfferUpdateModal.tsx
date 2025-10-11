/**
 * Quick Offer Update Modal Component
 * 
 * Provides interface for quick offer updates using Light Offer API (v4.4.9)
 * Allows updating price, stock, and other offer fields without full product documentation
 */

import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  InputNumber,
  Button,
  Space,
  message,
  Alert,
  Row,
  Col,
  Select,
  Switch,
  Divider,
  Typography,
  Badge,
  Card,
} from 'antd';
import {
  ThunderboltOutlined,
  DollarOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  SaveOutlined,
  PercentageOutlined,
} from '@ant-design/icons';
import { updateOfferLight, getVATRates, getHandlingTimes, VATRate, HandlingTime } from '../../services/emag/emagAdvancedApi';

const { Text } = Typography;

interface QuickOfferUpdateModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  productId: number;
  accountType: 'main' | 'fbe';
  currentData?: {
    sale_price?: number;
    recommended_price?: number;
    min_sale_price?: number;
    max_sale_price?: number;
    stock?: number;
    handling_time?: number;
    vat_id?: number;
    status?: number;
  };
}

const QuickOfferUpdateModal: React.FC<QuickOfferUpdateModalProps> = ({
  visible,
  onClose,
  onSuccess,
  productId,
  accountType,
  currentData,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [vatRates, setVatRates] = useState<VATRate[]>([]);
  const [handlingTimes, setHandlingTimes] = useState<HandlingTime[]>([]);
  const [loadingMetadata, setLoadingMetadata] = useState(false);

  useEffect(() => {
    if (visible) {
      loadMetadata();
      // Set initial form values
      form.setFieldsValue({
        sale_price: currentData?.sale_price,
        recommended_price: currentData?.recommended_price,
        min_sale_price: currentData?.min_sale_price,
        max_sale_price: currentData?.max_sale_price,
        stock_value: currentData?.stock,
        handling_time_value: currentData?.handling_time,
        vat_id: currentData?.vat_id,
        status: currentData?.status === 1,
        warehouse_id: 1,
      });
    }
  }, [visible, currentData]);

  const loadMetadata = async () => {
    setLoadingMetadata(true);
    try {
      const [vatResponse, handlingResponse] = await Promise.all([
        getVATRates(accountType),
        getHandlingTimes(accountType),
      ]);
      setVatRates(vatResponse.data.vat_rates);
      setHandlingTimes(handlingResponse.data.handling_times);
    } catch (error: any) {
      console.error('Error loading metadata:', error);
      message.warning('Nu s-au putut încărca toate datele auxiliare');
    } finally {
      setLoadingMetadata(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      setLoading(true);
      
      // Build request payload - only include changed fields
      const payload: any = {
        product_id: productId,
        account_type: accountType,
      };

      // Add only fields that have values
      if (values.sale_price !== undefined && values.sale_price !== currentData?.sale_price) {
        payload.sale_price = values.sale_price;
      }
      if (values.recommended_price !== undefined && values.recommended_price !== currentData?.recommended_price) {
        payload.recommended_price = values.recommended_price;
      }
      if (values.min_sale_price !== undefined && values.min_sale_price !== currentData?.min_sale_price) {
        payload.min_sale_price = values.min_sale_price;
      }
      if (values.max_sale_price !== undefined && values.max_sale_price !== currentData?.max_sale_price) {
        payload.max_sale_price = values.max_sale_price;
      }
      if (values.stock_value !== undefined && values.stock_value !== currentData?.stock) {
        payload.stock_value = values.stock_value;
        payload.warehouse_id = values.warehouse_id || 1;
      }
      if (values.handling_time_value !== undefined && values.handling_time_value !== currentData?.handling_time) {
        payload.handling_time_value = values.handling_time_value;
        payload.warehouse_id = values.warehouse_id || 1;
      }
      if (values.vat_id !== undefined && values.vat_id !== currentData?.vat_id) {
        payload.vat_id = values.vat_id;
      }
      if (values.status !== undefined) {
        payload.status = values.status ? 1 : 0;
      }

      await updateOfferLight(payload);
      
      message.success('Oferta a fost actualizată cu succes!');
      onSuccess?.();
      onClose();
    } catch (error: any) {
      console.error('Update offer error:', error);
      message.error(error.response?.data?.detail || 'Eroare la actualizarea ofertei');
    } finally {
      setLoading(false);
    }
  };

  const calculateDiscount = () => {
    const salePrice = form.getFieldValue('sale_price');
    const recommendedPrice = form.getFieldValue('recommended_price');
    
    if (salePrice && recommendedPrice && recommendedPrice > salePrice) {
      const discount = ((recommendedPrice - salePrice) / recommendedPrice) * 100;
      return discount.toFixed(1);
    }
    return null;
  };

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined style={{ fontSize: 20, color: '#52c41a' }} />
          <span>Actualizare Rapidă Ofertă</span>
          <Badge count="Light API v4.4.9" style={{ backgroundColor: '#52c41a' }} />
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={700}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={loading}>
          Anulează
        </Button>,
        <Button
          key="submit"
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSubmit}
          loading={loading}
        >
          Actualizează Oferta
        </Button>,
      ]}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          message="Actualizare rapidă și eficientă"
          description="Folosește Light Offer API pentru actualizări rapide de preț și stoc. Modifică doar câmpurile necesare - restul rămân neschimbate."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

        <Card size="small" style={{ background: '#f0f2f5' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary">Produs ID:</Text> <Text strong>{productId}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">Cont:</Text> <Text strong>{accountType.toUpperCase()}</Text>
            </Col>
          </Row>
        </Card>

        <Form
          form={form}
          layout="vertical"
          disabled={loading || loadingMetadata}
        >
          <Divider orientation="left">
            <Space>
              <DollarOutlined style={{ color: '#52c41a' }} />
              Prețuri
            </Space>
          </Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Preț Vânzare (fără TVA)"
                name="sale_price"
                rules={[
                  { type: 'number', min: 0, message: 'Prețul trebuie să fie pozitiv' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 99.99"
                  precision={2}
                  addonAfter="RON"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Preț Recomandat (RRP)"
                name="recommended_price"
                rules={[
                  { type: 'number', min: 0, message: 'Prețul trebuie să fie pozitiv' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 129.99"
                  precision={2}
                  addonAfter="RON"
                />
              </Form.Item>
            </Col>
          </Row>

          {calculateDiscount() && (
            <Alert
              message={
                <Space>
                  <PercentageOutlined />
                  <span>Reducere: {calculateDiscount()}%</span>
                </Space>
              }
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Preț Minim"
                name="min_sale_price"
                tooltip="Prețul minim acceptat pentru validare"
                rules={[
                  { type: 'number', min: 0, message: 'Prețul trebuie să fie pozitiv' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 80.00"
                  precision={2}
                  addonAfter="RON"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Preț Maxim"
                name="max_sale_price"
                tooltip="Prețul maxim acceptat pentru validare"
                rules={[
                  { type: 'number', min: 0, message: 'Prețul trebuie să fie pozitiv' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 150.00"
                  precision={2}
                  addonAfter="RON"
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">
            <Space>
              <InboxOutlined style={{ color: '#1890ff' }} />
              Stoc & Disponibilitate
            </Space>
          </Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Cantitate Stoc"
                name="stock_value"
                rules={[
                  { type: 'number', min: 0, message: 'Stocul trebuie să fie pozitiv' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 50"
                  addonAfter="buc"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Depozit ID"
                name="warehouse_id"
                tooltip="ID-ul depozitului (default: 1)"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="1"
                  min={1}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={
                  <Space>
                    <ClockCircleOutlined />
                    Timp Procesare (zile)
                  </Space>
                }
                name="handling_time_value"
                tooltip="Număr de zile de la comandă până la expediere"
              >
                <Select
                  placeholder="Selectează"
                  loading={loadingMetadata}
                  showSearch
                >
                  {handlingTimes.map((ht) => (
                    <Select.Option key={ht.id} value={ht.id}>
                      {ht.id} {ht.id === 1 ? 'zi' : 'zile'}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Rată TVA"
                name="vat_id"
                tooltip="Rata TVA aplicabilă produsului"
              >
                <Select
                  placeholder="Selectează"
                  loading={loadingMetadata}
                >
                  {vatRates.map((vat) => (
                    <Select.Option key={vat.vat_id} value={vat.vat_id}>
                      {vat.vat_rate}% TVA
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Status</Divider>

          <Form.Item
            label="Ofertă Activă"
            name="status"
            valuePropName="checked"
            tooltip="Activează sau dezactivează oferta"
          >
            <Switch checkedChildren="Activ" unCheckedChildren="Inactiv" />
          </Form.Item>
        </Form>

        <Alert
          message="Notă"
          description="Doar câmpurile modificate vor fi trimise către eMAG. Câmpurile necompletate rămân neschimbate."
          type="warning"
          showIcon
          style={{ fontSize: 12 }}
        />
      </Space>
    </Modal>
  );
};

export default QuickOfferUpdateModal;
