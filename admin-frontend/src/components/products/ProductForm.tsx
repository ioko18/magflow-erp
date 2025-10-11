import { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Card,
  Row,
  Col,
  message,
  Space,
  Collapse,
  Tag,
  Alert,
  Tooltip,
} from 'antd';
import {
  SaveOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import api from '../../services/api';

const { TextArea } = Input;
const { Option } = Select;

interface Category {
  id: number;
  name: string;
}

interface ProductFormData {
  // Basic Information
  name: string;
  sku: string;
  description?: string;
  short_description?: string;
  brand?: string;
  manufacturer?: string;
  
  // Pricing
  base_price?: number;
  recommended_price?: number;
  currency: string;
  
  // Physical Properties
  weight_kg?: number;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
  
  // Status
  is_active: boolean;
  is_discontinued: boolean;
  
  // eMAG Fields
  ean?: string;
  emag_category_id?: number;
  emag_brand_id?: number;
  emag_warranty_months?: number;
  
  // Metadata
  category_ids: number[];
  characteristics?: Record<string, string>;
  images?: string[];
  attachments?: string[];
  
  // Options
  auto_publish_emag?: boolean;
}

interface ValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  emag_ready: boolean;
  missing_fields: string[];
}

interface ProductFormProps {
  productId?: number;
  initialData?: Partial<ProductFormData>;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export default function ProductForm({ productId, initialData, onSuccess, onCancel }: ProductFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [characteristicKey, setCharacteristicKey] = useState('');
  const [characteristicValue, setCharacteristicValue] = useState('');
  const [characteristics, setCharacteristics] = useState<Record<string, string>>({});

  // Note: Product data should be passed via initialData prop
  // The productId is used only for update operations

  // Load initial data when provided
  useEffect(() => {
    fetchCategories();
    if (initialData) {
      form.setFieldsValue({
        ...initialData,
        currency: initialData.currency || 'RON',
        is_active: initialData.is_active !== undefined ? initialData.is_active : true,
        is_discontinued: initialData.is_discontinued || false,
      });
      if (initialData.characteristics) {
        setCharacteristics(initialData.characteristics);
      }
    }
  }, [initialData, form]);

  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories');
      if (response.data && Array.isArray(response.data)) {
        setCategories(response.data);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
      message.error('Eroare la încărcarea categoriilor');
    }
  };

