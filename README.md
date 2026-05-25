# job-watcher

Asistente local para revisar alertas de empleo, convertir correos en posibles
ofertas, puntuar coincidencias segun un perfil tecnico y ayudar a priorizar
postulaciones.

El proyecto no automatiza postulaciones, no automatiza login en plataformas, no
hace scraping y no incluye credenciales reales.

## Que Hace

job-watcher ejecuta un flujo local para revisar alertas laborales recibidas por
correo y guardar las ofertas que parecen relevantes:

```text
correo IMAP -> parser -> scoring -> SQLite -> Telegram/logs
                                      |
                                      `-> CSV manual
```

El worker puede correr una sola vez o de forma continua, usando checkpoint para
evitar reprocesar correos ya revisados.

## Stack

- Python
- SQLite
- IMAP con libreria estandar `imaplib`
- BeautifulSoup
- pandas
- PyYAML
- python-dotenv
- requests
- Telegram Bot API
- logging estandar de Python
- Endpoints publicos ATS tipo Greenhouse y Lever

## Estructura Principal

```text
job-watcher/
|-- main.py
|-- config.yaml
|-- .env.example
|-- requirements.txt
|-- README.md
|-- docs/
|   `-- USO_DIARIO.md
|-- scripts/
|   |-- run_job_watcher.py
|   |-- start_worker.ps1
|   |-- start_worker.bat
|   |-- save_scored_email_jobs.py
|   |-- export_saved_jobs.py
|   `-- notify_saved_jobs.py
|-- src/
|   |-- email_reader.py
|   |-- email_parser.py
|   |-- scorer.py
|   |-- database.py
|   |-- notifier.py
|   |-- email_checkpoint.py
|   |-- deduplication.py
|   |-- logger.py
|   `-- sources/
|-- data/
|-- output/
|-- logs/
`-- tests/
```

- `config.yaml`: configuracion editable del proyecto.
- `.env.example`: plantilla de variables de entorno sin secretos reales.
- `docs/USO_DIARIO.md`: guia practica para operar el MVP.
- `scripts/run_job_watcher.py`: worker automatico local.
- `scripts/start_worker.ps1`: arranque facil desde PowerShell.
- `scripts/start_worker.bat`: arranque facil con doble clic en Windows.
- `src/email_reader.py`: lectura IMAP.
- `src/email_parser.py`: parser inicial de correos laborales.
- `src/scorer.py`: motor de puntaje.
- `src/database.py`: persistencia en SQLite.
- `src/notifier.py`: notificaciones por consola y Telegram.
- `src/email_checkpoint.py`: checkpoint de correos procesados.
- `src/deduplication.py`: huellas para detectar ofertas repetidas entre fuentes.
- `src/logger.py`: logs persistentes del worker.
- `src/sources/`: fuentes ATS publicas permitidas.

## Inicio Rapido

Crear y activar entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Crear `.env` local desde `.env.example` y revisar `config.yaml`.

Para iniciar el worker con PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_worker.ps1
```

Para iniciar con doble clic en Windows:

```text
scripts/start_worker.bat
```

Para detener el worker:

```text
Ctrl + C
```

## Configuracion Minima Para Worker

Antes de correr el worker real, revisa en `config.yaml`:

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

Para una prueba corta, usa `worker_settings.run_once: true`.

## Documentacion

La guia practica de operacion diaria esta en
[docs/USO_DIARIO.md](docs/USO_DIARIO.md).

## Estado Actual Del MVP

- [x] Worker automatico local
- [x] Lectura de correos por IMAP
- [x] Parser inicial de alertas laborales
- [x] Scoring por tecnologias, nivel, ubicacion, modalidad y reglas especiales
- [x] Persistencia en SQLite
- [x] Exportacion manual a CSV
- [x] Notificaciones por consola y Telegram
- [x] Checkpoint de correos procesados
- [x] Logs persistentes del worker
- [x] Ejecucion continua estable
- [x] Scripts de arranque para Windows

## Fase 4.1

La Fase 4.1 agrega una base manual para consultar fuentes ATS publicas como
Greenhouse y Lever. Esta prueba no toca LinkedIn ni Computrabajo directo, no
guarda en SQLite y no envia Telegram.

La Fase 4.2 aplica filtros por keywords, exclusiones y scoring con
`calculate_score()` para ordenar mejor los resultados ATS en la prueba manual.

La Fase 4.3 permite que el worker tambien consulte ATS cuando
`ats_sources.enabled` esta en `true`. En ese modo guarda solo ofertas nuevas,
usa el link para evitar duplicados y notifica solo las nuevas ofertas que pasen
los filtros de notificacion.

La Fase 4.4 agrega deduplicacion por `fingerprint` para detectar ofertas
similares aunque vengan de correo y ATS con links distintos.

Para probar mas adelante, configura empresas en `ats_sources` y ejecuta:

```powershell
python scripts/test_ats_sources.py
```

## Archivos Locales Ignorados

Estos archivos son locales y no deben subirse a Git:

- `.env`
- `.venv/`
- `data/jobs.db`
- `data/email_checkpoint.json`
- `logs/*.log`
- `output/*.csv`
- `__pycache__/`

## Roadmap Resumido

- Ampliar fuentes compatibles sin scraping ni login automatizado.
- Incorporar IA/OpenAI para analisis mas inteligente de ofertas.
- Mejorar scoring con pesos configurables y aprendizaje manual.
- Detectar mejor seniority, salario, modalidad y tecnologias en textos reales.
- Crear reportes mas completos para priorizar postulaciones.
- Agregar pruebas automatizadas para parser, scoring y worker.
