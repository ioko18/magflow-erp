import React, { useState } from 'react';
import {
  Drawer,
  List,
  Avatar,
  Typography,
  Button,
  Space,
  Tag,
  Empty,
  Tooltip,
  Badge,
  Dropdown,
  Segmented,
  Input
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ShoppingCartOutlined,
  UserOutlined,
  WarningOutlined,
  DeleteOutlined,
  SettingOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { useNotifications, NotificationItem } from '../../contexts/NotificationContext';
import { formatDistanceToNow } from 'date-fns';

const { Text } = Typography;

interface NotificationPanelProps {
  visible: boolean;
  onClose: () => void;
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({ visible, onClose }) => {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead, 
    removeNotification, 
    clearAll 
  } = useNotifications();

  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const getIcon = (type: string, category: string) => {
    const iconProps = { style: { fontSize: '16px' } };
    
    if (category === 'emag') return <SyncOutlined {...iconProps} />;
    if (category === 'orders') return <ShoppingCartOutlined {...iconProps} />;
    if (category === 'users') return <UserOutlined {...iconProps} />;
    if (category === 'inventory') return <WarningOutlined {...iconProps} />;
    
    switch (type) {
      case 'success': return <CheckCircleOutlined {...iconProps} style={{ color: '#52c41a' }} />;
      case 'warning': return <ExclamationCircleOutlined {...iconProps} style={{ color: '#faad14' }} />;
      case 'error': return <CloseCircleOutlined {...iconProps} style={{ color: '#ff4d4f' }} />;
      default: return <InfoCircleOutlined {...iconProps} style={{ color: '#1890ff' }} />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'emag': return 'blue';
      case 'orders': return 'green';
      case 'users': return 'purple';
      case 'inventory': return 'orange';
      case 'system': return 'red';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'blue';
      case 'low': return 'green';
      default: return 'default';
    }
  };

  const filteredNotifications = notifications.filter(notification => {
    if (filter === 'unread' && notification.read) return false;
    if (filter === 'read' && !notification.read) return false;
    if (searchTerm && !notification.title.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !notification.message.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const handleMarkAsRead = (notification: NotificationItem) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  const dropdownItems = [
    {
      key: 'markAllRead',
      label: 'Mark All as Read',
      icon: <CheckCircleOutlined />,
      onClick: markAllAsRead,
      disabled: unreadCount === 0,
    },
    {
      key: 'clearAll',
      label: 'Clear All',
      icon: <DeleteOutlined />,
      onClick: clearAll,
      disabled: notifications.length === 0,
      danger: true,
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'settings',
      label: 'Notification Settings',
      icon: <SettingOutlined />,
      onClick: () => console.log('Open settings'),
    },
  ];

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <BellOutlined />
            <span>Notifications</span>
            {unreadCount > 0 && <Badge count={unreadCount} />}
          </Space>
          <Dropdown menu={{ items: dropdownItems }} placement="bottomRight">
            <Button type="text" icon={<SettingOutlined />} />
          </Dropdown>
        </div>
      }
      placement="right"
      width={400}
      open={visible}
      onClose={onClose}
      styles={{ body: { padding: 0 } }}
    >
      <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="Search notifications..."
            prefix={<SearchOutlined />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            allowClear
          />
          
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { label: 'All', value: 'all' },
              { label: `Unread (${unreadCount})`, value: 'unread' },
              { label: 'Read', value: 'read' },
            ]}
            size="small"
          />
        </Space>
      </div>

      <div style={{ height: 'calc(100vh - 200px)', overflow: 'auto' }}>
        {filteredNotifications.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No notifications"
            style={{ marginTop: '50px' }}
          />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={filteredNotifications}
            renderItem={(notification) => (
              <List.Item
                style={{
                  padding: '12px 16px',
                  backgroundColor: notification.read ? 'transparent' : '#f6ffed',
                  borderLeft: notification.read ? 'none' : '3px solid #52c41a',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                }}
                onClick={() => handleMarkAsRead(notification)}
                actions={[
                  <Tooltip title="Remove" key="remove">
                    <Button
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        removeNotification(notification.id);
                      }}
                      danger
                    />
                  </Tooltip>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar 
                      icon={getIcon(notification.type, notification.category)}
                      style={{ 
                        backgroundColor: notification.read ? '#f5f5f5' : '#fff',
                        border: `2px solid ${notification.read ? '#d9d9d9' : '#52c41a'}`
                      }}
                    />
                  }
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Text strong={!notification.read} style={{ fontSize: '14px' }}>
                        {notification.title}
                      </Text>
                      <Tag color={getPriorityColor(notification.priority)}>
                        {notification.priority.toUpperCase()}
                      </Tag>
                    </div>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>
                        {notification.message}
                      </Text>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Tag color={getCategoryColor(notification.category)}>
                          {notification.category}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                        </Text>
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </div>

      {notifications.length > 0 && (
        <div style={{ 
          padding: '12px 16px', 
          borderTop: '1px solid #f0f0f0',
          backgroundColor: '#fafafa'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {filteredNotifications.length} of {notifications.length} notifications
            </Text>
            <Space>
              {unreadCount > 0 && (
                <Button size="small" type="link" onClick={markAllAsRead}>
                  Mark all as read
                </Button>
              )}
              <Button size="small" type="link" onClick={clearAll} danger>
                Clear all
              </Button>
            </Space>
          </div>
        </div>
      )}
    </Drawer>
  );
};

export default NotificationPanel;
