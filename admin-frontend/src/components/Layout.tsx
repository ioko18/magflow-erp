import React, { useState } from 'react'
import { Layout as AntLayout, Menu, Button, Avatar, Dropdown, Badge, Switch, Tooltip } from 'antd'
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TeamOutlined,
  SunOutlined,
  MoonOutlined,
  TruckOutlined,
  BarcodeOutlined,
  EnvironmentOutlined,
  AppstoreOutlined,
  CloudUploadOutlined,
  CloudSyncOutlined,
  FileExcelOutlined,
  ShopOutlined,
  UsergroupAddOutlined,
  SafetyOutlined,
  FileTextOutlined,
  ShoppingOutlined,
  DatabaseOutlined,
  ApiOutlined,
  BellOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { useNotifications } from '../contexts/NotificationContext'
import { useAuth } from '../contexts/AuthContext'
import NotificationPanel from './dashboard/NotificationPanel'

const { Header, Sider, Content } = AntLayout

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(true)
  const [notificationPanelVisible, setNotificationPanelVisible] = useState(false)
  const location = useLocation()
  const { isDarkMode, toggleTheme } = useTheme()
  const { unreadCount } = useNotifications()
  const { logout } = useAuth()

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout()
    }
  }

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined style={{ fontSize: '16px' }} />,
      label: <Link to="/dashboard">Dashboard</Link>,
    },
    {
      key: 'emag-group',
      icon: <ApiOutlined style={{ fontSize: '16px' }} />,
      label: 'eMAG Integration',
      children: [
        {
          key: '/emag/sync-v2',
          icon: <CloudSyncOutlined />,
          label: (
            <span>
              <Link to="/emag/sync-v2">Product Sync V2</Link>
            </span>
          ),
        },
        {
          key: '/emag/publishing',
          icon: <CloudUploadOutlined />,
          label: <Link to="/emag/publishing">Product Publishing</Link>,
        },
        {
          key: '/emag/awb',
          icon: <TruckOutlined />,
          label: <Link to="/emag/awb">AWB Management</Link>,
        },
        {
          key: '/emag/ean',
          icon: <BarcodeOutlined />,
          label: <Link to="/emag/ean">EAN Matching</Link>,
        },
        {
          key: '/emag/invoices',
          icon: <FileTextOutlined />,
          label: <Link to="/emag/invoices">Invoices</Link>,
        },
        {
          key: '/emag/addresses',
          icon: <EnvironmentOutlined />,
          label: <Link to="/emag/addresses">Addresses</Link>,
        },
      ],
    },
    {
      key: 'products-group',
      icon: <ShoppingOutlined style={{ fontSize: '16px' }} />,
      label: 'Products',
      children: [
        {
          key: '/products',
          icon: <ShopOutlined />,
          label: <Link to="/products">Product Management</Link>,
        },
        {
          key: '/inventory',
          icon: <DatabaseOutlined />,
          label: (
            <span>
              <Link to="/inventory">Inventory & Low Stock</Link>
            </span>
          ),
        },
        {
          key: '/low-stock-suppliers',
          icon: <WarningOutlined />,
          label: (
            <span>
              <Link to="/low-stock-suppliers">Low Stock Suppliers</Link>
            </span>
          ),
        },
        {
          key: '/product-matching-suggestions',
          icon: <AppstoreOutlined />,
          label: (
            <span>
              <Link to="/product-matching-suggestions">Product Matching Suggestions</Link>
            </span>
          ),
        },
        {
          key: '/products/import',
          icon: <CloudUploadOutlined />,
          label: <Link to="/products/import">Import from Google Sheets</Link>,
        },
      ],
    },
    {
      key: '/orders',
      icon: <ShoppingCartOutlined style={{ fontSize: '16px' }} />,
      label: <Link to="/orders">Orders</Link>,
    },
    {
      key: '/customers',
      icon: <UsergroupAddOutlined style={{ fontSize: '16px' }} />,
      label: <Link to="/customers">Customers</Link>,
    },
    {
      key: 'suppliers-group',
      icon: <TeamOutlined style={{ fontSize: '16px' }} />,
      label: 'Suppliers',
      children: [
        {
          key: '/suppliers',
          icon: <TeamOutlined />,
          label: <Link to="/suppliers">Supplier List</Link>,
        },
        {
          key: '/suppliers/products',
          icon: <ShopOutlined />,
          label: <Link to="/suppliers/products">Supplier Products</Link>,
        },
        {
          key: '/suppliers/products-sheet',
          icon: <FileExcelOutlined />,
          label: <Link to="/suppliers/products-sheet">Products from Sheets</Link>,
        },
        {
          key: '/suppliers/matching',
          icon: <AppstoreOutlined />,
          label: <Link to="/suppliers/matching">Product Matching</Link>,
        },
      ],
    },
    {
      key: '/users',
      icon: <SafetyOutlined style={{ fontSize: '16px' }} />,
      label: <Link to="/users">Users</Link>,
    },
    {
      key: '/settings',
      icon: <SettingOutlined style={{ fontSize: '16px' }} />,
      label: <Link to="/settings">Settings</Link>,
    },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      danger: true,
    },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: collapsed ? '16px' : '18px',
            fontWeight: 'bold',
          }}
        >
          {collapsed ? 'MF' : 'MagFlow ERP'}
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
        />
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200 }}>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 1px 4px rgba(0,21,41,.08)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px' }}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Tooltip title="Notifications">
              <Badge count={unreadCount} size="small">
                <Button
                  type="text"
                  icon={<BellOutlined style={{ fontSize: '18px', color: '#1890ff' }} />}
                  onClick={() => setNotificationPanelVisible(true)}
                />
              </Badge>
            </Tooltip>

            <Tooltip title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
              <Switch
                checked={isDarkMode}
                onChange={toggleTheme}
                checkedChildren={<MoonOutlined />}
                unCheckedChildren={<SunOutlined />}
                style={{ backgroundColor: isDarkMode ? '#1890ff' : '#d9d9d9' }}
              />
            </Tooltip>

            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Avatar icon={<UserOutlined />} />
                <span style={{ fontWeight: 500 }}>Admin User</span>
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
            minHeight: 280,
          }}
        >
          {children}
        </Content>
      </AntLayout>
      
      <NotificationPanel
        visible={notificationPanelVisible}
        onClose={() => setNotificationPanelVisible(false)}
      />
    </AntLayout>
  )
}

export default Layout
