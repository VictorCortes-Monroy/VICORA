# railway.py - Configuración para Railway
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración específica para Railway
if os.getenv("RAILWAY_ENVIRONMENT"):
    # Railway detecta automáticamente el puerto
    PORT = os.getenv("PORT", "8000")
    print(f"🚀 Ejecutando en Railway en puerto {PORT}")
else:
    print("🔧 Ejecutando en desarrollo local")
