/**
 * Receive Order Modal Component
 * Modal for receiving purchase order items
 */

import React, { useState } from 'react';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import type { PurchaseOrder } from '../../types/purchaseOrder';

interface ReceiveOrderModalProps {
  order: PurchaseOrder;
  onClose: () => void;
  onSuccess: () => void;
}

export const ReceiveOrderModal: React.FC<ReceiveOrderModalProps> = ({
  order,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receiptDate, setReceiptDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [receivedQuantities, setReceivedQuantities] = useState<Record<number, number>>(
    order.lines.reduce((acc, line) => {
      if (line.id) {
        acc[line.id] = line.quantity - (line.received_quantity || 0);
      }
      return acc;
    }, {} as Record<number, number>)
  );
  const [lineNotes, setLineNotes] = useState<Record<number, string>>({});

  const updateReceivedQuantity = (lineId: number, quantity: number) => {
    setReceivedQuantities({
      ...receivedQuantities,
      [lineId]: quantity,
    });
  };

  const updateLineNotes = (lineId: number, note: string) => {
    setLineNotes({
      ...lineNotes,
      [lineId]: note,
    });
  };

  const validateQuantities = (): string | null => {
    for (const line of order.lines) {
      if (!line.id) continue;
      
      const receivedQty = receivedQuantities[line.id] || 0;
      const pendingQty = line.quantity - (line.received_quantity || 0);
      
      if (receivedQty < 0) {
        return `Received quantity cannot be negative for ${line.product?.name || 'product'}`;
      }
      
      if (receivedQty > pendingQty) {
        return `Received quantity (${receivedQty}) cannot exceed pending quantity (${pendingQty}) for ${line.product?.name || 'product'}`;
      }
    }
    
    const totalReceived = Object.values(receivedQuantities).reduce((sum, qty) => sum + qty, 0);
    if (totalReceived === 0) {
      return 'Please enter at least one received quantity';
    }
    
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationError = validateQuantities();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const lines = order.lines
        .filter(line => line.id && receivedQuantities[line.id] > 0)
        .map(line => ({
          purchase_order_line_id: line.id!,
          received_quantity: receivedQuantities[line.id!],
          notes: lineNotes[line.id!] || undefined,
        }));

      await purchaseOrdersApi.receive(order.id!, {
        receipt_date: receiptDate,
        lines,
        notes: notes || undefined,
      });

      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to receive order');
      console.error('Error receiving order:', err);
    } finally {
      setLoading(false);
    }
  };

  const getTotalReceived = () => {
    return Object.values(receivedQuantities).reduce((sum, qty) => sum + qty, 0);
  };

  const getTotalPending = () => {
    return order.lines.reduce((sum, line) => {
      return sum + (line.quantity - (line.received_quantity || 0));
    }, 0);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Receive Order</h2>
              <p className="text-sm text-gray-600">Order: {order.order_number}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              disabled={loading}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4">
            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}

            {/* Receipt Date */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Receipt Date *
              </label>
              <input
                type="date"
                value={receiptDate}
                onChange={(e) => setReceiptDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            {/* Order Lines */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-4">Products to Receive</h3>
              
              <div className="space-y-4">
                {order.lines.map((line) => {
                  const pendingQty = line.quantity - (line.received_quantity || 0);
                  const receivedQty = line.id ? (receivedQuantities[line.id] || 0) : 0;
                  
                  return (
                    <div key={line.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900">
                            {line.product?.name || `Product ${line.product_id}`}
                          </h4>
                          {line.product?.sku && (
                            <p className="text-sm text-gray-500">SKU: {line.product.sku}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-600">
                            Ordered: <span className="font-medium">{line.quantity}</span>
                          </div>
                          <div className="text-sm text-gray-600">
                            Already Received: <span className="font-medium">{line.received_quantity || 0}</span>
                          </div>
                          <div className="text-sm font-semibold text-blue-600">
                            Pending: {pendingQty}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Received Quantity */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Received Quantity *
                          </label>
                          <input
                            type="number"
                            min="0"
                            max={pendingQty}
                            value={receivedQty}
                            onChange={(e) => line.id && updateReceivedQuantity(line.id, Number(e.target.value))}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                          {receivedQty > 0 && receivedQty < pendingQty && (
                            <p className="text-xs text-yellow-600 mt-1">
                              ⚠️ Partial receipt: {pendingQty - receivedQty} items will remain pending
                            </p>
                          )}
                        </div>

                        {/* Line Notes */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Notes (optional)
                          </label>
                          <input
                            type="text"
                            value={line.id ? (lineNotes[line.id] || '') : ''}
                            onChange={(e) => line.id && updateLineNotes(line.id, e.target.value)}
                            placeholder="e.g., damaged items, quality issues"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Summary */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div className="flex justify-between items-center">
                <div>
                  <div className="text-sm text-gray-600">Total Pending</div>
                  <div className="text-2xl font-bold text-gray-900">{getTotalPending()}</div>
                </div>
                <div className="text-4xl text-gray-300">→</div>
                <div>
                  <div className="text-sm text-gray-600">Receiving Now</div>
                  <div className="text-2xl font-bold text-blue-600">{getTotalReceived()}</div>
                </div>
                <div className="text-4xl text-gray-300">=</div>
                <div>
                  <div className="text-sm text-gray-600">Will Remain Pending</div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {getTotalPending() - getTotalReceived()}
                  </div>
                </div>
              </div>
            </div>

            {/* General Notes */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                General Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Add any general notes about this receipt..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              disabled={loading || getTotalReceived() === 0}
            >
              {loading ? 'Receiving...' : 'Receive Items'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReceiveOrderModal;
