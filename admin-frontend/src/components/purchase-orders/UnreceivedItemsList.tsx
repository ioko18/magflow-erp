/**
 * Unreceived Items List Component
 * Displays list of unreceived items from purchase orders
 */

import React, { useState, useEffect } from 'react';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import type { UnreceivedItem, UnreceivedItemStatus, UnreceivedItemsListParams } from '../../types/purchaseOrder';

export const UnreceivedItemsList: React.FC = () => {
  const [items, setItems] = useState<UnreceivedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    total: 0,
    skip: 0,
    limit: 20,
    has_more: false,
  });

  const [filters, setFilters] = useState<UnreceivedItemsListParams>({
    skip: 0,
    limit: 20,
  });

  const [showResolveModal, setShowResolveModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<UnreceivedItem | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    loadItems();
  }, [filters]);

  const loadItems = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await purchaseOrdersApi.getUnreceivedItems(filters);
      
      if (response.status === 'success' && response.data) {
        setItems(response.data.items);
        setPagination(response.data.pagination);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load unreceived items');
      console.error('Error loading unreceived items:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedItem || !resolutionNotes.trim()) return;

    try {
      await purchaseOrdersApi.resolveUnreceivedItem(selectedItem.id, {
        resolution_notes: resolutionNotes,
        resolved_by: 1, // TODO: Get from current user
      });
      
      setShowResolveModal(false);
      setSelectedItem(null);
      setResolutionNotes('');
      loadItems();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to resolve item');
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ro-RO');
  };

  const getStatusBadge = (status: UnreceivedItemStatus) => {
    const config = {
      pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-800' },
      partial: { label: 'Partial', color: 'bg-blue-100 text-blue-800' },
      resolved: { label: 'Resolved', color: 'bg-green-100 text-green-800' },
      cancelled: { label: 'Cancelled', color: 'bg-red-100 text-red-800' },
    };

    const { label, color } = config[status];
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
        {label}
      </span>
    );
  };

  if (loading && items.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading unreceived items...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Unreceived Items</h1>
        <p className="text-gray-600 mt-2">Track and manage items that haven't been fully received</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onChange={(e) => setFilters({ ...filters, status: e.target.value as UnreceivedItemStatus || undefined, skip: 0 })}
              value={filters.status || ''}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="partial">Partial</option>
              <option value="resolved">Resolved</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {/* Clear Filters */}
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ skip: 0, limit: 20 })}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Items Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ordered</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Received</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unreceived</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expected</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                  No unreceived items found. All orders are fully received!
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {item.product?.name || `Product ${item.product_id}`}
                    </div>
                    {item.product?.sku && (
                      <div className="text-sm text-gray-500">{item.product.sku}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    PO-{item.purchase_order_id}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{item.ordered_quantity}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">{item.received_quantity}</td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-semibold text-red-600">
                      {item.unreceived_quantity}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(item.expected_date)}
                  </td>
                  <td className="px-6 py-4">{getStatusBadge(item.status)}</td>
                  <td className="px-6 py-4 text-sm font-medium">
                    {item.status === 'pending' && (
                      <button
                        onClick={() => {
                          setSelectedItem(item);
                          setShowResolveModal(true);
                        }}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination.total > 0 && (
        <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6 mt-4 rounded-lg shadow">
          <div className="flex-1 flex justify-between sm:hidden">
            <button
              onClick={() => setFilters({ ...filters, skip: Math.max(0, filters.skip! - filters.limit!) })}
              disabled={filters.skip === 0}
              className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setFilters({ ...filters, skip: filters.skip! + filters.limit! })}
              disabled={!pagination.has_more}
              className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{filters.skip! + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(filters.skip! + filters.limit!, pagination.total)}
                </span>{' '}
                of <span className="font-medium">{pagination.total}</span> results
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  onClick={() => setFilters({ ...filters, skip: Math.max(0, filters.skip! - filters.limit!) })}
                  disabled={filters.skip === 0}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setFilters({ ...filters, skip: filters.skip! + filters.limit! })}
                  disabled={!pagination.has_more}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {showResolveModal && selectedItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Resolve Unreceived Item</h3>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                Product: <span className="font-medium">{selectedItem.product?.name}</span>
              </p>
              <p className="text-sm text-gray-600 mb-4">
                Unreceived Quantity: <span className="font-medium text-red-600">{selectedItem.unreceived_quantity}</span>
              </p>
              
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resolution Notes *
              </label>
              <textarea
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Explain how this was resolved (e.g., refund issued, replacement sent, etc.)"
                required
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowResolveModal(false);
                  setSelectedItem(null);
                  setResolutionNotes('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleResolve}
                disabled={!resolutionNotes.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
              >
                Resolve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnreceivedItemsList;
