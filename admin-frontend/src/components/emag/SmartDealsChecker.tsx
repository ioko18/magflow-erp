/**
 * Smart Deals Checker Component
 * 
 * Check if a product is eligible for eMAG Smart Deals program
 * Based on eMAG API v4.4.9 smart-deals-price-check endpoint
 */

import React, { useState } from 'react'
import {
  Modal,
  Button,
  Space,
  Alert,
  Spin,
  Typography,
  Descriptions,
  Tag,
  message,
  Statistic,
  Row,
  Col,
  Card
} from 'antd'
import {
  DollarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  PercentageOutlined
} from '@ant-design/icons'
import api from '../../services/api'

const { Text, Title } = Typography

interface SmartDealsCheckerProps {
  visible: boolean
  onClose: () => void
  productId?: number | string
  currentPrice?: number
  currency?: string
}

interface SmartDealsEligibility {
  eligible: boolean
  product_id: number
  current_price: number
  target_price: number
  discount_required: number
  discount_percentage: number
  currency: string
  message: string
  recommendations?: string[]
}

const SmartDealsChecker: React.FC<SmartDealsCheckerProps> = ({
  visible,
  onClose,
  productId,
  currentPrice,
  currency = 'RON'
}) => {
  const [loading, setLoading] = useState(false)
  const [eligibility, setEligibility] = useState<SmartDealsEligibility | null>(null)
  const [checked, setChecked] = useState(false)

  const handleCheck = async () => {
    if (!productId) {
      message.warning('Product ID is required')
      return
    }

    setLoading(true)
    setChecked(true)

    try {
      const response = await api.post('/emag/smart-deals/check-eligibility', {
        product_id: productId,
        current_price: currentPrice
      })

      if (response.data) {
        setEligibility(response.data)
        
        if (response.data.eligible) {
          message.success('Product is eligible for Smart Deals!')
        } else {
          message.info('Product needs price adjustment for Smart Deals eligibility')
        }
      }
    } catch (error: any) {
      console.error('Smart Deals check failed:', error)
      message.error(error.response?.data?.detail || 'Failed to check Smart Deals eligibility')
      setEligibility(null)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setEligibility(null)
    setChecked(false)
  }

  const renderEligibilityResult = () => {
    if (!eligibility) return null

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Alert
          message={eligibility.eligible ? 'Eligible for Smart Deals' : 'Not Eligible'}
          description={eligibility.message}
          type={eligibility.eligible ? 'success' : 'warning'}
          showIcon
          icon={eligibility.eligible ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        />

        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title="Current Price"
                value={eligibility.current_price}
                precision={2}
                suffix={eligibility.currency}
                prefix={<DollarOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Target Price"
                value={eligibility.target_price}
                precision={2}
                suffix={eligibility.currency}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: eligibility.eligible ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Discount Required"
                value={eligibility.discount_percentage}
                precision={2}
                suffix="%"
                prefix={<PercentageOutlined />}
                valueStyle={{ color: eligibility.eligible ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="Product ID">
            {eligibility.product_id}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {eligibility.eligible ? (
              <Tag color="success" icon={<CheckCircleOutlined />}>
                Eligible
              </Tag>
            ) : (
              <Tag color="warning" icon={<CloseCircleOutlined />}>
                Not Eligible
              </Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Price Reduction Needed" span={2}>
            <Text strong style={{ color: '#cf1322' }}>
              {eligibility.discount_required.toFixed(2)} {eligibility.currency}
            </Text>
          </Descriptions.Item>
        </Descriptions>

        {eligibility.recommendations && eligibility.recommendations.length > 0 && (
          <>
            <Title level={5}>Recommendations</Title>
            <Alert
              message="How to become eligible"
              description={
                <ul style={{ marginBottom: 0, paddingLeft: '20px' }}>
                  {eligibility.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              }
              type="info"
              showIcon
            />
          </>
        )}
      </Space>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined />
          <span>Smart Deals Eligibility Checker</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="reset" onClick={handleReset} disabled={loading}>
          Reset
        </Button>,
        <Button key="check" type="primary" onClick={handleCheck} loading={loading}>
          Check Eligibility
        </Button>,
        <Button key="close" onClick={onClose}>
          Close
        </Button>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Alert
          message="Smart Deals Program"
          description="Check if your product is eligible for eMAG's Smart Deals program. Smart Deals products get special visibility and promotion on the platform."
          type="info"
          showIcon
        />

        {productId && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Product ID">{productId}</Descriptions.Item>
            <Descriptions.Item label="Current Price">
              {currentPrice ? `${currentPrice.toFixed(2)} ${currency}` : 'N/A'}
            </Descriptions.Item>
          </Descriptions>
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" tip="Checking Smart Deals eligibility..." />
          </div>
        )}

        {!loading && checked && renderEligibilityResult()}
      </Space>
    </Modal>
  )
}

export default SmartDealsChecker
