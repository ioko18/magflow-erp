/**
 * Purchase Order Form Component
 * Form for creating new purchase orders
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import { apiClient } from '../../api/client';
import type { CreatePurchaseOrderRequest, PurchaseOrderLine } from '../../types/purchaseOrder';

interface Supplier {
  id: number;
  name: string;
  email?: string;
  phone?: string;
}

interface Product {
  id: number;
  name: string;
  sku: string;
  base_price?: number;
  recommended_price?: number;
}

export const PurchaseOrderForm: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form data
  const [supplierId, setSupplierId] = useState<number | null>(null);
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState('');
  const [currency, setCurrency] = useState('RON');
  const [paymentTerms, setPaymentTerms] = useState('');
  const [notes, setNotes] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [lines, setLines] = useState<Array<Omit<PurchaseOrderLine, 'id'>>>([
    {
      product_id: 0,
      quantity: 1,
      unit_cost: 0,
      discount_percent: 0,
      tax_percent: 19,
    },
  ]);

  // Mock data - replace with actual API calls
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    // Load suppliers and products
    // TODO: Replace with actual API calls
    loadSuppliers();
    loadProducts();
  }, []);

  const loadSuppliers = async () => {
    try {
      const response = await apiClient.suppliers.list({ skip: 0, limit: 1000 });
      if (response.status === 'success' && response.data) {
        setSuppliers(response.data.suppliers || response.data);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
      // Fallback to empty array
      setSuppliers([]);
    }
  };

  const loadProducts = async () => {
    try {
      const response = await apiClient.products.list({ skip: 0, limit: 1000 });
      if (response.status === 'success' && response.data) {
        setProducts(response.data.products || response.data);
      }
    } catch (error) {
      console.error('Error loading products:', error);
      // Fallback to empty array
      setProducts([]);
    }
  };

  const addLine = () => {
    setLines([
      ...lines,
      {
        product_id: 0,
        quantity: 1,
        unit_cost: 0,
        discount_percent: 0,
        tax_percent: 19,
      },
    ]);
  };

  const removeLine = (index: number) => {
    if (lines.length > 1) {
      setLines(lines.filter((_, i) => i !== index));
    }
  };

  const updateLine = (index: number, field: keyof PurchaseOrderLine, value: any) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setLines(newLines);
  };

  const calculateLineTotal = (line: Omit<PurchaseOrderLine, 'id'>) => {
    const subtotal = line.quantity * line.unit_cost;
    const discount = subtotal * ((line.discount_percent || 0) / 100);
    const afterDiscount = subtotal - discount;
    const tax = afterDiscount * ((line.tax_percent || 0) / 100);
    return afterDiscount + tax;
  };

  const calculateTotal = () => {
    return lines.reduce((sum, line) => sum + calculateLineTotal(line), 0);
  };

  const validateForm = (): string | null => {
    if (!supplierId) return 'Please select a supplier';
    if (!orderDate) return 'Please select an order date';
    if (lines.length === 0) return 'Please add at least one product';
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.product_id) return `Please select a product for line ${i + 1}`;
      if (line.quantity <= 0) return `Quantity must be greater than 0 for line ${i + 1}`;
      if (line.unit_cost <= 0) return `Unit cost must be greater than 0 for line ${i + 1}`;
    }
    
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data: CreatePurchaseOrderRequest = {
        supplier_id: supplierId!,
        order_date: orderDate,
        expected_delivery_date: expectedDeliveryDate || undefined,
        currency,
        payment_terms: paymentTerms || undefined,
        notes: notes || undefined,
        delivery_address: deliveryAddress || undefined,
        lines: lines.map(line => ({
          product_id: line.product_id,
          quantity: line.quantity,
          unit_cost: line.unit_cost,
          discount_percent: line.discount_percent,
          tax_percent: line.tax_percent,
          notes: line.notes,
        })),
      };

      const response = await purchaseOrdersApi.create(data);
      
      if (response.status === 'success') {
        setSuccess(true);
        setTimeout(() => {
          navigate('/purchase-orders');
        }, 1500);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create purchase order');
      console.error('Error creating purchase order:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">New Purchase Order</h1>
        <button
          onClick={() => navigate('/purchase-orders')}
          className="text-gray-600 hover:text-gray-900"
        >
          ← Back to List
        </button>
      </div>

      {/* Success Message */}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
          Purchase order created successfully! Redirecting...
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Basic Information */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Supplier */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Supplier *
              </label>
              <select
                value={supplierId || ''}
                onChange={(e) => setSupplierId(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="">Select a supplier</option>
                {suppliers.map(supplier => (
                  <option key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Order Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Order Date *
              </label>
              <input
                type="date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            {/* Expected Delivery Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Expected Delivery Date
              </label>
              <input
                type="date"
                value={expectedDeliveryDate}
                onChange={(e) => setExpectedDeliveryDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Currency */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="RON">RON</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>

            {/* Payment Terms */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Payment Terms
              </label>
              <input
                type="text"
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                placeholder="e.g., Net 30"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Delivery Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Delivery Address
              </label>
              <input
                type="text"
                value={deliveryAddress}
                onChange={(e) => setDeliveryAddress(e.target.value)}
                placeholder="Enter delivery address"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Notes */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Additional notes..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Order Lines */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Order Lines</h2>
            <button
              type="button"
              onClick={addLine}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              + Add Line
            </button>
          </div>

          <div className="space-y-4">
            {lines.map((line, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-medium text-gray-900">Line {index + 1}</h3>
                  {lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeLine(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Product */}
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Product *
                    </label>
                    <select
                      value={line.product_id || ''}
                      onChange={(e) => {
                        const productId = Number(e.target.value);
                        const product = products.find(p => p.id === productId);
                        updateLine(index, 'product_id', productId);
                        if (product?.base_price) {
                          updateLine(index, 'unit_cost', product.base_price);
                        }
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    >
                      <option value="">Select a product</option>
                      {products.map(product => (
                        <option key={product.id} value={product.id}>
                          {product.name} ({product.sku})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Quantity */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Quantity *
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={line.quantity}
                      onChange={(e) => updateLine(index, 'quantity', Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  {/* Unit Cost */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Unit Cost *
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.unit_cost}
                      onChange={(e) => updateLine(index, 'unit_cost', Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  {/* Discount % */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Discount %
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={line.discount_percent || 0}
                      onChange={(e) => updateLine(index, 'discount_percent', Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Tax % */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tax %
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      value={line.tax_percent || 19}
                      onChange={(e) => updateLine(index, 'tax_percent', Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Line Total */}
                <div className="mt-4 text-right">
                  <span className="text-sm text-gray-600">Line Total: </span>
                  <span className="text-lg font-semibold text-gray-900">
                    {calculateLineTotal(line).toFixed(2)} {currency}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Total */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Total Amount</h2>
            <div className="text-3xl font-bold text-blue-600">
              {calculateTotal().toFixed(2)} {currency}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate('/purchase-orders')}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Purchase Order'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PurchaseOrderForm;
