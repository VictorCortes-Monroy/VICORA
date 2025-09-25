# /services/chatbot.py
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from services.availability import get_slots, book_appointment
from services.conversations import get_conversation_context, set_conversation_context

FAQS = {
    r"(precio|valen|cuánto).*botox": "El Botox facial tiene un valor desde $150.000. ¿Te gustaría reservar una evaluación gratuita?",
    r"(precio|valen|cuánto).*limpieza": "La Limpieza Facial tiene un valor desde $80.000. ¿Te gustaría agendar una cita?",
    r"(horario|abren|cierran)": "Atendemos de Lunes a Sábado, 09:00–19:00.",
    r"(direcci[oó]n|dónde)": "Estamos en Av. Ejemplo 1234, Piso 2, Ciudad."
}

SERVICIOS_DISPONIBLES = {
    "botox": {"name": "Botox Facial", "duration": 60, "price": "desde $150.000"},
    "limpieza": {"name": "Limpieza Facial", "duration": 90, "price": "desde $80.000"},
    "rellenos": {"name": "Rellenos Dérmicos", "duration": 45, "price": "desde $200.000"},
    "peeling": {"name": "Peeling Químico", "duration": 60, "price": "desde $120.000"}
}

def handle(text: str, sb=None, conversation_id: str = None, contact_id: str = None, clinic_id: str = None) -> str | None:
    """
    Maneja la lógica del chatbot con contexto de conversación.
    """
    t = text.lower().strip()
    
    # Obtener contexto de la conversación si está disponible
    context = {}
    if sb and conversation_id:
        try:
            conv_result = sb.table("conversations").select("context_data").eq("id", conversation_id).single().execute()
            if conv_result.data and conv_result.data.get("context_data"):
                context = conv_result.data["context_data"]
        except:
            context = {}
    
    # Estado actual del contexto
    current_state = context.get("state", "initial")
    
    # Manejo de confirmaciones y cancelaciones
    if re.search(r"(confirmar|sí|si|ok|vale)", t):
        if current_state == "appointment_pending":
            return _confirm_appointment(sb, context, conversation_id, contact_id, clinic_id)
        return "¡Perfecto! ¿En qué más puedo ayudarte?"
    
    if re.search(r"(cancelar|no|cambiar|reagendar)", t):
        if current_state in ["service_selected", "appointment_pending"]:
            _update_context(sb, conversation_id, {"state": "initial"})
            return "No hay problema. ¿Te gustaría agendar otro tratamiento o necesitas algo más?"
        return "Entendido. ¿En qué puedo ayudarte?"
    
    # Flujo principal basado en estado
    if current_state == "initial":
        return _handle_initial_state(t, sb, conversation_id)
    elif current_state == "awaiting_service":
        return _handle_service_selection(t, sb, conversation_id, clinic_id, contact_id)
    elif current_state == "service_selected":
        return _handle_date_selection(t, sb, conversation_id, context)
    elif current_state == "date_selected":
        return _handle_time_selection(t, sb, conversation_id, context, clinic_id)
    
    # Fallback para estados no reconocidos
    _update_context(sb, conversation_id, {"state": "initial"})
    return _handle_initial_state(t, sb, conversation_id)

def _handle_initial_state(text: str, sb, conversation_id: str) -> str:
    """Maneja el estado inicial de la conversación."""
    # Intención de reservar
    if re.search(r"(reservar|agendar|cita|hora)", text):
        _update_context(sb, conversation_id, {"state": "awaiting_service"})
        servicios_texto = "\n".join([f"• {info['name']} - {info['price']}" for info in SERVICIOS_DISPONIBLES.values()])
        return f"¡Perfecto! 🙌 Estos son nuestros tratamientos disponibles:\n\n{servicios_texto}\n\n¿Cuál te interesa?"
    
    # FAQs
    for pattern, answer in FAQS.items():
        if re.search(pattern, text):
            return answer
    
    # Saludo
    if re.search(r"(hola|buenos|buenas|saludos)", text):
        return "¡Hola! 👋 Soy el asistente de la clínica. Puedo ayudarte con información sobre tratamientos, precios y agendar citas. ¿En qué puedo ayudarte?"
    
    # Fallback
    return "Puedo ayudarte con información sobre tratamientos, precios y agendar citas. ¿Qué necesitas?"

