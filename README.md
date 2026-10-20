# PokéAPI → Google Sheets (pipeline ETL)

Script en Python que extrae datos de una API pública (PokéAPI), los transforma con pandas y los carga automáticamente en Google Sheets, en una pestaña de datos y otra con indicadores resumidos.


## Qué hace

1. **Extrae**: consulta la API y obtiene el detalle de 151 Pokémon.
2. **Transforma**: aplana el JSON en una tabla y calcula el promedio de stats por tipo, incluyendo la cantidad de registros (`n`) para saber qué tan representativo es cada promedio.
3. **Carga**: escribe los resultados en dos pestañas de un Google Sheet (`pokemon` y `resumen_por_tipo`).

El script se puede ejecutar varias veces: reescribe las pestañas sin duplicar datos.

## Tecnologías

- Python 3
- `requests`, `pandas`
- `gspread` (Google Sheets API) con cuenta de servicio

## Configuración

1. Crear un proyecto en Google Cloud y activar **Google Sheets API** y **Google Drive API**.
2. Crear una **cuenta de servicio**, generar una clave JSON y guardarla como `credentials.json` en la raíz del proyecto. Este archivo está en `.gitignore` y **nunca debe subirse al repositorio**.
3. Crear un Google Sheet llamado `pokemon-etl-demo` y compartirlo como **Editor** con el correo de la cuenta de servicio (campo `client_email` del JSON).

## Cómo correrlo

```bash
git clone https://github.com/jescalona-data/pokeapi-sheets.git
cd pokeapi-sheets

python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell

pip install -r requirements.txt
python pokeapi_a_sheets.py
```

## Estructura

```
pokeapi-sheets/
├── pokeapi_a_sheets.py   # extraer → transformar → cargar
├── requirements.txt
└── .gitignore            # excluye credenciales y entorno virtual
```

## Qué aprendí

- Autenticación con cuenta de servicio de Google y manejo seguro de credenciales.
- Separar un proceso en etapas (extraer, transformar, cargar) con funciones.
- Escribir resultados en Sheets de forma repetible y sin duplicar datos.
- Considerar el tamaño de la muestra al interpretar promedios.

## Próximos pasos

- Paginar para traer todos los Pokémon.
- Programar la ejecución automática (cron, GitHub Actions o n8n).
- Mover el nombre del Sheet y la cantidad de registros a variables de entorno.