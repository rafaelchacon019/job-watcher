# job-watcher

Asistente local para revisar alertas de empleo, guardar ofertas encontradas,
puntuar coincidencias segun un perfil tecnico y ayudar a priorizar
postulaciones.

## Alcance inicial

Este proyecto esta en Fase 1. Por ahora trabaja con ofertas locales de prueba,
calcula un puntaje simple, guarda resultados en SQLite y genera un CSV.

Importante: este proyecto no automatiza postulaciones, no automatiza login en
plataformas, no lee correos reales y no incluye credenciales reales.

## Estructura

```text
job-watcher/
|-- main.py
|-- config.yaml
|-- .env.example
|-- requirements.txt
|-- src/
|-- data/
|-- output/
`-- tests/
```

- `main.py`: punto de entrada inicial del proyecto.
- `config.yaml`: configuracion editable del asistente.
- `.env.example`: ejemplo de variables de entorno sin datos reales.
- `requirements.txt`: dependencias iniciales del proyecto.
- `src/`: modulos principales del motor local.
- `data/`: guarda la base SQLite local `jobs.db`.
- `output/`: guarda el reporte `ofertas_priorizadas.csv`.
- `tests/`: espacio para pruebas futuras.

## Fase 1

La Fase 1 ejecuta un flujo local completo:

1. Lee `config.yaml`.
2. Carga ofertas de prueba desde `src/parser.py`.
3. Calcula puntajes con `src/scorer.py`.
4. Guarda las ofertas en `data/jobs.db`.
5. Exporta un reporte CSV en `output/ofertas_priorizadas.csv`.
6. Muestra un resumen ordenado por puntaje en consola.

Las tecnologias Python y PL/SQL se manejan con una regla de compatibilidad por
nivel: solo suman puntos fuertes cuando la oferta tambien menciona un nivel
compatible o experiencia baja. Si aparecen en ofertas de mayor seniority, no se
priorizan por esas tecnologias.

## Fase 2.1

Esta fase solo deja preparada la configuracion para una lectura futura de
correos de alertas laborales mediante IMAP. Todavia no se leen correos reales.

`.env.example` es solo una plantilla. Cuando se use Gmail o IMAP, se debera
crear un archivo local `.env` que no se sube a Git. Para Gmail puede requerirse
IMAP habilitado y un metodo seguro de autenticacion, como una contrasena de
aplicacion o mecanismo equivalente.

## Fase 2.2

Existe un modulo inicial en `src/email_reader.py` para leer metadatos de
correos por IMAP en una fase futura. Todavia no esta conectado a `main.py` y no
lee correos reales automaticamente. Para usarlo mas adelante se necesitara un
archivo local `.env`, que no debe subirse al repositorio.

## Prueba Manual De Correo

El script `scripts/test_email_reader.py` sirve solo para probar metadatos de
correos por IMAP. No extrae ofertas, no guarda en SQLite y no genera reportes.

Antes de usarlo, crea un archivo local `.env` basado en `.env.example`. Ese
archivo no debe subirse al repositorio. Para probar, cambia temporalmente
`email_settings.enabled` a `true` en `config.yaml`; despues de la prueba se
recomienda volverlo a `false` si todavia no se va a usar.

```powershell
python scripts/test_email_reader.py
```

## Fase 2.5

La Fase 2.5 agrega un parser inicial en `src/email_parser.py` y una prueba
manual en `scripts/test_email_parser.py`. Todavia no esta conectado al flujo
principal, no guarda ofertas reales en SQLite y no genera CSV desde correos.

Para probarlo se requiere un `.env` local y cambiar temporalmente
`email_settings.enabled` a `true`. Despues de probar se recomienda volverlo a
`false`.

```powershell
python scripts/test_email_parser.py
```

## Fase 2.5.1

Esta mejora ajusta la decodificacion de correos, clasifica cada resultado con
`email_type` y prioriza links mas utiles. Sigue siendo una prueba manual: no
esta conectada a `main.py`, no guarda en SQLite y no genera CSV.

## Fase 2.6

La Fase 2.6 permite probar scoring sobre correos reales ya parseados usando
`scripts/test_email_scoring.py`. Todavia no esta conectada a `main.py`, no
guarda en base de datos y no genera CSV.

Para probar se requiere un `.env` local y cambiar temporalmente
`email_settings.enabled` a `true`. Despues de probar se recomienda volverlo a
`false`.

```powershell
python scripts/test_email_scoring.py
```

## Fase 2.7

La Fase 2.7 agrega un guardado manual de ofertas puntuadas con
`scripts/save_scored_email_jobs.py`. Todavia no esta conectada a `main.py` y no
genera CSV desde correos reales. Guarda solo ofertas tipo `job_alert` con score
mayor a 0, usando el link para evitar duplicados.

Para probar se requiere un `.env` local y cambiar temporalmente
`email_settings.enabled` a `true`. Despues de probar se recomienda volverlo a
`false`.

```powershell
python scripts/save_scored_email_jobs.py
```

## Fase 2.8

La Fase 2.8 permite exportar ofertas reales ya guardadas usando
`scripts/export_saved_jobs.py`. No lee correos, no usa IMAP y no guarda nuevas
ofertas. Exporta solo registros con `email_type` igual a `job_alert` y genera
`output/ofertas_reales_priorizadas.csv`, que esta ignorado por Git.

```powershell
python scripts/export_saved_jobs.py
```

## Fase 2.9.1

La Fase 2.9.1 permite probar notificaciones locales por consola con
`scripts/notify_saved_jobs.py`. No lee correos, no envia Telegram y usa ofertas
ya guardadas en SQLite.

Para probar temporalmente, cambia `notification_settings.enabled` a `true` en
`config.yaml`. Despues de probar se recomienda volverlo a `false`.

```powershell
python scripts/notify_saved_jobs.py
```

## Fase 2.9.2

La Fase 2.9.2 permite enviar por Telegram las mismas ofertas prioritarias que
se muestran por consola. Para usarlo se debe crear un bot y guardar
`TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en un `.env` local; ese archivo no se
sube al repositorio.

