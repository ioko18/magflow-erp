# 🚀 Instrucțiuni de Deployment - Fix SMS Service

**Data:** 11 Octombrie 2025  
**Versiune:** 1.0  
**Prioritate:** 🔴 CRITICAL

---

## ⚠️ IMPORTANT

Acest fix rezolvă o **eroare critică** care bloca complet funcționalitatea SMS. Deploy-ul este **urgent** dar trebuie făcut cu atenție.

---

## 📋 Pre-Deployment Checklist

### 1. Verificare Cod
```bash
# Compilare Python
python3 -m py_compile app/services/communication/sms_service.py
python3 -m py_compile app/services/orders/payment_service.py

# Verificare import
python3 -c "from app.services.communication.sms_service import SMSMessage, SMSService"
```

### 2. Rulare Teste
```bash
# Teste SMS
python3 -m pytest tests/test_sms_notifications.py -v

# Teste Payment (dacă există)
python3 -m pytest tests/test_payment*.py -v
```

### 3. Backup
```bash
# Backup cod curent
cd /path/to/MagFlow
git stash save "backup-before-sms-fix"

# Backup baza de date (dacă e cazul)
# pg_dump magflow_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## 🔄 Deployment Steps

### Opțiune 1: Git Deployment (Recomandat)

```bash
# 1. Verifică status
git status

# 2. Add modificările
git add app/services/communication/sms_service.py
git add app/services/orders/payment_service.py

# 3. Commit
git commit -m "fix: Critical SMS Service AttributeError - Add gateway_response attribute

- Added missing gateway_response attribute to SMSMessage dataclass
- Replaced deprecated datetime.utcnow() with datetime.now(timezone.utc)
- Added session validation in SMS and Payment providers
- Added explicit provider initialization

Fixes: SMS sending was completely broken due to AttributeError
Impact: Restores SMS notifications, order confirmations, stock alerts
Tests: 26/31 tests passing (84%)
"

# 4. Push
git push origin main  # sau branch-ul tău

# 5. Deploy pe server
ssh user@server
cd /path/to/MagFlow
git pull origin main
sudo systemctl restart magflow-api  # sau comanda ta de restart
```

### Opțiune 2: Manual Deployment

```bash
# 1. Copiază fișierele modificate pe server
scp app/services/communication/sms_service.py user@server:/path/to/MagFlow/app/services/communication/
scp app/services/orders/payment_service.py user@server:/path/to/MagFlow/app/services/orders/

# 2. Restart servicii
ssh user@server
sudo systemctl restart magflow-api
```

### Opțiune 3: Docker Deployment

```bash
# 1. Rebuild imagine
docker build -t magflow-api:latest .

# 2. Stop container vechi
docker stop magflow-api

# 3. Start container nou
docker run -d --name magflow-api \
  -p 8000:8000 \
  --env-file .env \
  magflow-api:latest

# 4. Verifică logs
docker logs -f magflow-api
```

---

## ✅ Post-Deployment Verification

### 1. Health Check
```bash
# Verifică că aplicația pornește
curl http://localhost:8000/health

# Răspuns așteptat:
# {"status": "healthy", ...}
```

### 2. Test SMS Functionality
```bash
# Test rapid în Python
python3 << EOF
from app.services.communication.sms_service import SMSMessage
msg = SMSMessage(phone_number='+40700123456', message='Test')
print('✅ SMS Service OK' if hasattr(msg, 'gateway_response') else '❌ SMS Service FAIL')
EOF
```

### 3. Monitor Logs
```bash
# Monitorizează logs pentru erori
tail -f /var/log/magflow/app.log | grep -i "error\|sms\|gateway"

# Sau pentru Docker:
docker logs -f magflow-api | grep -i "error\|sms\|gateway"
```

### 4. Test Manual SMS (Opțional)
```bash
# Trimite un SMS de test prin API
curl -X POST http://localhost:8000/api/v1/sms/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "phone_number": "+40700123456",
    "message": "Test message from MagFlow",
    "notification_type": "custom"
  }'
