import React, { useState, useEffect } from 'react';
import {
  Card,
  Space,
  Typography,
  Switch,
  Select,
  TimePicker,
  InputNumber,
  Button,
  Divider,
  message,
  Spin,
  Alert,
  Row,
  Col,
  Collapse,
  Tag,
} from 'antd';
import {
  BellOutlined,
  MailOutlined,
  MobileOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { notificationService, NotificationSettings as Settings } from '../../services/system/notificationService';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

const NotificationSettings: React.FC = () => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await notificationService.getSettings();
      setSettings(data);
      setHasChanges(false);
    } catch (error: any) {
      console.error('Error loading notification settings:', error);
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to load notification settings';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;

    try {
      setSaving(true);
      await notificationService.updateSettings(settings);
      message.success('Notification settings saved successfully');
      setHasChanges(false);
    } catch (error) {
      console.error('Error saving notification settings:', error);
      message.error('Failed to save notification settings');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      const defaultSettings = await notificationService.resetSettings();
      setSettings(defaultSettings);
      message.success('Notification settings reset to defaults');
      setHasChanges(false);
    } catch (error) {
      console.error('Error resetting notification settings:', error);
      message.error('Failed to reset notification settings');
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    if (settings) {
      setSettings({ ...settings, [key]: value });
      setHasChanges(true);
    }
  };

  const updateCategoryPreference = (category: string, channel: string, enabled: boolean) => {
    if (!settings) return;

    const newPreferences = { ...settings.category_preferences };
    if (!newPreferences[category]) {
      newPreferences[category] = {};
    }
    newPreferences[category][channel] = enabled;

    updateSetting('category_preferences', newPreferences);
  };

  const getCategoryPreference = (category: string, channel: string): boolean => {
    if (!settings?.category_preferences) return true;
    return settings.category_preferences[category]?.[channel] ?? true;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!settings) {
    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Alert
          message="Error Loading Settings"
          description={
            <Space direction="vertical">
              <Text>{error || "Failed to load notification settings. Please try again."}</Text>
              <Button type="primary" onClick={loadSettings} icon={<ReloadOutlined />}>
                Retry
              </Button>
            </Space>
          }
          type="error"
          showIcon
        />
      </Space>
    );
  }

  const categories = [
    { key: 'system', label: 'System', color: 'red', description: 'System alerts and maintenance' },
    { key: 'emag', label: 'eMAG', color: 'blue', description: 'eMAG synchronization and updates' },
    { key: 'orders', label: 'Orders', color: 'green', description: 'New orders and order updates' },
    { key: 'users', label: 'Users', color: 'purple', description: 'User management activities' },
    { key: 'inventory', label: 'Inventory', color: 'orange', description: 'Stock levels and inventory alerts' },
    { key: 'sync', label: 'Sync', color: 'cyan', description: 'Data synchronization progress' },
    { key: 'payment', label: 'Payment', color: 'gold', description: 'Payment processing notifications' },
    { key: 'shipping', label: 'Shipping', color: 'magenta', description: 'Shipping and delivery updates' },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 0 }}>
          <BellOutlined /> Notification Settings
        </Title>
        <Text type="secondary">
          Configure how and when you receive notifications from MagFlow ERP.
        </Text>
      </div>

      {hasChanges && (
        <Alert
          message="You have unsaved changes"
          description="Don't forget to save your changes before leaving this page."
          type="warning"
          showIcon
          closable
        />
      )}

      {/* Global Settings */}
      <Card title="Global Settings">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Text strong>Enable Notifications</Text>
              <br />
              <Text type="secondary">Master switch for all notifications</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.enabled}
                onChange={(checked) => updateSetting('enabled', checked)}
              />
            </Col>
          </Row>

          <Divider style={{ margin: '12px 0' }} />

          <Row align="middle" justify="space-between">
            <Col>
              <Text strong>Minimum Priority</Text>
              <br />
              <Text type="secondary">Only show notifications above this priority</Text>
            </Col>
            <Col>
              <Select
                value={settings.min_priority}
                onChange={(value) => updateSetting('min_priority', value)}
                style={{ width: 120 }}
                disabled={!settings.enabled}
              >
                <Select.Option value="low">Low</Select.Option>
                <Select.Option value="medium">Medium</Select.Option>
                <Select.Option value="high">High</Select.Option>
                <Select.Option value="critical">Critical</Select.Option>
              </Select>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* Channel Settings */}
      <Card title="Notification Channels">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <BellOutlined style={{ marginRight: 8 }} />
              <Text strong>Push Notifications</Text>
              <br />
              <Text type="secondary">In-app notifications</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.push_enabled}
                onChange={(checked) => updateSetting('push_enabled', checked)}
                disabled={!settings.enabled}
              />
            </Col>
          </Row>

          <Divider style={{ margin: '12px 0' }} />

          <Row align="middle" justify="space-between">
            <Col>
              <MailOutlined style={{ marginRight: 8 }} />
              <Text strong>Email Notifications</Text>
              <br />
              <Text type="secondary">Receive notifications via email</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.email_enabled}
                onChange={(checked) => updateSetting('email_enabled', checked)}
                disabled={!settings.enabled}
              />
            </Col>
          </Row>

          <Divider style={{ margin: '12px 0' }} />

          <Row align="middle" justify="space-between">
            <Col>
              <MobileOutlined style={{ marginRight: 8 }} />
              <Text strong>SMS Notifications</Text>
              <br />
              <Text type="secondary">Receive critical alerts via SMS</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.sms_enabled}
                onChange={(checked) => updateSetting('sms_enabled', checked)}
                disabled={!settings.enabled}
              />
            </Col>
          </Row>
        </Space>
      </Card>

      {/* Category Preferences */}
      <Card title="Category Preferences">
        <Paragraph type="secondary">
          Configure notification preferences for each category and channel.
        </Paragraph>
        
        <Collapse>
          {categories.map((category) => (
            <Panel
              key={category.key}
              header={
                <Space>
                  <Tag color={category.color}>{category.label}</Tag>
                  <Text type="secondary">{category.description}</Text>
                </Space>
              }
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Row align="middle" justify="space-between">
                  <Col>
                    <BellOutlined style={{ marginRight: 8 }} />
                    <Text>Push</Text>
                  </Col>
                  <Col>
                    <Switch
                      checked={getCategoryPreference(category.key, 'push')}
                      onChange={(checked) => updateCategoryPreference(category.key, 'push', checked)}
                      disabled={!settings.enabled || !settings.push_enabled}
                    />
                  </Col>
                </Row>
                <Row align="middle" justify="space-between">
                  <Col>
                    <MailOutlined style={{ marginRight: 8 }} />
                    <Text>Email</Text>
                  </Col>
                  <Col>
                    <Switch
                      checked={getCategoryPreference(category.key, 'email')}
                      onChange={(checked) => updateCategoryPreference(category.key, 'email', checked)}
                      disabled={!settings.enabled || !settings.email_enabled}
                    />
                  </Col>
                </Row>
                <Row align="middle" justify="space-between">
                  <Col>
                    <MobileOutlined style={{ marginRight: 8 }} />
                    <Text>SMS</Text>
                  </Col>
                  <Col>
                    <Switch
                      checked={getCategoryPreference(category.key, 'sms')}
                      onChange={(checked) => updateCategoryPreference(category.key, 'sms', checked)}
                      disabled={!settings.enabled || !settings.sms_enabled}
                    />
                  </Col>
                </Row>
              </Space>
            </Panel>
          ))}
        </Collapse>
      </Card>

      {/* Quiet Hours */}
      <Card title={<><ClockCircleOutlined /> Quiet Hours</>}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Text strong>Enable Quiet Hours</Text>
              <br />
              <Text type="secondary">Mute notifications during specific hours</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.quiet_hours_enabled}
                onChange={(checked) => updateSetting('quiet_hours_enabled', checked)}
                disabled={!settings.enabled}
              />
            </Col>
          </Row>

          {settings.quiet_hours_enabled && (
            <>
              <Divider style={{ margin: '12px 0' }} />
              <Row gutter={16}>
                <Col span={12}>
                  <Text>Start Time</Text>
                  <br />
                  <TimePicker
                    format="HH:mm"
                    value={settings.quiet_hours_start ? dayjs(settings.quiet_hours_start, 'HH:mm') : null}
                    onChange={(time) => updateSetting('quiet_hours_start', time?.format('HH:mm') || undefined)}
                    style={{ width: '100%' }}
                  />
                </Col>
                <Col span={12}>
                  <Text>End Time</Text>
                  <br />
                  <TimePicker
                    format="HH:mm"
                    value={settings.quiet_hours_end ? dayjs(settings.quiet_hours_end, 'HH:mm') : null}
                    onChange={(time) => updateSetting('quiet_hours_end', time?.format('HH:mm') || undefined)}
                    style={{ width: '100%' }}
                  />
                </Col>
              </Row>
            </>
          )}
        </Space>
      </Card>

      {/* Auto-Delete Settings */}
      <Card title={<><DeleteOutlined /> Auto-Delete</>}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Text strong>Auto-Delete Old Notifications</Text>
              <br />
              <Text type="secondary">Automatically delete read notifications after a period</Text>
            </Col>
            <Col>
              <Switch
                checked={settings.auto_delete_enabled}
                onChange={(checked) => updateSetting('auto_delete_enabled', checked)}
              />
            </Col>
          </Row>

          {settings.auto_delete_enabled && (
            <>
              <Divider style={{ margin: '12px 0' }} />
              <Row align="middle" justify="space-between">
                <Col>
                  <Text>Delete after (days)</Text>
                </Col>
                <Col>
                  <InputNumber
                    min={1}
                    max={365}
                    value={settings.auto_delete_days}
                    onChange={(value) => updateSetting('auto_delete_days', value || 30)}
                  />
                </Col>
              </Row>
            </>
          )}
        </Space>
      </Card>

      {/* Action Buttons */}
      <Card>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
            loading={saving}
            disabled={!hasChanges}
          >
            Reset to Defaults
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            disabled={!hasChanges}
          >
            Save Changes
          </Button>
        </Space>
      </Card>
    </Space>
  );
};

export default NotificationSettings;
