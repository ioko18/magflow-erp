import { Card, Space, Typography, Divider, Switch, Input, Button } from 'antd';

const { Title, Text } = Typography;

export default function SettingsPage() {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 0 }}>Setări aplicație</Title>
        <Text type="secondary">
          Configurează preferințele generale pentru MagFlow ERP Admin.
        </Text>
      </div>

      <Card title="Preferințe notificări">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
            <div>
              <Text strong>Notificări dashboard</Text>
              <br />
              <Text type="secondary">
                Primește alerte când apar modificări importante în indicatorii principali.
              </Text>
            </div>
            <Switch defaultChecked />
          </Space>
          <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
            <div>
              <Text strong>Notificări e-mail</Text>
              <br />
              <Text type="secondary">
                Trimite o notificare pe e-mail la finalizarea sincronizărilor eMAG.
              </Text>
            </div>
            <Switch />
          </Space>
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