  const handleValidate = async () => {
    try {
      setValidating(true);
      const values = await form.validateFields();
      
      const productData = {
        ...values,
        characteristics: Object.keys(characteristics).length > 0 ? characteristics : undefined,
      };

      const response = await api.post('/products/validate/', productData);
      setValidation(response.data);
      
      if (response.data.is_valid) {
        message.success('Produsul este valid!');
      } else {
        message.warning('Produsul are erori de validare');
      }
    } catch (error: any) {
      console.error('Validation error:', error);
      message.error('Eroare la validarea produsului');
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      const productData = {
        ...values,
        characteristics: Object.keys(characteristics).length > 0 ? characteristics : undefined,
      };

      if (productId) {
        // Update existing product
        await api.put(`/products/${productId}/`, productData);
        message.success('Produs actualizat cu succes!');
      } else {
        // Create new product
        await api.post('/products/', productData);
        message.success('Produs creat cu succes!');
      }

      if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      console.error('Submit error:', error);
      const errorMessage = error.response?.data?.detail || 'Eroare la salvarea produsului';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const addCharacteristic = () => {
    if (characteristicKey && characteristicValue) {
      setCharacteristics({
        ...characteristics,
        [characteristicKey]: characteristicValue,
      });
      setCharacteristicKey('');
      setCharacteristicValue('');
    }
  };

  const removeCharacteristic = (key: string) => {
    const newCharacteristics = { ...characteristics };
    delete newCharacteristics[key];
    setCharacteristics(newCharacteristics);
  };

  const generateSKU = () => {
    const name = form.getFieldValue('name') || '';
    const brand = form.getFieldValue('brand') || '';
    const timestamp = Date.now().toString().slice(-6);
    
    let sku = '';
    if (brand) {
      sku = brand.substring(0, 3).toUpperCase();
    }
    if (name) {
      sku += name.substring(0, 3).toUpperCase();
    }
    sku += timestamp;
    
    form.setFieldsValue({ sku });
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Card
        title={
          <Space>
            <ShopOutlined />
            {productId ? 'Editare Produs' : 'Produs Nou'}
          </Space>
        }
        extra={
          <Space>
            <Button onClick={onCancel} icon={<CloseOutlined />}>
              Anulează
            </Button>
            <Button
              type="default"
              onClick={handleValidate}
              loading={validating}
              icon={<CheckCircleOutlined />}
            >
              Validează
            </Button>
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={loading}
              icon={<SaveOutlined />}
            >
              Salvează
            </Button>
          </Space>
        }
      >
        {validation && (
          <Alert
            type={validation.is_valid ? 'success' : 'warning'}
            message={
              validation.is_valid
                ? 'Produs valid'
                : `Produs invalid: ${validation.errors.length} erori`
            }
            description={
              <div>
                {validation.errors.length > 0 && (
                  <div>
                    <strong>Erori:</strong>
                    <ul>
                      {validation.errors.map((error, idx) => (
                        <li key={idx}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {validation.warnings.length > 0 && (
                  <div>
                    <strong>Avertismente:</strong>
                    <ul>
                      {validation.warnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {!validation.emag_ready && (
                  <div>
                    <Tag color="orange">Nu este gata pentru eMAG</Tag>
                    <div>Câmpuri lipsă: {validation.missing_fields.join(', ')}</div>
                  </div>
                )}
                {validation.emag_ready && (
                  <Tag color="green" icon={<CheckCircleOutlined />}>
                    Gata pentru eMAG
                  </Tag>
                )}
              </div>
            }
            closable
            onClose={() => setValidation(null)}
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          initialValues={{
            currency: 'RON',
            is_active: true,
            is_discontinued: false,
            category_ids: [],
          }}
        >
          {/* Basic Information */}
          <Card type="inner" title="Informații de Bază" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="Nume Produs"
                  name="name"
                  rules={[
                    { required: true, message: 'Numele produsului este obligatoriu' },
                    { min: 3, message: 'Numele trebuie să aibă minim 3 caractere' },
                  ]}
                >
                  <Input placeholder="Ex: Modul amplificator audio stereo" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label={
                    <Space>
                      SKU (Cod Produs)
                      <Tooltip title="Cod unic pentru identificarea produsului">
                        <InfoCircleOutlined />
                      </Tooltip>
                    </Space>
                  }
                  name="sku"
                  rules={[
                    { required: true, message: 'SKU-ul este obligatoriu' },
                    { min: 2, message: 'SKU-ul trebuie să aibă minim 2 caractere' },
                  ]}
                >
                  <Input
                    placeholder="Ex: AMP-2024-001"
                    addonAfter={
                      <Button type="link" size="small" onClick={generateSKU}>
                        Generează
                      </Button>
                    }
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Brand" name="brand">
                  <Input placeholder="Ex: Arduino, Raspberry Pi" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Producător" name="manufacturer">
                  <Input placeholder="Ex: Texas Instruments" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item label="Descriere Scurtă" name="short_description">
              <Input.TextArea
                rows={2}
                maxLength={500}
                showCount
                placeholder="Descriere scurtă pentru listări (max 500 caractere)"
              />
            </Form.Item>

            <Form.Item label="Descriere Completă" name="description">
              <TextArea
                rows={4}
                placeholder="Descriere detaliată a produsului"
              />
            </Form.Item>

            <Form.Item label="Categorii" name="category_ids">
              <Select
                mode="multiple"
                placeholder="Selectează categorii"
                optionFilterProp="children"
              >
                {categories.map(cat => (
                  <Option key={cat.id} value={cat.id}>
                    {cat.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Card>

          {/* Pricing */}
          <Card type="inner" title="Prețuri" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  label="Preț de Bază"
                  name="base_price"
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
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Monedă" name="currency">
                  <Select>
                    <Option value="RON">RON</Option>
                    <Option value="EUR">EUR</Option>
                    <Option value="USD">USD</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Physical Properties */}
          <Card type="inner" title="Proprietăți Fizice" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item label="Greutate (kg)" name="weight_kg">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="Lungime (cm)" name="length_cm">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="Lățime (cm)" name="width_cm">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="Înălțime (cm)" name="height_cm">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={2}
                    placeholder="0.00"
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* eMAG Integration */}
          <Card
            type="inner"
            title={
              <Space>
                <ShopOutlined />
                Integrare eMAG
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Cod EAN" name="ean">
                  <Input placeholder="Ex: 5901234123457" maxLength={18} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Garanție (luni)" name="emag_warranty_months">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={240}
                    placeholder="24"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="ID Categorie eMAG" name="emag_category_id">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="Ex: 123"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="ID Brand eMAG" name="emag_brand_id">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="Ex: 456"
                  />
                </Form.Item>
              </Col>
            </Row>

            {!productId && (
              <Form.Item
                name="auto_publish_emag"
                valuePropName="checked"
                label="Auto-publicare eMAG"
              >
                <Switch checkedChildren="Da" unCheckedChildren="Nu" />
              </Form.Item>
            )}
          </Card>

          {/* Status */}
          <Card type="inner" title="Status" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="is_active" valuePropName="checked" label="Status Produs">
                  <Switch checkedChildren="Activ" unCheckedChildren="Inactiv" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="is_discontinued" valuePropName="checked" label="Discontinuat">
                  <Switch checkedChildren="Da" unCheckedChildren="Nu" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Advanced Options */}
          <Collapse
            items={[
              {
                key: '1',
                label: 'Opțiuni Avansate',
                children: (
                  <div>
              {/* Characteristics */}
              <Card type="inner" title="Caracteristici" size="small" style={{ marginBottom: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Row gutter={8}>
                    <Col span={10}>
                      <Input
                        placeholder="Cheie (ex: Culoare)"
                        value={characteristicKey}
                        onChange={(e) => setCharacteristicKey(e.target.value)}
                      />
                    </Col>
                    <Col span={10}>
                      <Input
                        placeholder="Valoare (ex: Roșu)"
                        value={characteristicValue}
                        onChange={(e) => setCharacteristicValue(e.target.value)}
                      />
                    </Col>
                    <Col span={4}>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={addCharacteristic}
                        block
                      >
                        Adaugă
                      </Button>
                    </Col>
                  </Row>

                  {Object.entries(characteristics).map(([key, value]) => (
                    <Tag
                      key={key}
                      closable
                      onClose={() => removeCharacteristic(key)}
                    >
                      <strong>{key}:</strong> {value}
                    </Tag>
                  ))}
                </Space>
              </Card>

              {/* Images */}
              <Card type="inner" title="Imagini" size="small" style={{ marginBottom: 16 }}>
                <Alert
                  message="Adaugă URL-uri pentru imagini sau încarcă fișiere"
                  type="info"
                  showIcon
                  style={{ marginBottom: 8 }}
                />
                <Form.Item name="images">
                  <Input.TextArea
                    rows={3}
                    placeholder="URL-uri imagini (câte unul pe linie)"
                  />
                </Form.Item>
              </Card>

              {/* Attachments */}
              <Card type="inner" title="Atașamente" size="small">
                <Alert
                  message="Adaugă URL-uri pentru manuale, certificate, etc."
                  type="info"
                  showIcon
                  style={{ marginBottom: 8 }}
                />
                <Form.Item name="attachments">
                  <Input.TextArea
                    rows={2}
                    placeholder="URL-uri atașamente (câte unul pe linie)"
                  />
                </Form.Item>
              </Card>
                  </div>
                ),
              },
            ]}
            style={{ marginBottom: 16 }}
          />
        </Form>
      </Card>
    </div>
  );
}
