# /routers/messages.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from db.supabase_client import get_client

router = APIRouter()

@router.get("/conversations/{conversation_id}")
def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Obtiene los mensajes de una conversación específica.
    """
    sb = get_client()
    
    try:
        # Verificar que la conversación existe
        conv_check = sb.table("conversations").select("id").eq("id", conversation_id).execute()
        if not conv_check.data:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        # Obtener mensajes ordenados por fecha
        messages = sb.table("messages").select(
            "id, direction, channel, content, status, created_at, staff_id, external_message_id"
        ).eq("conversation_id", conversation_id).order(
            "created_at", desc=False
        ).range(offset, offset + limit - 1).execute()
        
        return {
            "conversation_id": conversation_id,
            "messages": messages.data or [],
            "count": len(messages.data) if messages.data else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/{contact_id}/conversations")
def get_contact_conversations(
    contact_id: str,
    status: Optional[str] = Query(None, regex="^(open|closed)$")
):
    """
    Obtiene las conversaciones de un contacto específico.
    """
    sb = get_client()
    
    try:
        query = sb.table("conversations").select(
            "id, channel, status, created_at, updated_at, last_message_at, message_count"
        ).eq("contact_id", contact_id)
        
        if status:
            query = query.eq("status", status)
        
        conversations = query.order("last_message_at", desc=True).execute()
        
        return {
            "contact_id": contact_id,
            "conversations": conversations.data or []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send")
def send_manual_message(payload: dict):
    """
    Envía un mensaje manual (desde el panel admin).
    Payload: {
        "conversation_id": str,
        "content": str,
        "staff_id": str (opcional),
        "channel": str
    }
    """
    sb = get_client()
    
    try:
        # Validar campos requeridos
        required_fields = ["conversation_id", "content", "channel"]
        for field in required_fields:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        # Obtener información de la conversación
        conv = sb.table("conversations").select("clinic_id, contact_id").eq("id", payload["conversation_id"]).single().execute()
        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        # Crear mensaje outbound
        message_data = {
            "clinic_id": conv.data["clinic_id"],
            "conversation_id": payload["conversation_id"],
            "contact_id": conv.data["contact_id"],
            "direction": "outbound",
            "channel": payload["channel"],
            "content": payload["content"],
            "status": "pending",
            "staff_id": payload.get("staff_id")
        }
        
        new_message = sb.table("messages").insert(message_data).execute()
        
        # Actualizar conversación
        sb.table("conversations").update({
            "last_message_at": new_message.data[0]["created_at"],
            "message_count": sb.rpc("increment_message_count", {"conv_id": payload["conversation_id"]})
        }).eq("id", payload["conversation_id"]).execute()
        
        # TODO: Aquí se integraría el envío real por el canal correspondiente
        # Por ahora solo guardamos en DB
        
        return {
            "message": new_message.data[0],
            "status": "queued"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def get_message_stats(
    clinic_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90)
):
    """
    Obtiene estadísticas de mensajes para el dashboard.
    """
    sb = get_client()
    
    try:
        # Construir query base
        query = sb.table("messages").select("direction, channel, created_at")
        
        if clinic_id:
            query = query.eq("clinic_id", clinic_id)
        
        # Filtro de fecha (últimos N días)
        from datetime import datetime, timedelta, timezone
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = query.gte("created_at", since_date)
        
        messages = query.execute()
        
        # Procesar estadísticas
        stats = {
            "total_messages": len(messages.data) if messages.data else 0,
            "inbound_count": 0,
            "outbound_count": 0,
            "by_channel": {},
            "by_day": {}
        }
        
        for msg in messages.data or []:
            # Contar por dirección
            if msg["direction"] == "inbound":
                stats["inbound_count"] += 1
            else:
                stats["outbound_count"] += 1
            
            # Contar por canal
            channel = msg["channel"]
            stats["by_channel"][channel] = stats["by_channel"].get(channel, 0) + 1
            
            # Contar por día
            day = msg["created_at"][:10]  # YYYY-MM-DD
            stats["by_day"][day] = stats["by_day"].get(day, 0) + 1
        
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
