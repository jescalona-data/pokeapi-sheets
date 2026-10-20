from pathlib import Path

import gspread
import pandas as pd
import requests

# --- Configuración ---
BASE_URL = "https://pokeapi.co/api/v2/pokemon"
LIMITE = 150  # 151 = primera generación completa
NOMBRE_SHEET = "pokemon-etl-demo"
CREDENCIALES = Path(__file__).parent / "credentials.json"


def extraer(limite):
    """Pide la lista de Pokémon y luego el detalle de cada uno."""
    sesion = requests.Session()  # reutiliza la conexión, más rápido
    lista = sesion.get(BASE_URL, params={"limit": limite}, timeout=10).json()
    filas = []
    for i, item in enumerate(lista["results"], start=1):
        d = sesion.get(item["url"], timeout=10).json()
        stats = {s["stat"]["name"]: s["base_stat"] for s in d["stats"]}
        filas.append({
            "id": d["id"],
            "nombre": d["name"],
            "altura": d["height"],
            "peso": d["weight"],
            "tipo_principal": d["types"][0]["type"]["name"],
            "hp": stats["hp"],
            "ataque": stats["attack"],
            "defensa": stats["defense"],
            "velocidad": stats["speed"],
        })
        if i % 25 == 0:
            print(f"  {i}/{limite} descargados...")
    return pd.DataFrame(filas)


def resumir(df):
    """Indicador: promedio de stats por tipo, con la cantidad de registros."""
    return (
        df.groupby("tipo_principal")
        .agg(n=("id", "count"), hp=("hp", "mean"), ataque=("ataque", "mean"),
             defensa=("defensa", "mean"), velocidad=("velocidad", "mean"))
        .round(1)
        .reset_index()
    )


def escribir(sh, nombre_hoja, df):
    """Escribe un DataFrame en una pestaña (la crea si no existe)."""
    datos = [df.columns.tolist()] + df.astype(object).values.tolist()
    try:
        ws = sh.worksheet(nombre_hoja)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=nombre_hoja, rows=len(datos), cols=len(datos[0]))
    ws.resize(rows=len(datos), cols=len(datos[0]))
    ws.update(values=datos, range_name="A1")


def main():
    df = extraer(LIMITE)
    resumen = resumir(df)

    gc = gspread.service_account(filename=str(CREDENCIALES))
    try:
        sh = gc.open(NOMBRE_SHEET)
    except gspread.SpreadsheetNotFound:
        raise SystemExit(
            f"No encuentro '{NOMBRE_SHEET}'. "
            "¿La compartiste con el client_email como Editor?"
        )

    escribir(sh, "pokemon", df)
    escribir(sh, "resumen_por_tipo", resumen)
    print(f"Listo: {len(df)} filas en 'pokemon' y {len(resumen)} en 'resumen_por_tipo'.")


if __name__ == "__main__":
    main()