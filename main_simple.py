# main_simple.py - Versión ultra simple para Railway
import os
from fastapi import FastAPI

app = FastAPI(title="VICORA Backend")

@app.get("/")
async def root():
    return {"status": "ok", "message": "VICORA API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
