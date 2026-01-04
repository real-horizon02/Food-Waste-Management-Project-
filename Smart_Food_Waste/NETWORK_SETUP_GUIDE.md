# 🚀 NitA Network Connection Troubleshooting & Setup Guide

## ✅ Current System Status

**Backend (Flask):**
- ✅ Running on: `http://localhost:5000`
- ✅ API Endpoint: `http://localhost:5000/api`
- ✅ Health Check: `http://localhost:5000/api/health`
- ✅ CORS Enabled For: 6 origins including localhost:8000, localhost:3000

**Frontend (HTTP Server):**
- ✅ Running on: `http://localhost:8000`
- ✅ Index: `http://localhost:8000/index.html`
- ✅ Static Files: Served from `/frontend` directory

---

## 🔧 How to Run the System

### **Method 1: Manual - Two Terminal Windows (Recommended)**

#### Terminal 1 - Backend Server
```powershell
cd "f:\Code Playground\NitA\updated1\NitA\backend"
"F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe" app.py
```
**Expected Output:**
```
[OK] CORS enabled for 6 origin(s)
[INFO] OpenAI integration enabled for NLP processing
[OK] Dish routes registered
...
[INFO] Server listening on: 0.0.0.0:5000 (all interfaces)
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

#### Terminal 2 - Frontend Server
```powershell
cd "f:\Code Playground\NitA\updated1\NitA"
"F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe" -m http.server 8000 --directory frontend
```
**Expected Output:**
```
Serving HTTP on :: port 8000 (http://[::]:8000/) ...
```

### **Method 2: Automated - PowerShell Script**

Run the startup script:
```powershell
cd "f:\Code Playground\NitA\updated1\NitA"
. .\START_SYSTEM.ps1
```

This will:
1. Stop any existing processes on ports 5000 and 8000
2. Start Flask backend
3. Start frontend HTTP server
4. Test both connections
5. Display the URLs to open in your browser

### **Method 3: Batch File (Windows)**

Run the frontend batch file (requires separate backend):
```batch
"f:\Code Playground\NitA\updated1\NitA\START_FRONTEND.bat"
```

---

## 🌐 Accessing the Application

Once both servers are running:

1. **Open your browser**
2. **Go to:** `http://localhost:8000`
3. You should see the NitA dashboard

---

## 🧪 Testing Connectivity

### Test Backend
```powershell
Invoke-WebRequest -Uri http://localhost:5000/api/health
# Expected Response: {"status":"ok","service":"NitA API"}
```

### Test Frontend
```powershell
Invoke-WebRequest -Uri http://localhost:8000/index.html
# Expected Response: 200 OK with HTML content
```

### Test CORS
```powershell
Invoke-WebRequest -Uri http://localhost:5000/api/health `
  -Headers @{'Origin'='http://localhost:8000'}
# Expected CORS Header: Access-Control-Allow-Origin: http://localhost:8000
```

---

## ⚠️ If "Network Error - Not Connected to Backend"

### 1. **Check if Backend is Running**
```powershell
netstat -ano | findstr "5000" | findstr "LISTENING"
# Should show: TCP    0.0.0.0:5000           0.0.0.0:0              LISTENING       [PID]
```

**If NOT running:** Start Flask backend (Method 1, Terminal 1)

### 2. **Check if Frontend is Running**
```powershell
netstat -ano | findstr "8000" | findstr "LISTENING"
# Should show: TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       [PID]
```

**If NOT running:** Start HTTP server (Method 1, Terminal 2)

### 3. **Check CORS Configuration**
Edit `backend/.env`:
```dotenv
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1
```

**Then restart Flask backend**

### 4. **Check Frontend API URL**
Edit `frontend/js/api.js` - make sure API base URL is:
```javascript
return 'http://localhost:5000/api';
```

### 5. **Browser Console Debugging**
Open browser (F12) → Console tab:
```javascript
// Test API connection
fetch('http://localhost:5000/api/health')
  .then(r => r.json())
  .then(d => console.log('Success:', d))
  .catch(e => console.log('Error:', e))
```

---

## 🐛 Common Network Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **"Connection refused"** | Backend not running on port 5000 | Start Flask backend |
| **"Cannot GET /api/..."** | CORS error or endpoint not found | Check CORS_ORIGINS in .env, restart backend |
| **"404 Not Found"** | Frontend files not found | Check frontend is on port 8000 |
| **Blank page at localhost:8000** | HTTP server not serving frontend | Restart frontend server with `--directory frontend` |
| **"Failed to fetch"** | CORS blocked or network timeout | Check CORS headers, firewall settings |
| **Port already in use** | Another process using 5000/8000 | Kill process: `Get-Process -Id [PID] \| Stop-Process` |

---

## 🔒 CORS Configuration Details

**Currently Enabled Origins:**
- ✅ `http://localhost:8000`
- ✅ `http://127.0.0.1:8000`
- ✅ `http://localhost:3000`
- ✅ `http://127.0.0.1:3000`
- ✅ `http://localhost`
- ✅ `http://127.0.0.1`

**Backend CORS Settings (Flask):**
```python
cors_origins = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost',
    'http://127.0.0.1'
]
CORS(app, origins=cors_origins, supports_credentials=True, 
     allow_headers=['Content-Type', 'Authorization'])
```

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│         FRONTEND (Port 8000)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  index.html, main.js, api.js, ui.js             │  │
│  │  Served by Python HTTP Server                    │  │
│  └────────────────────┬────────────────────────────┘  │
│                       │ fetch() calls                   │
│                       ↓                                  │
│              http://localhost:5000/api                 │
└─────────────────────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │     BACKEND (Port 5000)                  │
        │ ┌──────────────────────────────────────┐ │
        │ │  Flask Application                   │ │
        │ │  - Routes (/api/dish, /api/health)  │ │
        │ │  - Services (recipe, PDF, nutrition)│ │
        │ │  - AI Module (OpenAI integration)    │ │
        │ │  - MongoDB (grocery tracking)        │ │
        │ │  - Scheduler (expiry alerts)         │ │
        │ └──────────────────────────────────────┘ │
        └──────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │     EXTERNAL SERVICES                    │
        │  - OpenAI API (AI processing)           │
        │  - Spoonacular API (recipes)            │
        │  - Google Search API (fallback)         │
        │  - MongoDB (grocery items)              │
        └──────────────────────────────────────────┘
```

---

## ✅ Final Checklist

- [ ] Backend running on `http://localhost:5000`
- [ ] Frontend running on `http://localhost:8000`
- [ ] Both services listening (netstat shows LISTENING)
- [ ] CORS enabled for `http://localhost:8000` in backend
- [ ] Frontend API base URL set to `http://localhost:5000/api`
- [ ] Can access `http://localhost:8000` in browser
- [ ] Browser console shows no network errors
- [ ] API health check works: `http://localhost:5000/api/health`

---

## 📞 Emergency Restart

If something goes wrong, completely reset:

```powershell
# Kill all Python processes
Get-Process python | Stop-Process -Force

# Start backend
cd "f:\Code Playground\NitA\updated1\NitA\backend"
"F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe" app.py

# In new terminal, start frontend
cd "f:\Code Playground\NitA\updated1\NitA"
"F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe" -m http.server 8000 --directory frontend

# Open browser
http://localhost:8000
```

---

**✅ System is now ready for use!**
