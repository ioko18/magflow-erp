/**
 * EAN Search Modal Component
 * 
 * Provides interface for searching products by EAN codes using eMAG API v4.4.9
 * Displays matched products with offer information and quick actions
 */

import { useState } from 'react';
import {
  Modal,
  Input,
  Button,
  Space,
  Tag,
  Card,
  List,
  Typography,
  message,
  Spin,
  Empty,
  Alert,
  Row,
  Col,
  Statistic,
  Image,
  Tooltip,
  Badge,
  Divider,
  Select,
} from 'antd';
import {
  SearchOutlined,
  BarcodeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FireOutlined,
  LinkOutlined,
  ShopOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { findProductsByEANs, EANSearchResult } from '../../services/emag/emagAdvancedApi';

const { TextArea } = Input;
const { Text } = Typography;

interface EANSearchModalProps {
  visible: boolean;
  onClose: () => void;
  onProductSelect?: (product: EANSearchResult) => void;
}

const EANSearchModal: React.FC<EANSearchModalProps> = ({
  visible,
  onClose,
  onProductSelect,
}) => {
  const [eanInput, setEanInput] = useState('');
  const [accountType, setAccountType] = useState<'main' | 'fbe'>('main');
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<Record<string, { products: EANSearchResult[] }> | null>(null);
  const [searchStats, setSearchStats] = useState<{ total: number; searched: number } | null>(null);

  const handleSearch = async () => {
    // Parse EAN codes from input (comma, space, or newline separated)
    const eans = eanInput
      .split(/[\s,\n]+/)
      .map(ean => ean.trim())
      .filter(ean => ean.length > 0);

    if (eans.length === 0) {
      message.warning('Introduceți cel puțin un cod EAN');
      return;
    }

    if (eans.length > 100) {
      message.warning('Maxim 100 coduri EAN per căutare');
      return;
    }

    setLoading(true);
    try {
      const response = await findProductsByEANs({ eans, account_type: accountType });
      setSearchResults(response.data.products);
      setSearchStats({
        total: response.data.total,
        searched: response.data.searched_eans,
      });
      
      if (response.data.total === 0) {
        message.info('Nu s-au găsit produse pentru codurile EAN introduse');
      } else {
        message.success(`Găsite ${response.data.total} produse din ${response.data.searched_eans} EAN-uri`);
      }
    } catch (error: any) {
      console.error('EAN search error:', error);
      message.error(error.response?.data?.detail || 'Eroare la căutarea produselor');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setEanInput('');
    setSearchResults(null);
    setSearchStats(null);
  };

  const getHotnessColor = (hotness: string) => {
    const lower = hotness.toLowerCase();
    if (lower.includes('hot')) return 'red';
    if (lower.includes('warm')) return 'orange';
    if (lower.includes('cold')) return 'blue';
    return 'default';
  };

  const getHotnessIcon = (hotness: string) => {
    const lower = hotness.toLowerCase();
    if (lower.includes('hot')) return <FireOutlined />;
    if (lower.includes('warm')) return <ThunderboltOutlined />;
    return null;
  };

  const renderProductCard = (ean: string, products: EANSearchResult[]) => {
    if (products.length === 0) return null;

    return products.map((product, index) => (
      <Card
        key={`${ean}-${index}`}
        size="small"
        style={{ marginBottom: 12 }}
        hoverable
        onClick={() => onProductSelect && onProductSelect(product)}
      >
        <Row gutter={16} align="middle">
          {product.product_image && (
            <Col flex="100px">
              <Image
                src={product.product_image}
                alt={product.product_name}
                width={80}
                height={80}
                style={{ objectFit: 'contain' }}
                fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
              />
            </Col>
          )}
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div>
                <Text strong style={{ fontSize: 14 }}>
                  {product.product_name}
                </Text>
              </div>
              
              <Space size={[8, 8]} wrap>
                <Tag color="blue" icon={<BarcodeOutlined />}>
                  {ean}
                </Tag>
                <Tag color="purple">
                  {product.brand_name}
                </Tag>
                <Tag color="cyan">
                  {product.category_name}
                </Tag>
                <Tag color={getHotnessColor(product.hotness)} icon={getHotnessIcon(product.hotness)}>
                  {product.hotness}
                </Tag>
              </Space>

              <Space size={[8, 8]} wrap>
                {product.allowed_to_add_offer ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    Poți adăuga ofertă
                  </Tag>
                ) : (
                  <Tag color="error" icon={<CloseCircleOutlined />}>
                    Nu poți adăuga ofertă
                  </Tag>
                )}
                
                {product.vendor_has_offer ? (
                  <Tag color="warning" icon={<ShopOutlined />}>
                    Ai deja ofertă
                  </Tag>
                ) : (
                  <Tag color="default">
                    Fără ofertă
                  </Tag>
                )}
              </Space>

              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Part Number Key: <Text code>{product.part_number_key}</Text>
                </Text>
                {product.site_url && (
                  <Tooltip title="Vezi pe eMAG">
                    <Button
                      type="link"
                      size="small"
                      icon={<LinkOutlined />}
                      href={product.site_url}
                      target="_blank"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Vezi produs
                    </Button>
                  </Tooltip>
                )}
              </Space>
            </Space>
          </Col>
        </Row>
      </Card>
    ));
  };

  return (
    <Modal
      title={
        <Space>
          <BarcodeOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <span>Căutare Produse după EAN</span>
          <Badge count="v4.4.9" style={{ backgroundColor: '#52c41a' }} />
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="reset" onClick={handleReset} disabled={loading}>
          Resetează
        </Button>,
        <Button key="close" onClick={onClose}>
          Închide
        </Button>,
        <Button
          key="search"
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={loading}
        >
          Caută
        </Button>,
      ]}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          message="Căutare rapidă produse eMAG"
          description="Introduceți coduri EAN (până la 100) separate prin virgulă, spațiu sau linie nouă. Sistemul va căuta produsele în catalogul eMAG și va afișa informații despre posibilitatea de a adăuga oferte."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Space>
            <Text strong>Cont eMAG:</Text>
            <Select
              value={accountType}
              onChange={setAccountType}
              style={{ width: 120 }}
              disabled={loading}
            >
              <Select.Option value="main">MAIN</Select.Option>
              <Select.Option value="fbe">FBE</Select.Option>
            </Select>
          </Space>

          <TextArea
            value={eanInput}
            onChange={(e) => setEanInput(e.target.value)}
            placeholder="Exemplu:&#10;5904862975146&#10;7086812930967&#10;sau&#10;5904862975146, 7086812930967"
            rows={4}
            disabled={loading}
            maxLength={2000}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {eanInput.split(/[\s,\n]+/).filter(s => s.trim()).length} coduri EAN introduse (max 100)
          </Text>
        </Space>

        {searchStats && (
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title="Produse găsite"
                value={searchStats.total}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="EAN-uri căutate"
                value={searchStats.searched}
                prefix={<BarcodeOutlined />}
              />
            </Col>
          </Row>
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" tip="Căutare produse în catalogul eMAG..." />
          </div>
        )}

        {!loading && searchResults && (
          <div style={{ maxHeight: 500, overflowY: 'auto' }}>
            {Object.keys(searchResults).length === 0 ? (
              <Empty description="Nu s-au găsit produse" />
            ) : (
              <List
                dataSource={Object.entries(searchResults)}
                renderItem={([ean, data]) => (
                  <List.Item style={{ padding: 0, border: 'none' }}>
                    <div style={{ width: '100%' }}>
                      {renderProductCard(ean, data.products)}
                    </div>
                  </List.Item>
                )}
              />
            )}
          </div>
        )}

        <Divider style={{ margin: '8px 0' }} />
        
        <Alert
          message="Rate Limits"
          description="5 cereri/secundă • 200 cereri/minut • 5,000 cereri/zi"
          type="warning"
          showIcon
          style={{ fontSize: 12 }}
        />
      </Space>
    </Modal>
  );
};

export default EANSearchModal;