def _handle_service_selection(text: str, sb, conversation_id: str, clinic_id: str, contact_id: str) -> str:
    """Maneja la selección de servicio."""
    # Buscar servicio mencionado
    servicio_seleccionado = None
    for key, info in SERVICIOS_DISPONIBLES.items():
        if key in text or info["name"].lower() in text:
            servicio_seleccionado = key
            break
    
    if servicio_seleccionado:
        # Obtener el service_id de la base de datos
        try:
            service_result = sb.table("services").select("id").eq("clinic_id", clinic_id).ilike("name", f"%{SERVICIOS_DISPONIBLES[servicio_seleccionado]['name']}%").limit(1).execute()
            if service_result.data:
                service_id = service_result.data[0]["id"]
                _update_context(sb, conversation_id, {
                    "state": "service_selected",
                    "selected_service": servicio_seleccionado,
                    "service_id": service_id
                })
                return f"Excelente elección: {SERVICIOS_DISPONIBLES[servicio_seleccionado]['name']} 💫\n\n¿Para qué fecha te gustaría agendar? (Por ejemplo: 'mañana', 'lunes', o '2024-01-15')"
            else:
                return "Lo siento, ese tratamiento no está disponible actualmente. ¿Te interesa algún otro de nuestra lista?"
        except:
            return "Hubo un error al verificar la disponibilidad. ¿Podrías intentar de nuevo?"
    else:
        return "No reconocí ese tratamiento. Por favor elige uno de la lista:\n" + "\n".join([f"• {info['name']}" for info in SERVICIOS_DISPONIBLES.values()])

def _handle_date_selection(text: str, sb, conversation_id: str, context: dict) -> str:
    """Maneja la selección de fecha."""
    # Parsear fecha del texto
    fecha_seleccionada = _parse_date_from_text(text)
    
    if fecha_seleccionada:
        _update_context(sb, conversation_id, {
            **context,
            "state": "date_selected",
            "selected_date": fecha_seleccionada.isoformat()
        })
        return f"Perfecto, para el {fecha_seleccionada.strftime('%A %d de %B')} 📅\n\n¿Qué horario prefieres? (Por ejemplo: '10:00', 'mañana', 'tarde')"
    else:
        return "No pude entender la fecha. ¿Podrías especificar? Por ejemplo: 'mañana', 'lunes próximo', o '15 de enero'"

def _handle_time_selection(text: str, sb, conversation_id: str, context: dict, clinic_id: str) -> str:
    """Maneja la selección de horario."""
    try:
        # Obtener slots disponibles
        service_id = context.get("service_id")
        selected_date = context.get("selected_date")
        
        if not service_id or not selected_date:
            _update_context(sb, conversation_id, {"state": "initial"})
            return "Hubo un error. Comencemos de nuevo. ¿Qué tratamiento te interesa?"
        
        slots_response = get_slots(sb, clinic_id, service_id, selected_date)
        available_slots = slots_response.get("slots", [])
        
        if not available_slots:
            return "Lo siento, no hay horarios disponibles para esa fecha. ¿Te gustaría elegir otra fecha?"
        
        # Buscar horario preferido o mostrar opciones
        preferred_time = _parse_time_preference(text)
        selected_slot = None
        
        if preferred_time:
            # Buscar slot más cercano al horario preferido
            for slot in available_slots:
                slot_hour = datetime.fromisoformat(slot["start_at"]).hour
                if abs(slot_hour - preferred_time) <= 1:  # Tolerancia de 1 hora
                    selected_slot = slot
                    break
        
        if selected_slot:
            # Mostrar confirmación
            start_time = datetime.fromisoformat(selected_slot["start_at"])
            _update_context(sb, conversation_id, {
                **context,
                "state": "appointment_pending",
                "selected_slot": selected_slot
            })
            return f"¡Perfecto! 🎉\n\nResumen de tu cita:\n• Tratamiento: {SERVICIOS_DISPONIBLES[context['selected_service']]['name']}\n• Fecha: {start_time.strftime('%A %d de %B')}\n• Hora: {start_time.strftime('%H:%M')}\n\n¿Confirmas la cita? (Responde 'confirmar' o 'cancelar')"
        else:
            # Mostrar horarios disponibles
            horarios_texto = "\n".join([
                f"• {datetime.fromisoformat(slot['start_at']).strftime('%H:%M')}"
                for slot in available_slots[:5]  # Mostrar máximo 5 opciones
            ])
            return f"Estos son los horarios disponibles:\n\n{horarios_texto}\n\n¿Cuál prefieres?"
    
    except Exception as e:
        _update_context(sb, conversation_id, {"state": "initial"})
        return "Hubo un error al consultar los horarios. ¿Podrías intentar de nuevo?"

