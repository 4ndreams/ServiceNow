# 📋 GUÍA DE CONFIGURACIÓN — Reporte Semanal Automático
## Tickets Proyecto Workflow IT · AFP Capital

---

## PASO 1 — Obtener la API Key de Claude

1. Ve a https://console.anthropic.com
2. Crea una cuenta (con tu correo personal o corporativo)
3. Agrega una tarjeta de crédito (cobro por uso, ~$0.10 por reporte)
4. Ve a **API Keys** → **Create Key**
5. Copia la clave (empieza con `sk-ant-...`) → guárdala, la necesitas en el Paso 4

---

## PASO 2 — Crear cuenta GitHub y subir el código

1. Ve a https://github.com y crea una cuenta gratuita
2. Crea un repositorio nuevo:
   - Haz clic en **"New repository"**
   - Nombre: `reporte-workflow-it`
   - Visibilidad: **Private** (importante, tiene credenciales)
   - Clic en **"Create repository"**
3. Sube los archivos de esta carpeta al repositorio:
   - Puedes arrastrarlos directamente en la web de GitHub
   - O usar GitHub Desktop (más fácil): https://desktop.github.com
   - Archivos a subir:
     ```
     main.py
     sn_fetch.py
     claude_report.py
     send_email.py
     requirements.txt
     .github/workflows/reporte_semanal.yml
     ```

---

## PASO 3 — Configurar contraseña de app en Gmail

> Necesitas una cuenta Gmail para enviar los correos automáticamente.

1. Ve a tu cuenta Google: https://myaccount.google.com
2. Ve a **Seguridad** → **Verificación en 2 pasos** (actívala si no está)
3. Luego ve a **Seguridad** → **Contraseñas de aplicaciones**
4. En "Seleccionar aplicación" elige **Correo**
5. En "Seleccionar dispositivo" elige **Otro** → escribe "Reporte WorkflowIT"
6. Clic en **Generar**
7. Copia la contraseña de 16 caracteres → la necesitas en el Paso 4

---

## PASO 4 — Configurar los secretos en GitHub

> Los secretos son como variables de entorno seguras. GitHub nunca los muestra.

1. En tu repositorio de GitHub, ve a **Settings** → **Secrets and variables** → **Actions**
2. Haz clic en **"New repository secret"** y agrega estos 7 secretos:

| Nombre del secreto   | Valor que debes poner                                      |
|----------------------|------------------------------------------------------------|
| `SN_BASE_URL`        | `https://ibmsurachileprod.service-now.com`                 |
| `SN_USERNAME`        | Tu usuario de ServiceNow                                   |
| `SN_PASSWORD`        | Tu contraseña de ServiceNow                                |
| `ANTHROPIC_API_KEY`  | La clave que copiaste en el Paso 1 (`sk-ant-...`)          |
| `EMAIL_SENDER`       | Tu Gmail (`tucorreo@gmail.com`)                            |
| `EMAIL_APP_PASSWORD` | La contraseña de 16 caracteres del Paso 3                  |
| `EMAIL_RECIPIENTS`   | Correos separados por coma (`a@afp.cl,b@afp.cl,c@afp.cl`) |

---

## PASO 5 — Probar que funciona

1. En tu repositorio, ve a la pestaña **Actions**
2. Haz clic en **"Reporte Semanal Workflow IT"**
3. Haz clic en **"Run workflow"** → **"Run workflow"** (botón verde)
4. Espera ~2-3 minutos
5. Si el círculo queda verde ✅ → revisa tu correo, debería haber llegado
6. Si el círculo queda rojo ❌ → haz clic en el error y dime qué dice

---

## PASO 6 — Listo, es automático

A partir de aquí, **cada lunes a las 8:00 AM** (hora Chile) el reporte se genera
y llega a los correos que configuraste. No tienes que hacer nada más.

Puedes ver el historial de ejecuciones en la pestaña **Actions** de GitHub.

---

## Costos estimados

| Servicio      | Costo                                    |
|---------------|------------------------------------------|
| GitHub        | $0 (gratuito para repositorios privados) |
| Claude API    | ~$0.05–0.15 USD por reporte              |
| Gmail SMTP    | $0 (gratuito)                            |
| **Total/mes** | **~$0.20–0.60 USD al mes**               |

---

## Preguntas frecuentes

**¿Qué pasa si ServiceNow cambia algo?**
Solo hay que actualizar `sn_fetch.py` con el nuevo campo o query.

**¿Puedo cambiar el día y hora del envío?**
Sí, en `.github/workflows/reporte_semanal.yml` cambia la línea `cron`.
Ejemplos:
- Lunes 8am Chile: `0 11 * * 1`
- Viernes 5pm Chile: `0 20 * * 5`
- Todos los días 9am Chile: `0 12 * * *`

**¿Puedo agregar más destinatarios?**
Sí, edita el secreto `EMAIL_RECIPIENTS` en GitHub y agrega más correos separados por coma.

**¿Puedo correrlo manualmente en cualquier momento?**
Sí, desde GitHub Actions → "Run workflow".
