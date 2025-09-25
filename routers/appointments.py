# /routers/appointments.py
from fastapi import APIRouter
from db.supabase_client import get_client
from services.availability import get_slots, book_appointment

router = APIRouter()

@router.get("/availability")
def availability(clinic_id: str, service_id: str, date: str):
    sb = get_client()
    return get_slots(sb, clinic_id, service_id, date)

@router.post("")
def create(payload: dict):
    sb = get_client()
    return book_appointment(sb, payload)
