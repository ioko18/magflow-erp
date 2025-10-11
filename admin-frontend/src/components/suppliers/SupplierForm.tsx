import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Row,
  Col,
  Upload,
  Alert,
  Divider,
  Typography
} from 'antd';
import { UploadOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;
const { Title } = Typography;

interface Supplier {
  id?: number;
  name: string;
  country: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  lead_time_days: number;
  min_order_value: number;
  min_order_qty: number;
  currency: string;
  payment_terms: string;
  notes?: string;
  tags?: string[];
}

interface SupplierFormProps {
  supplier?: Supplier | null;
  visible: boolean;
  onSave: (supplier: Supplier) => void;
  onCancel: () => void;
}

const SupplierForm: React.FC<SupplierFormProps> = ({
  supplier,
  visible,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (supplier && visible) {
      form.setFieldsValue({
        ...supplier,
        tags: supplier.tags || []
      });
    } else if (visible) {
      form.resetFields();
      form.setFieldsValue({
        country: 'China',
        currency: 'USD',
        lead_time_days: 30,
        min_order_value: 0,
        min_order_qty: 1,
        payment_terms: '30 days',
      });
    }
  }, [supplier, visible, form]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();

      const supplierData: Supplier = {
        ...values,
        tags: values.tags || []
      };

      onSave(supplierData);
    } catch (error) {
      console.error('Form validation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={supplier ? 'Editează Furnizor' : 'Furnizor Nou'}
      open={visible}
      onCancel={handleCancel}
      width={800}
      footer={[
        <Button key="cancel" onClick={handleCancel} icon={<CloseOutlined />}>
          Anulează
        </Button>,
        <Button
          key="save"
          type="primary"
          loading={loading}
          onClick={handleSubmit}
          icon={<SaveOutlined />}
        >
          {supplier ? 'Actualizează' : 'Creează'}
        </Button>
      ]}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark={true}
      >
        {/* Basic Information Section */}
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>Informații de Bază</Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Nume Furnizor"
                rules={[
                  { required: true, message: 'Numele furnizorului este obligatoriu' },
                  { min: 2, message: 'Numele trebuie să aibă cel puțin 2 caractere' },
                  { max: 255, message: 'Numele nu poate depăși 255 de caractere' }
                ]}
              >
                <Input placeholder="Numele companiei furnizor" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="country"
                label="Țară"
                rules={[{ required: true, message: 'Țara este obligatorie' }]}
              >
                <Select placeholder="Selectează țara furnizorului">
                  <Option value="China">🇨🇳 China</Option>
                  <Option value="Taiwan">🇹🇼 Taiwan</Option>
                  <Option value="Vietnam">🇻🇳 Vietnam</Option>
                  <Option value="South Korea">🇰🇷 Coreea de Sud</Option>
                  <Option value="Japan">🇯🇵 Japonia</Option>
                  <Option value="Malaysia">🇲🇾 Malaysia</Option>
                  <Option value="Thailand">🇹🇭 Thailanda</Option>
                  <Option value="Indonesia">🇮🇩 Indonezia</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </div>

        <Divider />

        {/* Contact Information Section */}
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>Informații Contact</Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contact_person"
                label="Persoană Contact"
                rules={[
                  { max: 255, message: 'Numele nu poate depăși 255 de caractere' }
                ]}
              >
                <Input placeholder="Nume persoană contact" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="email"
                label="Email"
                rules={[
                  { type: 'email', message: 'Email invalid' },
                  { max: 255, message: 'Email-ul nu poate depăși 255 de caractere' }
                ]}
              >
                <Input placeholder="email@furnizor.com" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="phone"
            label="Telefon"
            rules={[
              { max: 50, message: 'Telefonul nu poate depăși 50 de caractere' }
            ]}
          >
            <Input placeholder="+86 123 456 7890" />
          </Form.Item>
        </div>

        <Divider />

        {/* Commercial Terms Section */}
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>Termeni Comerciali</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="lead_time_days"
                label="Lead Time (zile)"
                rules={[
                  { required: true, message: 'Lead time-ul este obligatoriu' },
                  { type: 'number', min: 1, max: 365, message: 'Lead time-ul trebuie să fie între 1 și 365 de zile' }
                ]}
              >
                <InputNumber min={1} max={365} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="min_order_value"
                label="Valoare Minimă Comandă"
                rules={[
                  { type: 'number', min: 0, message: 'Valoarea minimă trebuie să fie pozitivă' }
                ]}
              >
                <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="min_order_qty"
                label="Cantitate Minimă"
                rules={[
                  { required: true, message: 'Cantitatea minimă este obligatorie' },
                  { type: 'number', min: 1, message: 'Cantitatea minimă trebuie să fie cel puțin 1' }
                ]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="currency"
                label="Monedă"
                rules={[{ required: true, message: 'Moneda este obligatorie' }]}
              >
                <Select placeholder="Selectează moneda">
                  <Option value="USD">💵 USD (Dolari americani)</Option>
                  <Option value="CNY">💰 CNY (Yuan chinezesc)</Option>
                  <Option value="EUR">💶 EUR (Euro)</Option>
                  <Option value="RON">🇷🇴 RON (Lei românești)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="payment_terms"
                label="Termeni de Plată"
                rules={[
                  { required: true, message: 'Termenii de plată sunt obligatorii' },
                  { max: 255, message: 'Termenii nu pot depăși 255 de caractere' }
                ]}
              >
                <Input placeholder="ex: 30 days, T/T, L/C" />
              </Form.Item>
            </Col>
          </Row>
        </div>

        <Divider />

        {/* Additional Information Section */}
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>Informații Suplimentare</Title>

          <Form.Item
            name="notes"
            label="Note și Observații"
          >
            <TextArea
              rows={4}
              placeholder="Observații suplimentare despre furnizor, calitatea produselor, relația comercială, etc."
            />
          </Form.Item>

          <Alert
            message="Sfaturi utile"
            description={
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                <li>Completează toate informațiile disponibile pentru o gestionare eficientă</li>
                <li>Lead time-ul afectează calculul cantităților de comandă</li>
                <li>Valoarea minimă comandă influențează deciziile de reaprovizionare</li>
                <li>Notează orice particularități ale relației comerciale</li>
              </ul>
            }
            type="info"
            showIcon
            style={{ marginTop: '16px' }}
          />
        </div>

        {/* File Upload Section */}
        <div style={{ marginBottom: '24px' }}>
          <Title level={5}>Documente și Fișiere</Title>
          <Upload
            name="files"
            listType="text"
            multiple
            beforeUpload={() => false} // Prevent auto upload
          >
            <Button icon={<UploadOutlined />}>
              Selectează fișiere (contracte, cataloage, etc.)
            </Button>
          </Upload>
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
            Formate acceptate: PDF, DOC, XLS, imagini. Maxim 10MB per fișier.
          </div>
        </div>
      </Form>
    </Modal>
  );
};

export default SupplierForm;
