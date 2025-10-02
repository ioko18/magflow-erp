# Quick Start Guide - eMAG Integration Improvements

## 🚀 What's New

### Order Synchronization (NEW!)
You can now synchronize orders from both eMAG accounts (MAIN and FBE) with full support for:
- Status filtering (new, in_progress, prepared, finalized, returned, canceled)
- Pagination (up to 200 pages per account)
- Rate limiting compliance (12 RPS for orders)
- Real-time progress tracking

## 📖 How to Use

### 1. Start the System

```bash
# Terminal 1 - Start Backend
cd /Users/macos/anaconda3/envs/MagFlow
./start_dev.sh backend

# Terminal 2 - Start Frontend
cd /Users/macos/anaconda3/envs/MagFlow
./start_dev.sh frontend
```

### 2. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:5173
```

Login with:
- **Email**: admin@example.com
- **Password**: secret

### 3. Sync Orders

1. Navigate to **eMAG Integration** page
2. Click **Advanced Options** (gear icon) to configure:
   - Max Pages: 1-200 (default: 50)
   - Delay: 0.1-10.0s (default: 1.2s)
3. Click **Sync Orders** button
4. Watch real-time progress notifications
5. View results showing MAIN and FBE order counts

### 4. View Synced Data

#### Products
- Navigate to **Products** page
- Filter by account type: All / eMAG MAIN / eMAG FBE / Local
- View sync status, prices, stock levels

#### Orders
- Navigate to **Orders** page
- View eMAG order analytics
- Filter by status, channel, date range
- See sync status for each order

#### Customers
- Navigate to **Customers** page
- View eMAG customer analytics
- See loyalty distribution
- Track channel preferences

## 🔧 API Endpoints

### New Order Sync Endpoints

#### Sync All Orders
```bash
POST /api/v1/emag/enhanced/sync/all-orders
Content-Type: application/json
Authorization: Bearer <your_jwt_token>

{
  "max_pages_per_account": 50,
  "delay_between_requests": 1.2,
  "status_filter": null
}
```

#### Get All Orders
```bash
GET /api/v1/emag/enhanced/orders/all?account_type=both&max_pages_per_account=10
Authorization: Bearer <your_jwt_token>
```

### Existing Endpoints

#### Sync Products
```bash
POST /api/v1/emag/enhanced/sync/all-products
```

#### Sync Offers
```bash
POST /api/v1/emag/enhanced/sync/all-offers
```

#### Get Status
```bash
GET /api/v1/emag/enhanced/status
```

## 📊 Features Overview

### eMAG Integration Page
- ✅ **Order Sync**: New button for order synchronization
- ✅ **Product Sync**: Sync all products from MAIN + FBE
- ✅ **Offer Sync**: Sync all offers from MAIN + FBE
- ✅ **Advanced Options**: Configure max pages and delays
- ✅ **Real-time Updates**: Toggle for auto-refresh
- ✅ **Advanced Metrics**: Performance analytics drawer
- ✅ **System Health**: Health monitoring with visual indicators
- ✅ **Sync History**: Complete history with analytics

### Products Page
- ✅ **Account Filtering**: Filter by MAIN, FBE, or Local
- ✅ **Sync Status**: Track sync status for each product
- ✅ **Advanced Filters**: Price range, stock, brand, category
- ✅ **Export**: Export product data

### Orders Page
- ✅ **eMAG Analytics**: 24h activity, sync stats
- ✅ **Status Filtering**: Filter by order status
- ✅ **Channel Filtering**: Filter by MAIN, FBE, or other
- ✅ **Date Range**: Filter by date range
- ✅ **Sync Status**: Track sync status for each order

### Customers Page
- ✅ **eMAG Metrics**: Customer counts, VIP tracking
- ✅ **Loyalty Distribution**: Bronze, Silver, Gold tiers
- ✅ **Channel Distribution**: MAIN, FBE, Mixed
- ✅ **Status Filtering**: Active, Inactive customers

## ⚙️ Configuration

### Rate Limiting (eMAG API v4.4.8 Compliant)
- **Orders**: 12 requests/second (720 requests/minute)
- **Other Resources**: 3 requests/second (180 requests/minute)
- **Jitter**: Automatic to avoid thundering herd

### Sync Options
- **Max Pages**: 
  - Products: 1-500 pages
  - Orders: 1-200 pages
  - Offers: 1-200 pages
- **Delay**: 0.1-10.0 seconds between requests
- **Auto-refresh**: 5-minute intervals (toggleable)

### Order Status Filters
- `1` = New
- `2` = In Progress
- `3` = Prepared
- `4` = Finalized
- `5` = Returned
- `0` = Canceled

## 🧪 Testing

### Run Tests
```bash
# Test order sync implementation
python3 test_order_sync.py

# Compile backend code
python3 -m py_compile app/services/enhanced_emag_service.py
python3 -m py_compile app/api/v1/endpoints/enhanced_emag_sync.py

# Build frontend
cd admin-frontend
npm run build
```

### Expected Results
- ✅ All Python files compile without errors
- ✅ Frontend builds successfully
- ✅ All tests pass
- ✅ API endpoints respond correctly

## 📚 Documentation

### Full Documentation
- [eMAG Full Sync Guide](./EMAG_FULL_SYNC_GUIDE.md)
- [Improvements Summary](./EMAG_IMPROVEMENTS_SUMMARY.md)
- [API Reference](./integrations/emag/api_reference.md)

### API Documentation
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

## 🐛 Troubleshooting

### Backend Not Starting
```bash
# Check if port 8000 is in use
lsof -i :8000

# Check logs
tail -f logs/app.log
```

### Frontend Not Starting
```bash
# Check if port 5173 is in use
lsof -i :5173

# Reinstall dependencies
cd admin-frontend
npm install
```

### Order Sync Not Working
1. Check eMAG credentials in `.env`
2. Verify IP is whitelisted in eMAG dashboard
3. Check rate limiting settings
4. Review logs for error messages

### Authentication Errors
- Verify JWT token is valid
- Check token expiration
- Re-login if necessary

## 💡 Tips

### Best Practices
1. **Start Small**: Test with 1-5 pages first
2. **Monitor Progress**: Watch real-time notifications
3. **Check Logs**: Review sync history for errors
4. **Use Filters**: Apply filters to reduce data volume
5. **Schedule Syncs**: Use off-peak hours for large syncs

### Performance Optimization
1. **Adjust Delays**: Increase delay if hitting rate limits
2. **Reduce Pages**: Lower max pages for faster syncs
3. **Use Filters**: Apply status filters to reduce data
4. **Monitor Health**: Check system health regularly

### Data Management
1. **Export Regularly**: Backup sync data periodically
2. **Clean Old Data**: Remove old sync logs
3. **Monitor Storage**: Check database size
4. **Verify Accuracy**: Compare with eMAG dashboard

## 🎯 Next Steps

1. **Test Order Sync**: Try syncing orders from both accounts
2. **Explore Filters**: Test different filter combinations
3. **Review Analytics**: Check performance metrics
4. **Export Data**: Try exporting sync data
5. **Monitor Health**: Enable real-time monitoring

## 📞 Support

For issues or questions:
- Check logs in `logs/` directory
- Review API documentation at `/docs`
- Verify configuration in `.env`
- Test endpoints with provided examples

---

**Version**: v2.1  
**Date**: September 29, 2025  
**Status**: ✅ Production Ready
