import { Space, Tag, Tooltip } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  SyncOutlined,
  WarningOutlined 
} from '@ant-design/icons';

interface AccountStatus {
  published: boolean;
  syncing?: boolean;
  hasError?: boolean;
  lastSync?: string;
  price?: number;
  stock?: number;
}

interface ProductAccountStatusProps {
  mainAccount?: AccountStatus;
  fbeAccount?: AccountStatus;
  showDetails?: boolean;
}

const ProductAccountStatus: React.FC<ProductAccountStatusProps> = ({
  mainAccount,
  fbeAccount,
  showDetails = false,
}) => {
  const renderAccountTag = (
    accountName: string,
    status?: AccountStatus,
    color: string = 'blue'
  ) => {
    if (!status) {
      return (
        <Tag color="default" icon={<CloseCircleOutlined />}>
          {accountName}: Nu e publicat
        </Tag>
      );
    }

    if (status.hasError) {
      return (
        <Tooltip title="Eroare la sincronizare">
          <Tag color="error" icon={<WarningOutlined />}>
            {accountName}: Eroare
          </Tag>
        </Tooltip>
      );
    }

    if (status.syncing) {
      return (
        <Tag color="processing" icon={<SyncOutlined spin />}>
          {accountName}: Se sincronizează...
        </Tag>
      );
    }

    if (status.published) {
      const details = showDetails && status.price && status.stock !== undefined
        ? ` (${status.price} RON, Stoc: ${status.stock})`
        : '';
      
      return (
        <Tooltip title={status.lastSync ? `Ultima sincronizare: ${status.lastSync}` : ''}>
          <Tag color={color} icon={<CheckCircleOutlined />}>
            {accountName}{details}
          </Tag>
        </Tooltip>
      );
    }

    return (
      <Tag color="default" icon={<CloseCircleOutlined />}>
        {accountName}: Nu e publicat
      </Tag>
    );
  };

  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      {renderAccountTag('MAIN', mainAccount, 'blue')}
      {renderAccountTag('FBE', fbeAccount, 'purple')}
    </Space>
  );
};

export default ProductAccountStatus;
