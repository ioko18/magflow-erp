---
title: Testing eMAG Integration cu Credențiale Reale
last_reviewed: 2025-09-25
owner: integrations-team
---

# 🧪 Testing eMAG Integration cu Credențiale Reale

## 📋 Prezentare Generală

Acest ghid explică cum să testezi în siguranță integrarea eMAG cu **crediențiale reale** în MagFlow ERP. Sistemul de testare este conceput să fie **sigur**, **controlat** și **informativ**.

## 🚀 Începe Testarea

### 1. Pregătire Prealabilă

#### **✅ Verifică Configurația**

```bash
# Asigură-te că server-ul rulează
curl http://localhost:8000/health

# Verifică status-ul sistemului de testare
curl http://localhost:8000/api/v1/emag/test/status
```

#### **✅ Pregătește Credențialele**

- **Username**: Username-ul tău eMAG Marketplace
- **Password**: Parola corespunzătoare
- **IP Whitelist**: Asigură-te că IP-ul tău este în whitelist-ul eMAG
- **API Quota**: Verifică că ai suficientă cotă API disponibilă

### 2. Rulare Teste

#### **Metoda 1: Script Interactiv**

```bash
# Rulare script interactiv cu meniu
./test_emag_credentials.sh
```

#### **Metoda 2: API Direct**

```bash
# Testare credentiale
curl -X POST "http://localhost:8000/api/v1/emag/test/credentials" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "username": "your_emag_username",
    "password": "your_emag_password"
  }'
```

## 📊 Tipuri de Teste Disponibile

### 1. Test Conexiune și Autentificare

```bash
curl -X POST "http://localhost:8000/api/v1/emag/test/credentials" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

**Ce testează:**

- ✅ Conectivitate la eMAG API
- ✅ Autentificare Basic Auth
- ✅ IP whitelisting
- ✅ Status API eMAG

### 2. Test Suite Complet

```bash
curl -X POST "http://localhost:8000/api/v1/emag/test/full-suite" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "password": "pass",
    "test_types": ["connection", "authentication", "rate_limits", "data_retrieval"]
  }'
```

**Include:**

- Conexiune și autentificare
- Rate limiting behavior
- Data retrieval capabilities
- Sync operations

### 3. Test Rate Limits

```bash
curl -X POST "http://localhost:8000/api/v1/emag/test/rate-limits" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "password": "pass",
    "test_duration_seconds": 60
  }'
```

**Analizează:**

- Rate limits per endpoint
- Comportament la supraîncărcare
- Recovery după rate limiting

### 4. Test Data Retrieval

```bash
curl -X POST "http://localhost:8000/api/v1/emag/test/data-retrieval" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "password": "pass",
    "max_pages": 5
  }'
```

**Verifică:**

- Preluare produse
- Preluare oferte
- Calitate date
- Performance

### 5. Test Sync Operation

```bash
curl -X POST "http://localhost:8000/api/v1/emag/test/sync-operation" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "password": "pass",
    "max_pages": 3
  }'
```

**Testează:**

- Sync complet MAIN + FBE
- Deduplicare SKU
- Performance sync

## 🔍 Interpretarea Rezultatelor

### 1. Rezultate Succes

#### **Conexiune și Autentificare ✅**

```json
{
  "test_results": {
    "connection": {"success": true, "duration_ms": 245},
    "authentication": {"success": true, "duration_ms": 180}
  },
  "overall_status": "success",
  "recommendations": ["✅ Credentials are valid and working"]
}
```

#### **Rate Limits ✅**

```json
{
  "test_result": {
    "success": true,
    "requests_per_second": 2.5,
    "rate_limited": false
  },
  "recommendations": ["✅ Rate limiting is working correctly"]
}
```

### 2. Rezultate cu Probleme

#### **Autentificare Eșuată ❌**

```json
{
  "test_results": {
    "connection": {"success": true, "duration_ms": 200},
    "authentication": {
      "success": false,
      "error": "Authentication failed - IP may not be whitelisted"
    }
  },
  "overall_status": "issues_detected",
  "recommendations": [
    "❌ Authentication failed - IP may not be whitelisted",
    "⚙️ Add your IP to eMAG API whitelist"
  ]
}
```

#### **Rate Limits Probleme ❌**

```json
{
  "test_result": {
    "success": false,
    "requests_per_second": 0.1,
    "rate_limited": true
  },
  "recommendations": [
    "⚠️ Rate limit test encountered issues",
    "⚙️ Consider increasing delays between requests"
  ]
}
```

## 🔧 Rezolvarea Problemelor Comune

### 1. **Authentication Failed**

```bash
# Soluții:
1. Verifică username și password
2. Adaugă IP-ul tău în whitelist-ul eMAG
3. Contactează support-ul eMAG pentru asistență
```

### 2. **Rate Limits Hit**

```bash
# Soluții:
1. Crește delay-ul între request-uri
2. Reduce numărul de pagini per test
3. Testează în afara orelor de peak
```

### 3. **Connection Timeout**

```bash
# Soluții:
1. Verifică conexiunea la internet
2. Testează status-ul eMAG API
3. Verifică firewall și proxy settings
```

### 4. **Insufficient Quota**

```bash
# Soluții:
1. Verifică API quota în dashboard-ul eMAG
2. Așteaptă resetarea cotelor
3. Contactează eMAG pentru limite suplimentare
```

## ⚙️ Configurare și Setări

### 1. **Setări de Testare**

```json
{
  "recommended_settings": {
    "max_pages_test": 5,
    "rate_limit_test_duration": 60,
    "data_retrieval_pages": 3
  },
  "safety_features": {
    "test_mode_enabled": true,
    "rate_limiting_respected": true,
    "error_recovery": true,
    "data_validation": true
  }
}
```

### 2. **Environment Configuration**

```bash
# Development/Testing
EMAG_API_BASE_URL=https://marketplace-api.emag.ro/api-3
TEST_ENVIRONMENT=staging

