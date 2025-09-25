# /services/reminders.py
from datetime import datetime, timezone
import os, httpx

async def send_whatsapp_text(text: str, to: str):
    token = os.environ["WHATSAPP_TOKEN"]
    phone_id = os.environ["WHATSAPP_PHONE_ID"]
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    payload = {"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":text}}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        return response.json()

def run_scheduled_reminders(sb):
    now = datetime.now(timezone.utc).isoformat()
    # buscar reminders vencidos
    res = sb.table("appointment_reminders").select("id, clinic_id, appointment_id").is_("sent_at","null").lte("scheduled_at", now).eq("status","scheduled").execute()
    reminders = res.data or []
    sent_count = 0
    for r in reminders:
        # obtener contacto y número
        appt = sb.table("appointments").select("contact_id, start_at, service_id").eq("id", r["appointment_id"]).single().execute().data
        contact = sb.table("contacts").select("phone, full_name").eq("id", appt["contact_id"]).single().execute().data
        if not contact or not contact["phone"]:
            continue
        msg = f"👋 Recordatorio: tienes una cita el {appt['start_at']}. Responde 'CONFIRMAR' o 'REAGENDAR'."
        # enviar
        import asyncio
        asyncio.run(send_whatsapp_text(msg, contact["phone"]))
        # marcar enviado
        sb.table("appointment_reminders").update({"sent_at": now, "status":"sent"}).eq("id", r["id"]).execute()
        sent_count += 1
    return sent_count
