import { Row, Col, Card, Statistic, Progress, Tag, Space, Divider } from 'antd';
import {
  ShopOutlined,
  DollarOutlined,
  DatabaseOutlined,
  RiseOutlined,
  FallOutlined,
  SwapOutlined,
  WarningOutlined,
} from '@ant-design/icons';

interface AccountMetrics {
  totalProducts: number;
  activeProducts: number;
  totalValue: number;
  avgPrice: number;
  lastSync?: string;
}

interface OverlapMetrics {
  sharedProducts: number;
  priceDifferences: number;
  stockDifferences: number;
  conflicts: number;
}

interface AccountComparisonProps {
  mainMetrics: AccountMetrics;
  fbeMetrics: AccountMetrics;
  overlapMetrics?: OverlapMetrics;
}

const AccountComparison: React.FC<AccountComparisonProps> = ({
  mainMetrics,
  fbeMetrics,
  overlapMetrics,
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'RON',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const calculateDifference = (main: number, fbe: number) => {
    if (main === 0) return 0;
    return ((fbe - main) / main) * 100;
  };

  const productDiff = calculateDifference(mainMetrics.totalProducts, fbeMetrics.totalProducts);
  const valueDiff = calculateDifference(mainMetrics.totalValue, fbeMetrics.totalValue);

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* MAIN Account Card */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ShopOutlined style={{ color: '#1890ff' }} />
                <span>Cont MAIN</span>
              </Space>
            }
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #e6f7ff 0%, #ffffff 100%)',
              borderLeft: '4px solid #1890ff',
            }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Total Produse"
                  value={mainMetrics.totalProducts}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Active"
                  value={mainMetrics.activeProducts}
                  suffix={`/ ${mainMetrics.totalProducts}`}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Valoare Totală"
                  value={mainMetrics.totalValue}
                  prefix={<DollarOutlined />}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ color: '#1890ff', fontSize: '20px' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Preț Mediu"
                  value={mainMetrics.avgPrice}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ fontSize: '18px' }}
                />
              </Col>
            </Row>
            
            {mainMetrics.lastSync && (
              <>
                <Divider />
                <Tag color="blue">Ultima sincronizare: {mainMetrics.lastSync}</Tag>
              </>
            )}
          </Card>
        </Col>

        {/* FBE Account Card */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ShopOutlined style={{ color: '#722ed1' }} />
                <span>Cont FBE</span>
              </Space>
            }
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #f9f0ff 0%, #ffffff 100%)',
              borderLeft: '4px solid #722ed1',
            }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Total Produse"
                  value={fbeMetrics.totalProducts}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Active"
                  value={fbeMetrics.activeProducts}
                  suffix={`/ ${fbeMetrics.totalProducts}`}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Valoare Totală"
                  value={fbeMetrics.totalValue}
                  prefix={<DollarOutlined />}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ color: '#722ed1', fontSize: '20px' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Preț Mediu"
                  value={fbeMetrics.avgPrice}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ fontSize: '18px' }}
                />
              </Col>
            </Row>
            
            {fbeMetrics.lastSync && (
              <>
                <Divider />
                <Tag color="purple">Ultima sincronizare: {fbeMetrics.lastSync}</Tag>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* Comparison Card */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={
              <Space>
                <SwapOutlined />
                <span>Comparație Conturi</span>
              </Space>
            }
            bordered={false}
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Diferență Produse"
                  value={Math.abs(productDiff)}
                  precision={1}
                  suffix="%"
                  prefix={productDiff >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  valueStyle={{ color: productDiff >= 0 ? '#3f8600' : '#cf1322' }}
                />
                <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                  FBE {productDiff >= 0 ? 'are mai multe' : 'are mai puține'} produse
                </div>
              </Col>
              
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Diferență Valoare"
                  value={Math.abs(valueDiff)}
                  precision={1}
                  suffix="%"
                  prefix={valueDiff >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  valueStyle={{ color: valueDiff >= 0 ? '#3f8600' : '#cf1322' }}
                />
                <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                  FBE {valueDiff >= 0 ? 'are valoare mai mare' : 'are valoare mai mică'}
                </div>
              </Col>

              {overlapMetrics && (
                <>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic
                      title="Produse Comune"
                      value={overlapMetrics.sharedProducts}
                      prefix={<DatabaseOutlined />}
                      valueStyle={{ color: '#1890ff' }}
                    />
                    <Progress 
                      percent={Math.round((overlapMetrics.sharedProducts / mainMetrics.totalProducts) * 100)} 
                      size="small"
                      showInfo={false}
                    />
                  </Col>
                  
                  <Col xs={24} sm={12} md={6}>
                    <Statistic
                      title="Conflicte"
                      value={overlapMetrics.conflicts}
                      prefix={<WarningOutlined />}
                      valueStyle={{ color: overlapMetrics.conflicts > 0 ? '#ff4d4f' : '#52c41a' }}
                    />
                    <div style={{ marginTop: 8 }}>
                      {overlapMetrics.conflicts > 0 ? (
                        <Tag color="error">Necesită atenție</Tag>
                      ) : (
                        <Tag color="success">Totul OK</Tag>
                      )}
                    </div>
                  </Col>
                </>
              )}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AccountComparison;
