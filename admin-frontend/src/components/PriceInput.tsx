/**
 * PriceInput Component
 * 
 * Reusable component for price input with support for both dot and comma separators
 * Handles free editing while maintaining numeric value for backend
 */

import React from 'react';
import { Input, Space, Tag, Button, Alert } from 'antd';
import { SaveOutlined, CloseOutlined } from '@ant-design/icons';
import { usePriceInput } from '../hooks/usePriceInput';

export interface PriceInputProps {
  initialPrice: number;
  currency: string;
  onSave: (newPrice: number) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export const PriceInput: React.FC<PriceInputProps> = ({
  initialPrice,
  currency,
  onSave,
  onCancel,
  loading = false,
}) => {
  const priceInput = usePriceInput(initialPrice);
  const [saving, setSaving] = React.useState(false);

  const handleSave = async () => {
    if (!priceInput.isValid || priceInput.numericValue === initialPrice) {
      return;
    }

    try {
      setSaving(true);
      await onSave(priceInput.numericValue);
    } finally {
      setSaving(false);
    }
  };

  const priceChanged = priceInput.numericValue !== initialPrice;

  return (
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
      <Space size={8} style={{ width: '100%' }}>
        <Input
          size="middle"
          type="text"
          inputMode="decimal"
          value={priceInput.displayValue}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
            priceInput.handleChange(e.target.value);
          }}
          onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
            // Save on Enter key if price is valid and changed
            if (e.key === 'Enter' && priceChanged && priceInput.isValid) {
              handleSave();
            }
            // Cancel on Escape key
            if (e.key === 'Escape') {
              onCancel();
            }
          }}
          style={{
            width: 150,
            borderColor: !priceInput.isValid ? '#ff4d4f' : undefined,
          }}
          disabled={saving || loading}
          placeholder="Enter price (0.46 or 0,46)"
          autoFocus
          status={!priceInput.isValid ? 'error' : undefined}
        />
        <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
          {currency}
        </Tag>
      </Space>

      <Space size={8}>
        <Button
          type="primary"
          size="middle"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
          disabled={!priceChanged || !priceInput.isValid || loading}
        >
          Save Price
        </Button>
        <Button
          size="middle"
          icon={<CloseOutlined />}
          onClick={onCancel}
          disabled={saving || loading}
        >
          Cancel
        </Button>
      </Space>

      {priceChanged && priceInput.isValid && (
        <Alert
          message={
            <span>
              Original: <strong>{initialPrice.toFixed(2)} {currency}</strong> →
              New: <strong>{priceInput.numericValue.toFixed(2)} {currency}</strong>
              {' '}(Difference: <strong style={{
                color: priceInput.numericValue > initialPrice ? '#cf1322' : '#52c41a'
              }}>
                {priceInput.numericValue > initialPrice ? '+' : ''}{(priceInput.numericValue - initialPrice).toFixed(2)}
              </strong>)
            </span>
          }
          type="info"
          showIcon
        />
      )}

      {!priceInput.isValid && (
        <Alert
          message="Invalid price format. Use digits and one separator (. or ,)"
          type="error"
          showIcon
        />
      )}
    </Space>
  );
};

export default PriceInput;
