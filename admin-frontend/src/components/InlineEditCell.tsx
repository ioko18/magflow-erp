import { useState, useEffect, useRef } from 'react';
import { InputNumber, Input, Select, message } from 'antd';
import { CheckOutlined, CloseOutlined, EditOutlined } from '@ant-design/icons';

const { Option } = Select;

interface InlineEditCellProps {
  value: string | number;
  type: 'text' | 'number' | 'select';
  options?: { label: string; value: string | number }[];
  onSave: (value: string | number) => Promise<void>;
  min?: number;
  max?: number;
  precision?: number;
  placeholder?: string;
  disabled?: boolean;
}

export default function InlineEditCell({
  value: initialValue,
  type,
  options = [],
  onSave,
  min,
  max,
  precision = 0,
  placeholder,
  disabled = false,
}: InlineEditCellProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initialValue);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<any>(null);

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editing]);

  const handleSave = async () => {
    if (value === initialValue) {
      setEditing(false);
      return;
    }

    try {
      setLoading(true);
      await onSave(value);
      message.success('Actualizat cu succes!');
      setEditing(false);
    } catch (error: any) {
      console.error('Error saving:', error);
      message.error(error.response?.data?.detail || 'Eroare la salvare');
      setValue(initialValue); // Revert on error
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setValue(initialValue);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (!editing) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          cursor: disabled ? 'not-allowed' : 'pointer',
          padding: '4px 8px',
          borderRadius: 4,
          transition: 'background-color 0.2s',
        }}
        onMouseEnter={(e) => {
          if (!disabled) {
            e.currentTarget.style.backgroundColor = '#f0f0f0';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
        onClick={() => !disabled && setEditing(true)}
      >
        <span>{value}</span>
        {!disabled && (
          <EditOutlined
            style={{
              fontSize: 12,
              color: '#999',
              opacity: 0.6,
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {type === 'number' && (
        <InputNumber
          ref={inputRef}
          value={value as number}
          onChange={(val) => setValue(val || 0)}
          onKeyDown={handleKeyDown}
          min={min}
          max={max}
          precision={precision}
          style={{ width: 100 }}
          disabled={loading}
        />
      )}
      {type === 'text' && (
        <Input
          ref={inputRef}
          value={value as string}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          style={{ width: 150 }}
          disabled={loading}
        />
      )}
      {type === 'select' && (
        <Select
          ref={inputRef}
          value={value}
          onChange={(val) => setValue(val)}
          style={{ width: 120 }}
          disabled={loading}
        >
          {options.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      )}
      <CheckOutlined
        style={{
          color: '#52c41a',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 14,
        }}
        onClick={!loading ? handleSave : undefined}
      />
      <CloseOutlined
        style={{
          color: '#ff4d4f',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 14,
        }}
        onClick={!loading ? handleCancel : undefined}
      />
    </div>
  );
}
