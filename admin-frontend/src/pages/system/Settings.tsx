import { Card, Space, Typography, Divider, Input, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { BellOutlined, SettingOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

export default function SettingsPage() {
  const navigate = useNavigate();

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 0 }}>Setări aplicație</Title>
        <Text type="secondary">
          Configurează preferințele generale pentru MagFlow ERP Admin.
        </Text>
      </div>

      <Card 
        title={
          <Space>
            <BellOutlined />
            <span>Preferințe notificări</span>
          </Space>
        }
        extra={
          <Button 
            type="link" 
            icon={<SettingOutlined />}
            onClick={() => navigate('/notification-settings')}
          >
            Setări avansate
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text type="secondary">
            Configurează cum și când primești notificări din sistem. Accesează setările avansate pentru opțiuni detaliate.
          </Text>
          <Button 
            type="primary" 
            icon={<SettingOutlined />}
            onClick={() => navigate('/notification-settings')}
          >
            Deschide setări notificări
          </Button>
        </Space>
      </Card>

      <Card title="Branding personalizat">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>Nume companie</Text>
            <Input placeholder="Introdu numele companiei tale" defaultValue="MagFlow" />
          </div>
          <div>
            <Text strong>URL logo</Text>
            <Input placeholder="https://exemplu.ro/logo.png" />
          </div>
          <Divider style={{ margin: '12px 0' }} />
          <Button type="primary" disabled>
            Salvează modificările
          </Button>
          <Text type="secondary" italic>
            Funcționalitate în curs de implementare.
          </Text>
        </Space>
      </Card>
    </Space>
  );
}
