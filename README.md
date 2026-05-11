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
