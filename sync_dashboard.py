#!/usr/bin/env python3
"""
eMAG Sync Dashboard
FastAPI web interface for monitoring eMAG sync operations
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sync_scheduler import SyncScheduler
from sync_monitor import SyncMonitor

app = FastAPI(
    title="eMAG Sync Dashboard",
    description="Real-time monitoring dashboard for eMAG synchronization",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Global scheduler instance
scheduler = SyncScheduler()
monitor = SyncMonitor()

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts"""
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the app shuts down"""
    scheduler.stop()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        report = monitor.generate_report()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "report": report,
            "scheduler_status": report.get("scheduler", {}),
            "alerts": report.get("alerts", [])
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def api_status():
    """API endpoint for status"""
    try:
        report = monitor.generate_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/start")
async def start_scheduler():
    """Start the sync scheduler"""
    try:
        scheduler.start()
        return {"status": "success", "message": "Scheduler started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the sync scheduler"""
    try:
        scheduler.stop()
        return {"status": "success", "message": "Scheduler stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/status")
async def scheduler_status():
    """Get detailed scheduler status"""
    try:
        return scheduler.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/{account_type}")
async def sync_account(account_type: str):
    """Manually trigger sync for specific account"""
    try:
        if account_type not in scheduler.accounts:
            raise HTTPException(status_code=404, detail=f"Account {account_type} not found")

        # Run sync in background
        success = scheduler.run_sync(scheduler.accounts[account_type])

        return {
            "status": "success" if success else "failed",
            "account": account_type,
            "message": f"Sync {'completed' if success else 'failed'} for {account_type}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounts")
