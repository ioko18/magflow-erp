import React, { useState } from 'react';
import {
  Drawer,
  Form,
  Space,
  Button,
  Slider,
  Select,
  DatePicker,
  InputNumber,
  Divider,
  Typography,
  Row,
  Col,
  Switch,
  Tag,
} from 'antd';
import {
  FilterOutlined,
  ClearOutlined,
  SearchOutlined,
} from '@ant-design/icons';
const { Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface AdvancedFiltersProps {
  visible: boolean;
  onClose: () => void;
  onApply: (filters: FilterValues) => void;
  initialValues?: FilterValues;
}

export interface FilterValues {
  priceRange?: [number, number];
  stockRange?: [number, number];
  dateRange?: [string, string];
  categoryId?: number;
  brand?: string;
  vatId?: number;
  hasImages?: boolean;
  hasDescription?: boolean;
  hasEAN?: boolean;
  syncStatus?: string;
  warrantyRange?: [number, number];
}

const AdvancedFilters: React.FC<AdvancedFiltersProps> = ({
  visible,
  onClose,
  onApply,
  initialValues,
}) => {
  const [form] = Form.useForm();
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 1000]);
  const [stockRange, setStockRange] = useState<[number, number]>([0, 500]);
  const [warrantyRange, setWarrantyRange] = useState<[number, number]>([0, 60]);

  const handleApply = () => {
    const values = form.getFieldsValue();
    
    // Build filter object
    const filters: FilterValues = {
      priceRange: priceRange[0] > 0 || priceRange[1] < 1000 ? priceRange : undefined,
      stockRange: stockRange[0] > 0 || stockRange[1] < 500 ? stockRange : undefined,
      warrantyRange: warrantyRange[0] > 0 || warrantyRange[1] < 60 ? warrantyRange : undefined,
      categoryId: values.categoryId,
      brand: values.brand,
      vatId: values.vatId,
      hasImages: values.hasImages,
      hasDescription: values.hasDescription,
      hasEAN: values.hasEAN,
      syncStatus: values.syncStatus,
    };

    // Add date range if selected
    if (values.dateRange && values.dateRange.length === 2) {
      filters.dateRange = [
        values.dateRange[0].format('YYYY-MM-DD'),
        values.dateRange[1].format('YYYY-MM-DD'),
      ];
    }

    onApply(filters);
    onClose();
  };

  const handleReset = () => {
    form.resetFields();
    setPriceRange([0, 1000]);
    setStockRange([0, 500]);
    setWarrantyRange([0, 60]);
  };

  return (
    <Drawer
      title={
        <Space>
          <FilterOutlined />
          <span>Filtre Avansate</span>
        </Space>
      }
      placement="right"
      width={450}
      open={visible}
      onClose={onClose}
      footer={
        <Space style={{ float: 'right' }}>
          <Button icon={<ClearOutlined />} onClick={handleReset}>
            Resetează
          </Button>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleApply}>
            Aplică Filtre
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initialValues}
      >
        {/* Price Range */}
        <div>
          <Text strong>Interval Preț (RON)</Text>
          <div style={{ padding: '16px 8px' }}>
            <Slider
              range
              min={0}
              max={1000}
              step={10}
              value={priceRange}
              onChange={(value) => setPriceRange(value as [number, number])}
              marks={{
                0: '0',
                250: '250',
                500: '500',
                750: '750',
                1000: '1000+',
              }}
              tooltip={{
                formatter: (value) => `${value} RON`,
              }}
            />
          </div>
          <Row gutter={16}>
            <Col span={12}>
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={priceRange[1]}
                value={priceRange[0]}
                onChange={(value) => setPriceRange([value || 0, priceRange[1]])}
                prefix="Min:"
                suffix="RON"
              />
            </Col>
            <Col span={12}>
              <InputNumber
                style={{ width: '100%' }}
                min={priceRange[0]}
                max={10000}
                value={priceRange[1]}
                onChange={(value) => setPriceRange([priceRange[0], value || 1000])}
                prefix="Max:"
                suffix="RON"
              />
            </Col>
          </Row>
        </div>

        <Divider />

        {/* Stock Range */}
        <div>
          <Text strong>Interval Stoc</Text>
          <div style={{ padding: '16px 8px' }}>
            <Slider
              range
              min={0}
              max={500}
              step={10}
              value={stockRange}
              onChange={(value) => setStockRange(value as [number, number])}
              marks={{
                0: '0',
                100: '100',
                250: '250',
                500: '500+',
              }}
              tooltip={{
                formatter: (value) => `${value} buc`,
              }}
            />
          </div>
          <Row gutter={16}>
            <Col span={12}>
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={stockRange[1]}
                value={stockRange[0]}
                onChange={(value) => setStockRange([value || 0, stockRange[1]])}
                prefix="Min:"
                suffix="buc"
              />
            </Col>
            <Col span={12}>
              <InputNumber
                style={{ width: '100%' }}
                min={stockRange[0]}
                max={10000}
                value={stockRange[1]}
                onChange={(value) => setStockRange([stockRange[0], value || 500])}
                prefix="Max:"
                suffix="buc"
              />
            </Col>
          </Row>
        </div>

        <Divider />

        {/* Warranty Range */}
        <div>
          <Text strong>Garanție (luni)</Text>
          <div style={{ padding: '16px 8px' }}>
            <Slider
              range
              min={0}
              max={60}
              step={6}
              value={warrantyRange}
              onChange={(value) => setWarrantyRange(value as [number, number])}
              marks={{
                0: '0',
                12: '12',
                24: '24',
                36: '36',
                60: '60',
              }}
              tooltip={{
                formatter: (value) => `${value} luni`,
              }}
            />
          </div>
        </div>

        <Divider />

        {/* Date Range */}
        <Form.Item label="Interval Dată Creare" name="dateRange">
          <RangePicker
            style={{ width: '100%' }}
            format="DD/MM/YYYY"
            placeholder={['Data început', 'Data sfârșit']}
          />
        </Form.Item>

        {/* Category */}
        <Form.Item label="Categorie eMAG" name="categoryId">
          <Select
            placeholder="Selectează categorie"
            allowClear
            showSearch
            filterOption={(input, option) =>
              String(option?.children || '').toLowerCase().includes(input.toLowerCase())
            }
          >
            <Option value={1}>Electronice</Option>
            <Option value={2}>Calculatoare</Option>
            <Option value={3}>Telefoane</Option>
            {/* Add more categories dynamically */}
          </Select>
        </Form.Item>

        {/* Brand */}
        <Form.Item label="Brand" name="brand">
          <Select
            placeholder="Selectează brand"
            allowClear
            showSearch
            filterOption={(input, option) =>
              String(option?.children || '').toLowerCase().includes(input.toLowerCase())
            }
          >
            <Option value="Samsung">Samsung</Option>
            <Option value="Apple">Apple</Option>
            <Option value="Huawei">Huawei</Option>
            {/* Add more brands dynamically */}
          </Select>
        </Form.Item>

        {/* VAT Rate */}
        <Form.Item label="Cotă TVA" name="vatId">
          <Select placeholder="Selectează TVA" allowClear>
            <Option value={1}>19%</Option>
            <Option value={2}>9%</Option>
            <Option value={3}>5%</Option>
          </Select>
        </Form.Item>

        <Divider />

        {/* Boolean Filters */}
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Form.Item label="Are Imagini" name="hasImages" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item label="Are Descriere" name="hasDescription" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item label="Are Cod EAN" name="hasEAN" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>

        <Divider />

        {/* Sync Status */}
        <Form.Item label="Status Sincronizare" name="syncStatus">
          <Select placeholder="Selectează status" allowClear>
            <Option value="synced">
              <Tag color="success">Sincronizat</Tag>
            </Option>
            <Option value="pending">
              <Tag color="warning">În așteptare</Tag>
            </Option>
            <Option value="failed">
              <Tag color="error">Eșuat</Tag>
            </Option>
          </Select>
        </Form.Item>
      </Form>
    </Drawer>
  );
};

export default AdvancedFilters;