def _confirm_appointment(sb, context: dict, conversation_id: str, contact_id: str, clinic_id: str) -> str:
    """Confirma y crea la cita."""
    try:
        selected_slot = context.get("selected_slot")
        service_id = context.get("service_id")
        selected_service = context.get("selected_service")
        
        if not all([selected_slot, service_id, selected_service]):
            return "Hubo un error con los datos de la cita. ¿Podrías intentar agendar de nuevo?"
        
        # Crear la cita
        appointment_payload = {
            "clinic_id": clinic_id,
            "contact_id": contact_id,
            "service_id": service_id,
            "start_at": selected_slot["start_at"],
            "end_at": selected_slot["end_at"]
        }
        
        appointment = book_appointment(sb, appointment_payload)
        
        # Limpiar contexto
        _update_context(sb, conversation_id, {"state": "initial"})
        
        start_time = datetime.fromisoformat(selected_slot["start_at"])
        return f"¡Cita confirmada! ✅\n\n📋 Detalles:\n• Tratamiento: {SERVICIOS_DISPONIBLES[selected_service]['name']}\n• Fecha: {start_time.strftime('%A %d de %B')}\n• Hora: {start_time.strftime('%H:%M')}\n\nTe enviaremos un recordatorio 24 horas antes. ¡Nos vemos pronto! 😊"
    
    except Exception as e:
        return "Hubo un error al confirmar la cita. Por favor intenta de nuevo o contacta directamente a la clínica."

def _update_context(sb, conversation_id: str, new_context: dict):
    """Actualiza el contexto de la conversación."""
    if sb and conversation_id:
        try:
            set_conversation_context(sb, conversation_id, new_context)
        except:
            pass  # Silently fail to avoid breaking the flow

def _parse_date_from_text(text: str) -> Optional[datetime]:
    """Parsea una fecha del texto del usuario."""
    text = text.lower()
    today = datetime.now().date()
    
    if "mañana" in text:
        return datetime.combine(today + timedelta(days=1), datetime.min.time())
    elif "hoy" in text:
        return datetime.combine(today, datetime.min.time())
    elif "lunes" in text:
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return datetime.combine(today + timedelta(days=days_ahead), datetime.min.time())
    elif "martes" in text:
        days_ahead = 1 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return datetime.combine(today + timedelta(days=days_ahead), datetime.min.time())
    # Agregar más días de la semana según necesidad
    
    # Intentar parsear formato YYYY-MM-DD
    import re
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), '%Y-%m-%d')
        except:
            pass
    
    return None

def _parse_time_preference(text: str) -> Optional[int]:
    """Parsea preferencia de horario del texto."""
    text = text.lower()
    
    if "mañana" in text:
        return 10  # 10:00 AM
    elif "tarde" in text:
        return 15  # 3:00 PM
    elif "medio" in text and "día" in text:
        return 12  # 12:00 PM
    
    # Buscar formato HH:MM o HH
    import re
    time_match = re.search(r'(\d{1,2}):?(\d{2})?', text)
    if time_match:
        hour = int(time_match.group(1))
        if 8 <= hour <= 19:  # Horario válido
            return hour
    
    return None
