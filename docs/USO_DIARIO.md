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

## Checklist Antes De Iniciar Worker

- Confirmar que estas en la raiz del proyecto.
- Confirmar que existe `.venv`.
- Confirmar que existe `.env`.
- Confirmar que `worker_settings.enabled` esta en `true`.
- Confirmar que `email_settings.enabled` esta en `true`.
- Confirmar que `notification_settings.enabled` esta en `true` si quieres alertas.
- Confirmar si quieres `worker_settings.run_once: true` para prueba corta o
  `false` para modo continuo.
- Confirmar que `logs/worker.log` y `logs/errors.log` no estan abiertos en modo
  bloqueo por otro programa.
- Confirmar que no vas a subir `.env`, `data/jobs.db`, `data/email_checkpoint.json`
  ni archivos de `logs/` u `output/`.

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

## Checklist Antes De Hacer Commit

- Ejecutar `git status`.
- Revisar que no aparezca `.env`.
- Revisar que no aparezca `.venv/`.
- Revisar que no aparezca `data/jobs.db`.
- Revisar que no aparezca `data/email_checkpoint.json`.
- Revisar que no aparezcan archivos `logs/*.log`.
- Revisar que no aparezcan archivos `output/*.csv`.
- Revisar que no aparezcan carpetas `__pycache__/`.
- Revisar que `config.yaml` no quede con valores activos por accidente si no
  quieres subirlos asi.
- Revisar que no haya tokens, correos, contrasenas ni datos sensibles en los
  archivos modificados.

## Checklist Si Telegram Deja De Funcionar

- Confirmar que `TELEGRAM_BOT_TOKEN` existe en `.env`.
- Confirmar que `TELEGRAM_CHAT_ID` existe en `.env`.
- Confirmar que `notification_settings.enabled` esta en `true`.
- Confirmar que `notification_settings.channels.telegram` esta en `true`.
- Ejecutar una prueba manual con `python scripts/notify_saved_jobs.py`.
- Revisar `logs/errors.log`.
- Revisar que el bot no haya sido bloqueado o eliminado del chat.
- Revisar que existan ofertas que superen `notification_settings.strict_min_score`.

## Checklist Si IMAP Falla

- Confirmar que `EMAIL_USER` existe en `.env`.
- Confirmar que `EMAIL_PASSWORD` existe en `.env`.
- Confirmar que `EMAIL_IMAP_SERVER` y `EMAIL_IMAP_PORT` son correctos.
- Confirmar que `EMAIL_USE_SSL=true`.
- Confirmar que IMAP esta habilitado en la cuenta.
- Confirmar que la contrasena usada sea de aplicacion o mecanismo seguro
  equivalente.
- Probar metadatos con `python scripts/test_email_reader.py`.
- Revisar `logs/errors.log`.

## Checklist Si El Worker No Detecta Ofertas Nuevas

- Revisar `logs/worker.log` para ver cuantos correos leyo el ciclo.
- Revisar si `Correos ignorados por checkpoint` es alto.
- Revisar `data/email_checkpoint.json` localmente si quieres confirmar IDs
  procesados.
- Confirmar que `email_settings.days_back` no este demasiado bajo.
- Confirmar que `email_settings.max_emails` no este demasiado bajo.
- Revisar `subject_keywords`, `sender_keywords` e `ignored_keywords`.
- Confirmar que las alertas nuevas realmente llegaron al correo configurado.
- Ejecutar `python scripts/test_email_parser.py` para revisar parsing manual.
- Ejecutar `python scripts/test_email_scoring.py` para revisar scoring manual.

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
