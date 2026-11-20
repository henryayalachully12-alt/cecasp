"""Descarga el CSV de la estación desde dpsproserver.com (DPS-Promatic) y actualiza data/lecturas.csv y data/reciente.json."""
import csv, io, json, os, time
import datetime as dt
from zoneinfo import ZoneInfo
import requests

STATION = os.getenv("STATION", "PERU")   # nombre de la estación (página pública: https://dpsproserver.com/station/1151)
URL = "https://dpsproserver.com/grep.php"   # descarga del CSV; respeta el rango de fechas que se le pide
TZ_SERVIDOR = ZoneInfo("Europe/Rome")   # el servidor nuevo entrega la fecha y hora de Italia
TZ_LOCAL = ZoneInfo("America/Lima")     # se guarda en hora de Perú, igual que el historial anterior
COLS = ["smsc","si","was","press","wmins","wgust","dwgust","leaf","wdir","wdsd","sun","temp","dmintemp",
        "dmaxtemp","soilt","rf","drf","soilw","dp","rh","dminrh","dmaxrh","pwr","vbatt"]
PANTALLA = ["ts"] + COLS   # todos los parámetros que envía la estación
DIAS = 35   # días que la página puede mostrar en pantalla (el historial completo queda en lecturas.csv)
BAJAR = 7   # días que se piden en cada actualización (recupera solas las lecturas que falten)

def _descargar_una_vez(desde, hasta, limite):
    rango = {"tcsid": STATION, "aada": desde.year, "mmda": desde.month, "ggda": desde.day,
             "aaa": hasta.year, "mma": hasta.month, "gga": hasta.day}
    r = requests.get(URL, params=rango, headers={"User-Agent": "EstacionMeteoProyecto/1.0"}, timeout=(10, limite))
    r.raise_for_status()
    if "$DPTAW" not in r.text and r.text.strip(): raise RuntimeError("el servidor no devolvió un CSV de la estación")
    return r.text

def descargar(desde=None, hasta=None, intentos=3, limite=60):
    """Pide las lecturas entre dos fechas (en el calendario del servidor). Por defecto, los últimos BAJAR días.
    Si el servidor está lento o falla, reintenta en vez de quedarse colgado."""
    hasta = hasta or dt.datetime.now(TZ_SERVIDOR).date()
    desde = desde or hasta - dt.timedelta(days=BAJAR)
    ultimo = None
    for i in range(1, intentos + 1):
        try:
            return _descargar_una_vez(desde, hasta, limite)
        except Exception as e:
            ultimo = e; print(f"Intento {i}/{intentos} falló: {e}")
            time.sleep(3)
    raise SystemExit(f"dpsproserver.com no respondió tras {intentos} intentos: {ultimo}")

def leer_dps(texto):
    """Cada fila: "$DPTAW",fecha,hora,estación, 24 valores en el orden de COLS, suma de control.
    La fecha y hora vienen en hora de Italia y se pasan a hora de Perú."""
    for f in csv.reader(io.StringIO(texto)):
        if len(f) < 4 + len(COLS) or f[0] != "$DPTAW" or f[3] != STATION: continue
        italia = dt.datetime.strptime(f[1] + " " + f[2], "%Y/%m/%d %H:%M").replace(tzinfo=TZ_SERVIDOR)
        ts = italia.astimezone(TZ_LOCAL).replace(tzinfo=None).isoformat(timespec="minutes")
        yield {"ts": ts, **dict(zip(COLS, (v.strip() for v in f[4:4 + len(COLS)])))}

def numero(v):
    if v == "": return None
    try: return float(v)
    except ValueError: return v

def main():
    os.makedirs("data", exist_ok=True)
    ruta = "data/lecturas.csv"
    filas = {}
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f): filas[r["ts"]] = r
    nuevas = 0
    for r in leer_dps(descargar()):
        if r["ts"] not in filas:
            nuevas += 1; filas[r["ts"]] = r
    try:   # si la página pide columnas nuevas, se reescribe aunque no haya lecturas nuevas
        al_dia = json.load(open("data/reciente.json", encoding="utf-8"))["cols"] == PANTALLA
    except Exception:
        al_dia = False
    if not nuevas and al_dia:
        print("Sin lecturas nuevas"); return
    guardar(filas)
    print(nuevas, "lecturas nuevas; total", len(filas))

def guardar(filas):
    """Escribe el historial completo (lecturas.csv) y la ventana reciente que lee la página (reciente.json)."""
    orden = sorted(filas)
    with open("data/lecturas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["ts"] + COLS); w.writeheader()
        for k in orden: w.writerow(filas[k])
    corte = (dt.datetime.fromisoformat(orden[-1]) - dt.timedelta(days=DIAS)).isoformat(timespec="minutes")
    rows = [[k] + [numero(filas[k][c]) for c in PANTALLA[1:]] for k in orden if k >= corte]
    with open("data/reciente.json", "w", encoding="utf-8") as f:
        json.dump({"cols": PANTALLA, "rows": rows}, f, separators=(",", ":"))
    import eto; eto.main()   # recalcula data/diario.csv (ETo diaria FAO-56) con el historial completo

if __name__ == "__main__":
    main()