```

---

## 🔍 Troubleshooting

### Problemă: Import Error
```bash
# Eroare: ModuleNotFoundError
# Soluție: Verifică PYTHONPATH
export PYTHONPATH=/path/to/MagFlow:$PYTHONPATH
```

### Problemă: SMS Provider Not Initialized
```bash
# Eroare: "SMS provider not initialized"
# Soluție: Verifică configurația în .env
cat .env | grep -i twilio
cat .env | grep -i messagebird

# Asigură-te că ai:
# TWILIO_ACCOUNT_SID=...
# TWILIO_AUTH_TOKEN=...
# MESSAGEBIRD_API_KEY=...
```

### Problemă: Session is None
```bash
# Eroare: "NoneType has no attribute 'post'"
# Soluție: Verifică că serviciul este inițializat corect
# Caută în logs: "SMS service initialized with X providers"
```

### Problemă: Timezone Warning
```bash
# Warning: "datetime.utcnow() is deprecated"
# Soluție: Verifică că ai versiunea corectă a fișierului
grep "datetime.now(timezone.utc)" app/services/communication/sms_service.py
```

---

## 📊 Monitoring

### Metrici de Urmărit

1. **SMS Success Rate**
   ```sql
   -- Query pentru success rate (dacă ai tabel de logs)
   SELECT 
     COUNT(*) FILTER (WHERE status = 'sent') * 100.0 / COUNT(*) as success_rate
   FROM sms_logs
   WHERE created_at > NOW() - INTERVAL '1 hour';
   ```

2. **Erori în Logs**
   ```bash
   # Caută erori SMS în ultimele 10 minute
   tail -n 1000 /var/log/magflow/app.log | grep -i "sms.*error"
   ```

3. **Provider Status**
   ```bash
   # Verifică status provideri prin API
   curl http://localhost:8000/api/v1/sms/providers/status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

---

## 🔙 Rollback Plan

Dacă ceva merge prost, rollback rapid:

### Git Rollback
```bash
# 1. Identifică commit-ul anterior
git log --oneline -n 5

# 2. Revert la commit-ul anterior
git revert HEAD

# 3. Push
git push origin main

# 4. Deploy
ssh user@server
cd /path/to/MagFlow
git pull origin main
sudo systemctl restart magflow-api
```

### Manual Rollback
```bash
# 1. Restaurează backup
git stash pop  # sau
git checkout HEAD~1 -- app/services/communication/sms_service.py

# 2. Restart
sudo systemctl restart magflow-api
```

---

## 📞 Support

### În caz de probleme:

1. **Verifică documentația:**
   - `FINAL_FIX_REPORT_2025_10_11.md` - Raport complet
   - `SMS_SERVICE_FIX_REPORT.md` - Detalii SMS Service
   - `FIX_SUMMARY.md` - Rezumat rapid

2. **Verifică logs:**
   ```bash
   tail -f /var/log/magflow/app.log
   ```

3. **Test rapid:**
   ```bash
   python3 -c "from app.services.communication.sms_service import SMSMessage; print('OK')"
   ```

---

## ✅ Success Criteria

Deployment-ul este considerat reușit când:

- ✅ Aplicația pornește fără erori
- ✅ Health check returnează status healthy
- ✅ Import SMS Service funcționează
- ✅ Nu există erori în logs legate de SMS
- ✅ Test manual SMS funcționează (opțional)
- ✅ Metrici arată success rate > 95%

---

## 📝 Post-Deployment Tasks

După deployment reușit:

1. ✅ **Update documentație** cu data deployment-ului
2. ✅ **Notifică echipa** că fix-ul este live
3. ✅ **Monitorizează** pentru 24h
4. ✅ **Colectează metrici** success rate
5. ✅ **Planifică** fix-ul pentru `datetime.utcnow()` în restul aplicației

---

**Autor:** Cascade AI  
**Data:** 11 Octombrie 2025  
**Versiune:** 1.0  
**Status:** 🟢 READY FOR DEPLOYMENT