Para probar temporalmente, cambia `notification_settings.enabled` a `true` y
`notification_settings.channels.telegram` a `true`. Despues de probar se
recomienda volver ambos a `false` cuando no se vayan a usar.

```powershell
python scripts/notify_saved_jobs.py
```

## Fase 3.1

La Fase 3.1 agrega un worker local en `scripts/run_job_watcher.py`. El worker
puede leer correos, parsear ofertas, calcular puntajes, guardar ofertas nuevas
y notificar por consola o Telegram segun la configuracion. No esta conectado a
`main.py` y no genera CSV.

Para probar temporalmente, activa `worker_settings.enabled` y
`email_settings.enabled` en `config.yaml`. Si `worker_settings.run_once` esta en
`true`, ejecuta una sola pasada; si esta en `false`, repite cada
`worker_settings.interval_minutes`.

```powershell
python scripts/run_job_watcher.py
```

## Fase 3.2

La Fase 3.2 agrega un checkpoint local en `data/email_checkpoint.json` para que
el worker ignore correos ya procesados. El archivo queda ignorado por Git y
guarda la ultima ejecucion junto con una lista limitada de `message_id`
procesados.

## Fase 3.3

La Fase 3.3 mejora el modo continuo del worker. Para probarlo, activa
`worker_settings.enabled`, deja `worker_settings.run_once` en `false` y ejecuta
el script. El worker repetira el ciclo cada `worker_settings.interval_minutes`
y se puede detener con `Ctrl + C`.

```powershell
python scripts/run_job_watcher.py
```

## Fase 3.4

La Fase 3.4 agrega logs persistentes para revisar ejecuciones del worker en
`logs/worker.log` y errores en `logs/errors.log`. Los archivos `.log` estan
ignorados por Git.

## Fase 3.5.1

La Fase 3.5.1 agrega scripts de arranque para Windows. Antes de usarlos, revisa
que `config.yaml` tenga activos `worker_settings.enabled`,
`email_settings.enabled` y `notification_settings.enabled`.

En PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_worker.ps1
```

Con doble clic en Windows:

```text
scripts/start_worker.bat
```

Para detener el worker usa `Ctrl + C`.

## Uso Diario

La guia practica para uso diario esta en [docs/USO_DIARIO.md](docs/USO_DIARIO.md).

## Instalacion local

Crear el entorno virtual:

```powershell
python -m venv .venv
```

Activar el entorno virtual en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Ejecutar la aplicacion inicial:

```powershell
python main.py
```
