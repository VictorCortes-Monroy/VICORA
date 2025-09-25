# /services/whatsapp.py
import os
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.token = os.environ.get("WHATSAPP_TOKEN")
        self.phone_id = os.environ.get("WHATSAPP_PHONE_ID")
        self.base_url = "https://graph.facebook.com/v19.0"
        
        if not self.token or not self.phone_id:
            raise ValueError("WHATSAPP_TOKEN y WHATSAPP_PHONE_ID son requeridos")

    async def send_text_message(self, to: str, text: str) -> Dict[str, Any]:
        """
        Envía un mensaje de texto por WhatsApp.
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando mensaje WhatsApp: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado enviando WhatsApp: {e}")
            raise

    async def send_template_message(self, to: str, template_name: str, language: str = "es", components: Optional[list] = None) -> Dict[str, Any]:
        """
        Envía un mensaje de plantilla por WhatsApp.
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language}
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando plantilla WhatsApp: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado enviando plantilla: {e}")
            raise

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca un mensaje como leído.
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error marcando mensaje como leído: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado marcando como leído: {e}")
            raise

# Instancia global del servicio
whatsapp_service = WhatsAppService() if os.environ.get("WHATSAPP_TOKEN") else None

# Funciones de conveniencia para compatibilidad
async def send_whatsapp_text(text: str, to: str) -> Dict[str, Any]:
    """
    Función de conveniencia para enviar texto por WhatsApp.
    """
    if not whatsapp_service:
        raise ValueError("WhatsApp service no está configurado")
    
    return await whatsapp_service.send_text_message(to, text)

async def send_whatsapp_template(to: str, template_name: str, language: str = "es", components: Optional[list] = None) -> Dict[str, Any]:
    """
    Función de conveniencia para enviar plantilla por WhatsApp.
    """
    if not whatsapp_service:
        raise ValueError("WhatsApp service no está configurado")
    
    return await whatsapp_service.send_template_message(to, template_name, language, components)
