/**
 * Category Browser Modal Component
 * 
 * Browse eMAG categories with characteristics and family types
 * Helps users understand category requirements before creating products
 */

import { useState, useEffect } from 'react';
import {
  Modal,
  Input,
  Tree,
  Descriptions,
  Tag,
  Card,
  Space,
  message,
  Spin,
  Empty,
  Alert,
  Typography,
  Badge,
  Divider,
  List,
  Button,
  Select,
} from 'antd';
import {
  SearchOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  BarcodeOutlined,
  SafetyOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { getEmagCategories, EmagCategory } from '../services/emagAdvancedApi';
import type { DataNode } from 'antd/es/tree';

const { Search } = Input;
const { Text, Title } = Typography;

interface CategoryBrowserModalProps {
  visible: boolean;
  onClose: () => void;
  onCategorySelect?: (category: EmagCategory) => void;
}

interface Characteristic {
  id: number;
  name: string;
  type_id: number;
  display_order: number;
  is_mandatory: number;
  is_filter: number;
  allow_new_value: number;
  values?: any[];
  tags?: string[];
}

interface FamilyType {
  id: number;
  name: string;
}

const CategoryBrowserModal: React.FC<CategoryBrowserModalProps> = ({
  visible,
  onClose,
  onCategorySelect,
}) => {
  const [accountType, setAccountType] = useState<'main' | 'fbe'>('main');
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<EmagCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<EmagCategory | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  useEffect(() => {
    if (visible) {
      loadCategories();
    }
  }, [visible, accountType]);

  const loadCategories = async () => {
    setLoading(true);
    try {
      const response = await getEmagCategories(accountType);
      setCategories(response.data.categories);
      message.success(`Încărcate ${response.data.categories.length} categorii`);
    } catch (error: any) {
      console.error('Error loading categories:', error);
      message.error('Eroare la încărcarea categoriilor');
    } finally {
      setLoading(false);
    }
  };

  const loadCategoryDetails = async (categoryId: number) => {
    setLoadingDetails(true);
    try {
      const response = await getEmagCategories(accountType, categoryId);
      if (response.data.categories.length > 0) {
        setSelectedCategory(response.data.categories[0]);
      }
    } catch (error: any) {
      console.error('Error loading category details:', error);
      message.error('Eroare la încărcarea detaliilor categoriei');
    } finally {
      setLoadingDetails(false);
    }
  };

  const buildTreeData = (): DataNode[] => {
    const filteredCategories = categories.filter(cat =>
      cat.name.toLowerCase().includes(searchValue.toLowerCase())
    );

    return filteredCategories.map(category => ({
      title: (
        <Space>
          <span>{category.name}</span>
          {category.is_allowed === 1 ? (
            <Tag color="success" icon={<CheckCircleOutlined />}>Permis</Tag>
          ) : (
            <Tag color="error" icon={<CloseCircleOutlined />}>Nepermis</Tag>
          )}
          {category.is_ean_mandatory === 1 && (
            <Tag color="blue" icon={<BarcodeOutlined />}>EAN obligatoriu</Tag>
          )}
          {category.is_warranty_mandatory === 1 && (
            <Tag color="orange" icon={<SafetyOutlined />}>Garanție obligatorie</Tag>
          )}
        </Space>
      ),
      key: category.id,
      icon: selectedCategory?.id === category.id ? <FolderOpenOutlined /> : <FolderOutlined />,
      isLeaf: true,
    }));
  };

  const handleCategorySelect = (selectedKeys: React.Key[]) => {
    if (selectedKeys.length > 0) {
      const categoryId = selectedKeys[0] as number;
      loadCategoryDetails(categoryId);
    }
  };

  const getCharacteristicTypeName = (typeId: number): string => {
    const types: Record<number, string> = {
      1: 'Numeric',
      2: 'Numeric + unitate',
      11: 'Text fix (≤255 chars)',
      20: 'Boolean (Da/Nu/N/A)',
      30: 'Rezoluție (Width x Height)',
      40: 'Volum (W x H x D)',
      60: 'Mărime',
    };
    return types[typeId] || `Type ${typeId}`;
  };

  const renderCharacteristics = () => {
    if (!selectedCategory?.characteristics || selectedCategory.characteristics.length === 0) {
      return <Empty description="Nicio caracteristică disponibilă" />;
    }

    const characteristics = selectedCategory.characteristics as Characteristic[];

    return (
      <List
        dataSource={characteristics}
        renderItem={(char: Characteristic) => (
          <List.Item>
            <Card size="small" style={{ width: '100%' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <Text strong>{char.name}</Text>
                  {char.is_mandatory === 1 && (
                    <Tag color="error" icon={<WarningOutlined />}>Obligatoriu</Tag>
                  )}
                  {char.is_filter === 1 && (
                    <Tag color="blue">Filtru</Tag>
                  )}
                  {char.allow_new_value === 1 && (
                    <Tag color="success">Valori noi permise</Tag>
                  )}
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ID: {char.id} | Tip: {getCharacteristicTypeName(char.type_id)} | Ordine: {char.display_order}
                </Text>
                {char.tags && char.tags.length > 0 && (
                  <Space size={[4, 4]} wrap>
                    <TagsOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
                    {char.tags.map(tag => (
                      <Tag key={tag} color="purple" style={{ fontSize: 11 }}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                )}
                {char.values && char.values.length > 0 && (
                  <div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      Valori disponibile (primele {Math.min(char.values.length, 10)}):
                    </Text>
                    <div style={{ marginTop: 4 }}>
                      <Space size={[4, 4]} wrap>
                        {char.values.slice(0, 10).map((val: any, idx: number) => (
                          <Tag key={idx} style={{ fontSize: 11 }}>
                            {typeof val === 'object' ? val.name || val.value : val}
                          </Tag>
                        ))}
                        {char.values.length > 10 && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            +{char.values.length - 10} mai multe
                          </Text>
                        )}
                      </Space>
                    </div>
                  </div>
                )}
              </Space>
            </Card>
          </List.Item>
        )}
      />
    );
  };

  const renderFamilyTypes = () => {
    if (!selectedCategory?.family_types || selectedCategory.family_types.length === 0) {
      return <Empty description="Niciun tip de familie disponibil" />;
    }

    const familyTypes = selectedCategory.family_types as FamilyType[];

    return (
      <Space size={[8, 8]} wrap>
        {familyTypes.map((ft: FamilyType) => (
          <Tag key={ft.id} color="geekblue" style={{ fontSize: 13, padding: '4px 12px' }}>
            {ft.name} (ID: {ft.id})
          </Tag>
        ))}
      </Space>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <FolderOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <span>Browser Categorii eMAG</span>
          <Badge count="v4.4.9" style={{ backgroundColor: '#52c41a' }} />
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1200}
      footer={[
        <Button key="close" onClick={onClose}>
          Închide
        </Button>,
        selectedCategory && onCategorySelect && (
          <Button
            key="select"
            type="primary"
            onClick={() => {
              onCategorySelect(selectedCategory);
              message.success(`Categorie selectată: ${selectedCategory.name}`);
              onClose();
            }}
            disabled={selectedCategory.is_allowed !== 1}
          >
            Selectează Categorie
          </Button>
        ),
      ]}
      style={{ top: 20 }}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          message="Browser Categorii eMAG"
          description="Explorează categoriile eMAG pentru a înțelege cerințele de documentație. Fiecare categorie are caracteristici și tipuri de familie specifice."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

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
          <Button
            icon={<SearchOutlined />}
            onClick={loadCategories}
            loading={loading}
          >
            Reîncarcă
          </Button>
        </Space>

        <div style={{ display: 'flex', gap: 16, height: 600 }}>
          {/* Left Panel - Category Tree */}
          <div style={{ flex: '0 0 400px', overflowY: 'auto', borderRight: '1px solid #f0f0f0', paddingRight: 16 }}>
            <Search
              placeholder="Caută categorie..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              style={{ marginBottom: 16 }}
            />
            {loading ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin tip="Încărcare categorii..." />
              </div>
            ) : (
              <Tree
                showIcon
                treeData={buildTreeData()}
                onSelect={handleCategorySelect}
                expandedKeys={expandedKeys}
                onExpand={setExpandedKeys}
              />
            )}
          </div>

          {/* Right Panel - Category Details */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loadingDetails ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin tip="Încărcare detalii categorie..." />
              </div>
            ) : selectedCategory ? (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Card size="small">
                  <Title level={4}>{selectedCategory.name}</Title>
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="ID Categorie">
                      {selectedCategory.id}
                    </Descriptions.Item>
                    <Descriptions.Item label="Parent ID">
                      {selectedCategory.parent_id || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Permis să postezi">
                      {selectedCategory.is_allowed === 1 ? (
                        <Tag color="success" icon={<CheckCircleOutlined />}>Da</Tag>
                      ) : (
                        <Tag color="error" icon={<CloseCircleOutlined />}>Nu</Tag>
                      )}
                    </Descriptions.Item>
                    <Descriptions.Item label="EAN Obligatoriu">
                      {selectedCategory.is_ean_mandatory === 1 ? (
                        <Tag color="blue">Da</Tag>
                      ) : (
                        <Tag color="default">Nu</Tag>
                      )}
                    </Descriptions.Item>
                    <Descriptions.Item label="Garanție Obligatorie">
                      {selectedCategory.is_warranty_mandatory === 1 ? (
                        <Tag color="orange">Da</Tag>
                      ) : (
                        <Tag color="default">Nu</Tag>
                      )}
                    </Descriptions.Item>
                  </Descriptions>
                </Card>

                <Divider orientation="left">Caracteristici Produs</Divider>
                {renderCharacteristics()}

                <Divider orientation="left">Tipuri de Familie</Divider>
                {renderFamilyTypes()}
              </Space>
            ) : (
              <Empty
                description="Selectează o categorie din listă pentru a vedea detalii"
                style={{ marginTop: 100 }}
              />
            )}
          </div>
        </div>
      </Space>
    </Modal>
  );
};

export default CategoryBrowserModal;
