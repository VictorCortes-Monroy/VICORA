# main_simple.py - Versión ultra simple para Railway
import os
from fastapi import FastAPI, Request, HTTPException

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

# Webhook de WhatsApp
@app.get("/webhooks/whatsapp")
async def verify_webhook(mode: str = None, challenge: str = None, token: str = None):
    """Verificación del webhook de WhatsApp"""
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "mi-token-secreto-vicora-2024")
    
    # Debug logs
    print(f"🔍 DEBUG: mode={mode}, challenge={challenge}, token={token}")
    print(f"🔍 DEBUG: verify_token={verify_token}")
    
    if mode == "subscribe" and token == verify_token:
        print(f"✅ Verificación exitosa, devolviendo challenge: {challenge}")
        return int(challenge)
    
    print(f"❌ Verificación fallida: mode={mode}, token={token}")
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
