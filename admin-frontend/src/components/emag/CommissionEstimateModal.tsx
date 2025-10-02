/**
 * Commission Estimate Modal Component
 * 
 * Displays commission estimates for eMAG products to help with pricing strategy.
 * Uses the Commission Estimate API (v4.4.9) to fetch real-time commission data.
 */

import React, { useState } from 'react'
import { Modal, Spin, Alert, Descriptions, Typography, Button, Space, Statistic, Row, Col, Tag } from 'antd'
import { DollarOutlined, PercentageOutlined, InfoCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../../services/api'

const { Paragraph } = Typography

interface CommissionEstimateModalProps {
  visible: boolean
  onClose: () => void
  productId?: string
  productName?: string
  currentPrice?: number
  accountType?: 'main' | 'fbe'
}

interface CommissionData {
  product_id: number
  commission_value: number | null
  commission_percentage: number | null
  created: string | null
  end_date: string | null
  error: string | null
}

const CommissionEstimateModal: React.FC<CommissionEstimateModalProps> = ({
  visible,
  onClose,
  productId,
  productName,
  currentPrice,
  accountType = 'main'
}) => {
  const [loading, setLoading] = useState(false)
  const [commissionData, setCommissionData] = useState<CommissionData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchCommissionEstimate = async () => {
    if (!productId) return

    setLoading(true)
    setError(null)

    try {
      const response = await api.get(`/emag/pricing-intelligence/commission/estimate/${productId}`, {
        params: { account_type: accountType }
      })

      if (response.data) {
        setCommissionData(response.data)
      }
    } catch (err: any) {
      console.error('Failed to fetch commission estimate:', err)
      setError(err.response?.data?.detail || 'Failed to fetch commission estimate')
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => {
    if (visible && productId) {
      fetchCommissionEstimate()
    }
  }, [visible, productId])

  const calculateNetRevenue = () => {
    if (!currentPrice || !commissionData?.commission_value) return null
    return currentPrice - commissionData.commission_value
  }

  const calculateMarginPercentage = () => {
    const netRevenue = calculateNetRevenue()
    if (!netRevenue || !currentPrice) return null
    return (netRevenue / currentPrice) * 100
  }

  const netRevenue = calculateNetRevenue()
  const marginPercentage = calculateMarginPercentage()

  return (
    <Modal
      title={
        <Space>
          <DollarOutlined />
          <span>Commission Estimate</span>
          {productName && <Tag color="blue">{productName}</Tag>}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={700}
      footer={[
        <Button key="refresh" icon={<ReloadOutlined />} onClick={fetchCommissionEstimate} loading={loading}>
          Refresh
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          Close
        </Button>
      ]}
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>
            Fetching commission estimate from eMAG API...
          </Paragraph>
        </div>
      )}

      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {!loading && commissionData && !commissionData.error && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Commission Statistics */}
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title="Commission Amount"
                value={commissionData.commission_value || 0}
                precision={2}
                suffix="RON"
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="Commission Rate"
                value={commissionData.commission_percentage || 0}
                precision={1}
                suffix="%"
                prefix={<PercentageOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
          </Row>

          {/* Net Revenue Calculation */}
          {currentPrice && netRevenue !== null && (
            <>
              <Alert
                message="Profit Margin Analysis"
                description={
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="Current Price"
                          value={currentPrice}
                          precision={2}
                          suffix="RON"
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Net Revenue"
                          value={netRevenue}
                          precision={2}
                          suffix="RON"
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Profit Margin"
                          value={marginPercentage || 0}
                          precision={1}
                          suffix="%"
                          valueStyle={{ color: marginPercentage && marginPercentage > 20 ? '#3f8600' : '#faad14' }}
                        />
                      </Col>
                    </Row>
                  </Space>
                }
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
              />
            </>
          )}

          {/* Commission Details */}
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Product ID">
              {commissionData.product_id}
            </Descriptions.Item>
            <Descriptions.Item label="Estimate Created">
              {commissionData.created ? new Date(commissionData.created).toLocaleString() : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Estimate Expiration">
              {commissionData.end_date ? new Date(commissionData.end_date).toLocaleString() : 'No expiration'}
            </Descriptions.Item>
            <Descriptions.Item label="Account Type">
              <Tag color={accountType === 'main' ? 'blue' : 'green'}>
                {accountType.toUpperCase()}
              </Tag>
            </Descriptions.Item>
          </Descriptions>

          {/* Important Notes */}
          <Alert
            message="Important Notes"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>This is an <strong>estimate</strong> for pricing guidance</li>
                <li>Actual commission at settlement may vary based on:
                  <ul>
                    <li>Current marketplace rules</li>
                    <li>Active promotional programs</li>
                    <li>Category-specific commission rates</li>
                    <li>Volume-based discounts</li>
                  </ul>
                </li>
                <li>Commission rates may change; refresh estimates periodically</li>
                <li>Use this data for pricing strategy and profit margin calculations</li>
              </ul>
            }
            type="warning"
            showIcon
          />
        </Space>
      )}

      {!loading && commissionData?.error && (
        <Alert
          message="Commission Estimate Error"
          description={commissionData.error}
          type="error"
          showIcon
        />
      )}
    </Modal>
  )
}

export default CommissionEstimateModal
