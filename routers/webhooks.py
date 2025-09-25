# /routers/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import os, httpx
from db.supabase_client import get_client
from services import contacts, conversations, chatbot

router = APIRouter()
VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]

@router.get("/whatsapp")
async def verify(mode: str = None, challenge: str = None, token: str = None):
    print(f"DEBUG: mode={mode}, challenge={challenge}, token={token}")
    print(f"DEBUG: VERIFY_TOKEN={VERIFY_TOKEN}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/whatsapp")
async def inbound(request: Request):
    body = await request.json()
    # WhatsApp Cloud API changes structure; handle messages only
    entries = body.get("entry", [])
    sb = get_client()

    for e in entries:
        for change in e.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts_w = value.get("contacts", [])
            metadata = value.get("metadata", {})
            channel = "whatsapp"

            for m in messages:
                if m.get("type") != "text":  # MVP: solo texto
                    continue
                text = m["text"]["body"].strip()
                wa_from = m["from"]  # número
                external_message_id = m["id"]

                # 1) Upsert contacto + canal
                contact = contacts.upsert_contact_from_whatsapp(sb, wa_from, clinic_id=None)  # clinic_id se resuelve x phone mapping o 1er tenant piloto

                # 2) Upsert conversación
                conv = conversations.ensure_open_conversation(sb, contact["clinic_id"], contact["id"], channel)

                # 3) Persistir mensaje inbound
                sb.table("messages").insert({
                    "clinic_id": contact["clinic_id"],
                    "conversation_id": conv["id"],
                    "contact_id": contact["id"],
                    "direction": "inbound",
                    "channel": channel,
                    "content": text,
                    "external_message_id": external_message_id,
                    "status": "delivered"
                }).execute()

                # 4) Chatbot básico con contexto
                reply = chatbot.handle(text, sb, conv["id"], contact["id"], contact["clinic_id"])
                if reply:
                    # guardar outbound + enviar
                    sb.table("messages").insert({
                        "clinic_id": contact["clinic_id"],
                        "conversation_id": conv["id"],
                        "staff_id": None,
                        "direction": "outbound",
                        "channel": channel,
                        "content": reply,
                        "status": "delivered"
                    }).execute()

                    # enviar por WhatsApp
                    from services.whatsapp import send_whatsapp_text
                    await send_whatsapp_text(reply, wa_from)

    return {"ok": True}

