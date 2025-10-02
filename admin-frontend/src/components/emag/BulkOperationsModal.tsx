/**
 * Bulk Operations Modal Component
 * 
 * Allows bulk operations on multiple products (max 50 per API limits).
 * Supports: price updates, stock updates, status changes.
 */

import React, { useState } from 'react'
import {
  Modal,
  Form,
  Select,
  InputNumber,
  Button,
  Space,
  Alert,
  Table,
  Progress,
  Tag,
  Divider,
  Statistic,
  Row,
  Col,
  message
} from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  WarningOutlined
} from '@ant-design/icons'
import api from '../../services/api'

const { Option } = Select

interface BulkOperationsModalProps {
  visible: boolean
  onClose: () => void
  onSuccess?: () => void
  selectedProducts: any[]
  accountType?: 'main' | 'fbe'
}

type OperationType = 'price' | 'stock' | 'status'

interface BulkOperationResult {
  product_id: string
  sku: string
  status: 'success' | 'error' | 'pending'
  message?: string
}

const BulkOperationsModal: React.FC<BulkOperationsModalProps> = ({
  visible,
  onClose,
  onSuccess,
  selectedProducts,
  accountType = 'main'
}) => {
  const [form] = Form.useForm()
  const [operationType, setOperationType] = useState<OperationType>('price')
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState<BulkOperationResult[]>([])
  const [progress, setProgress] = useState(0)

  const maxProducts = 50 // API limit

  const handleSubmit = async (values: any) => {
    if (selectedProducts.length === 0) {
      message.warning('No products selected')
      return
    }

    if (selectedProducts.length > maxProducts) {
      message.error(`Maximum ${maxProducts} products allowed per bulk operation`)
      return
    }

    setProcessing(true)
    setProgress(0)
    
    const operationResults: BulkOperationResult[] = selectedProducts.map(p => ({
      product_id: p.id || p.emag_id,
      sku: p.sku,
      status: 'pending'
    }))
    setResults(operationResults)

    try {
      // Process in batches of 10 for better performance
      const batchSize = 10
      let completed = 0

      for (let i = 0; i < selectedProducts.length; i += batchSize) {
        const batch = selectedProducts.slice(i, i + batchSize)
        
        // Process batch in parallel
        const batchPromises = batch.map(async (product, index) => {
          const globalIndex = i + index
          try {
            let endpoint = ''
            let payload: any = {}

            switch (operationType) {
              case 'price':
                endpoint = `/emag/v449/products/${product.emag_id}/offer-quick-update`
                payload = { sale_price: values.price }
                break
              
              case 'stock':
                endpoint = `/emag/v449/products/${product.emag_id}/stock-only`
                payload = { stock_value: values.stock, warehouse_id: 1 }
                break
              
              case 'status':
                endpoint = `/emag/v449/products/${product.emag_id}/offer-quick-update`
                payload = { status: values.status }
                break
            }

            const method = operationType === 'stock' ? 'patch' : 'patch'
            await api[method](endpoint, payload, {
              params: { account_type: accountType }
            })

            operationResults[globalIndex] = {
              ...operationResults[globalIndex],
              status: 'success',
              message: 'Updated successfully'
            }
          } catch (error: any) {
            operationResults[globalIndex] = {
              ...operationResults[globalIndex],
              status: 'error',
              message: error.response?.data?.detail || 'Update failed'
            }
          }

          completed++
          setProgress(Math.round((completed / selectedProducts.length) * 100))
          setResults([...operationResults])
        })

        await Promise.all(batchPromises)
        
        // Small delay between batches to respect rate limits
        if (i + batchSize < selectedProducts.length) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      }

      const successCount = operationResults.filter(r => r.status === 'success').length
      const errorCount = operationResults.filter(r => r.status === 'error').length

      if (successCount > 0) {
        message.success(`Successfully updated ${successCount} products`)
      }
      if (errorCount > 0) {
        message.error(`Failed to update ${errorCount} products`)
      }

      onSuccess?.()
    } catch (error: any) {
      message.error('Bulk operation failed: ' + (error.message || 'Unknown error'))
    } finally {
      setProcessing(false)
    }
  }

  const handleClose = () => {
    if (!processing) {
      form.resetFields()
      setResults([])
      setProgress(0)
      onClose()
    }
  }

  const successCount = results.filter(r => r.status === 'success').length
  const errorCount = results.filter(r => r.status === 'error').length
  const pendingCount = results.filter(r => r.status === 'pending').length

  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 150
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const config = {
          success: { color: 'success', icon: <CheckCircleOutlined /> },
          error: { color: 'error', icon: <CloseCircleOutlined /> },
          pending: { color: 'processing', icon: <SyncOutlined spin /> }
        }
        const { color, icon } = config[status as keyof typeof config]
        return <Tag color={color} icon={icon}>{status.toUpperCase()}</Tag>
      }
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      render: (text: string) => text || '-'
    }
  ]

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined />
          <span>Bulk Operations</span>
          <Tag color={accountType === 'main' ? 'blue' : 'green'}>
            {accountType.toUpperCase()}
          </Tag>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={900}
      footer={null}
      maskClosable={!processing}
      closable={!processing}
    >
      {selectedProducts.length > maxProducts && (
        <Alert
          message="Too Many Products Selected"
          description={`You have selected ${selectedProducts.length} products. Maximum ${maxProducts} products allowed per bulk operation. Please reduce your selection.`}
          type="error"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {selectedProducts.length > 0 && selectedProducts.length <= maxProducts && (
        <>
          <Alert
            message="Bulk Operation Limits"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>Maximum <strong>50 products</strong> per operation (API limit)</li>
                <li>Operations are processed in batches of 10</li>
                <li>Rate limiting: ~3 requests/second</li>
                <li>Selected: <strong>{selectedProducts.length} products</strong></li>
              </ul>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            disabled={processing}
          >
            <Form.Item
              label="Operation Type"
              name="operation_type"
              initialValue="price"
            >
              <Select onChange={(value) => setOperationType(value as OperationType)}>
                <Option value="price">Update Price</Option>
                <Option value="stock">Update Stock</Option>
                <Option value="status">Change Status</Option>
              </Select>
            </Form.Item>

            {operationType === 'price' && (
              <Form.Item
                label="New Price (without VAT)"
                name="price"
                rules={[{ required: true, message: 'Please enter price' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.01}
                  step={0.01}
                  precision={2}
                  suffix="RON"
                  placeholder="Enter new price for all selected products"
                />
              </Form.Item>
            )}

            {operationType === 'stock' && (
              <Form.Item
                label="New Stock Quantity"
                name="stock"
                rules={[{ required: true, message: 'Please enter stock quantity' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  placeholder="Enter new stock for all selected products"
                />
              </Form.Item>
            )}

            {operationType === 'status' && (
              <Form.Item
                label="New Status"
                name="status"
                rules={[{ required: true, message: 'Please select status' }]}
              >
                <Select placeholder="Select new status">
                  <Option value={1}>Active</Option>
                  <Option value={0}>Inactive</Option>
                  <Option value={2}>End of Life</Option>
                </Select>
              </Form.Item>
            )}

            <Divider />

            {processing && (
              <>
                <Progress percent={progress} status="active" />
                <Row gutter={16} style={{ marginTop: 16, marginBottom: 16 }}>
                  <Col span={8}>
                    <Statistic
                      title="Success"
                      value={successCount}
                      valueStyle={{ color: '#3f8600' }}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Errors"
                      value={errorCount}
                      valueStyle={{ color: '#cf1322' }}
                      prefix={<CloseCircleOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Pending"
                      value={pendingCount}
                      valueStyle={{ color: '#1890ff' }}
                      prefix={<SyncOutlined spin />}
                    />
                  </Col>
                </Row>
              </>
            )}

            {results.length > 0 && (
              <Table
                dataSource={results}
                columns={columns}
                rowKey="product_id"
                pagination={{ pageSize: 10 }}
                size="small"
                style={{ marginTop: 16 }}
              />
            )}

            <Form.Item style={{ marginTop: 16, marginBottom: 0 }}>
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={processing}
                  disabled={selectedProducts.length === 0 || selectedProducts.length > maxProducts}
                  icon={<ThunderboltOutlined />}
                >
                  {processing ? 'Processing...' : 'Execute Bulk Operation'}
                </Button>
                <Button onClick={handleClose} disabled={processing}>
                  {processing ? 'Please wait...' : 'Cancel'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </>
      )}
    </Modal>
  )
}

export default BulkOperationsModal
