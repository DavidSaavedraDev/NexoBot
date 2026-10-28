# Demostración comercial para el primer cliente
+
+Este documento explica cómo presentar NexoBot a un cliente potencial en una
+demostración realista, sin necesidad de OpenAI ni de frontend.
+
+## 1. Objetivo de la demostración
+
+Mostrar a un cliente que NexoBot puede:
+
+- responder mensajes automáticos por WhatsApp;
+- registrar clientes y conversaciones;
+- adaptar respuestas a un negocio real;
+- responder dudas frecuentes sin intervención humana;
+- dar la apariencia de un sistema listo para comercializar.
+
+## 2. Negocio de la demo
+
+La configuración demo es:
+
+- Nombre: Peluquería Bella Estilo
+- Horario: Lunes a sábado de 8:00am a 6:00pm.
+- Dirección: Carrera 10 #15-22, Moniquirá.
+- Precios: corte hombre $20.000, corte mujer $35.000, barba $15.000.
+- Mensaje de bienvenida: Bienvenido a Peluquería Bella Estilo.
+
+## 3. Cargar la demo
+
+```powershell
+python scripts/load_demo_business.py
+```
+
+Luego valida:
+
+```powershell
+curl http://127.0.0.1:8000/api/business
+```
+
+## 4. Ejemplos de conversación para la demo
+
+### Conversación 1
+
+Cliente: Hola
+
+Bot: Bienvenido a Peluquería Bella Estilo. ¿En qué te podemos ayudar?
+
+### Conversación 2
+
+Cliente: ¿Cuánto vale un corte de cabello?
+
+Bot: El corte para hombre cuesta $20.000, el corte para mujer $35.000 y la barba $15.000.
+
+### Conversación 3
+
+Cliente: ¿Cuál es el horario?
+
+Bot: Atendemos de lunes a sábado de 8:00am a 6:00pm.
+
+### Conversación 4
+
+Cliente: ¿Dónde están ubicados?
+
+Bot: Estamos en Carrera 10 #15-22, Moniquirá.
+
+## 5. Cómo presentar la demo
+
+1. Muestra el valor comercial con una historia concreta: "un cliente escribiendo
+   desde WhatsApp y recibiendo información de precios y horario en segundos".
+2. Haz la demostración con el número de WhatsApp conectado a la app.
+3. Recorre los casos prácticos: saludo, horario, precios, ubicación, cita.
+4. Muestra que el negocio puede adaptarse a un cliente distinto mediante
+   `PUT /api/business`.
+5. Explica el crecimiento previsto: CRM, agenda, recordatorios, pagos,
+   dashboard, multiempresa y OpenAI.
+
+## 6. Qué destacar al cliente
+
+- Baja fricción para el cliente final.
+- Respuesta instantánea fuera del horario.
+- Ahorro en atención repetitiva.
+- Base preparada para crecer a SaaS.
+- Fácil personalización por negocio.
+
+## 7. Siguiente paso comercial
+
+Al final de la demo responde con una propuesta de valor clara:
+
+> NexoBot convierte WhatsApp en un canal comercial automatizado para pequeñas
+> empresas, reduciendo trabajo manual y mejorando la atención del cliente.
+
+## 8. Recomendación
+
+La demo debe centrarse en un caso de negocio sencillo y realista, y no en
+tecnología o arquitectura. El mensaje comercial debe ser claro: "tu negocio
+responde automáticamente a las preguntas más frecuentes por WhatsApp".
