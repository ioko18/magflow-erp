/**
 * Purchase Order Details Component
 * Displays detailed information about a purchase order
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import PurchaseOrderStatusBadge from './PurchaseOrderStatusBadge';
import type { PurchaseOrder, PurchaseOrderHistory, PurchaseOrderStatus } from '../../types/purchaseOrder';

export const PurchaseOrderDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [history, setHistory] = useState<PurchaseOrderHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState<PurchaseOrderStatus>('draft');
  const [statusNotes, setStatusNotes] = useState('');

  useEffect(() => {
    if (id) {
      loadOrderDetails();
      loadOrderHistory();
    }
  }, [id]);

  const loadOrderDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await purchaseOrdersApi.get(Number(id));
      
      if (response.status === 'success' && response.data) {
        // API returns data directly, not wrapped in purchase_order
        setOrder(response.data as any);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to load purchase order');
      console.error('Error loading purchase order:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadOrderHistory = async () => {
    try {
      const response = await purchaseOrdersApi.getHistory(Number(id));
      if (response.status === 'success' && response.data) {
        setHistory(response.data.history);
      }
    } catch (err) {
      console.error('Error loading history:', err);
    }
  };

  const handleUpdateStatus = async () => {
    if (!order) return;

    try {
      await purchaseOrdersApi.updateStatus(order.id!, {
        status: newStatus,  // Backend expects 'status', not 'new_status'
        notes: statusNotes || undefined,
      });
      
      setShowStatusModal(false);
      setStatusNotes('');
      loadOrderDetails();
      loadOrderHistory();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to update status');
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ro-RO', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('ro-RO');
  };

  const formatCurrency = (amount: number, currency: string = 'RON') => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading purchase order...</div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Purchase order not found'}
        </div>
        <button
          onClick={() => navigate('/purchase-orders')}
          className="mt-4 text-blue-600 hover:text-blue-800"
        >
          ← Back to List
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <button
            onClick={() => navigate('/purchase-orders')}
            className="text-gray-600 hover:text-gray-900 mb-2"
          >
            ← Back to List
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            Purchase Order {order.order_number}
          </h1>
        </div>
        <div className="flex space-x-3">
          {order.status === 'confirmed' && (
            <button
              onClick={() => navigate(`/purchase-orders/${id}/receive`)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Receive Order
            </button>
          )}
          <button
            onClick={() => setShowStatusModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Update Status
          </button>
        </div>
      </div>

      {/* Basic Information */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-semibold">Order Information</h2>
          <PurchaseOrderStatusBadge status={order.status} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-500">Supplier</div>
            <div className="font-medium">{order.supplier?.name || '-'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Order Date</div>
            <div className="font-medium">{formatDate(order.order_date)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Expected Delivery</div>
            <div className="font-medium">{formatDate(order.expected_delivery_date)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Actual Delivery</div>
            <div className="font-medium">{formatDate(order.actual_delivery_date)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Currency</div>
            <div className="font-medium">{order.currency}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Payment Terms</div>
            <div className="font-medium">{order.payment_terms || '-'}</div>
          </div>
          {order.delivery_address && (
            <div className="md:col-span-2">
              <div className="text-sm text-gray-500">Delivery Address</div>
              <div className="font-medium">{order.delivery_address}</div>
            </div>
          )}
          {order.tracking_number && (
            <div>
              <div className="text-sm text-gray-500">Tracking Number</div>
              <div className="font-medium">{order.tracking_number}</div>
            </div>
          )}
        </div>

        {order.notes && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-500 mb-1">Notes</div>
            <div className="text-gray-900">{order.notes}</div>
          </div>
        )}
      </div>

      {/* Order Lines */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Order Lines</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Received</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unit Cost</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Line Total</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {order.lines.map((line, index) => (
                <tr key={index}>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {line.product?.name || `Product ${line.product_id}`}
                    </div>
                    {line.product?.sku && (
                      <div className="text-sm text-gray-500">{line.product.sku}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{line.quantity}</td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {line.received_quantity || 0}
                      {line.received_quantity !== line.quantity && (
                        <span className="ml-2 text-yellow-600">
                          ({line.quantity - (line.received_quantity || 0)} pending)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {formatCurrency(line.unit_cost, order.currency)}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {formatCurrency(line.line_total || (line.quantity * line.unit_cost), order.currency)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={4} className="px-6 py-4 text-right font-semibold">Total Amount:</td>
                <td className="px-6 py-4 text-lg font-bold text-blue-600">
                  {formatCurrency(order.total_amount, order.currency)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Order History</h2>
          
          <div className="space-y-4">
            {history.map((entry) => (
              <div key={entry.id} className="border-l-4 border-blue-500 pl-4 py-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-gray-900">{entry.action}</div>
                    {entry.old_status && entry.new_status && (
                      <div className="text-sm text-gray-600">
                        Status changed from <span className="font-medium">{entry.old_status}</span> to{' '}
                        <span className="font-medium">{entry.new_status}</span>
                      </div>
                    )}
                    {entry.notes && (
                      <div className="text-sm text-gray-600 mt-1">{entry.notes}</div>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatDateTime(entry.changed_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Update Status Modal */}
      {showStatusModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Update Order Status</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                New Status
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value as PurchaseOrderStatus)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="confirmed">Confirmed</option>
                <option value="partially_received">Partially Received</option>
                <option value="received">Received</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notes (optional)
              </label>
              <textarea
                value={statusNotes}
                onChange={(e) => setStatusNotes(e.target.value)}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Add notes about this status change..."
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowStatusModal(false);
                  setStatusNotes('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateStatus}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Update Status
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PurchaseOrderDetails;