# Production
EMAG_API_BASE_URL=https://marketplace-api.emag.ro/api-3
TEST_ENVIRONMENT=production
```

## 📈 Metrici și Performanță

### 1. **Target Metrics**

| Metrică                 | Valoare Target | Status |
| ----------------------- | -------------- | ------ |
| **Connection Time**     | \<500ms        | ✅     |
| **Authentication Time** | \<300ms        | ✅     |
| **Requests/Second**     | >1.0           | ✅     |
| **Success Rate**        | >95%           | ✅     |
| **Data Quality**        | >90%           | ✅     |

### 2. **Performance Benchmarks**

```json
{
  "sync_performance": {
    "products_per_minute": 85,
    "average_response_time_ms": 245,
    "error_rate_percentage": 1.3
  },
  "rate_limiting": {
    "respected_limits": true,
    "adaptive_behavior": true,
    "burst_handling": true
  }
}
```

## 🛡️ Caracteristici de Siguranță

### 1. **Test Mode**

- ✅ Nu modifică date în eMAG
- ✅ Respectă rate limits
- ✅ Logging detaliat pentru troubleshooting
- ✅ Error recovery automat

### 2. **IP Whitelisting Check**

- ✅ Verifică automat whitelist status
- ✅ Oferă instrucțiuni pentru whitelist
- ✅ Previne teste cu IP neautorizat

### 3. **Quota Management**

- ✅ Monitorizează utilizarea API quota
- ✅ Oferă alternative la quota epuizată
- ✅ Previzionează consumul de quota

### 4. **Error Handling**

- ✅ Graceful failure handling
- ✅ Detailed error messages
- ✅ Recommendations pentru rezolvare
- ✅ Recovery automat

## 🚀 Best Practices pentru Testare

### 1. **Înainte de Testare**

```bash
# Checklist:
✅ IP whitelisted în eMAG
✅ Sufficient API quota available
✅ Valid credentials ready
✅ Backup plan if tests fail
✅ Test environment vs production
```

### 2. **În Timpul Testării**

```bash
# Monitor:
📊 Response times
⚡ Error rates
🔄 Rate limit hits
📦 Data quality
🔐 Authentication success
```

### 3. **După Testare**

```bash
# Analyze:
📈 Performance metrics
❌ Failed tests reasons
⚠️ Warning signs
✅ Success patterns
🚀 Improvement opportunities
```

## 📞 Suport și Troubleshooting

### 1. **Contact eMAG Support**

- **Website**: https://marketplace.emag.ro
- **API Documentation**: https://developers.emag.ro
- **Support Email**: marketplace@emag.ro
- **Status Page**: https://status.emag.ro

### 2. **Common Issues & Solutions**

#### **Issue: IP Not Whitelisted**

```bash
# Solution:
1. Login to eMAG Marketplace
2. Go to Settings → API Settings
3. Add your IP: YOUR.IP.ADDRESS.HERE
4. Save and wait 5-10 minutes
5. Retry test
```

#### **Issue: Invalid Credentials**

```bash
# Solution:
1. Verify username in eMAG account
2. Reset password if necessary
3. Check account status (active/suspended)
4. Contact eMAG support
```

#### **Issue: Rate Limits Exceeded**

```bash
# Solution:
1. Reduce test intensity
2. Increase delays between requests
3. Test during off-peak hours
4. Request higher rate limits
```

## 🎯 Concluzie

### ✅ **Sistemul de Testare Oferă:**

1. **🛡️ Siguranță Completă**

   - Test mode fără modificări date
   - Rate limiting respectat
   - Error recovery robust

1. **📊 Diagnostic Detaliat**

   - Teste comprehensive
   - Metrici detaliate
   - Recommendations automate

1. **🚀 Ușurință în Utilizare**

   - Script interactiv
   - API endpoints simple
   - Documentație comprehensivă

1. **🔧 Troubleshooting Eficient**

   - Error messages clare
   - Ghiduri de rezolvare
   - Suport pentru probleme comune

### 🎉 **Poți Acum să Testezi cu Încredere!**

**Sistemul este pregătit pentru testare cu credentiale reale eMAG în deplină siguranță!**

**Următorii pași:**

1. **Testează cu credentiale** folosind script-ul interactiv
1. **Configurează pentru production** dacă testele trec
1. **Monitorizează și alertează** în timp real
1. **Scalează și optimizează** după nevoi

**🚀 Succes cu testarea eMAG integration!**
