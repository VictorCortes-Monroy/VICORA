#!/usr/bin/env python3
# start.py - Script de inicio para Railway
import os
import uvicorn
from main_simple import app

if __name__ == "__main__":
    # Obtener el puerto de Railway o usar 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Iniciando VICORA en puerto {port}")
    
    # Iniciar el servidor
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
