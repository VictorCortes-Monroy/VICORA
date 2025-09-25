# /services/contacts.py
from datetime import datetime, timezone
from typing import Optional

def upsert_contact_from_whatsapp(sb, phone: str, clinic_id: Optional[str] = None) -> dict:
    """
    Crea o actualiza un contacto basado en el número de WhatsApp.
    Si clinic_id es None, usa el primer tenant (MVP).
    """
    # Normalizar número de teléfono (remover espacios, guiones, etc.)
    phone_normalized = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    # Si no se proporciona clinic_id, usar el primer tenant (MVP)
    if not clinic_id:
        # Obtener el primer clinic_id disponible para MVP
        clinic_result = sb.table("clinics").select("id").limit(1).execute()
        if clinic_result.data:
            clinic_id = clinic_result.data[0]["id"]
        else:
            raise Exception("No hay clínicas configuradas en el sistema")
    
    # Buscar contacto existente por teléfono y clínica
    existing = sb.table("contacts").select("*").eq("phone", phone_normalized).eq("clinic_id", clinic_id).execute()
    
    if existing.data:
        # Contacto existe, actualizar última actividad
        contact = existing.data[0]
        sb.table("contacts").update({
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", contact["id"]).execute()
        
        # Verificar/crear canal de WhatsApp si no existe
        ensure_whatsapp_channel(sb, contact["id"], phone_normalized)
        
        return contact
    else:
        # Crear nuevo contacto
        now = datetime.now(timezone.utc).isoformat()
        new_contact = sb.table("contacts").insert({
            "clinic_id": clinic_id,
            "phone": phone_normalized,
            "full_name": f"Cliente WhatsApp {phone_normalized[-4:]}",  # Nombre temporal
            "source": "whatsapp",
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now
        }).execute()
        
        contact = new_contact.data[0]
        
        # Crear canal de WhatsApp para el nuevo contacto
        ensure_whatsapp_channel(sb, contact["id"], phone_normalized)
        
        return contact

def ensure_whatsapp_channel(sb, contact_id: str, phone: str):
    """
    Asegura que existe un canal de WhatsApp para el contacto.
    """
    # Verificar si ya existe el canal
    existing_channel = sb.table("contact_channels").select("*").eq("contact_id", contact_id).eq("channel_type", "whatsapp").execute()
    
    if not existing_channel.data:
        # Crear canal de WhatsApp
        sb.table("contact_channels").insert({
            "contact_id": contact_id,
            "channel_type": "whatsapp",
            "channel_value": phone,
            "is_primary": True,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

def get_contact_by_phone(sb, phone: str, clinic_id: str) -> Optional[dict]:
    """
    Obtiene un contacto por número de teléfono y clínica.
    """
    phone_normalized = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    result = sb.table("contacts").select("*").eq("phone", phone_normalized).eq("clinic_id", clinic_id).execute()
    return result.data[0] if result.data else None

def update_contact_name(sb, contact_id: str, full_name: str):
    """
    Actualiza el nombre completo de un contacto.
    """
    sb.table("contacts").update({
        "full_name": full_name.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", contact_id).execute()
