import { Radio, Badge, Space } from 'antd';
import { GlobalOutlined, ShopOutlined } from '@ant-design/icons';

interface AccountSwitcherProps {
  value: 'all' | 'main' | 'fbe';
  onChange: (value: 'all' | 'main' | 'fbe') => void;
  mainCount?: number;
  fbeCount?: number;
  showCounts?: boolean;
}

const AccountSwitcher: React.FC<AccountSwitcherProps> = ({
  value,
  onChange,
  mainCount = 0,
  fbeCount = 0,
  showCounts = true,
}) => {
  return (
    <Radio.Group 
      value={value} 
      onChange={(e) => onChange(e.target.value)}
      buttonStyle="solid"
      size="large"
    >
      <Radio.Button value="all">
        <Space>
          <GlobalOutlined />
          <span>Toate Conturile</span>
          {showCounts && (
            <Badge 
              count={mainCount + fbeCount} 
              style={{ backgroundColor: '#52c41a' }}
              overflowCount={9999}
            />
          )}
        </Space>
      </Radio.Button>
      
      <Radio.Button value="main">
        <Space>
          <ShopOutlined />
          <span>MAIN</span>
          {showCounts && (
            <Badge 
              count={mainCount} 
              style={{ backgroundColor: '#1890ff' }}
              overflowCount={9999}
            />
          )}
        </Space>
      </Radio.Button>
      
      <Radio.Button value="fbe">
        <Space>
          <ShopOutlined />
          <span>FBE</span>
          {showCounts && (
            <Badge 
              count={fbeCount} 
              style={{ backgroundColor: '#722ed1' }}
              overflowCount={9999}
            />
          )}
        </Space>
      </Radio.Button>
    </Radio.Group>
  );
};

export default AccountSwitcher;
