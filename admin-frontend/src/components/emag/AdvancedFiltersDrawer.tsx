/**
 * Advanced Filters Drawer Component
 * 
 * Provides advanced filtering options for eMAG products based on API v4.4.9 specifications.
 * Includes validation_status, offer_validation_status, stock ranges, and more.
 */

import React, { useState } from 'react'
import {
  Drawer,
  Form,
  Select,
  InputNumber,
  Button,
  Space,
  Divider,
  Typography,
  Tag,
  Collapse,
  Tooltip,
  Row,
  Col
} from 'antd'
import {
  FilterOutlined,
  ClearOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'

const { Text } = Typography
const { Option } = Select
const { Panel } = Collapse

export interface ProductFilters {
  validation_status?: number[]
  offer_validation_status?: number
  stock_min?: number
  stock_max?: number
  genius_eligibility?: number
  ownership?: number
  status?: number
  part_number_key?: string
  general_stock?: number
  estimated_stock?: number
}

interface AdvancedFiltersDrawerProps {
  visible: boolean
  onClose: () => void
  onApplyFilters: (filters: ProductFilters) => void
  currentFilters?: ProductFilters
}

// Validation Status values from API v4.4.9
const VALIDATION_STATUS_OPTIONS = [
  { value: 0, label: 'Draft', description: 'Product is in draft state', color: 'default' },
  { value: 1, label: 'Pending Approval', description: 'Waiting for approval', color: 'processing' },
  { value: 2, label: 'Rejected', description: 'Product rejected', color: 'error' },
  { value: 3, label: 'Waiting EAN Approval', description: 'EAN pending approval', color: 'warning' },
  { value: 4, label: 'Waiting Documentation', description: 'Documentation pending', color: 'warning' },
  { value: 5, label: 'Waiting Translation', description: 'Translation pending', color: 'warning' },
  { value: 6, label: 'Waiting Images', description: 'Images pending', color: 'warning' },
  { value: 7, label: 'Waiting Characteristics', description: 'Characteristics pending', color: 'warning' },
  { value: 8, label: 'Waiting Category', description: 'Category pending', color: 'warning' },
  { value: 9, label: 'Approved Documentation', description: 'Documentation approved', color: 'success' },
  { value: 10, label: 'Rejected Documentation', description: 'Documentation rejected', color: 'error' },
  { value: 11, label: 'Update Accepted', description: 'Update accepted', color: 'success' },
  { value: 12, label: 'Update Rejected', description: 'Update rejected (allowed)', color: 'warning' },
  { value: 13, label: 'Waiting Saleable Offer', description: 'Waiting for saleable offer', color: 'warning' },
  { value: 14, label: 'Unsuccessful Translation', description: 'Translation failed', color: 'error' },
  { value: 15, label: 'Translation in Progress', description: 'Being translated', color: 'processing' },
  { value: 16, label: 'Translation Pending', description: 'Translation queued', color: 'warning' },
  { value: 17, label: 'Partial Translation', description: 'Partially translated (allowed)', color: 'warning' }
]

// Offer Validation Status from API v4.4.9
const OFFER_VALIDATION_STATUS_OPTIONS = [
  { value: 1, label: 'Valid', description: 'Offer is valid and can be sold', color: 'success', icon: <CheckCircleOutlined /> },
  { value: 2, label: 'Invalid Price', description: 'Price is invalid (not allowed)', color: 'error', icon: <CloseCircleOutlined /> }
]

// Genius Eligibility
const GENIUS_ELIGIBILITY_OPTIONS = [
  { value: 0, label: 'Not Eligible', color: 'default' },
  { value: 1, label: 'Eligible', color: 'gold' }
]

// Ownership
const OWNERSHIP_OPTIONS = [
  { value: 1, label: 'eMAG Owned', description: 'Product owned by eMAG', color: 'blue' },
  { value: 2, label: 'Vendor Owned', description: 'Product owned by vendor', color: 'green' }
]

// Status
const STATUS_OPTIONS = [
  { value: 0, label: 'Inactive', color: 'default' },
  { value: 1, label: 'Active', color: 'success' },
  { value: 2, label: 'End of Life', color: 'warning' }
]

const AdvancedFiltersDrawer: React.FC<AdvancedFiltersDrawerProps> = ({
  visible,
  onClose,
  onApplyFilters,
  currentFilters
}) => {
  const [form] = Form.useForm()
  const [activeKeys, setActiveKeys] = useState<string[]>(['validation', 'stock'])

  const handleApply = () => {
    const values = form.getFieldsValue()
    
    // Remove undefined/null values
    const filters: ProductFilters = {}
    Object.keys(values).forEach(key => {
      if (values[key] !== undefined && values[key] !== null && values[key] !== '') {
        filters[key as keyof ProductFilters] = values[key]
      }
    })
    
    onApplyFilters(filters)
    onClose()
  }

  const handleClear = () => {
    form.resetFields()
    onApplyFilters({})
  }

  return (
    <Drawer
      title={
        <Space>
          <FilterOutlined />
          <span>Advanced Filters</span>
        </Space>
      }
      placement="right"
      onClose={onClose}
      open={visible}
      width={500}
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={handleClear} icon={<ClearOutlined />}>
            Clear All
          </Button>
          <Button type="primary" onClick={handleApply} icon={<FilterOutlined />}>
            Apply Filters
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={currentFilters}
      >
        <Collapse
          activeKey={activeKeys}
          onChange={(keys) => setActiveKeys(keys as string[])}
          bordered={false}
        >
          {/* Validation Status */}
          <Panel
            header={
              <Space>
                <Text strong>Validation Status</Text>
                <Tooltip title="Product validation status (0-17)">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            key="validation"
          >
            <Form.Item
              label="Validation Status"
              name="validation_status"
              tooltip="Select one or more validation statuses"
            >
              <Select
                mode="multiple"
                placeholder="Select validation statuses"
                optionFilterProp="label"
                maxTagCount="responsive"
              >
                {VALIDATION_STATUS_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value} label={opt.label}>
                    <Space>
                      <Tag color={opt.color}>{opt.value}</Tag>
                      <Text>{opt.label}</Text>
                    </Space>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {opt.description}
                    </Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Offer Validation Status"
              name="offer_validation_status"
              tooltip="Offer validation status (1=Valid, 2=Invalid Price)"
            >
              <Select placeholder="Select offer validation status" allowClear>
                {OFFER_VALIDATION_STATUS_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>
                    <Space>
                      {opt.icon}
                      <Tag color={opt.color}>{opt.label}</Tag>
                    </Space>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {opt.description}
                    </Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Panel>

          {/* Stock Filters */}
          <Panel
            header={
              <Space>
                <Text strong>Stock Filters</Text>
                <Tooltip title="Filter by stock quantity ranges">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            key="stock"
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="Min Stock"
                  name="stock_min"
                  tooltip="Minimum stock quantity"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    placeholder="Min"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="Max Stock"
                  name="stock_max"
                  tooltip="Maximum stock quantity"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    placeholder="Max"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              label="General Stock"
              name="general_stock"
              tooltip="Return offers with general_stock between 0 and this value"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                placeholder="e.g., 100"
              />
            </Form.Item>

            <Form.Item
              label="Estimated Stock"
              name="estimated_stock"
              tooltip="Return offers with estimated_stock between 0 and this value"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                placeholder="e.g., 100"
              />
            </Form.Item>
          </Panel>

          {/* Product Attributes */}
          <Panel
            header={
              <Space>
                <Text strong>Product Attributes</Text>
                <Tooltip title="Filter by product attributes">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            key="attributes"
          >
            <Form.Item
              label="Status"
              name="status"
              tooltip="Product status (0=Inactive, 1=Active, 2=EOL)"
            >
              <Select placeholder="Select status" allowClear>
                {STATUS_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>
                    <Tag color={opt.color}>{opt.label}</Tag>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Genius Eligibility"
              name="genius_eligibility"
              tooltip="Genius program eligibility"
            >
              <Select placeholder="Select genius eligibility" allowClear>
                {GENIUS_ELIGIBILITY_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>
                    <Tag color={opt.color}>{opt.label}</Tag>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Ownership"
              name="ownership"
              tooltip="Product ownership (1=eMAG, 2=Vendor)"
            >
              <Select placeholder="Select ownership" allowClear>
                {OWNERSHIP_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>
                    <Space>
                      <Tag color={opt.color}>{opt.label}</Tag>
                    </Space>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {opt.description}
                    </Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Panel>
        </Collapse>

        <Divider />

        <Text type="secondary" style={{ fontSize: 12 }}>
          <InfoCircleOutlined /> Filters are applied according to eMAG API v4.4.9 specifications.
          Multiple validation statuses can be selected for OR logic.
        </Text>
      </Form>
    </Drawer>
  )
}

export default AdvancedFiltersDrawer
