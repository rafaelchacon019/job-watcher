# job-watcher

Asistente local para revisar alertas de empleo, guardar ofertas encontradas,
puntuar coincidencias segun un perfil tecnico y ayudar a priorizar
postulaciones.

## Alcance inicial

Este proyecto esta en una fase base. Por ahora solo contiene la estructura
inicial y archivos guia para trabajar por etapas.

Importante: este proyecto no automatiza postulaciones, no automatiza login en
plataformas y no incluye credenciales reales.

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
- `src/`: modulos principales que se implementaran por fases.
- `data/`: espacio para datos locales permitidos.
- `output/`: espacio para reportes generados.
- `tests/`: espacio para pruebas futuras.

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
