# VICORA - Chatbot WhatsApp para Clínicas Estéticas

MVP de automatización para atención inicial por WhatsApp en clínicas estéticas. Contesta preguntas frecuentes, toma reservas y envía recordatorios automáticos.

## 🚀 Características

- **Webhook WhatsApp**: Recibe y procesa mensajes de WhatsApp Cloud API
- **Chatbot inteligente**: Maneja FAQs y flujo completo de reservas
- **Gestión de citas**: Consulta disponibilidad y crea citas automáticamente
- **Recordatorios**: Sistema de notificaciones automáticas 24h antes
- **Base de datos**: Integración completa con Supabase
- **API REST**: Endpoints para gestión de mensajes y citas

## 🛠 Stack Tecnológico

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Base de datos**: Supabase (PostgreSQL + Auth + Realtime)
- **Integraciones**: WhatsApp Cloud API (Meta)
- **HTTP Client**: httpx
- **Scheduler**: Endpoints internos + cron externo

## 📋 Requisitos Previos

1. **Proyecto Supabase** configurado
2. **WhatsApp Business Account** con Cloud API
3. **Python 3.11+**
4. **Variables de entorno** configuradas

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd VICORA
```

### 2. Crear entorno virtual

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia `env.example` a `.env` y completa los valores:

```bash
cp env.example .env
```

Edita `.env`:

```env
# Configuración de Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-aqui

# Configuración de WhatsApp Cloud API
WHATSAPP_TOKEN=tu-whatsapp-access-token
WHATSAPP_PHONE_ID=tu-phone-number-id
WHATSAPP_VERIFY_TOKEN=tu-verify-token-personalizado

# Configuración del entorno
ENVIRONMENT=development
DEBUG=true
```

### 5. Configurar Supabase

#### Tablas necesarias:

```sql
-- Clínicas
CREATE TABLE clinics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contactos
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    phone TEXT NOT NULL,
    full_name TEXT,
    source TEXT DEFAULT 'whatsapp',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Canales de contacto
CREATE TABLE contact_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id),
    channel_type TEXT NOT NULL,
    channel_value TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversaciones
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    contact_id UUID REFERENCES contacts(id),
    channel TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    context_data JSONB,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    close_reason TEXT
);

-- Mensajes
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    conversation_id UUID REFERENCES conversations(id),
    contact_id UUID REFERENCES contacts(id),
    staff_id UUID,
    direction TEXT NOT NULL, -- 'inbound' or 'outbound'
    channel TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    external_message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Servicios
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    name TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    price DECIMAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Configuración de clínicas
CREATE TABLE clinic_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    business_hours JSONB,
    booking_window_days INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Citas
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    contact_id UUID REFERENCES contacts(id),
    service_id UUID REFERENCES services(id),
    start_at TIMESTAMP WITH TIME ZONE NOT NULL,
    end_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT DEFAULT 'confirmed',
    source TEXT DEFAULT 'whatsapp',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recordatorios
CREATE TABLE appointment_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    appointment_id UUID REFERENCES appointments(id),
    channel TEXT NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Función para verificar solapamiento:

```sql
CREATE OR REPLACE FUNCTION fn_check_overlap(
    p_clinic_id UUID,
    p_start TIMESTAMP WITH TIME ZONE,
    p_end TIMESTAMP WITH TIME ZONE
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM appointments 
        WHERE clinic_id = p_clinic_id 
        AND status IN ('confirmed', 'pending')
        AND (
            (start_at <= p_start AND end_at > p_start) OR
            (start_at < p_end AND end_at >= p_end) OR
            (start_at >= p_start AND end_at <= p_end)
        )
    );
END;
$$ LANGUAGE plpgsql;
```

### 6. Datos de prueba

```sql
-- Insertar clínica de prueba
INSERT INTO clinics (name) VALUES ('Clínica Estética Demo');

-- Insertar servicios de prueba
INSERT INTO services (clinic_id, name, duration_min, price) 
SELECT c.id, 'Botox Facial', 60, 150000 FROM clinics c LIMIT 1;

INSERT INTO services (clinic_id, name, duration_min, price) 
SELECT c.id, 'Limpieza Facial', 90, 80000 FROM clinics c LIMIT 1;

-- Configuración básica
INSERT INTO clinic_settings (clinic_id, business_hours, booking_window_days)
SELECT c.id, '{"monday": {"start": "09:00", "end": "19:00"}}', 30 FROM clinics c LIMIT 1;
```

## 🏃‍♂️ Ejecutar el proyecto

### Desarrollo local

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔗 Configurar Webhook de WhatsApp

1. **Configurar webhook URL** en Meta Developers:
   - URL: `https://tu-dominio.com/webhooks/whatsapp`
   - Verify Token: El valor de `WHATSAPP_VERIFY_TOKEN`

2. **Suscribirse a eventos**:
   - `messages`
   - `message_deliveries` (opcional)

## ⏰ Configurar Scheduler

Para los recordatorios automáticos, configurar un cron job que llame cada 5-10 minutos:

```bash
# Ejemplo con cURL
*/10 * * * * curl -X POST https://tu-dominio.com/internal/scheduler/run
```

## 📡 API Endpoints

### Webhooks
- `GET /webhooks/whatsapp` - Verificación de webhook
- `POST /webhooks/whatsapp` - Recibir mensajes

### Citas
- `GET /api/appointments/availability` - Consultar disponibilidad
- `POST /api/appointments` - Crear cita

### Mensajes
- `GET /api/messages/conversations/{id}` - Obtener mensajes
- `GET /api/messages/contacts/{id}/conversations` - Conversaciones de contacto
- `POST /api/messages/send` - Enviar mensaje manual

### Scheduler
- `POST /internal/scheduler/run` - Ejecutar recordatorios

## 🧪 Pruebas

### Flujo de reserva por WhatsApp:

1. Envía "Hola" al número de WhatsApp configurado
2. Responde "quiero agendar"
3. Selecciona un tratamiento: "botox"
4. Especifica fecha: "mañana"
5. Especifica hora: "10:00"
6. Confirma: "confirmar"

## 🚀 Despliegue

### Variables de entorno en producción:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key
WHATSAPP_TOKEN=tu-token-produccion
WHATSAPP_PHONE_ID=tu-phone-id
WHATSAPP_VERIFY_TOKEN=tu-verify-token
ENVIRONMENT=production
DEBUG=false
```

### Plataformas recomendadas:
- **Render**: Autodeploy desde Git
- **Railway**: Configuración simple
- **Fly.io**: Global edge deployment

## 🔒 Seguridad

- Usa **Service Role Key** solo en el backend
- Valida todos los webhooks de WhatsApp
- Implementa rate limiting en producción
- Usa HTTPS en todos los endpoints

## 📝 Notas del MVP

### Incluido:
- ✅ Webhook WhatsApp funcional
- ✅ Chatbot con flujo de reservas completo
- ✅ Gestión de disponibilidad y citas
- ✅ Sistema de recordatorios
- ✅ Persistencia en Supabase

### Fuera de alcance:
- ❌ Panel de administración web
- ❌ Integración con otros canales
- ❌ IA semántica avanzada
- ❌ Pagos online
- ❌ Sincronización con Google Calendar

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.
