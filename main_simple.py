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
        
        # Aquí procesarías el mensaje de WhatsApp
        # Por ahora solo devolvemos OK
        return {"status": "received", "message": "Mensaje procesado"}
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
