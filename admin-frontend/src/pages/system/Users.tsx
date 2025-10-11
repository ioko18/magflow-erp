import { useMemo } from 'react';
import { Card, Table, Tag, Typography, Space, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';

interface UserRecord {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'manager' | 'operator';
  status: 'active' | 'invited' | 'suspended';
}

const { Title, Text } = Typography;

export default function UsersPage() {
  const dataSource: UserRecord[] = useMemo(
    () => [
      { id: 1, name: 'Andrei Popescu', email: 'andrei.popescu@example.com', role: 'admin', status: 'active' },
      { id: 2, name: 'Ioana Marinescu', email: 'ioana.marinescu@example.com', role: 'manager', status: 'invited' },
      { id: 3, name: 'Mihai Georgescu', email: 'mihai.georgescu@example.com', role: 'operator', status: 'suspended' },
    ],
    []
  );

  const columns: ColumnsType<UserRecord> = useMemo(
    () => [
      {
        title: 'ID',
        dataIndex: 'id',
        sorter: (a, b) => a.id - b.id,
      },
      {
        title: 'Nume',
        dataIndex: 'name',
      },
      {
        title: 'Email',
        dataIndex: 'email',
      },
      {
        title: 'Rol',
        dataIndex: 'role',
        render: (role: UserRecord['role']) => {
          const labelMap = {
            admin: 'Administrator',
            manager: 'Manager',
            operator: 'Operator',
          } as const;
          const colorMap = {
            admin: 'magenta',
            manager: 'blue',
            operator: 'green',
          } as const;
          return <Tag color={colorMap[role]}>{labelMap[role]}</Tag>;
        },
      },
      {
        title: 'Status',
        dataIndex: 'status',
        render: (status: UserRecord['status']) => {
          const labelMap = {
            active: 'Activ',
            invited: 'Invitat',
            suspended: 'Suspendat',
          } as const;
          const colorMap = {
            active: 'success',
            invited: 'processing',
            suspended: 'error',
          } as const;
          return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
        },
      },
      {
        title: 'Acțiuni',
        key: 'actions',
        render: () => (
          <Space size="middle">
            <Button type="link" size="small" disabled>
              Editează
            </Button>
            <Button type="link" size="small" danger disabled>
              Dezactivează
            </Button>
          </Space>
        ),
      },
    ],
    []
  );

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 0 }}>
          Utilizatori
        </Title>
        <Text type="secondary">Gestionează accesul și rolurile membrilor echipei.</Text>
      </div>

      <Card title="Lista utilizatori">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={dataSource}
          pagination={{ pageSize: 5 }}
        />
      </Card>
    </Space>
  );
}
