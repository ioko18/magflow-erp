import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Row,
  Col,
  Space,
  Tag,
  Divider,
} from 'antd';
import {
  SaveOutlined,
  DollarOutlined,
  InboxOutlined,
  TagOutlined,
} from '@ant-design/icons';
import api from '../services/api';

const { TextArea } = Input;
const { Option } = Select;

interface Product {
  id: number;
  name: string;
  part_number?: string;
  brand?: string;
  description?: string | null;
  price?: number | null;
  sale_price?: number | null;
  recommended_price?: number | null;
  stock: number;
  status: 'active' | 'inactive';
  currency?: string;
  warranty?: number | null;
  account_type?: string;
}

interface QuickEditModalProps {
  visible: boolean;
  product: Product | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function QuickEditModal({ visible, product, onClose, onSuccess }: QuickEditModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (product && visible) {
      form.setFieldsValue({
        name: product.name,
        description: product.description || '',
        price: product.price || 0,
        sale_price: product.sale_price || undefined,
        recommended_price: product.recommended_price || undefined,
        stock: product.stock,
        status: product.status,
        warranty: product.warranty || undefined,
      });
    }
  }, [product, visible, form]);

  const handleSubmit = async () => {
    if (!product) return;

    try {
      setLoading(true);
      const values = await form.validateFields();

      // Determine the correct API endpoint based on product type
      const isEmagProduct = product.account_type && ['main', 'fbe'].includes(product.account_type);
      
      if (isEmagProduct) {
        // For eMAG products, use the enhanced API
        await api.put(`/api/v1/emag/enhanced/products/${product.id}`, {
          ...values,
          account_type: product.account_type,
        });
      } else {
        // For local products, use the standard products API
        await api.put(`/products/${product.id}`, values);
      }

      message.success('Produsul a fost actualizat cu succes!');
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error updating product:', error);
      const errorMessage = error.response?.data?.detail || 'Eroare la actualizarea produsului';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <TagOutlined />
          <span>Editare Rapidă: {product?.name}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText="Salvează"
      cancelText="Anulează"
      width={700}
      okButtonProps={{ icon: <SaveOutlined /> }}
    >
      {product && (
        <>
          <Space style={{ marginBottom: 16 }}>
            <Tag color="blue">ID: {product.id}</Tag>
            {product.part_number && <Tag color="purple">SKU: {product.part_number}</Tag>}
            {product.brand && <Tag color="green">{product.brand}</Tag>}
            {product.account_type && (
              <Tag color={product.account_type === 'fbe' ? 'cyan' : 'geekblue'}>
                {product.account_type.toUpperCase()}
              </Tag>
            )}
          </Space>

          <Divider style={{ margin: '12px 0' }} />

          <Form
            form={form}
            layout="vertical"
            initialValues={{
              status: 'active',
            }}
          >
            {/* Basic Info */}
            <Form.Item
              label="Nume Produs"
              name="name"
              rules={[
                { required: true, message: 'Numele produsului este obligatoriu' },
                { min: 3, message: 'Numele trebuie să aibă minim 3 caractere' },
              ]}
            >
              <Input placeholder="Nume produs" />
            </Form.Item>

            <Form.Item label="Descriere" name="description">
              <TextArea rows={3} placeholder="Descriere produs" />
            </Form.Item>

            {/* Pricing */}
            <Divider orientation="left">
              <Space>
                <DollarOutlined />
                Prețuri
              </Space>
            </Divider>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  label="Preț de Bază"
                  name="price"
                  rules={[
                    { required: true, message: 'Prețul este obligatoriu' },
                    { type: 'number', min: 0, message: 'Prețul trebuie să fie pozitiv' },
                  ]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                    addonAfter={product.currency || 'RON'}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Preț Vânzare" name="sale_price">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                    addonAfter={product.currency || 'RON'}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Preț Recomandat" name="recommended_price">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                    addonAfter={product.currency || 'RON'}
                  />
                </Form.Item>
              </Col>
            </Row>

            {/* Stock & Status */}
            <Divider orientation="left">
              <Space>
                <InboxOutlined />
                Stoc & Status
              </Space>
            </Divider>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  label="Stoc"
                  name="stock"
                  rules={[
                    { required: true, message: 'Stocul este obligatoriu' },
                    { type: 'number', min: 0, message: 'Stocul trebuie să fie pozitiv' },
                  ]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    placeholder="0"
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Status" name="status">
                  <Select>
                    <Option value="active">Activ</Option>
                    <Option value="inactive">Inactiv</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Garanție (luni)" name="warranty">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={240}
                    placeholder="24"
                  />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </>
      )}
    </Modal>
  );
}
