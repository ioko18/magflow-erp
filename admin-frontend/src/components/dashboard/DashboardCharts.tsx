import { Card, Row, Col, Empty } from 'antd';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface SalesData {
  name: string;
  sales: number;
  orders: number;
  profit: number;
}

interface TopProduct {
  name: string;
  value: number;
  sales: number;
}

interface InventoryStatus {
  category: string;
  inStock: number;
  lowStock: number;
  outOfStock: number;
}

interface DashboardChartsProps {
  salesData?: SalesData[];
  topProducts?: TopProduct[];
  inventoryStatus?: InventoryStatus[];
}

const DashboardCharts: React.FC<DashboardChartsProps> = ({
  salesData = [],
  topProducts = [],
  inventoryStatus = [],
}) => {
  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'RON',
      minimumFractionDigits: 0,
    }).format(value);
  };

  // Custom tooltip for sales chart
  const SalesTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'white',
          padding: '10px',
          border: '1px solid #ccc',
          borderRadius: '4px',
        }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>{payload[0].payload.name}</p>
          <p style={{ margin: '5px 0 0 0', color: '#1890ff' }}>
            Vânzări: {formatCurrency(payload[0].value)}
          </p>
          <p style={{ margin: '5px 0 0 0', color: '#52c41a' }}>
            Comenzi: {payload[1]?.value || 0}
          </p>
        </div>
      );
    }
    return null;
  };

  // Prepare inventory pie chart data
  const inventoryPieData = inventoryStatus.length > 0 ? [
    { name: 'În Stoc', value: inventoryStatus[0].inStock, color: '#52c41a' },
    { name: 'Stoc Redus', value: inventoryStatus[0].lowStock, color: '#faad14' },
    { name: 'Fără Stoc', value: inventoryStatus[0].outOfStock, color: '#ff4d4f' },
  ] : [];

  return (
    <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
      {/* Sales Trend Chart */}
      <Col xs={24} lg={16}>
        <Card 
          title="Tendință Vânzări (Ultimele 6 Luni)"
          variant="borderless"
          style={{ height: '100%' }}
        >
          {salesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={salesData}>
                <defs>
                  <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1890ff" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#1890ff" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorOrders" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#52c41a" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#52c41a" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip content={<SalesTooltip />} />
                <Legend />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="sales"
                  stroke="#1890ff"
                  fillOpacity={1}
                  fill="url(#colorSales)"
                  name="Vânzări (RON)"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="orders"
                  stroke="#52c41a"
                  fillOpacity={1}
                  fill="url(#colorOrders)"
                  name="Comenzi"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="Nu există date disponibile" />
          )}
        </Card>
      </Col>

      {/* Inventory Status Pie Chart */}
      <Col xs={24} lg={8}>
        <Card 
          title="Status Inventar"
          variant="borderless"
          style={{ height: '100%' }}
        >
          {inventoryPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={inventoryPieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {inventoryPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="Nu există date disponibile" />
          )}
        </Card>
      </Col>

      {/* Top Products Bar Chart */}
      <Col xs={24}>
        <Card 
          title="Top 5 Produse după Stoc"
          variant="borderless"
        >
          {topProducts.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topProducts}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name" 
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis />
                <Tooltip 
                  formatter={(value: number, name: string) => {
                    if (name === 'sales') {
                      return [formatCurrency(value), 'Valoare'];
                    }
                    return [value, 'Cantitate'];
                  }}
                />
                <Legend />
                <Bar dataKey="value" fill="#1890ff" name="Cantitate în Stoc" />
                <Bar dataKey="sales" fill="#52c41a" name="Valoare (RON)" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="Nu există date disponibile" />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default DashboardCharts;
