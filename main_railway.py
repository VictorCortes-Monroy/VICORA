# main_railway.py - Versión simplificada para Railway
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

from fastapi import FastAPI

app = FastAPI(title="VICORA Backend")

@app.get("/")
async def root():
    return {"message": "VICORA WhatsApp Chatbot API", "status": "running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "vicora-backend",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/ready")
async def ready():
    return {"status": "ready", "message": "Application is ready to receive requests"}

# Importar routers solo si las variables de entorno están disponibles
try:
    from routers import webhooks, appointments, messages, scheduler
    
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
    app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
    app.include_router(scheduler.router, prefix="/internal/scheduler", tags=["scheduler"])
    
    print("✅ Todos los routers cargados correctamente")
except Exception as e:
    print(f"⚠️ Error cargando routers: {e}")
    print("✅ Aplicación básica funcionando")
