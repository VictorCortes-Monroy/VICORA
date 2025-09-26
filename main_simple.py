# main_simple.py - Versión ultra simple para Railway
import os
from fastapi import FastAPI, Request, HTTPException, Query

app = FastAPI(title="VICORA Backend")

@app.get("/")
async def root():
    return {"status": "ok", "message": "VICORA API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    """Endpoint de prueba para verificar que la app funciona"""
    return {
        "status": "ok", 
        "message": "VICORA API funcionando",
        "webhook_url": "/webhooks/whatsapp",
        "verify_token": os.environ.get("WHATSAPP_VERIFY_TOKEN", "mi-token-secreto-vicora-2024")
    }

@app.get("/test-supabase")
async def test_supabase():
    """Endpoint para probar la conexión con Supabase"""
    try:
        from supabase import create_client, Client
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "status": "error",
                "message": "Variables de Supabase no configuradas",
                "supabase_url": bool(supabase_url),
                "supabase_key": bool(supabase_key)
            }
        
        # Probar conexión
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Probar consulta simple
        result = supabase.table("contacts").select("*").limit(1).execute()
        
        return {
            "status": "success",
            "message": "Conexión con Supabase exitosa",
            "supabase_url": supabase_url,
            "contacts_count": len(result.data),
            "first_contact": result.data[0] if result.data else None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando con Supabase: {str(e)}",
            "supabase_url": os.environ.get("SUPABASE_URL"),
            "supabase_key": bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
        }

@app.get("/data")
async def get_data():
    """Endpoint para ver los datos guardados en Supabase"""
    try:
        from supabase import create_client, Client
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"error": "Variables de Supabase no configuradas"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Obtener contactos
        contacts = supabase.table("contacts").select("*").execute()
        
        # Obtener conversaciones
        conversations = supabase.table("conversations").select("*").execute()
        
        # Obtener mensajes
        messages = supabase.table("messages").select("*").order("created_at", desc=True).limit(10).execute()
        
        return {
            "contacts": contacts.data,
            "conversations": conversations.data,
            "messages": messages.data,
            "counts": {
                "contacts": len(contacts.data),
                "conversations": len(conversations.data),
                "messages": len(messages.data)
            }
        }
        
    except Exception as e:
        return {"error": f"Error obteniendo datos: {str(e)}"}

# Webhook de WhatsApp
@app.get("/webhooks/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"), 
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    mode: str = Query(None),
    challenge: str = Query(None),
    token: str = Query(None)
):
    """Verificación del webhook de WhatsApp"""
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "mi-token-secreto-vicora-2024")
    
    # Usar parámetros con prefijo hub. si están disponibles, sino usar los normales
    actual_mode = hub_mode or mode
    actual_challenge = hub_challenge or challenge
    actual_token = hub_verify_token or token
    
    # Debug logs
    print(f"🔍 DEBUG: hub_mode={hub_mode}, hub_challenge={hub_challenge}, hub_verify_token={hub_verify_token}")
    print(f"🔍 DEBUG: mode={mode}, challenge={challenge}, token={token}")
    print(f"🔍 DEBUG: actual_mode={actual_mode}, actual_challenge={actual_challenge}, actual_token={actual_token}")
    print(f"🔍 DEBUG: verify_token={verify_token}")
    
    if actual_mode == "subscribe" and actual_token == verify_token:
        print(f"✅ Verificación exitosa, devolviendo challenge: {actual_challenge}")
        return int(actual_challenge)
    
    print(f"❌ Verificación fallida: actual_mode={actual_mode}, actual_token={actual_token}")
    raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhooks/whatsapp")
async def receive_webhook(request: Request):
    """Recibir mensajes de WhatsApp"""
    try:
        body = await request.json()
        print(f"📱 Mensaje recibido: {body}")
        
        # Procesar el mensaje de WhatsApp
        entries = body.get("entry", [])
        
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])
                
                for message in messages:
                    if message.get("type") != "text":
                        continue
                        
                    text = message["text"]["body"]
                    from_number = message["from"]
                    message_id = message["id"]
                    
                    print(f"📝 Procesando mensaje: {text} de {from_number}")
                    
                    # Guardar en Supabase
                    try:
                        from supabase import create_client, Client
                        
                        supabase_url = os.environ.get("SUPABASE_URL")
                        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
                        
                        if supabase_url and supabase_key:
                            supabase: Client = create_client(supabase_url, supabase_key)
                            
                            # Crear/actualizar contacto
                            contact_data = {
                                "clinic_id": "clinic-test-001",  # ID genérico para pruebas
                                "phone": from_number,
                                "full_name": contacts[0]["profile"]["name"] if contacts else f"Usuario {from_number}"
                            }
                            
                            # Buscar contacto existente
                            existing_contact = supabase.table("contacts").select("*").eq("phone", from_number).execute()
                            
                            if existing_contact.data:
                                contact = existing_contact.data[0]
                                print(f"👤 Contacto existente: {contact['full_name']}")
                            else:
                                # Crear nuevo contacto
                                contact = supabase.table("contacts").insert(contact_data).execute().data[0]
                                print(f"👤 Nuevo contacto creado: {contact['full_name']}")
                            
                            # Crear/actualizar conversación
                            conversation_data = {
                                "clinic_id": "clinic-test-001",  # ID genérico para pruebas
                                "contact_id": contact["id"],
                                "channel": "whatsapp",
                                "status": "open"
                            }
                            
                            existing_conversation = supabase.table("conversations").select("*").eq("contact_id", contact["id"]).eq("channel", "whatsapp").eq("status", "open").execute()
                            
                            if existing_conversation.data:
                                conversation = existing_conversation.data[0]
                                print(f"💬 Conversación existente: {conversation['id']}")
                            else:
                                # Crear nueva conversación
                                conversation = supabase.table("conversations").insert(conversation_data).execute().data[0]
                                print(f"💬 Nueva conversación creada: {conversation['id']}")
                            
                            # Guardar mensaje
                            message_data = {
                                "clinic_id": "clinic-test-001",  # ID genérico para pruebas
                                "conversation_id": conversation["id"],
                                "contact_id": contact["id"],
                                "direction": "inbound",
                                "channel": "whatsapp",
                                "content": text,
                                "external_message_id": message_id,
                                "status": "delivered"
                            }
                            
                            saved_message = supabase.table("messages").insert(message_data).execute().data[0]
                            print(f"💾 Mensaje guardado: {saved_message['id']}")
                            
                            # Responder automáticamente
                            response_text = f"Hola {contact['full_name']}! Recibí tu mensaje: '{text}'. ¿En qué puedo ayudarte?"
                            
                            # Guardar respuesta
                            response_data = {
                                "clinic_id": "clinic-test-001",  # ID genérico para pruebas
                                "conversation_id": conversation["id"],
                                "contact_id": contact["id"],
                                "direction": "outbound",
                                "channel": "whatsapp",
                                "content": response_text,
                                "status": "sent"
                            }
                            
                            supabase.table("messages").insert(response_data).execute()
                            print(f"📤 Respuesta enviada: {response_text}")
                            
                        else:
                            print("❌ Variables de Supabase no configuradas")
                            
                    except Exception as e:
                        print(f"❌ Error guardando en Supabase: {e}")
        
        return {"status": "received", "message": "Mensaje procesado y guardado"}
        
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
