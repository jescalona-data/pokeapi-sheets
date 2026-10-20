from pathlib import Path

import gspread
import pandas as pd
import requests

# --- Configuración ---
BASE_URL = "https://pokeapi.co/api/v2/pokemon"
LIMITE = 151  # primera generación completa
NOMBRE_SHEET = "pokemon-etl-demo"
CREDENCIALES = Path(__file__).parent / "credentials.json"

# --- Paleta del Sheet ---
AZUL_OSCURO = {"red": 0.11, "green": 0.22, "blue": 0.36}
AZUL_CLARO = {"red": 0.93, "green": 0.96, "blue": 0.99}
BLANCO = {"red": 1, "green": 1, "blue": 1}
VERDE = {"red": 0.34, "green": 0.73, "blue": 0.54}


def extraer(limite):
    """Pide la lista de Pokémon y luego el detalle de cada uno."""
    sesion = requests.Session()
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


def preparar_hoja(sh, nombre, filas, cols):
    """Devuelve una pestaña limpia: si ya existía, la recrea sin formato viejo."""
    try:
        vieja = sh.worksheet(nombre)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=nombre, rows=filas, cols=cols)
    nueva = sh.add_worksheet(title=f"{nombre}_nueva", rows=filas, cols=cols)
    sh.del_worksheet(vieja)
    nueva.update_title(nombre)
    return nueva


def formatear(sh, ws, n_filas, n_cols, columnas_color=(), patron_numero=None):
    """Aplica estilo: encabezado, filas alternadas, filtro y mapa de calor."""
    sid = ws.id
    encabezado = {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": 0, "endColumnIndex": n_cols}
    cuerpo = {"sheetId": sid, "startRowIndex": 1, "endRowIndex": n_filas,
              "startColumnIndex": 0, "endColumnIndex": n_cols}

    pedidos = [
        # Encabezado: fondo azul oscuro, texto blanco en negrita
        {"repeatCell": {
            "range": encabezado,
            "cell": {"userEnteredFormat": {
                "backgroundColor": AZUL_OSCURO,
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "textFormat": {"bold": True, "foregroundColor": BLANCO, "fontSize": 11},
            }},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,"
                      "verticalAlignment,textFormat)",
        }},
        # Cuerpo centrado
        {"repeatCell": {
            "range": cuerpo,
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)",
        }},
        # Fila de encabezado fija y sin líneas de cuadrícula
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {
                "frozenRowCount": 1, "hideGridlines": True}},
            "fields": "gridProperties(frozenRowCount,hideGridlines)",
        }},
        # Filas alternadas
        {"addBanding": {"bandedRange": {
            "range": cuerpo,
            "rowProperties": {"firstBandColor": BLANCO, "secondBandColor": AZUL_CLARO},
        }}},
        # Filtros en el encabezado
        {"setBasicFilter": {"filter": {"range": {
            "sheetId": sid, "startRowIndex": 0, "endRowIndex": n_filas,
            "startColumnIndex": 0, "endColumnIndex": n_cols}}}},
        # Alto del encabezado y ancho de columnas
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 34}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": n_cols},
            "properties": {"pixelSize": 120}, "fields": "pixelSize"}},
    ]

    # Mapa de calor por columna (blanco -> verde) y formato numérico opcional
    for c in columnas_color:
        rango_col = {"sheetId": sid, "startRowIndex": 1, "endRowIndex": n_filas,
                     "startColumnIndex": c, "endColumnIndex": c + 1}
        pedidos.append({"addConditionalFormatRule": {"rule": {
            "ranges": [rango_col],
            "gradientRule": {
                "minpoint": {"type": "MIN", "color": BLANCO},
                "maxpoint": {"type": "MAX", "color": VERDE},
            }}, "index": 0}})
        if patron_numero:
            pedidos.append({"repeatCell": {
                "range": rango_col,
                "cell": {"userEnteredFormat": {
                    "numberFormat": {"type": "NUMBER", "pattern": patron_numero}}},
                "fields": "userEnteredFormat.numberFormat",
            }})

    sh.batch_update({"requests": pedidos})


def escribir(sh, nombre_hoja, df, columnas_color=(), patron_numero=None):
    """Escribe un DataFrame en una pestaña y le aplica formato."""
    datos = [df.columns.tolist()] + df.astype(object).values.tolist()
    n_filas, n_cols = len(datos), len(datos[0])
    ws = preparar_hoja(sh, nombre_hoja, n_filas, n_cols)
    ws.update(values=datos, range_name="A1")
    formatear(sh, ws, n_filas, n_cols, columnas_color, patron_numero)


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

    escribir(sh, "pokemon", df, columnas_color=[5, 6, 7, 8])
    escribir(sh, "resumen_por_tipo", resumen,
             columnas_color=[2, 3, 4, 5], patron_numero="0.0")
    print(f"Listo: {len(df)} filas en 'pokemon' y {len(resumen)} en 'resumen_por_tipo'.")


if __name__ == "__main__":
    main()