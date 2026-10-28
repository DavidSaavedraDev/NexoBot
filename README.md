# NexoBot

Asistente virtual para pequeños negocios sobre WhatsApp Cloud API. NexoBot
recibe mensajes, registra clientes y conversaciones, responde preguntas
frecuentes configurables y ofrece un endpoint local para demostraciones sin
depender de Meta.

> Estado: MVP funcional preparado para pruebas locales y una integración
> controlada con WhatsApp Cloud API. OpenAI, frontend y autenticación de
> usuarios finales todavía no forman parte del proyecto.

Backend MVP de un asistente virtual para pequeños negocios sobre WhatsApp Cloud
API. El sistema recibe mensajes, registra clientes y conversaciones, responde
preguntas frecuentes y deja una base preparada para una futura integración con
OpenAI. OpenAI, frontend y autenticación no forman parte de esta fase.

## Arquitectura

```text
backend/
├── main.py                 # Aplicación FastAPI, lifespan y middleware
├── api/                    # Webhook de WhatsApp y endpoints administrativos
├── config/                 # Configuración tipada desde variables de entorno
├── database/               # Sesiones, base declarativa y datos demo
├── models/                 # Business, Customer, Conversation y Message
├── repositories/           # Acceso a datos y control de idempotencia
├── schemas/                # Contratos Pydantic
├── services/               # FAQ, webhook y cliente WhatsApp
└── utils/                  # Logging estructurado
alembic/
└── versions/               # Migraciones versionadas
scripts/
└── setup_dev.py            # Preparación reproducible del entorno
tests/
└── test_mvp.py             # Pruebas de API, persistencia e idempotencia
```

La lógica HTTP no accede directamente al ORM: los casos de uso pasan por
servicios y repositorios. SQLite se usa en desarrollo y las migraciones
permiten cambiar a PostgreSQL sin depender de `create_all()` en producción.
Los secretos se cargan desde variables de entorno.

## Instalación

Requiere Python 3.12 o superior.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Configuración

Edita `.env`:

```env
DATABASE_URL=sqlite:///./nexobot.db
WHATSAPP_VERIFY_TOKEN=change-me
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ENABLED=false
```

`WHATSAPP_ENABLED=false` permite probar el flujo sin enviar mensajes reales.
Para WhatsApp Cloud API se requieren el token, el identificador de teléfono y
`WHATSAPP_ENABLED=true`.

La guía completa para Meta, tokens, webhook, ngrok y la primera prueba real está
en [docs/WHATSAPP_SETUP.md](./docs/WHATSAPP_SETUP.md).

## Migraciones

Crear o actualizar la base de datos:

```powershell
python -m alembic upgrade head
```

Consultar la versión:

```powershell
python -m alembic current
```

Crear una nueva migración después de modificar modelos:

```powershell
python -m alembic revision --autogenerate -m "describe el cambio"
```

Retroceder una migración:

```powershell
python -m alembic downgrade -1
```

La migración inicial `0001_initial` crea todas las tablas, índices y la
restricción única de `messages.whatsapp_message_id`.

## Datos demo y ejecución

El script prepara la base, ejecuta migraciones, inserta un negocio, cinco
clientes, cinco conversaciones y mensajes de ejemplo, y verifica `/health`:

```powershell
python scripts/setup_dev.py
uvicorn backend.main:app --reload
```

Endpoints:

- `GET /health`
- `GET /webhook` para la verificación de Meta
- `POST /webhook` para mensajes Cloud API
- `GET /api/customers?page=1&page_size=20`
- `GET /api/conversations?page=1&page_size=20`
- `GET /api/messages?page=1&page_size=20`
- `GET /api/business` (requiere `X-API-Key`)
- `PUT /api/business` (requiere `X-API-Key`)
- `POST /api/demo/message` para simular mensajes localmente sin HMAC ni Meta
- Swagger: `http://127.0.0.1:8000/docs`
- Diagnóstico WhatsApp: `GET /api/debug/whatsapp`

Los endpoints administrativos requieren el header `X-API-Key` con el valor de
`ADMIN_API_KEY`. El endpoint local de demo no requiere API key porque está
destinado exclusivamente al desarrollo local; no debe exponerse públicamente.

### Demostración local

Con la aplicación ejecutándose, abre Swagger en
`http://127.0.0.1:8000/docs`, selecciona `POST /api/demo/message` y envía:

```json
{
  "phone": "573001112233",
  "name": "Carlos",
  "message": "hola"
}
```

La respuesta se genera con la misma lógica del webhook real y se guardan el
cliente, la conversación, el mensaje entrante y el mensaje saliente. La ruta
local no llama a Meta, por lo que funciona aunque WhatsApp Cloud API esté
deshabilitado o todavía no tenga credenciales reales.

Para pruebas locales con Ngrok:

```powershell
ngrok http 8000
```

Configura en Meta `https://<dominio-ngrok>/webhook` y el mismo
`WHATSAPP_VERIFY_TOKEN` del archivo `.env`.

## Pruebas

```powershell
pytest -q
```

La suite comprueba health, challenge de Meta, payload de WhatsApp, creación de
clientes/conversaciones/mensajes, idempotencia y paginación administrativa.

## Observabilidad

Cada respuesta HTTP incluye `X-Request-ID` y el logging estructurado registra:

- timestamp UTC;
- nivel y logger;
- request ID;
- customer ID;
- conversation ID;
- mensaje.

Los errores de integración HTTP, configuración de WhatsApp y base de datos se
registran con nivel `ERROR` y devuelven un error HTTP explícito.

## Troubleshooting

**`ModuleNotFoundError` al arrancar:** activa el entorno virtual y ejecuta
`pip install -r requirements.txt`.

**Alembic no encuentra la base:** comprueba `DATABASE_URL` y ejecuta
`python -m alembic upgrade head` desde la raíz del proyecto.

**Meta rechaza la verificación:** `hub.verify_token` debe coincidir exactamente
con `WHATSAPP_VERIFY_TOKEN`; el endpoint devuelve el challenge como texto plano.

**No se envían respuestas reales:** verifica `WHATSAPP_ENABLED`, el access token
y `WHATSAPP_PHONE_NUMBER_ID`. En desarrollo desactivado, el mensaje se registra
pero no se realiza ninguna llamada externa.

**Un mensaje aparece como ignorado:** WhatsApp puede reenviar eventos. Si el
`whatsapp_message_id` ya existe, el sistema devuelve `processed=false` sin
crear mensajes duplicados.
