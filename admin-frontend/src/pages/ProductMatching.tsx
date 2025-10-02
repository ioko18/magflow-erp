import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Image,
  Modal,
  Alert,
  Statistic,
  Divider,
  Tooltip,
  message,
  Select
} from 'antd';
import {
  CheckCircleOutlined,
  EyeOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  CheckOutlined,
  CloseOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { Option } = Select;

interface ProductMatch {
  id: number;
  local_product: {
    id: number;
    name: string;
    sku: string;
    brand?: string;
    category?: string;
  };
  supplier_product: {
    name_chinese: string;
    price: number;
    currency: string;
    image_url: string;
    url: string;
  };
  confidence_score: number;
  manual_confirmed: boolean;
  created_at: string;
}

interface MatchingStats {
  total_matches: number;
  confirmed_matches: number;
  pending_matches: number;
  average_confidence: number;
  confirmation_rate: number;
}

const ProductMatchingPage: React.FC = () => {
  const [matches, setMatches] = useState<ProductMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<MatchingStats | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<ProductMatch | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [confidenceFilter, setConfidenceFilter] = useState<number>(0.5);

  useEffect(() => {
    fetchMatches();
    fetchStats();
  }, [confidenceFilter]);

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/suppliers/1/products/match?confidence_threshold=${confidenceFilter}`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setMatches(data.data.matches);
        }
      }
    } catch (error) {
      message.error('Eroare la încărcarea matching-urilor');
      console.error('Error fetching matches:', error);
    } finally {
      setLoading(false);
    }
  }, [confidenceFilter]);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/suppliers/1/matching/statistics');
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setStats(data.data);
        }
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleConfirmMatch = async (matchId: number) => {
    try {
      const response = await fetch(`/api/v1/suppliers/1/products/${matchId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true })
      });

      if (response.ok) {
        message.success('Potrivire confirmată cu succes');
        fetchMatches();
        fetchStats();
      }
    } catch (error) {
      message.error('Eroare la confirmarea potrivirii');
    }
  };

  const handleRejectMatch = async (matchId: number) => {
    try {
      const response = await fetch(`/api/v1/suppliers/1/products/${matchId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: false })
      });

      if (response.ok) {
        message.success('Potrivire respinsă');
        fetchMatches();
        fetchStats();
      }
    } catch (error) {
      message.error('Eroare la respingerea potrivirii');
    }
  };

  const viewMatchDetails = (match: ProductMatch) => {
    setSelectedMatch(match);
    setDetailModalVisible(true);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return '#52c41a'; // Verde - foarte sigur
    if (score >= 0.6) return '#faad14'; // Portocaliu - mediu
    return '#ff4d4f'; // Roșu - scăzut
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'Foarte sigur';
    if (score >= 0.6) return 'Mediu';
    return 'Scăzut';
  };

  const columns: ColumnsType<ProductMatch> = [
    {
      title: 'Produs Local',
      key: 'local_product',
      render: (_, record) => (
        <div>
          <div><strong>{record.local_product.name}</strong></div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            SKU: {record.local_product.sku}
          </div>
          {record.local_product.brand && (
            <Tag color="blue">{record.local_product.brand}</Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Produs 1688',
      key: 'supplier_product',
      render: (_, record) => (
        <div>
          <div><strong>{record.supplier_product.name_chinese}</strong></div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.supplier_product.price} {record.supplier_product.currency}
          </div>
          <a href={record.supplier_product.url} target="_blank" rel="noopener noreferrer">
            Vezi pe 1688
          </a>
        </div>
      ),
    },
    {
      title: 'Imagine',
      key: 'image',
      width: 100,
      render: (_, record) => (
        <Image
          src={record.supplier_product.image_url}
          alt={record.supplier_product.name_chinese}
          width={60}
          height={60}
          style={{ objectFit: 'cover', borderRadius: '4px' }}
          fallback="/placeholder-product.png"
        />
      ),
    },
    {
      title: 'Scor Potrivire',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      width: 120,
      render: (score: number) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 'bold', color: getConfidenceColor(score) }}>
            {Math.round(score * 100)}%
          </div>
          <Tag color={getConfidenceColor(score)}>
            {getConfidenceLabel(score)}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'manual_confirmed',
      key: 'status',
      width: 100,
      render: (confirmed: boolean) => (
        <Tag color={confirmed ? 'green' : 'orange'}>
          {confirmed ? 'Confirmat' : 'În așteptare'}
        </Tag>
      ),
    },
    {
      title: 'Data',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString('ro-RO'),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="Vezi detalii">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => viewMatchDetails(record)}
            />
          </Tooltip>
          {!record.manual_confirmed && (
            <>
              <Tooltip title="Confirmă potrivire">
                <Button
                  type="text"
                  icon={<CheckOutlined />}
                  style={{ color: '#52c41a' }}
                  onClick={() => handleConfirmMatch(record.id)}
                />
              </Tooltip>
              <Tooltip title="Respinge potrivire">
                <Button
                  type="text"
                  icon={<CloseOutlined />}
                  style={{ color: '#ff4d4f' }}
                  onClick={() => handleRejectMatch(record.id)}
                />
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <SyncOutlined style={{ marginRight: '8px' }} />
              Product Matching - 1688.com
            </Title>
            <p style={{ color: '#666', margin: 0 }}>
              Potrivirea automată între produsele locale și cele de pe 1688.com
            </p>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchMatches} loading={loading}>
              Reîmprospătează
            </Button>
          </Space>
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Total Potriviri"
                value={stats.total_matches}
                prefix={<SyncOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Confirmate"
                value={stats.confirmed_matches}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="În Așteptare"
                value={stats.pending_matches}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Scor Mediu"
                value={stats.average_confidence}
                precision={3}
                suffix="/1.0"
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: '16px' }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <div>
              <Text strong>Filtru Scor Potrivire:</Text>
              <Select
                value={confidenceFilter}
                onChange={setConfidenceFilter}
                style={{ width: '100%', marginTop: '8px' }}
              >
                <Option value={0.3}>Scăzut (&gt;30%)</Option>
                <Option value={0.5}>Mediu (&gt;50%)</Option>
                <Option value={0.7}>Ridicat (&gt;70%)</Option>
                <Option value={0.8}>Foarte Ridicat (&gt;80%)</Option>
              </Select>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <Alert
              message={`Afișează ${matches.length} potriviri cu scor > ${Math.round(confidenceFilter * 100)}%`}
              type="info"
              showIcon
            />
          </Col>
        </Row>
      </Card>

      {/* Matches Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={matches}
          rowKey="id"
          loading={loading}
          pagination={{
            total: matches.length,
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} din ${total} potriviri`,
          }}
          scroll={{ x: 1200 }}
          size="small"
        />
      </Card>

      {/* Match Details Modal */}
      <Modal
        title="Detalii Potrivire Produs"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Închide
          </Button>
        ]}
      >
        {selectedMatch && (
          <div>
            <Row gutter={24}>
              <Col span={12}>
                <Card title="Produs Local" size="small">
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Text strong style={{ fontSize: '16px' }}>
                      {selectedMatch.local_product.name}
                    </Text>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>SKU:</strong> {selectedMatch.local_product.sku}</Text>
                  </div>
                  {selectedMatch.local_product.brand && (
                    <div style={{ marginBottom: '8px' }}>
                      <Text><strong>Brand:</strong> {selectedMatch.local_product.brand}</Text>
                    </div>
                  )}
                  {selectedMatch.local_product.category && (
                    <div style={{ marginBottom: '8px' }}>
                      <Text><strong>Categorie:</strong> {selectedMatch.local_product.category}</Text>
                    </div>
                  )}
                </Card>
              </Col>

              <Col span={12}>
                <Card title="Produs 1688.com" size="small">
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Image
                      src={selectedMatch.supplier_product.image_url}
                      alt={selectedMatch.supplier_product.name_chinese}
                      width={120}
                      height={120}
                      style={{ objectFit: 'cover', borderRadius: '8px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>Nume Chinezesc:</strong></Text>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {selectedMatch.supplier_product.name_chinese}
                    </div>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text><strong>Preț:</strong> {selectedMatch.supplier_product.price} {selectedMatch.supplier_product.currency}</Text>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <a href={selectedMatch.supplier_product.url} target="_blank" rel="noopener noreferrer">
                      Vezi pe 1688.com
                    </a>
                  </div>
                </Card>
              </Col>
            </Row>

            <Divider />

            <Card title="Analiză Potrivire" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Scor Potrivire"
                    value={Math.round(selectedMatch.confidence_score * 100)}
                    suffix="%"
                    valueStyle={{
                      color: getConfidenceColor(selectedMatch.confidence_score)
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Status"
                    value={selectedMatch.manual_confirmed ? 'Confirmat' : 'În așteptare'}
                    valueStyle={{
                      color: selectedMatch.manual_confirmed ? '#52c41a' : '#faad14'
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Data Creare"
                    value={new Date(selectedMatch.created_at).toLocaleDateString('ro-RO')}
                  />
                </Col>
              </Row>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ProductMatchingPage;
