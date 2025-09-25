# main.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

from fastapi import FastAPI
from routers import webhooks, appointments, messages, scheduler

app = FastAPI(title="AURA Backend")

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(scheduler.router, prefix="/internal/scheduler", tags=["scheduler"])
