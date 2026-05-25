# Uso Diario De job-watcher

Esta guia resume como usar el proyecto en el dia a dia desde Windows.

## Requisitos Previos

- Tener Python instalado.
- Tener el entorno virtual `.venv` creado en la raiz del proyecto.
- Tener dependencias instaladas con `pip install -r requirements.txt`.
- Tener un archivo local `.env` basado en `.env.example`.
- Tener `config.yaml` revisado antes de iniciar el worker.

El archivo `.env` no se sube a Git y no debe contenerse en capturas o mensajes
compartidos.

## Activar .venv

Desde PowerShell, en la raiz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activacion, puedes usar el script de arranque con:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_worker.ps1
```

## Configurar .env

Crea un archivo `.env` local usando `.env.example` como plantilla.

Variables importantes:

```env
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USE_SSL=true

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Notas:
- `EMAIL_PASSWORD` debe ser una contrasena de aplicacion o mecanismo seguro
  equivalente, no una contrasena personal escrita en el repositorio.
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` solo se necesitan si vas a enviar
  notificaciones por Telegram.

## Revisar config.yaml

Antes de iniciar el worker, revisa estas secciones:

```yaml
worker_settings:
  enabled: true
  interval_minutes: 5
  run_once: false

email_settings:
  enabled: true

notification_settings:
  enabled: true
  channels:
    console: true
    telegram: true
```

Para una prueba corta, puedes usar:

```yaml
worker_settings:
  run_once: true
```

Para dejar el worker corriendo, usa:

```yaml
worker_settings:
  run_once: false
```

## Iniciar Worker Con PowerShell

Desde la raiz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_worker.ps1
```

Este script valida `.venv`, valida `.env`, activa el entorno virtual y ejecuta
`scripts/run_job_watcher.py`.

## Iniciar Worker Con .bat

Para uso con doble clic en Windows:

```text
scripts/start_worker.bat
```

La ventana queda abierta al final para que puedas leer errores o mensajes.

## Detener El Worker

En la terminal donde esta corriendo el worker:

```text
Ctrl + C
```

El worker debe mostrar:

```text
Worker detenido manualmente.
```

## Revisar Logs

Los logs locales quedan en:

```text
logs/worker.log
logs/errors.log
```

Uso sugerido:
- `logs/worker.log`: revisar ciclos, correos leidos, ofertas guardadas y
  notificaciones.
- `logs/errors.log`: revisar errores de IMAP, Telegram, configuracion o parsing.

Los archivos `.log` estan ignorados por Git.

## Exportar CSV Manualmente

Para generar un CSV desde ofertas reales ya guardadas:

```powershell
python scripts/export_saved_jobs.py
```

El archivo generado es:

```text
output/ofertas_reales_priorizadas.csv
```

Ese CSV esta ignorado por Git.

## Probar Telegram

1. Crea o revisa tu bot de Telegram.
2. Guarda `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`.
3. En `config.yaml`, activa temporalmente:

```yaml
notification_settings:
  enabled: true
  channels:
    telegram: true
```

4. Ejecuta:

```powershell
python scripts/notify_saved_jobs.py
```

Si solo quieres probar notificaciones guardadas, este script no lee correos ni
usa IMAP.

## Errores Comunes

### Falta .venv

Mensaje probable:

```text
No se encontro la carpeta .venv.
```

Solucion:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Falta .env

Mensaje probable:

```text
No se encontro el archivo .env local.
```

Solucion: crea `.env` desde `.env.example` y completa solo tus valores locales.

### Gmail No Conecta

Revisa:
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `EMAIL_IMAP_SERVER`
- `EMAIL_IMAP_PORT`
- `EMAIL_USE_SSL`
- que IMAP este habilitado en la cuenta.

### Telegram No Envia

Revisa:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- que `notification_settings.channels.telegram` este en `true`.
- `logs/errors.log` para ver el error.

### No Llegan Notificaciones

Revisa:
- que existan ofertas guardadas con `email_type: job_alert`.
- `notification_settings.strict_min_score`.
- `notification_settings.skip_generic_titles`.
- `notification_settings.skip_non_target_areas`.
- `logs/worker.log` para ver cuantas ofertas pasaron el filtro.

### El Worker No Hace Nada

Revisa:

```yaml
worker_settings:
  enabled: true

email_settings:
  enabled: true
```

Tambien revisa si el checkpoint ya marco esos correos como procesados. El
checkpoint local esta en:

```text
data/email_checkpoint.json
```

No lo subas a Git.
