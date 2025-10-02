import React, { useState } from 'react';
import {
  Input,
  InputNumber,
  Typography,
  Space,
  Button,
  Tooltip,
  message,
  Modal,
  Form,
} from 'antd';
import {
  EditOutlined,
  CloseOutlined,
  CheckOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import api from '../services/api';

const { Text } = Typography;
const { TextArea } = Input;

interface ProductFieldEditorProps {
  productId: number;
  fieldName: string;
  fieldLabel: string;
  value: string | number | null | undefined;
  type?: 'text' | 'number' | 'textarea';
  maxLength?: number;
  min?: number;
  max?: number;
  prefix?: string;
  suffix?: string;
  placeholder?: string;
  onUpdate?: () => void;
  showHistory?: boolean;
  onShowHistory?: () => void;
  validateSKU?: boolean; // Special validation for SKU changes
}

const ProductFieldEditor: React.FC<ProductFieldEditorProps> = ({
  productId,
  fieldName,
  fieldLabel,
  value,
  type = 'text',
  maxLength,
  min,
  max,
  prefix,
  suffix,
  placeholder,
  onUpdate,
  showHistory = false,
  onShowHistory,
  validateSKU = false,
}) => {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState<string | number | null>(value ?? null);
  const [loading, setLoading] = useState(false);
  const [changeReason, setChangeReason] = useState('');
  const [showReasonModal, setShowReasonModal] = useState(false);

  const handleStartEdit = () => {
    setEditValue(value ?? null);
    setEditing(true);
  };

  const handleCancel = () => {
    setEditValue(value ?? null);
    setEditing(false);
    setChangeReason('');
  };

  const performUpdate = async (reason?: string) => {
    if (editValue === value) {
      setEditing(false);
      return;
    }

    setLoading(true);
    try {
      const updateData: any = {
        [fieldName]: editValue,
      };

      if (reason) {
        updateData.change_reason = reason;
      }

      await api.patch(`/products/${productId}`, updateData);

      message.success(`${fieldLabel} actualizat cu succes!`);
      setEditing(false);
      setChangeReason('');
      setShowReasonModal(false);

      if (onUpdate) {
        onUpdate();
      }
    } catch (error: any) {
      console.error('Error updating field:', error);
      const errorMsg = error.response?.data?.detail || `Eroare la actualizarea ${fieldLabel}`;
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    // For SKU changes, always ask for reason
    if (validateSKU && fieldName === 'sku' && editValue !== value) {
      setShowReasonModal(true);
    } else {
      performUpdate();
    }
  };

  const handleReasonSubmit = () => {
    if (!changeReason.trim()) {
      message.warning('Vă rugăm să introduceți un motiv pentru schimbarea SKU-ului');
      return;
    }
    performUpdate(changeReason);
  };

  const displayValue = value ?? '-';

  if (!editing) {
    return (
      <Space>
        <Text>{displayValue}</Text>
        <Tooltip title={`Editează ${fieldLabel}`}>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={handleStartEdit}
          />
        </Tooltip>
        {showHistory && onShowHistory && (
          <Tooltip title="Vezi istoric">
            <Button
              type="text"
              size="small"
              icon={<HistoryOutlined />}
              onClick={onShowHistory}
            />
          </Tooltip>
        )}
      </Space>
    );
  }

  return (
    <>
      <Space.Compact style={{ width: '100%' }}>
        {type === 'number' ? (
          <InputNumber
            value={editValue as number}
            onChange={(val) => setEditValue(val)}
            min={min}
            max={max}
            prefix={prefix}
            suffix={suffix}
            placeholder={placeholder}
            style={{ width: '100%' }}
            autoFocus
            onPressEnter={handleSave}
          />
        ) : type === 'textarea' ? (
          <TextArea
            value={editValue as string}
            onChange={(e) => setEditValue(e.target.value)}
            maxLength={maxLength}
            placeholder={placeholder}
            autoSize={{ minRows: 2, maxRows: 6 }}
            autoFocus
          />
        ) : (
          <Input
            value={editValue as string}
            onChange={(e) => setEditValue(e.target.value)}
            maxLength={maxLength}
            prefix={prefix}
            suffix={suffix}
            placeholder={placeholder}
            autoFocus
            onPressEnter={handleSave}
          />
        )}

        <Button
          type="primary"
          icon={<CheckOutlined />}
          onClick={handleSave}
          loading={loading}
        />
        <Button
          icon={<CloseOutlined />}
          onClick={handleCancel}
          disabled={loading}
        />
      </Space.Compact>

      {/* SKU Change Reason Modal */}
      <Modal
        title="Motiv schimbare SKU"
        open={showReasonModal}
        onOk={handleReasonSubmit}
        onCancel={() => {
          setShowReasonModal(false);
          setChangeReason('');
        }}
        okText="Salvează"
        cancelText="Anulează"
        okButtonProps={{ loading }}
      >
        <Form layout="vertical">
          <Form.Item
            label="De ce schimbați SKU-ul acestui produs?"
            required
            help="Această informație va fi salvată în istoricul produsului"
          >
            <TextArea
              value={changeReason}
              onChange={(e) => setChangeReason(e.target.value)}
              placeholder="Ex: Corecție eroare, Reorganizare catalog, etc."
              rows={4}
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ProductFieldEditor;
