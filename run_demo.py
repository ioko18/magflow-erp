"""
Minimal FastAPI demo runner for MagFlow
Bypasses complex initialization for demo purposes
"""
from fastapi import FastAPI

from app.api.v1.api import api_router

app = FastAPI(
    title="MagFlow ERP API",
    description="Demo version - bypassing complex initialization",
    version="1.0-demo"
)

# Include only essential routers
app.include_router(api_router, prefix="/api/v1")

# Simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Demo mode active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
