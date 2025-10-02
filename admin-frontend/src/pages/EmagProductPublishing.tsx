import React, { useState, useEffect } from 'react';
import {
  Card,
  Steps,
  Button,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Space,
  Divider,
  Alert,
  Spin,
  Tag,
  Row,
  Col,
  Typography,
  Modal,
  Table,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import api from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;
const { Step } = Steps;

interface Category {
  id: number;
  name: string;
  is_allowed: number;
  characteristics?: Characteristic[];
}

interface Characteristic {
  id: number;
  name: string;
  type_id: number;
  is_mandatory: number;
  values?: CharacteristicValue[];
}

interface CharacteristicValue {
  id: number;
  name: string;
}

interface VatRate {
  id: number;
  name: string;
  rate: number;
}

interface HandlingTime {
  id: number;
  value: number;
  name: string;
}

const EmagProductPublishing: React.FC = () => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [accountType, setAccountType] = useState<'main' | 'fbe'>('main');
  const [publishingMode, setPublishingMode] = useState<'draft' | 'complete'>('draft');
  
  // Reference data
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [vatRates, setVatRates] = useState<VatRate[]>([]);
  const [handlingTimes, setHandlingTimes] = useState<HandlingTime[]>([]);
  
  // Category browser modal
  const [categoryModalVisible, setCategoryModalVisible] = useState(false);
  const [categoryLoading, setCategoryLoading] = useState(false);
  
  // EAN matcher modal
  const [eanModalVisible, setEanModalVisible] = useState(false);
  const [eanSearchValue, setEanSearchValue] = useState('');
  const [eanResults, setEanResults] = useState<any[]>([]);

  useEffect(() => {
    loadReferenceData();
  }, [accountType]);

  const loadReferenceData = async () => {
    try {
      setLoading(true);
      
      // Load VAT rates
      const vatResponse = await api.get(`/emag/publishing/vat-rates?account_type=${accountType}`);
      if (vatResponse.data.status === 'success') {
        setVatRates(vatResponse.data.data.vat_rates || []);
      }
      
      // Load handling times
      const htResponse = await api.get(`/emag/publishing/handling-times?account_type=${accountType}`);
      if (htResponse.data.status === 'success') {
        setHandlingTimes(htResponse.data.data.handling_times || []);
      }
      
      message.success('Reference data loaded successfully');
    } catch (error: any) {
      message.error('Failed to load reference data: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async (page: number = 1) => {
    try {
      setCategoryLoading(true);
      const response = await api.get(
        `/emag/publishing/categories?current_page=${page}&items_per_page=20&account_type=${accountType}`
      );
      
      if (response.data.status === 'success') {
        setCategories(response.data.data.results || []);
      }
    } catch (error: any) {
      message.error('Failed to load categories: ' + (error.response?.data?.detail || error.message));
    } finally {
      setCategoryLoading(false);
    }
  };

  const loadCategoryDetails = async (categoryId: number) => {
    try {
      const response = await api.get(
        `/emag/publishing/categories/${categoryId}?account_type=${accountType}`
      );
      
      if (response.data.status === 'success' && response.data.data.results?.[0]) {
        setSelectedCategory(response.data.data.results[0]);
        form.setFieldsValue({ category_id: categoryId });
        message.success('Category loaded with characteristics');
      }
    } catch (error: any) {
      message.error('Failed to load category details: ' + (error.response?.data?.detail || error.message));
    }
  };

  const searchByEAN = async () => {
    if (!eanSearchValue) {
      message.warning('Please enter an EAN code');
      return;
    }

    try {
      setLoading(true);
      const response = await api.post(
        `/emag/publishing/match-ean?account_type=${accountType}`,
        { eans: [eanSearchValue] }
      );
      
      if (response.data.status === 'success') {
        setEanResults(response.data.data.products || []);
        if (response.data.data.products_found === 0) {
          message.info('No products found with this EAN');
        } else {
          message.success(`Found ${response.data.data.products_found} product(s)`);
        }
      }
    } catch (error: any) {
      message.error('EAN search failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      let endpoint = '';
      let payload: any = {};

      if (publishingMode === 'draft') {
        endpoint = '/emag/publishing/draft';
        payload = {
          product_id: values.product_id,
          name: values.name,
          brand: values.brand,
          part_number: values.part_number,
          category_id: values.category_id,
          ean: values.ean ? [values.ean] : undefined,
        };
      } else {
        endpoint = '/emag/publishing/complete';
        payload = {
          product_id: values.product_id,
          category_id: values.category_id,
          name: values.name,
          part_number: values.part_number,
          brand: values.brand,
          description: values.description,
          sale_price: values.sale_price,
          vat_id: values.vat_id,
          stock: [{ warehouse_id: 1, value: values.stock || 0 }],
          handling_time: [{ warehouse_id: 1, value: values.handling_time || 0 }],
          images: values.images || [],
          characteristics: values.characteristics || [],
          ean: values.ean ? [values.ean] : undefined,
        };
      }

      const response = await api.post(`${endpoint}?account_type=${accountType}`, payload);
      
      if (response.data.status === 'success') {
        message.success('Product published successfully!');
        form.resetFields();
        setCurrentStep(0);
      }
    } catch (error: any) {
      message.error('Publishing failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const categoryColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Allowed',
      dataIndex: 'is_allowed',
      key: 'is_allowed',
      width: 100,
      render: (allowed: number) => (
        <Tag color={allowed === 1 ? 'green' : 'red'}>
          {allowed === 1 ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Action',
      key: 'action',
      width: 100,
      render: (_: any, record: Category) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            loadCategoryDetails(record.id);
            setCategoryModalVisible(false);
          }}
        >
          Select
        </Button>
      ),
    },
  ];

  const renderBasicInfo = () => (
    <Card title="Basic Product Information">
      <Form.Item
        label="Product ID"
        name="product_id"
        rules={[{ required: true, message: 'Please enter product ID' }]}
      >
        <InputNumber style={{ width: '100%' }} placeholder="Enter product ID" />
      </Form.Item>

      <Form.Item
        label="Product Name"
        name="name"
        rules={[{ required: true, message: 'Please enter product name' }]}
      >
        <Input placeholder="Enter product name" />
      </Form.Item>

      <Form.Item
        label="Brand"
        name="brand"
        rules={[{ required: true, message: 'Please enter brand' }]}
      >
        <Input placeholder="Enter brand name" />
      </Form.Item>

      <Form.Item
        label="Part Number"
        name="part_number"
        rules={[{ required: true, message: 'Please enter part number' }]}
      >
        <Input placeholder="Enter unique part number" />
      </Form.Item>

      <Form.Item label="EAN Code" name="ean">
        <Input
          placeholder="Enter EAN code (optional)"
          addonAfter={
            <Button
              type="link"
              size="small"
              icon={<SearchOutlined />}
              onClick={() => setEanModalVisible(true)}
            >
              Search
            </Button>
          }
        />
      </Form.Item>

      <Form.Item
        label="Category"
        name="category_id"
        rules={[{ required: true, message: 'Please select category' }]}
      >
        <Input
          placeholder="Select category"
          readOnly
          addonAfter={
            <Button
              type="link"
              size="small"
              onClick={() => {
                loadCategories();
                setCategoryModalVisible(true);
              }}
            >
              Browse
            </Button>
          }
        />
      </Form.Item>

      {selectedCategory && (
        <Alert
          message={`Selected Category: ${selectedCategory.name}`}
          description={`Category ID: ${selectedCategory.id} | Characteristics: ${selectedCategory.characteristics?.length || 0}`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
    </Card>
  );

  const renderCompleteInfo = () => (
    <>
      <Card title="Product Details" style={{ marginTop: 16 }}>
        <Form.Item
          label="Description"
          name="description"
          rules={[{ required: publishingMode === 'complete', message: 'Please enter description' }]}
        >
          <TextArea rows={4} placeholder="Enter product description (HTML allowed)" />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Sale Price"
              name="sale_price"
              rules={[{ required: publishingMode === 'complete', message: 'Please enter price' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                placeholder="Enter price"
                min={0}
                step={0.01}
                precision={2}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="VAT Rate"
              name="vat_id"
              rules={[{ required: publishingMode === 'complete', message: 'Please select VAT rate' }]}
            >
              <Select placeholder="Select VAT rate">
                {vatRates.map((vat) => (
                  <Option key={vat.id} value={vat.id}>
                    {vat.name} ({(vat.rate * 100).toFixed(0)}%)
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Stock Quantity" name="stock">
              <InputNumber
                style={{ width: '100%' }}
                placeholder="Enter stock quantity"
                min={0}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Handling Time (days)" name="handling_time">
              <Select placeholder="Select handling time">
                {handlingTimes.map((ht) => (
                  <Option key={ht.id} value={ht.value}>
                    {ht.name} ({ht.value} days)
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
      </Card>
    </>
  );

  const steps = [
    {
      title: 'Basic Info',
      content: renderBasicInfo(),
    },
    {
      title: 'Details',
      content: publishingMode === 'complete' ? renderCompleteInfo() : null,
    },
    {
      title: 'Review',
      content: (
        <Card title="Review & Publish">
          <Alert
            message="Ready to Publish"
            description="Please review all information before publishing to eMAG."
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Button
            type="primary"
            size="large"
            icon={<CheckCircleOutlined />}
            onClick={handlePublish}
            loading={loading}
            block
          >
            Publish to eMAG
          </Button>
        </Card>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <PlusOutlined /> eMAG Product Publishing
      </Title>
      <Paragraph>
        Publish products to eMAG marketplace. Choose between draft mode (minimal fields) or complete mode (all fields).
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>Account Type:</Text>
              <Select
                value={accountType}
                onChange={setAccountType}
                style={{ width: '100%' }}
              >
                <Option value="main">MAIN Account</Option>
                <Option value="fbe">FBE Account</Option>
              </Select>
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>Publishing Mode:</Text>
              <Select
                value={publishingMode}
                onChange={setPublishingMode}
                style={{ width: '100%' }}
              >
                <Option value="draft">Draft Mode (Minimal Fields)</Option>
                <Option value="complete">Complete Mode (All Fields)</Option>
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          {steps.map((item) => (
            <Step key={item.title} title={item.title} />
          ))}
        </Steps>

        <Form form={form} layout="vertical">
          <div>{steps[currentStep].content}</div>
        </Form>

        <Divider />

        <Space>
          {currentStep > 0 && (
            <Button onClick={() => setCurrentStep(currentStep - 1)}>
              Previous
            </Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
              Next
            </Button>
          )}
        </Space>
      </Spin>

      {/* Category Browser Modal */}
      <Modal
        title="Browse Categories"
        open={categoryModalVisible}
        onCancel={() => setCategoryModalVisible(false)}
        width={800}
        footer={null}
      >
        <Spin spinning={categoryLoading}>
          <Table
            dataSource={categories}
            columns={categoryColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        </Spin>
      </Modal>

      {/* EAN Matcher Modal */}
      <Modal
        title="Search by EAN"
        open={eanModalVisible}
        onCancel={() => setEanModalVisible(false)}
        width={600}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="Enter EAN code"
            value={eanSearchValue}
            onChange={(e) => setEanSearchValue(e.target.value)}
            onPressEnter={searchByEAN}
            addonAfter={
              <Button type="link" icon={<SearchOutlined />} onClick={searchByEAN}>
                Search
              </Button>
            }
          />
          {eanResults.length > 0 && (
            <Alert
              message={`Found ${eanResults.length} product(s)`}
              type="success"
              showIcon
            />
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default EmagProductPublishing;
