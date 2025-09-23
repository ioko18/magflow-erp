import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import EmagSync from './pages/EmagSync'
import Products from './pages/Products'
import Users from './pages/Users'
import Settings from './pages/Settings'
import Login from './pages/Login'

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <Layout>
                <Dashboard />
              </Layout>
            } />
            <Route path="/dashboard" element={
              <Layout>
                <Dashboard />
              </Layout>
            } />
            <Route path="/emag" element={
              <Layout>
                <EmagSync />
              </Layout>
            } />
            <Route path="/products" element={
              <Layout>
                <Products />
              </Layout>
            } />
            <Route path="/users" element={
              <Layout>
                <Users />
              </Layout>
            } />
            <Route path="/settings" element={
              <Layout>
                <Settings />
              </Layout>
            } />
          </Routes>
        </div>
      </Router>
    </ConfigProvider>
  )
}

export default App