async def get_accounts():
    """Get list of configured accounts"""
    try:
        return {
            "accounts": list(scheduler.accounts.keys()),
            "configurations": {
                name: {
                    "account_type": account.account_type,
                    "sync_interval": account.sync_interval,
                    "sync_types": [st.value for st in account.sync_types],
                    "status": account.status
                }
                for name, account in scheduler.accounts.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        report = monitor.generate_report()

        # Check for critical alerts
        critical_alerts = [a for a in report.get("alerts", []) if a["type"] == "critical"]

        if critical_alerts:
            return {
                "status": "unhealthy",
                "alerts": critical_alerts,
                "timestamp": datetime.now().isoformat()
            }

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# HTML Template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>eMAG Sync Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-100 min-h-screen" x-data="dashboard()">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex justify-between items-center">
                <div>
                    <h1 class="text-3xl font-bold text-gray-800">🚀 eMAG Sync Dashboard</h1>
                    <p class="text-gray-600 mt-2">Monitorizare în timp real pentru sincronizarea eMAG</p>
                </div>
                <div class="text-right">
                    <p class="text-sm text-gray-500">Ultima actualizare</p>
                    <p class="text-lg font-semibold" x-text="currentTime"></p>
                </div>
            </div>
        </div>

        <!-- Alerts -->
        <div x-show="alerts.length > 0" class="mb-6">
            <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4" x-show="alerts.some(a => a.type === 'warning')">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm text-yellow-700">
                            <strong>Atenționări:</strong>
                            <span x-text="alerts.filter(a => a.type === 'warning').length"></span> avertismente detectate
                        </p>
                    </div>
                </div>
            </div>

            <div class="bg-red-50 border-l-4 border-red-400 p-4" x-show="alerts.some(a => a.type === 'critical')">
                <div class="flex">
                    <div class="ml-3">
                        <p class="text-sm text-red-700">
                            <strong>Probleme critice:</strong>
                            <span x-text="alerts.filter(a => a.type === 'critical').length"></span> probleme detectate
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Scheduler Status -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            <!-- Scheduler Card -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">🎯 Scheduler Status</h3>
                <div class="space-y-3">
                    <div class="flex justify-between items-center">
                        <span>Status:</span>
                        <span x-text="schedulerStatus.scheduler_running ? '✅ Running' : '❌ Stopped'"
                              :class="schedulerStatus.scheduler_running ? 'text-green-600' : 'text-red-600'"></span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Conturi configurate:</span>
                        <span x-text="Object.keys(schedulerStatus.accounts || {}).length"></span>
                    </div>
                </div>
            </div>

            <!-- Account Status Cards -->
            <template x-for="(accountInfo, accountName) in schedulerStatus.accounts" :key="accountName">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4" x-text="accountName.toUpperCase() + ' Account'"></h3>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <span>Status:</span>
                            <span x-text="accountInfo.status"
                                  :class="accountInfo.status === 'completed' ? 'text-green-600' : accountInfo.status === 'failed' ? 'text-red-600' : 'text-yellow-600'"></span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>Ultimul sync:</span>
                            <span x-text="formatDate(accountInfo.last_sync)" class="text-sm"></span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>Următorul sync:</span>
                            <span x-text="formatDate(accountInfo.next_sync)" class="text-sm"></span>
                        </div>
                        <button @click="syncAccount(accountName)"
                                class="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition duration-200"
                                :disabled="loading">
                            <span x-show="!loading">🔄 Sync Acum</span>
                            <span x-show="loading">⏳ Se sincronizează...</span>
                        </button>
                    </div>
                </div>
            </template>
        </div>

        <!-- Log Summary -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">📋 Rezumat Log-uri (Ultima oră)</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="text-center">
                    <div class="text-2xl font-bold text-red-600" x-text="report.logs.errors_last_hour"></div>
                    <div class="text-sm text-gray-600">Erori</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-yellow-600" x-text="report.logs.warnings_last_hour"></div>
                    <div class="text-sm text-gray-600">Avertismente</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-gray-600" x-text="report.logs.last_log_time ? '✅' : '❌'"></div>
                    <div class="text-sm text-gray-600">Log activ</div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">🎮 Acțiuni</h3>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <button @click="startScheduler()"
                        class="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md transition duration-200">
                    ▶️ Start Scheduler
                </button>
                <button @click="stopScheduler()"
                        class="bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-md transition duration-200">
                    ⏹️ Stop Scheduler
                </button>
                <button @click="refreshData()"
                        class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition duration-200">
                    🔄 Refresh
                </button>
                <button onclick="window.location.href='/api/status'"
                        class="bg-purple-500 hover:bg-purple-600 text-white font-medium py-2 px-4 rounded-md transition duration-200">
                    📊 API Status
                </button>
            </div>
        </div>
    </div>

    <script>
        function dashboard() {
            return {
                report: {{ report | safe }},
                schedulerStatus: {{ scheduler_status | safe }},
                alerts: {{ alerts | safe }},
                loading: false,
                currentTime: new Date().toLocaleString('ro-RO'),

                init() {
                    // Update time every second
                    setInterval(() => {
                        this.currentTime = new Date().toLocaleString('ro-RO');
                    }, 1000);
                },

                formatDate(dateStr) {
                    if (!dateStr) return 'N/A';
                    return new Date(dateStr).toLocaleString('ro-RO');
                },

                async syncAccount(accountName) {
                    this.loading = true;
                    try {
                        const response = await fetch(`/api/sync/${accountName}`);
                        const result = await response.json();
                        alert(`Sync ${result.status}: ${result.message}`);
                        this.refreshData();
                    } catch (error) {
                        alert('Eroare la sincronizare: ' + error.message);
                    } finally {
                        this.loading = false;
                    }
                },

                async startScheduler() {
                    try {
                        const response = await fetch('/api/scheduler/start');
                        const result = await response.json();
                        alert(result.message);
                        this.refreshData();
                    } catch (error) {
                        alert('Eroare la pornirea scheduler-ului: ' + error.message);
                    }
                },

                async stopScheduler() {
                    try {
                        const response = await fetch('/api/scheduler/stop');
                        const result = await response.json();
                        alert(result.message);
                        this.refreshData();
                    } catch (error) {
                        alert('Eroare la oprirea scheduler-ului: ' + error.message);
                    }
                },

                async refreshData() {
                    try {
                        const response = await fetch('/api/status');
                        const data = await response.json();
                        this.report = data;
                        this.schedulerStatus = data.scheduler || {};
                        this.alerts = data.alerts || [];
                    } catch (error) {
                        alert('Eroare la actualizarea datelor: ' + error.message);
                    }
                }
            }
        }
    </script>
</body>
</html>
"""

# Save dashboard HTML
dashboard_path = Path("templates/dashboard.html")
dashboard_path.parent.mkdir(exist_ok=True)
with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(DASHBOARD_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Dashboard page (alias for /)"""
    return await dashboard(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
