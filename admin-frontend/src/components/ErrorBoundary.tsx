import { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Typography, Card } from 'antd';
import { BugOutlined, ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Log to external service (e.g., Sentry)
    // logErrorToService(error, errorInfo);
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{ 
          padding: '50px',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f0f2f5'
        }}>
          <Card style={{ maxWidth: 600, width: '100%' }}>
            <Result
              status="error"
              icon={<BugOutlined style={{ color: '#ff4d4f' }} />}
              title="Oops! Ceva nu a mers bine"
              subTitle="Ne pare rău, dar a apărut o eroare neașteptată. Echipa noastră a fost notificată."
              extra={[
                <Button 
                  type="primary" 
                  key="reload"
                  icon={<ReloadOutlined />}
                  onClick={this.handleReload}
                >
                  Reîncarcă Pagina
                </Button>,
                <Button 
                  key="home"
                  icon={<HomeOutlined />}
                  onClick={this.handleGoHome}
                >
                  Înapoi la Dashboard
                </Button>,
              ]}
            >
              {import.meta.env.DEV && this.state.error && (
                <div style={{ marginTop: 24, textAlign: 'left' }}>
                  <Paragraph>
                    <Text strong style={{ color: '#ff4d4f' }}>
                      Detalii Eroare (Development Mode):
                    </Text>
                  </Paragraph>
                  <Card 
                    size="small" 
                    style={{ 
                      background: '#fff1f0',
                      border: '1px solid #ffccc7',
                      marginBottom: 16
                    }}
                  >
                    <Paragraph style={{ marginBottom: 8 }}>
                      <Text code>{this.state.error.toString()}</Text>
                    </Paragraph>
                    {this.state.errorInfo && (
                      <Paragraph style={{ marginBottom: 0 }}>
                        <Text code style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>
                          {this.state.errorInfo.componentStack}
                        </Text>
                      </Paragraph>
                    )}
                  </Card>
                  <Button 
                    size="small" 
                    onClick={this.handleReset}
                  >
                    Încearcă din nou
                  </Button>
                </div>
              )}
            </Result>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
