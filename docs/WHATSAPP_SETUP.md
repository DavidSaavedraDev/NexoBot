# Configuración de WhatsApp Cloud API para NexoBot

Esta guía configura el primer flujo real:

```text
Usuario de WhatsApp -> Meta -> POST /webhook -> NexoBot -> Graph API -> Usuario
```

No se necesita OpenAI para esta prueba. NexoBot responde con reglas FAQ
locales.

## 1. Requisitos

- Una cuenta de Facebook/Meta.
- Un número de teléfono que pueda usarse para WhatsApp Business.
- Python 3.12+ y las dependencias del proyecto.
- `ngrok` instalado y autenticado.
- Una URL pública HTTPS para el webhook.

Durante el desarrollo, Meta ofrece números y destinatarios de prueba. En modo
de prueba, agrega tu propio número como destinatario autorizado en WhatsApp
> API Setup.

## 2. Crear la aplicación en Meta Developers

1. Abre [Meta for Developers](https://developers.facebook.com/).
2. Inicia sesión y entra en **My Apps**.
3. Selecciona **Create App**.
4. Elige un tipo de aplicación orientado a negocio y completa nombre, correo y
   cuenta Business si Meta lo solicita.
5. En el panel de la app selecciona **Add Product** y agrega **WhatsApp**.
6. En **WhatsApp > API Setup** selecciona o crea una cuenta de WhatsApp
   Business.

Guarda estos identificadores:

- **Phone Number ID**: identifica el número que envía mensajes.
- **WhatsApp Business Account ID (WABA ID)**: identifica la cuenta empresarial.
- **App ID** y **App Secret**: pertenecen a la aplicación, pero no son
  necesarios para este MVP si usas un token de acceso correctamente generado.

El **Phone Number ID** se encuentra en **WhatsApp > API Setup**, junto al número
de prueba o número conectado. El **WABA ID** suele aparecer en **WhatsApp >
Getting Started**, **Business Settings** o en la información de la cuenta
Business.

## 3. Obtener un token temporal

En **WhatsApp > API Setup**:

1. Copia el token temporal mostrado por Meta.
2. Copia el **Phone Number ID**.
3. En **To**, agrega el número de teléfono que recibirá las pruebas.
4. Envía primero un mensaje desde el panel para confirmar que Meta puede
   entregar mensajes.

El token temporal expira y no debe usarse como credencial permanente.

Configura localmente el token sin incluirlo en Git:

```env
WHATSAPP_ACCESS_TOKEN=token-temporal-de-meta
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=un-secreto-largo-generado-por-ti
WHATSAPP_API_VERSION=v21.0
WHATSAPP_ENABLED=true
```

`WHATSAPP_VERIFY_TOKEN` no lo proporciona Meta: es un secreto que eliges tú y
debe coincidir exactamente con el valor usado al registrar el webhook.

## 4. Obtener un token permanente

Para una integración persistente no dependas del token temporal. La opción
recomendada es crear un **System User** en **Business Settings**:

1. Abre **Business Settings > Users > System Users**.
2. Selecciona **Add** y crea un usuario de sistema con acceso administrativo
   apropiado para la cuenta Business.
3. En **Assign Assets**, asigna la cuenta de WhatsApp Business y los permisos
   necesarios.
4. En **Generate New Token**, selecciona la aplicación de Meta.
5. Concede, como mínimo, los permisos que Meta indique para enviar y gestionar
   mensajes de WhatsApp Business.
6. Copia el token una sola vez y guárdalo en un gestor de secretos.

El nombre exacto de permisos y pantallas puede cambiar según la versión de
Meta. No publiques el token ni lo pongas en `.env.example`, capturas o logs.
En producción usa un secret manager y rota el token si se expone.

## 5. Configurar el webhook

### 5.1 Arrancar NexoBot

Desde la raíz del proyecto:

```powershell
python -m alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Comprueba:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

### 5.2 Exponerlo con ngrok

En otra terminal:

```powershell
ngrok http 8000
```

Usa la URL HTTPS que muestra ngrok, por ejemplo:

```text
https://abc123.ngrok-free.app
```

La URL del callback será:

```text
https://abc123.ngrok-free.app/webhook
```

### 5.3 Registrar URL y token en Meta

En **WhatsApp > Configuration** o en la configuración del producto WhatsApp:

1. Selecciona **Edit** en Webhook.
2. Introduce la **Callback URL** HTTPS terminada en `/webhook`.
3. Introduce exactamente el valor de `WHATSAPP_VERIFY_TOKEN`.
4. Pulsa **Verify and Save**.
5. Suscribe el campo **messages**.

Meta hará una solicitud GET con `hub.mode`, `hub.challenge` y
`hub.verify_token`. NexoBot devuelve el challenge como texto plano.

## 6. Diagnóstico seguro

Consulta:

```text
GET /api/debug/whatsapp
```

Ejemplo con `curl`:

```powershell
curl http://127.0.0.1:8000/api/debug/whatsapp
```

El endpoint informa:

- si WhatsApp está habilitado;
- si están configuradas las variables;
- versión Graph API;
- si el Phone Number ID y token están presentes;
- si el token fue aceptado por Graph API;
- estado de conexión;
- tiempo de respuesta.

Nunca devuelve el token ni el valor del verify token. Con
`WHATSAPP_ENABLED=false` no realiza llamadas externas y devuelve estado
`disabled`. Si faltan credenciales con el servicio habilitado, devuelve
`invalid_configuration` sin enviar mensajes.

## 7. Prueba end-to-end

### Caso 1: saludo

1. Desde un número autorizado escribe `hola`.
2. Meta debe enviar un POST a NexoBot.
3. NexoBot registra el cliente, conversación y mensaje entrante.
4. NexoBot responde:

```text
Hola, somos Mi negocio. ¿En qué podemos ayudarte?
```

### Caso 2: horario

Envía:

```text
¿Cuál es el horario?
```

Resultado esperado:

```text
Nuestro horario de atención es de lunes a viernes de 9:00 a 18:00.
```

### Caso 3: precios

Envía:

```text
¿Cuáles son sus precios?
```

Resultado esperado:

```text
Cuéntanos qué servicio necesitas y te compartiremos la información.
```

### Caso 4: texto desconocido

Envía cualquier texto que no coincida con las reglas anteriores.

Resultado esperado:

```text
Gracias por escribirnos. Un miembro del equipo te responderá pronto.
```

Puedes revisar los registros en:

```text
GET /api/customers
GET /api/conversations
GET /api/messages
```

El mismo `whatsapp_message_id` reenviado por Meta no crea mensajes duplicados.

## 8. Logs específicos

NexoBot registra JSON con timestamp UTC, nivel, `request_id`,
`whatsapp_message_id`, `customer_id`, `conversation_id` y duración en
milisegundos.

Eventos principales:

- `Mensaje recibido desde WhatsApp`.
- `Mensaje entrante registrado`.
- `Mensaje enviado por WhatsApp`.
- `Error API Meta al enviar mensaje`.
- `Error API Meta durante diagnóstico`.

No se registra el access token ni el contenido de headers de autorización.

## 9. Checklist de despliegue

- [ ] Aplicación creada en Meta Developers.
- [ ] WhatsApp agregado como producto.
- [ ] WABA ID documentado.
- [ ] Phone Number ID verificado.
- [ ] Número receptor autorizado para pruebas.
- [ ] Token temporal probado.
- [ ] Token permanente creado para el entorno estable.
- [ ] `WHATSAPP_VERIFY_TOKEN` generado y almacenado como secreto.
- [ ] `WHATSAPP_ACCESS_TOKEN` almacenado como secreto.
- [ ] `WHATSAPP_ENABLED=true`.
- [ ] `WHATSAPP_API_VERSION` soportada por la cuenta.
- [ ] Migraciones ejecutadas.
- [ ] Servicio accesible por HTTPS.
- [ ] Webhook `/webhook` verificado en Meta.
- [ ] Campo `messages` suscrito.
- [ ] `GET /api/debug/whatsapp` devuelve `connected`.
- [ ] Casos manuales de saludo, horario, precio y desconocido validados.
- [ ] Logs no contienen tokens.
- [ ] Endpoint administrativo protegido antes de publicar el servicio.
- [ ] ngrok sustituido por dominio y TLS de producción.

## 10. Solución de problemas

### Meta no verifica el webhook

- Confirma que la URL termina en `/webhook`.
- Confirma que es HTTPS y está accesible desde Internet.
- Confirma que el token coincide exactamente.
- Revisa que el proceso Uvicorn y ngrok sigan activos.
- Observa los logs de ngrok y la respuesta GET.

### `invalid_configuration`

Comprueba las cinco variables y especialmente:

- `WHATSAPP_ENABLED=true`;
- `WHATSAPP_ACCESS_TOKEN` no vacío;
- `WHATSAPP_PHONE_NUMBER_ID` correcto;
- `WHATSAPP_VERIFY_TOKEN` configurado;
- `WHATSAPP_API_VERSION` con formato como `v21.0`.

### `unavailable` o `token_valid=false`

- El token puede estar expirado o revocado.
- El token puede no tener permisos para la WABA.
- El Phone Number ID puede pertenecer a otra aplicación.
- Puede existir un problema de red, DNS o rate limit.
- Ejecuta de nuevo el diagnóstico y consulta el código HTTP de Meta en los
  logs sin revelar el token.

### El mensaje entra, pero no sale

- Comprueba `WHATSAPP_ENABLED=true`.
- Comprueba que el número receptor esté autorizado en modo prueba.
- Comprueba el Phone Number ID, no el número de teléfono visible.
- Revisa `Error API Meta al enviar mensaje`.
- Confirma que el token tiene permisos de mensajería.

### Se reciben estados, pero no textos

Es normal. NexoBot ignora eventos que no contienen `messages` de tipo `text`.

### Se reciben duplicados

Meta puede reenviar eventos. NexoBot usa `whatsapp_message_id` como clave
idempotente y no vuelve a generar la respuesta para un mensaje ya procesado.
