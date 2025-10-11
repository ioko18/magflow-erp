import React from 'react';
import { Table, Tag, Space, Button, Tooltip, Rate, Typography } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  GlobalOutlined,
  PhoneOutlined,
  MailOutlined,
  HolderOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface Supplier {
  id: number;
  name: string;
  country: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  lead_time_days: number;
  rating: number;
  is_active: boolean;
  total_orders: number;
  display_order?: number;
}

interface DraggableSuppliersTableProps {
  suppliers: Supplier[];
  loading: boolean;
  onEdit: (supplier: Supplier) => void;
  onDelete: (id: number) => void;
  onReorder: (suppliers: Supplier[]) => void;
}

interface RowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  'data-row-key': string;
}

const Row: React.FC<RowProps> = (props) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: props['data-row-key'],
  });

  const style: React.CSSProperties = {
    ...props.style,
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: 'move',
    ...(isDragging ? { position: 'relative', zIndex: 9999 } : {}),
  };

  return (
    <tr
      {...props}
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
    />
  );
};

const DraggableSuppliersTable: React.FC<DraggableSuppliersTableProps> = ({
  suppliers,
  loading,
  onEdit,
  onDelete,
  onReorder,
}) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = suppliers.findIndex((item) => item.id === Number(active.id));
      const newIndex = suppliers.findIndex((item) => item.id === Number(over.id));

      const newSuppliers = arrayMove(suppliers, oldIndex, newIndex);
      
      // Update display_order based on new position
      const updatedSuppliers = newSuppliers.map((supplier, index) => ({
        ...supplier,
        display_order: (index + 1) * 10, // 10, 20, 30, etc.
      }));

      onReorder(updatedSuppliers);
    }
  };

  const columns: ColumnsType<Supplier> = [
    {
      key: 'sort',
      width: 50,
      align: 'center',
      render: () => <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />,
    },
    {
      title: '#',
      key: 'order',
      width: 60,
      render: (_, __, index) => (
        <Text strong style={{ color: '#1890ff' }}>
          {index + 1}
        </Text>
      ),
    },
    {
      title: 'Furnizor',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: Supplier) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <GlobalOutlined /> {record.country}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Contact',
      key: 'contact',
      width: 200,
      render: (_, record: Supplier) => (
        <Space direction="vertical" size={0}>
          {record.contact_person && (
            <Text style={{ fontSize: '12px' }}>{record.contact_person}</Text>
          )}
          {record.email && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              <MailOutlined /> {record.email}
            </Text>
          )}
          {record.phone && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              <PhoneOutlined /> {record.phone}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Rating',
      dataIndex: 'rating',
      key: 'rating',
      width: 150,
      render: (rating: number) => <Rate disabled defaultValue={rating} style={{ fontSize: '14px' }} />,
    },
    {
      title: 'Lead Time',
      dataIndex: 'lead_time_days',
      key: 'lead_time_days',
      width: 100,
      render: (days: number) => <Tag color="blue">{days} zile</Tag>,
    },
    {
      title: 'Comenzi',
      dataIndex: 'total_orders',
      key: 'total_orders',
      width: 80,
      align: 'center',
      render: (total: number) => <Tag color="green">{total}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Activ' : 'Inactiv'}
        </Tag>
      ),
    },
    {
      title: 'Acțiuni',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record: Supplier) => (
        <Space size="small">
          <Tooltip title="Editează">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="Șterge">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record.id)}
              size="small"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={suppliers.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <Table
          components={{
            body: {
              row: Row,
            },
          }}
          rowKey="id"
          columns={columns}
          dataSource={suppliers}
          loading={loading}
          pagination={false}
          scroll={{ x: 1200 }}
        />
      </SortableContext>
    </DndContext>
  );
};

export default DraggableSuppliersTable;
