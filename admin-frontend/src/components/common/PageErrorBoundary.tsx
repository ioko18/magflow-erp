/**
 * Page-level Error Boundary
 * 
 * Lighter error boundary for individual pages
 */

import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { ErrorBoundary } from './ErrorBoundary';

interface PageErrorBoundaryProps {
  children: React.ReactNode;
}

const PageErrorFallback: React.FC<{ error: Error }> = ({ error }) => {
  const navigate = useNavigate();

  return (
    <div style={{ padding: '50px 20px', textAlign: 'center' }}>
      <Result
        status="500"
        title="Eroare la încărcarea paginii"
        subTitle={
          import.meta.env.DEV
            ? error.message
            : 'Ne pare rău, această pagină nu poate fi încărcată momentan.'
        }
        extra={[
          <Button type="primary" key="back" onClick={() => navigate(-1)}>
            Înapoi
          </Button>,
          <Button key="home" onClick={() => navigate('/')}>
            Pagina principală
          </Button>,
        ]}
      />
    </div>
  );
};

export const PageErrorBoundary: React.FC<PageErrorBoundaryProps> = ({ children }) => {
  return (
    <ErrorBoundary
      fallback={<PageErrorFallback error={new Error('Page error')} />}
    >
      {children}
    </ErrorBoundary>
  );
};
