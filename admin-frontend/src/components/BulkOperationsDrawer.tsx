/**
 * Bulk Operations Drawer Component
 * 
 * Perform bulk operations on multiple products:
 * - Bulk price updates
 * - Bulk stock updates
 * - Bulk measurements
 * - Bulk status changes
 */

import { useState } from 'react';
import {
  Drawer,
  Tabs,
  Form,
  InputNumber,
  Button,
  Space,
  message,
  Alert,
  Typography,
  Badge,
  Card,
  Progress,
  List,
  Tag,
  Divider,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  ThunderboltOutlined,
  DollarOutlined,
  InboxOutlined,
  ColumnHeightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PercentageOutlined,
} from '@ant-design/icons';
import { batchUpdateOffersLight, batchSaveMeasurements } from '../services/emagAdvancedApi';

const { Text } = Typography;
const { TabPane } = Tabs;

interface Product {
  id: number;
  name: string;
  account_type?: string;
  sale_price?: number;
  stock?: number;
}

interface BulkOperationsDrawerProps {
  visible: boolean;
  onClose: () => void;
  selectedProducts: Product[];
  onSuccess?: () => void;
}

interface BulkResult {
  product_id: number;
  product_name: string;
  success: boolean;
  error?: string;
}

const BulkOperationsDrawer: React.FC<BulkOperationsDrawerProps> = ({
  visible,
  onClose,
  selectedProducts,
  onSuccess,
}) => {
  const [priceForm] = Form.useForm();
  const [stockForm] = Form.useForm();
  const [measurementsForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BulkResult[]>([]);
  const [progress, setProgress] = useState(0);

  const emagProducts = selectedProducts.filter(p => 
    p.account_type && ['main', 'fbe'].includes(p.account_type)
  );

  const handleBulkPriceUpdate = async () => {
    try {
      const values = await priceForm.validateFields();
      
      if (emagProducts.length === 0) {
        message.warning('Niciun produs eMAG selectat');
        return;
      }

      setLoading(true);
      setResults([]);
      setProgress(0);

      const updates = emagProducts.map(product => ({
        product_id: product.id,
        account_type: product.account_type as 'main' | 'fbe',
        ...(values.sale_price !== undefined && { sale_price: values.sale_price }),
        ...(values.price_adjustment && {
          sale_price: product.sale_price 
            ? product.sale_price * (1 + values.price_adjustment / 100)
            : undefined
        }),
      }));

      const batchResults = await batchUpdateOffersLight(updates);
      
      const formattedResults: BulkResult[] = batchResults.map((result, index) => ({
        product_id: emagProducts[index].id,
        product_name: emagProducts[index].name,
        success: result.success,
        error: result.error?.message || result.error,
      }));

      setResults(formattedResults);
      setProgress(100);

      const successCount = formattedResults.filter(r => r.success).length;
      message.success(`${successCount}/${emagProducts.length} produse actualizate cu succes!`);
      
      if (successCount > 0) {
        onSuccess?.();
      }
    } catch (error: any) {
      console.error('Bulk price update error:', error);
      message.error('Eroare la actualizarea în masă a prețurilor');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkStockUpdate = async () => {
    try {
      const values = await stockForm.validateFields();
      
      if (emagProducts.length === 0) {
        message.warning('Niciun produs eMAG selectat');
        return;
      }

      setLoading(true);
      setResults([]);
      setProgress(0);

      const updates = emagProducts.map(product => ({
        product_id: product.id,
        account_type: product.account_type as 'main' | 'fbe',
        ...(values.stock_value !== undefined && { 
          stock_value: values.stock_value,
          warehouse_id: values.warehouse_id || 1,
        }),
        ...(values.stock_adjustment && {
          stock_value: (product.stock || 0) + values.stock_adjustment,
          warehouse_id: values.warehouse_id || 1,
        }),
      }));

      const batchResults = await batchUpdateOffersLight(updates);
      
      const formattedResults: BulkResult[] = batchResults.map((result, index) => ({
        product_id: emagProducts[index].id,
        product_name: emagProducts[index].name,
        success: result.success,
        error: result.error?.message || result.error,
      }));

      setResults(formattedResults);
      setProgress(100);

      const successCount = formattedResults.filter(r => r.success).length;
      message.success(`${successCount}/${emagProducts.length} produse actualizate cu succes!`);
      
      if (successCount > 0) {
        onSuccess?.();
      }
    } catch (error: any) {
      console.error('Bulk stock update error:', error);
      message.error('Eroare la actualizarea în masă a stocului');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkMeasurements = async () => {
    try {
      const values = await measurementsForm.validateFields();
      
      if (emagProducts.length === 0) {
        message.warning('Niciun produs eMAG selectat');
        return;
      }

      setLoading(true);
      setResults([]);
      setProgress(0);

      const measurements = emagProducts.map(product => ({
        product_id: product.id,
        account_type: product.account_type as 'main' | 'fbe',
        length: values.length,
        width: values.width,
        height: values.height,
        weight: values.weight,
      }));

      const batchResults = await batchSaveMeasurements(measurements);
      
      const formattedResults: BulkResult[] = batchResults.map((result, index) => ({
        product_id: emagProducts[index].id,
        product_name: emagProducts[index].name,
        success: result.success,
        error: result.error?.message || result.error,
      }));

      setResults(formattedResults);
      setProgress(100);

      const successCount = formattedResults.filter(r => r.success).length;
      message.success(`${successCount}/${emagProducts.length} măsurători salvate cu succes!`);
      
      if (successCount > 0) {
        onSuccess?.();
      }
    } catch (error: any) {
      console.error('Bulk measurements error:', error);
      message.error('Eroare la salvarea în masă a măsurătorilor');
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (results.length === 0) return null;

    const successCount = results.filter(r => r.success).length;
    const failCount = results.length - successCount;

    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title="Succes"
                value={successCount}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="Erori"
                value={failCount}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          </Row>

          <Progress percent={progress} status={loading ? 'active' : 'success'} />

          <List
            size="small"
            dataSource={results}
            renderItem={(result) => (
              <List.Item>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text ellipsis style={{ maxWidth: 300 }}>
                    {result.product_name}
                  </Text>
                  {result.success ? (
                    <Tag color="success" icon={<CheckCircleOutlined />}>Succes</Tag>
                  ) : (
                    <Tag color="error" icon={<CloseCircleOutlined />}>
                      {result.error || 'Eroare'}
                    </Tag>
                  )}
                </Space>
              </List.Item>
            )}
            style={{ maxHeight: 200, overflowY: 'auto' }}
          />
        </Space>
      </Card>
    );
  };

  return (
    <Drawer
      title={
        <Space>
          <ThunderboltOutlined style={{ fontSize: 20, color: '#52c41a' }} />
          <span>Operații în Masă</span>
          <Badge count="v4.4.9" style={{ backgroundColor: '#52c41a' }} />
        </Space>
      }
      placement="right"
      width={600}
      open={visible}
      onClose={onClose}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          message={`${selectedProducts.length} produse selectate (${emagProducts.length} eMAG)`}
          description="Operațiile în masă se aplică doar produselor eMAG (MAIN/FBE)"
          type="info"
          showIcon
        />

        <Tabs defaultActiveKey="price">
          <TabPane
            tab={
              <Space>
                <DollarOutlined />
                Prețuri
              </Space>
            }
            key="price"
          >
            <Form form={priceForm} layout="vertical" disabled={loading}>
              <Alert
                message="Actualizare prețuri în masă"
                description="Setează un preț fix sau ajustează prețurile cu un procent"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                label="Preț Fix (RON)"
                name="sale_price"
                tooltip="Setează același preț pentru toate produsele"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 99.99"
                  precision={2}
                  addonAfter="RON"
                />
              </Form.Item>

              <Divider>SAU</Divider>

              <Form.Item
                label="Ajustare Preț (%)"
                name="price_adjustment"
                tooltip="Crește sau scade prețurile cu un procent"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 10 (pentru +10%) sau -5 (pentru -5%)"
                  precision={2}
                  addonAfter="%"
                  addonBefore={<PercentageOutlined />}
                />
              </Form.Item>

              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleBulkPriceUpdate}
                loading={loading}
                block
                size="large"
              >
                Actualizează Prețuri ({emagProducts.length} produse)
              </Button>

              {renderResults()}
            </Form>
          </TabPane>

          <TabPane
            tab={
              <Space>
                <InboxOutlined />
                Stoc
              </Space>
            }
            key="stock"
          >
            <Form form={stockForm} layout="vertical" disabled={loading}>
              <Alert
                message="Actualizare stoc în masă"
                description="Setează un stoc fix sau ajustează stocurile"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                label="Stoc Fix"
                name="stock_value"
                tooltip="Setează același stoc pentru toate produsele"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 50"
                  addonAfter="buc"
                />
              </Form.Item>

              <Divider>SAU</Divider>

              <Form.Item
                label="Ajustare Stoc"
                name="stock_adjustment"
                tooltip="Adaugă sau scade din stocul curent"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Ex: 10 (pentru +10) sau -5 (pentru -5)"
                  addonAfter="buc"
                />
              </Form.Item>

              <Form.Item
                label="Depozit ID"
                name="warehouse_id"
                initialValue={1}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                />
              </Form.Item>

              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleBulkStockUpdate}
                loading={loading}
                block
                size="large"
              >
                Actualizează Stoc ({emagProducts.length} produse)
              </Button>

              {renderResults()}
            </Form>
          </TabPane>

          <TabPane
            tab={
              <Space>
                <ColumnHeightOutlined />
                Măsurători
              </Space>
            }
            key="measurements"
          >
            <Form form={measurementsForm} layout="vertical" disabled={loading}>
              <Alert
                message="Măsurători în masă"
                description="Setează aceleași dimensiuni și greutate pentru toate produsele"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="Lungime (mm)"
                    name="length"
                    rules={[{ required: true, message: 'Obligatoriu' }]}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      placeholder="200"
                      precision={2}
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Lățime (mm)"
                    name="width"
                    rules={[{ required: true, message: 'Obligatoriu' }]}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      placeholder="150"
                      precision={2}
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Înălțime (mm)"
                    name="height"
                    rules={[{ required: true, message: 'Obligatoriu' }]}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      placeholder="80"
                      precision={2}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="Greutate (g)"
                name="weight"
                rules={[{ required: true, message: 'Obligatoriu' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="450"
                  precision={2}
                  addonAfter="g"
                />
              </Form.Item>

              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleBulkMeasurements}
                loading={loading}
                block
                size="large"
              >
                Salvează Măsurători ({emagProducts.length} produse)
              </Button>

              {renderResults()}
            </Form>
          </TabPane>
        </Tabs>
      </Space>
    </Drawer>
  );
};

export default BulkOperationsDrawer;
