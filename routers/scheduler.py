# /routers/scheduler.py
from fastapi import APIRouter
from db.supabase_client import get_client
from services.reminders import run_scheduled_reminders

router = APIRouter()

@router.post("/run")
def run():
    sb = get_client()
    sent = run_scheduled_reminders(sb)
    return {"sent": sent}
