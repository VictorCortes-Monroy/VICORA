# /services/conversations.py
from datetime import datetime, timezone
from typing import Optional

def ensure_open_conversation(sb, clinic_id: str, contact_id: str, channel: str) -> dict:
    """
    Busca una conversación abierta o crea una nueva para el contacto.
    Mantiene solo una conversación abierta por canal por contacto.
    """
    # Buscar conversación abierta existente
    existing = sb.table("conversations").select("*").eq("clinic_id", clinic_id).eq("contact_id", contact_id).eq("channel", channel).eq("status", "open").execute()
    
    if existing.data:
        # Ya existe una conversación abierta, actualizarla
        conversation = existing.data[0]
        sb.table("conversations").update({
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", conversation["id"]).execute()
        
        return conversation
    else:
        # Crear nueva conversación
        now = datetime.now(timezone.utc).isoformat()
        new_conversation = sb.table("conversations").insert({
            "clinic_id": clinic_id,
            "contact_id": contact_id,
            "channel": channel,
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
            "message_count": 0
        }).execute()
        
        return new_conversation.data[0]

def close_conversation(sb, conversation_id: str, reason: str = "completed"):
    """
    Cierra una conversación con el motivo especificado.
    """
    sb.table("conversations").update({
        "status": "closed",
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "close_reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", conversation_id).execute()

def increment_message_count(sb, conversation_id: str):
    """
    Incrementa el contador de mensajes de una conversación.
    """
    # Obtener el conteo actual
    conv = sb.table("conversations").select("message_count").eq("id", conversation_id).single().execute()
    current_count = conv.data.get("message_count", 0) if conv.data else 0
    
    # Incrementar
    sb.table("conversations").update({
        "message_count": current_count + 1,
        "last_message_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", conversation_id).execute()

def get_conversation_context(sb, conversation_id: str, limit: int = 10) -> list:
    """
    Obtiene los últimos mensajes de una conversación para contexto.
    """
    messages = sb.table("messages").select("direction, content, created_at").eq("conversation_id", conversation_id).order("created_at", desc=True).limit(limit).execute()
    
    return list(reversed(messages.data)) if messages.data else []

def set_conversation_context(sb, conversation_id: str, context_data: dict):
    """
    Guarda contexto adicional de la conversación (estado del bot, etc.).
    """
    sb.table("conversations").update({
        "context_data": context_data,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", conversation_id).execute()

def get_active_conversations_by_contact(sb, contact_id: str) -> list:
    """
    Obtiene todas las conversaciones activas de un contacto.
    """
    result = sb.table("conversations").select("*").eq("contact_id", contact_id).eq("status", "open").execute()
    return result.data or []
