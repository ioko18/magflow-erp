/**
 * Loading States Components
 * 
 * Reusable loading indicators and skeleton screens
 */

import React from 'react';
import { Spin, Skeleton, Card } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

/**
 * Full page loading spinner
 */
export const PageLoader: React.FC<{ message?: string }> = ({ message = 'Se încarcă...' }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      <Spin size="large" indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      <div style={{ color: '#666', fontSize: '16px' }}>{message}</div>
    </div>
  );
};

/**
 * Content loading spinner
 */
export const ContentLoader: React.FC<{ message?: string; size?: 'small' | 'default' | 'large' }> = ({ 
  message = 'Se încarcă...', 
  size = 'default' 
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '50px 20px',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      <Spin size={size} />
      <div style={{ color: '#666' }}>{message}</div>
    </div>
  );
};

/**
 * Inline loading spinner
 */
export const InlineLoader: React.FC = () => {
  return <Spin size="small" style={{ marginLeft: '8px' }} />;
};

/**
 * Table skeleton
 */
export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div style={{ padding: '20px' }}>
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} active paragraph={{ rows: 1 }} style={{ marginBottom: '16px' }} />
      ))}
    </div>
  );
};

/**
 * Card skeleton
 */
export const CardSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index}>
          <Skeleton active />
        </Card>
      ))}
    </div>
  );
};

/**
 * Form skeleton
 */
export const FormSkeleton: React.FC<{ fields?: number }> = ({ fields = 5 }) => {
  return (
    <div style={{ padding: '20px' }}>
      {Array.from({ length: fields }).map((_, index) => (
        <div key={index} style={{ marginBottom: '24px' }}>
          <Skeleton.Input active style={{ width: '100%', marginBottom: '8px' }} />
          <Skeleton.Input active style={{ width: '100%', height: '40px' }} />
        </div>
      ))}
    </div>
  );
};

/**
 * List skeleton
 */
export const ListSkeleton: React.FC<{ items?: number }> = ({ items = 5 }) => {
  return (
    <div style={{ padding: '20px' }}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} style={{ marginBottom: '16px', display: 'flex', gap: '16px' }}>
          <Skeleton.Avatar active size="large" />
          <div style={{ flex: 1 }}>
            <Skeleton active paragraph={{ rows: 2 }} />
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * Dashboard skeleton
 */
export const DashboardSkeleton: React.FC = () => {
  return (
    <div style={{ padding: '20px' }}>
      {/* Stats cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index}>
            <Skeleton active paragraph={{ rows: 1 }} />
          </Card>
        ))}
      </div>
      
      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        {Array.from({ length: 2 }).map((_, index) => (
          <Card key={index}>
            <Skeleton active paragraph={{ rows: 6 }} />
          </Card>
        ))}
      </div>
    </div>
  );
};

/**
 * Suspense fallback
 */
export const SuspenseFallback: React.FC<{ type?: 'page' | 'content' }> = ({ type = 'content' }) => {
  if (type === 'page') {
    return <PageLoader />;
  }
  return <ContentLoader />;
};
