/**
 * Product Measurements Modal Component
 * 
 * Add or update product dimensions and weight using eMAG Measurements API (v4.4.9)
 * Helps with accurate shipping calculations and product display
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
  Typography,
  Badge,
  Card,
  Statistic,
  Divider,
} from 'antd';
import {
  ColumnHeightOutlined,
  SaveOutlined,
  InfoCircleOutlined,
  CarOutlined,
} from '@ant-design/icons';
import { saveProductMeasurements } from '../services/emagAdvancedApi';

const { Text } = Typography;

interface ProductMeasurementsModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  productId: number;
  productName: string;
  accountType: 'main' | 'fbe';
  currentMeasurements?: {
    length?: number;
    width?: number;
    height?: number;
    weight?: number;
  };
}

const ProductMeasurementsModal: React.FC<ProductMeasurementsModalProps> = ({
  visible,
  onClose,
  onSuccess,
  productId,
  productName,
  accountType,
  currentMeasurements,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [volume, setVolume] = useState<number>(0);

  useEffect(() => {
    if (visible && currentMeasurements) {
      form.setFieldsValue({
        length: currentMeasurements.length,
        width: currentMeasurements.width,
        height: currentMeasurements.height,
        weight: currentMeasurements.weight,
      });
      calculateVolume();
    }
  }, [visible, currentMeasurements]);

  const calculateVolume = () => {
    const length = form.getFieldValue('length') || 0;
    const width = form.getFieldValue('width') || 0;
    const height = form.getFieldValue('height') || 0;
    
    if (length > 0 && width > 0 && height > 0) {
      // Volume in cubic centimeters (mm³ to cm³)
      const volumeCm3 = (length * width * height) / 1000;
      setVolume(volumeCm3);
    } else {
      setVolume(0);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      setLoading(true);
      
      await saveProductMeasurements({
        product_id: productId,
        account_type: accountType,
        length: values.length,
        width: values.width,
        height: values.height,
        weight: values.weight,
      });
      
      message.success('Măsurătorile au fost salvate cu succes!');
      onSuccess?.();
      onClose();
    } catch (error: any) {
      console.error('Save measurements error:', error);
      if (error.errorFields) {
        message.error('Completează toate câmpurile obligatorii');
      } else {
        message.error(error.response?.data?.detail || 'Eroare la salvarea măsurătorilor');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleValuesChange = () => {
    calculateVolume();
  };

  return (
    <Modal
      title={
        <Space>
          <ColumnHeightOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <span>Măsurători Produs</span>
          <Badge count="v4.4.9" style={{ backgroundColor: '#52c41a' }} />
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
          Salvează Măsurători
        </Button>,
      ]}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          message="Măsurători volumetrice pentru transport"
          description="Adaugă dimensiunile și greutatea produsului pentru calculul corect al costurilor de transport și afișare pe site."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

        <Card size="small" style={{ background: '#f0f2f5' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary">Produs:</Text> <Text strong>{productName}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">ID:</Text> <Text strong>{productId}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">Cont:</Text> <Text strong>{accountType.toUpperCase()}</Text>
            </Col>
          </Row>
        </Card>

        <Form
          form={form}
          layout="vertical"
          disabled={loading}
          onValuesChange={handleValuesChange}
        >
          <Divider orientation="left">
            <Space>
              <ColumnHeightOutlined style={{ color: '#1890ff' }} />
              Dimensiuni (milimetri)
            </Space>
          </Divider>

          <Alert
            message="Unitate de măsură: milimetri (mm)"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="Lungime (mm)"
                name="length"
                rules={[
                  { required: true, message: 'Lungimea este obligatorie' },
                  { type: 'number', min: 0, max: 999999, message: 'Valoare între 0 și 999,999' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 200.00"
                  precision={2}
                  addonAfter="mm"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Lățime (mm)"
                name="width"
                rules={[
                  { required: true, message: 'Lățimea este obligatorie' },
                  { type: 'number', min: 0, max: 999999, message: 'Valoare între 0 și 999,999' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 150.50"
                  precision={2}
                  addonAfter="mm"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Înălțime (mm)"
                name="height"
                rules={[
                  { required: true, message: 'Înălțimea este obligatorie' },
                  { type: 'number', min: 0, max: 999999, message: 'Valoare între 0 și 999,999' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 80.00"
                  precision={2}
                  addonAfter="mm"
                />
              </Form.Item>
            </Col>
          </Row>

          {volume > 0 && (
            <Card size="small" style={{ marginBottom: 16, background: '#e6f7ff' }}>
              <Statistic
                title="Volum Calculat"
                value={volume.toFixed(2)}
                suffix="cm³"
                prefix={<ColumnHeightOutlined />}
                valueStyle={{ color: '#1890ff', fontSize: 18 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                Volum = Lungime × Lățime × Înălțime
              </Text>
            </Card>
          )}

          <Divider orientation="left">
            <Space>
              <CarOutlined style={{ color: '#52c41a' }} />
              Greutate
            </Space>
          </Divider>

          <Alert
            message="Unitate de măsură: grame (g)"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="Greutate (g)"
            name="weight"
            rules={[
              { required: true, message: 'Greutatea este obligatorie' },
              { type: 'number', min: 0, max: 999999, message: 'Valoare între 0 și 999,999' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="Ex: 450.75"
              precision={2}
              addonAfter="g"
            />
          </Form.Item>
        </Form>

        <Alert
          message="Conversii utile"
          description={
            <Space direction="vertical" size={4}>
              <Text style={{ fontSize: 12 }}>• 1 cm = 10 mm</Text>
              <Text style={{ fontSize: 12 }}>• 1 kg = 1000 g</Text>
              <Text style={{ fontSize: 12 }}>• Toate valorile acceptă până la 2 zecimale</Text>
            </Space>
          }
          type="info"
          style={{ fontSize: 12 }}
        />

        <Divider />

        <Card size="small" style={{ background: '#fffbe6' }}>
          <Space direction="vertical" size={4}>
            <Text strong style={{ fontSize: 13 }}>
              <InfoCircleOutlined /> Beneficii măsurători corecte:
            </Text>
            <Text style={{ fontSize: 12 }}>✓ Calculul corect al costurilor de transport</Text>
            <Text style={{ fontSize: 12 }}>✓ Afișare precisă pe pagina produsului</Text>
            <Text style={{ fontSize: 12 }}>✓ Reducerea retururilor din cauza așteptărilor greșite</Text>
            <Text style={{ fontSize: 12 }}>✓ Optimizarea logisticii și depozitării</Text>
          </Space>
        </Card>
      </Space>
    </Modal>
  );
};

export default ProductMeasurementsModal;
