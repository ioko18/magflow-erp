/**
 * Campaign Proposal Modal Component
 * 
 * Allows proposing products to eMAG campaigns with full support for:
 * - Standard campaigns
 * - Stock-in-site campaigns
 * - MultiDeals campaigns with date intervals
 */

import React, { useState } from 'react'
import {
  Modal,
  Form,
  InputNumber,
  Switch,
  Button,
  Space,
  Alert,
  Divider,
  Typography,
  Row,
  Col,
  DatePicker,
  Card,
  Tag
} from 'antd'
import {
  RocketOutlined,
  PlusOutlined,
  DeleteOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import api from '../../services/api'
import dayjs from 'dayjs'

const { Text } = Typography
const { RangePicker } = DatePicker

interface CampaignProposalModalProps {
  visible: boolean
  onClose: () => void
  onSuccess?: () => void
  productId?: string
  productName?: string
  currentPrice?: number
  accountType?: 'main' | 'fbe'
}

interface DateInterval {
  start_date: {
    date: string
    timezone_type: number
    timezone: string
  }
  end_date: {
    date: string
    timezone_type: number
    timezone: string
  }
  voucher_discount: number
  index: number
}

const CampaignProposalModal: React.FC<CampaignProposalModalProps> = ({
  visible,
  onClose,
  onSuccess,
  productId,
  productName,
  currentPrice,
  accountType = 'main'
}) => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [isMultiDeals, setIsMultiDeals] = useState(false)
  const [dateIntervals, setDateIntervals] = useState<DateInterval[]>([])

  const handleSubmit = async (values: any) => {
    if (!productId) return

    setLoading(true)

    try {
      const payload: any = {
        campaign_id: values.campaign_id,
        sale_price: values.sale_price,
        stock: values.stock,
        max_qty_per_order: values.max_qty_per_order,
        voucher_discount: values.voucher_discount,
        post_campaign_sale_price: values.post_campaign_sale_price,
        not_available_post_campaign: values.not_available_post_campaign || false
      }

      if (isMultiDeals && dateIntervals.length > 0) {
        payload.date_intervals = dateIntervals
      }

      await api.post(
        `/emag/v449/products/${productId}/campaign-proposal`,
        payload,
        { params: { account_type: accountType } }
      )

      Modal.success({
        title: 'Campaign Proposal Submitted',
        content: `Product successfully proposed to campaign ${values.campaign_id}`,
      })

      form.resetFields()
      setDateIntervals([])
      setIsMultiDeals(false)
      onSuccess?.()
      onClose()
    } catch (error: any) {
      Modal.error({
        title: 'Campaign Proposal Failed',
        content: error.response?.data?.detail || 'Failed to submit campaign proposal',
      })
    } finally {
      setLoading(false)
    }
  }

  const addDateInterval = () => {
    const newInterval: DateInterval = {
      start_date: {
        date: dayjs().format('YYYY-MM-DD 00:00:00.000000'),
        timezone_type: 3,
        timezone: 'Europe/Bucharest'
      },
      end_date: {
        date: dayjs().add(1, 'day').format('YYYY-MM-DD 23:59:59.000000'),
        timezone_type: 3,
        timezone: 'Europe/Bucharest'
      },
      voucher_discount: 10,
      index: dateIntervals.length + 1
    }
    setDateIntervals([...dateIntervals, newInterval])
  }

  const removeDateInterval = (index: number) => {
    const updated = dateIntervals.filter((_, i) => i !== index)
    // Re-index
    updated.forEach((interval, i) => {
      interval.index = i + 1
    })
    setDateIntervals(updated)
  }

  const updateDateInterval = (index: number, field: string, value: any) => {
    const updated = [...dateIntervals]
    if (field === 'dates') {
      updated[index].start_date.date = value[0].format('YYYY-MM-DD 00:00:00.000000')
      updated[index].end_date.date = value[1].format('YYYY-MM-DD 23:59:59.000000')
    } else if (field === 'voucher_discount') {
      updated[index].voucher_discount = value
    }
    setDateIntervals(updated)
  }

  return (
    <Modal
      title={
        <Space>
          <RocketOutlined />
          <span>Propose to Campaign</span>
          {productName && <Tag color="blue">{productName}</Tag>}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <Alert
        message="Campaign Types"
        description={
          <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
            <li><strong>Standard</strong>: Basic campaign with sale price and stock</li>
            <li><strong>Stock-in-site</strong>: Requires max quantity per order</li>
            <li><strong>MultiDeals</strong>: Multiple discount intervals (max 30)</li>
          </ul>
        }
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 16 }}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          sale_price: currentPrice,
          stock: 10,
          max_qty_per_order: 1,
          voucher_discount: 10,
          not_available_post_campaign: false
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Campaign ID"
              name="campaign_id"
              rules={[{ required: true, message: 'Please enter campaign ID' }]}
              tooltip="eMAG internal campaign ID"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={1}
                placeholder="e.g., 344"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Campaign Price (no VAT)"
              name="sale_price"
              rules={[{ required: true, message: 'Please enter sale price' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0.01}
                step={0.01}
                precision={2}
                suffix="RON"
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Reserved Stock"
              name="stock"
              rules={[{ required: true, message: 'Please enter stock' }]}
              tooltip="Stock reserved for campaign (separate from regular stock)"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={1}
                max={255}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Max Qty per Order"
              name="max_qty_per_order"
              tooltip="Required for Stock-in-site campaigns"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={1}
                max={100}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Voucher Discount (%)"
              name="voucher_discount"
              tooltip="Discount percentage (10-100%)"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={10}
                max={100}
                suffix="%"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Post-Campaign Price"
              name="post_campaign_sale_price"
              tooltip="Price after campaign ends (defaults to current price)"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0.01}
                step={0.01}
                precision={2}
                suffix="RON"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label="Deactivate After Campaign"
          name="not_available_post_campaign"
          valuePropName="checked"
          tooltip="If enabled, offer becomes inactive after campaign ends"
        >
          <Switch />
        </Form.Item>

        <Divider />

        <Form.Item label="MultiDeals Campaign">
          <Space>
            <Switch
              checked={isMultiDeals}
              onChange={setIsMultiDeals}
              checkedChildren="Enabled"
              unCheckedChildren="Disabled"
            />
            <Text type="secondary">Enable for campaigns with multiple discount intervals</Text>
          </Space>
        </Form.Item>

        {isMultiDeals && (
          <Card
            title="Date Intervals"
            size="small"
            extra={
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={addDateInterval}
                disabled={dateIntervals.length >= 30}
              >
                Add Interval
              </Button>
            }
          >
            {dateIntervals.length === 0 ? (
              <Alert
                message="No intervals added"
                description="Click 'Add Interval' to create discount periods"
                type="info"
                showIcon
              />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {dateIntervals.map((interval, index) => (
                  <Card key={index} size="small" type="inner">
                    <Row gutter={16} align="middle">
                      <Col span={2}>
                        <Tag color="blue">#{interval.index}</Tag>
                      </Col>
                      <Col span={12}>
                        <RangePicker
                          showTime
                          format="YYYY-MM-DD HH:mm"
                          defaultValue={[
                            dayjs(interval.start_date.date, 'YYYY-MM-DD HH:mm:ss.SSSSSS'),
                            dayjs(interval.end_date.date, 'YYYY-MM-DD HH:mm:ss.SSSSSS')
                          ]}
                          onChange={(dates) => updateDateInterval(index, 'dates', dates)}
                        />
                      </Col>
                      <Col span={6}>
                        <InputNumber
                          min={10}
                          max={100}
                          value={interval.voucher_discount}
                          onChange={(value) => updateDateInterval(index, 'voucher_discount', value)}
                          suffix="%"
                          style={{ width: '100%' }}
                        />
                      </Col>
                      <Col span={4}>
                        <Button
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={() => removeDateInterval(index)}
                        >
                          Remove
                        </Button>
                      </Col>
                    </Row>
                  </Card>
                ))}
              </Space>
            )}
          </Card>
        )}

        <Divider />

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />}>
              Submit Proposal
            </Button>
            <Button onClick={onClose}>
              Cancel
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default CampaignProposalModal
