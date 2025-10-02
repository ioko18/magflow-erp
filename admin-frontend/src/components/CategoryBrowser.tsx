import React, { useState, useEffect } from 'react';
import {
  Modal,
  Tree,
  Input,
  Spin,
  Alert,
  Space,
  Typography,
  Tag,
  Divider,
  Descriptions,
  Empty,
} from 'antd';
import {
  SearchOutlined,
  FolderOutlined,
  TagOutlined,
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import api from '../services/api';

const { Text } = Typography;
const { Search } = Input;

interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  level: number;
  is_ean_mandatory: boolean;
  characteristics?: any[];
}

interface CategoryBrowserProps {
  visible: boolean;
  onClose: () => void;
  onSelect: (category: Category) => void;
  selectedCategoryId?: number;
}

const CategoryBrowser: React.FC<CategoryBrowserProps> = ({
  visible,
  onClose,
  onSelect,
  selectedCategoryId,
}) => {
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [treeData, setTreeData] = useState<DataNode[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  const [searchValue, setSearchValue] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);

  // Fetch categories from API
  useEffect(() => {
    if (visible) {
      fetchCategories();
    }
  }, [visible]);

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const response = await api.get('/products-v1/categories', {
        params: { page: 1, per_page: 1000 },
      });

      if (response.data) {
        const categoriesData = response.data.categories || [];
        setCategories(categoriesData);
        buildTreeData(categoriesData);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Build tree structure from flat categories
  const buildTreeData = (categoriesData: Category[]) => {
    const categoryMap = new Map<number, Category>();
    categoriesData.forEach((cat) => categoryMap.set(cat.id, cat));

    const buildNode = (category: Category): DataNode => {
      const children = categoriesData
        .filter((c) => c.parent_id === category.id)
        .map((c) => buildNode(c));

      return {
        key: category.id,
        title: (
          <Space>
            {category.is_ean_mandatory && (
              <Tag color="orange" style={{ fontSize: 10 }}>
                EAN
              </Tag>
            )}
            <Text>{category.name}</Text>
          </Space>
        ),
        icon: children.length > 0 ? <FolderOutlined /> : <TagOutlined />,
        children: children.length > 0 ? children : undefined,
      };
    };

    // Get root categories (level 1 or parent_id = null)
    const rootCategories = categoriesData.filter(
      (cat) => cat.parent_id === null || cat.level === 1
    );

    const tree = rootCategories.map((cat) => buildNode(cat));
    setTreeData(tree);

    // Auto-expand to selected category if provided
    if (selectedCategoryId) {
      const keysToExpand = findPathToCategory(selectedCategoryId, categoriesData);
      setExpandedKeys(keysToExpand);
      setSelectedKeys([selectedCategoryId]);
    }
  };

  // Find path from root to a specific category
  const findPathToCategory = (
    categoryId: number,
    categoriesData: Category[]
  ): number[] => {
    const path: number[] = [];
    let currentId: number | null = categoryId;

    while (currentId !== null) {
      const category = categoriesData.find((c) => c.id === currentId);
      if (!category) break;
      path.unshift(currentId);
      currentId = category.parent_id;
    }

    return path;
  };

  // Handle tree node selection
  const handleSelect = (selectedKeysValue: React.Key[]) => {
    const categoryId = selectedKeysValue[0] as number;
    const category = categories.find((c) => c.id === categoryId);

    if (category) {
      setSelectedKeys(selectedKeysValue);
      setSelectedCategory(category);
    }
  };

  // Handle tree node expansion
  const handleExpand = (expandedKeysValue: React.Key[]) => {
    setExpandedKeys(expandedKeysValue);
  };

  // Filter tree by search value
  const filterTreeData = (data: DataNode[], searchVal: string): DataNode[] => {
    if (!searchVal) return data;

    return data
      .map((node) => {
        const title = typeof node.title === 'string' ? node.title : '';
        const matches = title.toLowerCase().includes(searchVal.toLowerCase());
        const filteredChildren = node.children
          ? filterTreeData(node.children, searchVal)
          : [];

        if (matches || filteredChildren.length > 0) {
          return {
            ...node,
            children: filteredChildren.length > 0 ? filteredChildren : node.children,
          };
        }
        return null;
      })
      .filter((node) => node !== null) as DataNode[];
  };

  // Handle search
  const handleSearch = (value: string) => {
    setSearchValue(value);
    if (value) {
      // Expand all nodes when searching
      const allKeys = categories.map((c) => c.id);
      setExpandedKeys(allKeys);
    }
  };

  // Handle confirm selection
  const handleConfirm = () => {
    if (selectedCategory) {
      onSelect(selectedCategory);
      onClose();
    }
  };

  const filteredTreeData = filterTreeData(treeData, searchValue);

  return (
    <Modal
      title="Selectează Categorie eMAG"
      open={visible}
      onCancel={onClose}
      onOk={handleConfirm}
      okText="Selectează"
      cancelText="Anulează"
      width={900}
      okButtonProps={{ disabled: !selectedCategory }}
      style={{ top: 20 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Search */}
        <Search
          placeholder="Caută categorie..."
          prefix={<SearchOutlined />}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
        />

        {/* Tree and Details */}
        <div style={{ display: 'flex', gap: 16, minHeight: 500 }}>
          {/* Category Tree */}
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: 500 }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: 50 }}>
                <Spin size="large" />
              </div>
            ) : filteredTreeData.length > 0 ? (
              <Tree
                showIcon
                expandedKeys={expandedKeys}
                selectedKeys={selectedKeys}
                onSelect={handleSelect}
                onExpand={handleExpand}
                treeData={filteredTreeData}
                height={480}
                virtual
              />
            ) : (
              <Empty description="Nu s-au găsit categorii" />
            )}
          </div>

          {/* Category Details */}
          <div
            style={{
              width: 350,
              borderLeft: '1px solid #f0f0f0',
              paddingLeft: 16,
              overflowY: 'auto',
              maxHeight: 500,
            }}
          >
            {selectedCategory ? (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <div>
                  <Text strong style={{ fontSize: 16 }}>
                    {selectedCategory.name}
                  </Text>
                </div>

                <Divider style={{ margin: '8px 0' }} />

                <Descriptions column={1} size="small">
                  <Descriptions.Item label="ID Categorie">
                    {selectedCategory.id}
                  </Descriptions.Item>
                  <Descriptions.Item label="Nivel">
                    {selectedCategory.level}
                  </Descriptions.Item>
                  <Descriptions.Item label="EAN Obligatoriu">
                    {selectedCategory.is_ean_mandatory ? (
                      <Tag color="orange">DA</Tag>
                    ) : (
                      <Tag color="green">NU</Tag>
                    )}
                  </Descriptions.Item>
                </Descriptions>

                {selectedCategory.characteristics &&
                  selectedCategory.characteristics.length > 0 && (
                    <>
                      <Divider style={{ margin: '8px 0' }} />
                      <div>
                        <Text strong>Caracteristici Disponibile:</Text>
                        <div style={{ marginTop: 8 }}>
                          {selectedCategory.characteristics.map((char: any, idx: number) => (
                            <Tag key={idx} style={{ marginBottom: 4 }}>
                              {char.name}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                <Alert
                  message="Info"
                  description="Selectați o categorie și apăsați 'Selectează' pentru a o atribui produsului."
                  type="info"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              </Space>
            ) : (
              <Empty
                description="Selectați o categorie pentru a vedea detalii"
                style={{ marginTop: 100 }}
              />
            )}
          </div>
        </div>
      </Space>
    </Modal>
  );
};

export default CategoryBrowser;
