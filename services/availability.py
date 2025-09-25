# /services/availability.py
from datetime import datetime, timedelta
from dateutil.parser import isoparse

def get_slots(sb, clinic_id: str, service_id: str, date_iso: str):
    # 1) obtener duración del servicio
    svc = sb.table("services").select("duration_min").eq("id", service_id).single().execute().data
    dur = int(svc["duration_min"])
    # 2) business_hours
    settings = sb.table("clinic_settings").select("business_hours, booking_window_days").eq("clinic_id", clinic_id).single().execute().data
    # MVP: genera slots cada 60min en la fecha
    date = isoparse(date_iso).date()
    slots = []
    start = datetime.combine(date, datetime.min.time()).replace(hour=9)   # 09:00
    end = start.replace(hour=19)                                          # 19:00
    cur = start
    while cur + timedelta(minutes=dur) <= end:
        # check solape con citas
        overlap = sb.rpc("fn_check_overlap", {"p_clinic_id": clinic_id, "p_start": cur.isoformat(), "p_end": (cur+timedelta(minutes=dur)).isoformat()}).execute().data
        if not overlap:
            slots.append({"start_at": cur.isoformat(), "end_at": (cur+timedelta(minutes=dur)).isoformat()})
        cur += timedelta(minutes=60)
    return {"slots": slots}

def book_appointment(sb, payload: dict):
    # payload: clinic_id, contact_id, service_id, start_at, end_at
    appt = sb.table("appointments").insert({
        "clinic_id": payload["clinic_id"],
        "contact_id": payload["contact_id"],
        "service_id": payload["service_id"],
        "start_at": payload["start_at"],
        "end_at": payload["end_at"],
        "status": "confirmed",
        "source": "whatsapp"
    }).execute().data[0]
    # crear reminders (24h)
    sb.table("appointment_reminders").insert({
        "clinic_id": payload["clinic_id"],
        "appointment_id": appt["id"],
        "channel": "whatsapp",
        "scheduled_at": payload["start_at"]  # en producción: restar 24h según settings
    }).execute()
    return appt
