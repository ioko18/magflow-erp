# Troubleshooting: Proxy Error ECONNRESET

**Eroare**: `http proxy error: /api/v1/auth/login Error: read ECONNRESET`  
**Data**: 2025-10-10 17:59:56

---

## 🔍 Problema

Frontend-ul (Vite) nu poate comunica cu backend-ul (FastAPI) prin proxy, primind eroare `ECONNRESET`.

### Simptome
- Frontend rulează pe `http://localhost:5173`
- Backend ar trebui să ruleze pe `http://localhost:8000`
- Proxy requests eșuează cu `ECONNRESET`
- Conexiunea se închide brusc

---

## ✅ Soluții Aplicate

### 1. Îmbunătățire Configurație Proxy Vite

**Fișier**: `admin-frontend/vite.config.ts`

**Modificări**:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false,
    ws: true, // ✅ Enable WebSocket proxying
    timeout: 30000, // ✅ 30 second timeout
    proxyTimeout: 30000, // ✅ Proxy timeout
    configure: (proxy, options) => {
      // ✅ Better error handling
      proxy.on('error', (err, req, res) => {
        console.error('❌ Proxy error:', err.message);
        if (!res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ 
            error: 'Proxy Error', 
            message: 'Backend connection failed.',
            details: err.message 
          }));
        }
      });
      
      // ✅ Keep-alive headers
      proxy.on('proxyReq', (proxyReq, req, res) => {
        proxyReq.setHeader('Connection', 'keep-alive');
      });
    },
  },
}
```

**Beneficii**:
- ✅ Timeout-uri configurate (30s)
- ✅ WebSocket support
- ✅ Keep-alive connections
- ✅ Error handling îmbunătățit
- ✅ Logging mai clar

---

## 🔧 Verificări Necesare

### 1. Verifică Backend Rulează
```bash
# Check proces
ps aux | grep uvicorn

# Check port 8000
lsof -ti:8000

# Test health endpoint
curl http://localhost:8000/health
```

**Expected**: Backend răspunde cu status 200

### 2. Verifică Database Connection
```bash
# Test database
psql $DATABASE_URL -c "SELECT 1;"

# Check Redis
redis-cli -u $REDIS_URL ping
```

### 3. Restart Backend (dacă e necesar)
```bash
# Oprește backend
pkill -f uvicorn

# Pornește backend
cd /Users/macos/anaconda3/envs/MagFlow
conda activate MagFlow
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Restart Frontend
```bash
# În terminal frontend, apasă Ctrl+C apoi:
npm run dev
```

---

## 🐛 Cauze Posibile

### 1. Backend Nu Rulează
**Simptom**: `curl http://localhost:8000/health` eșuează

**Soluție**:
```bash
# Pornește backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Database Connection Issues
**Simptom**: Backend pornește dar crapă la primul request

**Soluție**:
```bash
# Verifică .env
cat .env | grep DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### 3. Port Conflict
**Simptom**: Backend nu poate porni pe port 8000

**Soluție**:
```bash
# Găsește procesul care folosește portul
lsof -ti:8000

# Oprește procesul
kill -9 $(lsof -ti:8000)

# Repornește backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. CORS Issues
**Simptom**: Backend răspunde dar frontend primește CORS errors

**Soluție**: Verifică `app/main.py` - CORS middleware:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Timeout Issues
**Simptom**: Requests mari (export Excel) timeout

**Soluție**: Deja implementat - timeout 30s în proxy config

---

## 📊 Verificare Completă

### Checklist
```bash
# 1. Backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. API docs accessible
curl http://localhost:8000/docs
# Expected: HTML response

# 3. Test API endpoint
curl http://localhost:8000/api/v1/emag-inventory/statistics \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: JSON response

# 4. Frontend proxy
# Open browser: http://localhost:5173
# Check browser console for errors
```

---

## 🚀 Quick Fix Commands

### Restart Everything
```bash
# Terminal 1: Backend
cd /Users/macos/anaconda3/envs/MagFlow
conda activate MagFlow
pkill -f uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (Ctrl+C first)
cd /Users/macos/anaconda3/envs/MagFlow/admin-frontend
npm run dev
```

### Check Logs
```bash
# Backend logs (if using systemd)
journalctl -u magflow-api -f

# Backend logs (if running manually)
# Check terminal output

# Frontend logs
# Check terminal output where npm run dev is running
```

---

## 💡 Best Practices

### 1. Development Setup
```bash
# Always run backend first
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Then run frontend
npm run dev
```

### 2. Environment Variables
```bash
# Backend .env
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
CORS_ORIGINS=["http://localhost:5173"]

# Frontend .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Monitoring
```bash
# Watch backend logs
tail -f logs/app.log

# Watch frontend console
# Open browser DevTools (F12)
```

---

## 📚 Related Documentation

- **Vite Proxy Config**: https://vitejs.dev/config/server-options.html#server-proxy
- **FastAPI CORS**: https://fastapi.tiangolo.com/tutorial/cors/
- **Troubleshooting Guide**: `/docs/deployment/INVENTORY_DEPLOYMENT_GUIDE.md`

---

## ✅ Rezolvare Finală

După aplicarea modificărilor în `vite.config.ts`:

1. **Restart frontend** (Ctrl+C în terminal, apoi `npm run dev`)
2. **Verifică backend** rulează pe port 8000
3. **Test în browser** - ar trebui să funcționeze

**Dacă problema persistă**:
1. Verifică backend logs pentru erori
2. Verifică database connection
3. Restart complet (backend + frontend)

---

**Status**: ✅ Configurație îmbunătățită  
**Next**: Restart frontend pentru a aplica modificările
