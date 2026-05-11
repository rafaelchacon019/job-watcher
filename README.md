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
